#!/bin/bash
# Opens a separate GNOME desktop in a window with the Backstage island running,
# to try changes without logging out. It has its own home folder, settings
# and session bus, so the real desktop is never touched. Close the window to
# finish.
#
# While it runs, the real helper is paused (both use the phone page port)
# and started again afterwards. Sessions recorded in the preview are saved
# to the normal records folder (~/Downloads/Backstage).
set -u

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
PREVIEW_HOME="$HOME/.cache/backstage-preview"
UUID="backstage@saiftherehman.github.io"

# Second stage: runs inside the private session bus started below.
if [ "${1:-}" = "--inside" ]; then
    gsettings set org.gnome.shell enabled-extensions "['$UUID']"
    gsettings set org.gnome.shell disable-user-extensions false
    gsettings set org.gnome.shell.keybindings toggle-application-view "[]"
    gsettings set org.gnome.shell welcome-dialog-last-shown-version "999"
    cd "$PROJECT/helper"
    HOME="$REAL_HOME" HF_HUB_OFFLINE=1 "$PROJECT/.venv/bin/python" -m backstage &
    HELPER=$!
    sleep 2
    gnome-shell --devkit --no-x11 --wayland-display backstage-preview
    kill "$HELPER"
    exit 0
fi

mkdir -p "$PREVIEW_HOME/.local/share/gnome-shell/extensions" "$PREVIEW_HOME/.config"
ln -sfn "$PROJECT/extension/$UUID" "$PREVIEW_HOME/.local/share/gnome-shell/extensions/$UUID"
glib-compile-schemas "$PROJECT/extension/$UUID/schemas"

# A short private runtime folder: Wayland socket paths are limited to 108 characters.
RUNTIME=$(mktemp -d /tmp/backstage-preview.XXXX)
chmod 700 "$RUNTIME"
trap 'rm -rf "$RUNTIME"; systemctl --user start backstage-helper' EXIT
systemctl --user stop backstage-helper

# Everything is set before dbus-run-session, so services it starts (like the
# settings store) also use the preview home instead of the real one.
env REAL_HOME="$HOME" \
    WAYLAND_DISPLAY="$XDG_RUNTIME_DIR/${WAYLAND_DISPLAY:-wayland-0}" \
    PIPEWIRE_RUNTIME_DIR="$XDG_RUNTIME_DIR" \
    XDG_RUNTIME_DIR="$RUNTIME" \
    HOME="$PREVIEW_HOME" \
    XDG_CONFIG_HOME="$PREVIEW_HOME/.config" \
    XDG_DATA_HOME="$PREVIEW_HOME/.local/share" \
    XDG_CACHE_HOME="$PREVIEW_HOME/.cache" \
    dbus-run-session -- "$0" --inside
