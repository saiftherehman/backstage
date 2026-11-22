# Troubleshooting

## The island does not appear

- After the first install, log out and back in once. GNOME on Wayland only
  loads new extensions at login.
- Check it is enabled: `gnome-extensions info backstage@saiftherehman.github.io`
- Look for errors: `journalctl --user -b /usr/bin/gnome-shell | grep -i backstage`
- Try it in the preview window (`Super+Alt+P`) to see if the problem is the
  extension or your desktop.

## "Helper not running"

```bash
systemctl --user status backstage-helper
journalctl --user -u backstage-helper -n 50
systemctl --user restart backstage-helper
```

## "No microphone found"

PipeWire has no input device. Check Settings > Sound > Input, or
`wpctl status` (look under Sources). Some laptop sound cards start on an
output-only profile; pick a profile with input in Settings > Sound. Without a
microphone, only the other people are transcribed and the teleprompter cannot
follow you.

## The teleprompter does not follow me

- Make sure a teleprompter session is running (red dot, timer in the pill).
- Speak the script words; it matches what you say against the next 40 words.
  If you skipped ahead further, press **Next** a few times.
- Lower `match_score` in `config.toml` (for example to 65) if it is too
  strict for your accent or microphone.

## The assistant does not answer

- The screen must change and then stay still for one screenshot. Press
  `Super+A` to analyse right away.
- Check an AI tool is signed in: the AI button on the Assistant tab should
  show a name, not "No AI tool signed in". For Claude Code, run `claude` once
  in a terminal and sign in.
- Errors show in the Assistant tab. More detail:
  `journalctl --user -u backstage-helper -n 50`

## Answers use too much of my AI plan

- Raise `min_screen_change` (for example to 0.05) so small changes are ignored.
- Raise `watch_interval` (for example to 4).
- Use a cheaper model: `claude = "haiku"` under `[assistant.models]`.
- Turn off `summary_on_stop`.

## The phone cannot open the page

- The phone must be on the same Wi-Fi as the laptop, not mobile data.
- ufw blocks it until allowed; see the firewall section in
  [privacy and security](privacy-and-security.md).
- Guest and office networks often stop devices from reaching each other
  ("client isolation"). Try a home network or a phone hotspot with the laptop
  connected to it.
- If the laptop's address changed, reopen the Phone tab: the QR code updates.
- An old bookmark starting with `http://` no longer works. The page is HTTPS
  now; scan the QR code again.

## The phone says the connection is not private

Expected on the first visit, and again whenever the laptop's address changes,
until the laptop's certificate is installed on the phone. Check that the
fingerprint in the warning's certificate details matches the one on the
island's Phone tab, then continue. To stop the warning for good, install the
certificate; steps in [privacy and security](privacy-and-security.md#phone-page).

If the certificate was installed and the warning is back, the certificates
were made again (for example after deleting `~/.local/state/backstage/tls/`).
Remove the old one from the phone and install the new one.

## The assistant says "Paused" or "Not sending the screen"

- "Paused": press **Resume** on the Assistant tab or `Super+Alt+H`.
- "Not sending the screen: <app> is in front": that window matches an entry
  in `[privacy] private_windows`. Switch to another window, or remove the
  entry from `config.toml` if it matches more than you meant (for example
  `"bank"` also matches any window title with "bank" in it).

## An answer starts with "Check this answer"

Text on the screen may have tried to steer the AI, or the screen is about
prompts or instructions. Read the answer with care. To change what counts,
edit `STEERED_PATTERNS` at the top of `helper/backstage/assistant.py`.

## "Only GNOME Shell may use the Backstage helper"

The helper refuses calls from any program but GNOME Shell. For testing with
`gdbus` from a terminal, run the helper by hand with `BACKSTAGE_ANY_CALLER=1`
(see [development](development.md)). If GNOME Shell itself is refused, check
where it lives with `readlink /proc/$(pgrep -x gnome-shell)/exe` and add that
path to `ALLOWED_PROGRAMS` in `helper/backstage/service.py`.

## Encrypted records

- "Could not encrypt": the keyring may be locked or missing. Open Passwords
  and Keys and unlock the Login keyring, then restart the helper; folders left
  plain are encrypted when it starts.
- `tools/records.sh open` says there is no key: the "Backstage records key"
  entry is gone from the keyring. Without it the records cannot be opened;
  restore the key from your copy into the keyring (attribute `purpose` =
  `records`).

## Answers are not read aloud

They are only read aloud during an **entire-screen** share, and only when the
meeting cannot hear your microphone. Muting inside the meeting app does not
count; mute with the keyboard microphone key or GNOME's sound menu. To always
read aloud during a full share, set `speak_answers = "always"`.

## The other people's words appear twice

Your microphone hears the speakers. Use headphones.

## Super+A opens the app grid

The GNOME default was not turned off. Run `./install.sh` again, or:

```bash
gsettings set org.gnome.shell.keybindings toggle-application-view "[]"
```

## Undo everything

```bash
./uninstall.sh
```

It removes the service, the extension, the shortcuts and the phone files, and
gives `Super+A` back to GNOME. Your records in `~/Downloads/Backstage/` are kept.
