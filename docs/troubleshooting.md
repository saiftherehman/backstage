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

It removes the service, the extension, the shortcuts and the phone key, and
gives `Super+A` back to GNOME. Your `sessions/` records stay in the project
folder.
