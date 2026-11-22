#!/bin/bash
# Removes what install.sh set up. The project folder itself, including
# models/, and your meeting records in ~/Downloads/Backstage, are left alone.
set -uo pipefail

UUID="backstage@saiftherehman.github.io"
KEYS="org.gnome.settings-daemon.plugins.media-keys"
ENTRY="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/backstage-preview/"

echo "Background helper"
systemctl --user disable --now backstage-helper.service 2>/dev/null
rm -f "$HOME/.config/systemd/user/backstage-helper.service"
systemctl --user daemon-reload

echo "GNOME extension"
gnome-extensions disable "$UUID" 2>/dev/null
rm -f "$HOME/.local/share/gnome-shell/extensions/$UUID"
python3 -c "
import ast, subprocess
def edit(key, drop):
    current = ast.literal_eval(subprocess.check_output(['gsettings', 'get', *key], text=True).removeprefix('@as '))
    subprocess.check_call(['gsettings', 'set', *key, str([x for x in current if x != drop])])
edit(['org.gnome.shell', 'enabled-extensions'], '$UUID')
edit(['$KEYS', 'custom-keybindings'], '$ENTRY')"
gsettings reset-recursively "$KEYS.custom-keybinding:$ENTRY" 2>/dev/null

echo "Super+A back to GNOME's app grid"
gsettings reset org.gnome.shell.keybindings toggle-application-view

echo "Phone key, certificates, live screenshot and preview home"
rm -rf "$HOME/.local/state/backstage" "$HOME/.cache/backstage-preview"

echo
echo "Done. Log out and back in to clear the island from the running desktop."
echo "If you opened the phone port in ufw, remove that rule with: sudo ufw status numbered"
echo "The \"Backstage records key\" stays in the keyring so encrypted records can"
echo "still be opened; delete it in Passwords and Keys once you no longer need them."
