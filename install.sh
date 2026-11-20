#!/bin/bash
# Sets up Backstage on this machine. Safe to run again after changing
# config.toml (for example to fetch a different Whisper model).
set -euo pipefail

PROJECT="$(cd "$(dirname "$0")" && pwd)"
UUID="backstage@saiftherehman.github.io"
EXTENSIONS="$HOME/.local/share/gnome-shell/extensions"
UNITS="$HOME/.config/systemd/user"
PY="$PROJECT/.venv/bin/python"

echo "Python environment"
if [ ! -x "$PY" ]; then
    # --without-pip: Ubuntu ships pip system wide but not ensurepip, and the
    # system pip installs into the venv just as well.
    python3 -m venv --without-pip --system-site-packages "$PROJECT/.venv"
fi
"$PY" -m pip install -q -r "$PROJECT/requirements.txt"

echo "Speech models"
read -r WHISPER VOSK VOICE < <("$PY" -c "
import tomllib
c = tomllib.load(open('$PROJECT/config.toml', 'rb'))
print(c['speech']['whisper_model'], c['speech']['vosk_model'], c['voice']['voice'])")
mkdir -p "$PROJECT/models"
if [ ! -d "$PROJECT/models/$VOSK" ]; then
    curl -sSL -o "$PROJECT/models/$VOSK.zip" "https://alphacephei.com/vosk/models/$VOSK.zip"
    "$PY" -m zipfile -e "$PROJECT/models/$VOSK.zip" "$PROJECT/models"
    rm "$PROJECT/models/$VOSK.zip"
fi
# Piper voices live at <lang>/<lang_REGION>/<name>/<quality>/ on Hugging Face.
mkdir -p "$PROJECT/models/piper"
if [ ! -f "$PROJECT/models/piper/$VOICE.onnx" ]; then
    IFS=- read -r LOCALE NAME QUALITY <<< "$VOICE"
    BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/${LOCALE%%_*}/$LOCALE/$NAME/$QUALITY"
    for f in "$VOICE.onnx" "$VOICE.onnx.json"; do
        curl -sSL -o "$PROJECT/models/piper/$f" "$BASE/$f"
    done
fi
"$PY" -c "
from faster_whisper import download_model
download_model('$WHISPER', cache_dir='$PROJECT/models/whisper')"

echo "GNOME extension"
glib-compile-schemas "$PROJECT/extension/$UUID/schemas"
mkdir -p "$EXTENSIONS"
ln -sfn "$PROJECT/extension/$UUID" "$EXTENSIONS/$UUID"

echo "Background helper"
mkdir -p "$UNITS"
sed "s#@PROJECT@#$PROJECT#g" "$PROJECT/systemd/backstage-helper.service" > "$UNITS/backstage-helper.service"
systemctl --user daemon-reload
systemctl --user enable backstage-helper.service
systemctl --user restart backstage-helper.service

# gnome-extensions enable fails for an extension the running shell has not
# seen yet, so add it to the enabled list directly. It loads at next login.
if ! gnome-extensions enable "$UUID" 2>/dev/null; then
    "$PY" -c "
import ast, subprocess
key = ['org.gnome.shell', 'enabled-extensions']
current = ast.literal_eval(subprocess.check_output(['gsettings', 'get', *key], text=True).removeprefix('@as '))
if '$UUID' not in current:
    subprocess.check_call(['gsettings', 'set', *key, str(current + ['$UUID'])])"
fi
echo "Shortcut for the preview window (Super+Alt+P)"
# A GNOME custom shortcut; other custom shortcuts in the list are kept.
KEYS="org.gnome.settings-daemon.plugins.media-keys"
ENTRY="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/backstage-preview/"
"$PY" -c "
import ast, subprocess
key = ['$KEYS', 'custom-keybindings']
current = ast.literal_eval(subprocess.check_output(['gsettings', 'get', *key], text=True).removeprefix('@as '))
if '$ENTRY' not in current:
    subprocess.check_call(['gsettings', 'set', *key, str(current + ['$ENTRY'])])"
gsettings set "$KEYS.custom-keybinding:$ENTRY" name "Backstage preview window"
gsettings set "$KEYS.custom-keybinding:$ENTRY" command "$PROJECT/tools/preview.sh"
gsettings set "$KEYS.custom-keybinding:$ENTRY" binding "<Super><Alt>p"

echo
echo "Done. If the island does not appear, log out and back in once:"
echo "GNOME on Wayland only loads new extensions at login."
