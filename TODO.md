# To do

Planned features, not built yet.

## Meeting audio recording

Save the meeting's audio as a file in the session folder, next to the
transcript, as an option on each session:

- **Both sides:** your microphone and the other people, mixed into one file.
- **Other side only:** just what the computer plays (the other people).
- **Off:** transcript only, as now (the default).

Notes:
- The audio is already captured for the transcript (`audio.py`), so recording
  means also writing it to disk, for example as Opus or MP3 to keep files small.
- Add a setting in `config.toml` (`[recording] mode = "off" | "both" | "others"`)
  and a choice on the Session tab before starting.
- Pause the recording while an answer is read aloud, like the transcript does.
- Recording people may need their consent; show a clear "recording" mark
  while it runs.

## More ways to open Backstage

Today it opens from the island at the top centre and the keys. Add:

- **Top bar:** a Backstage icon in the GNOME top bar with a menu: start
  teleprompter, start assistant, stop and save, open the island, open records,
  phone link.
- **Bottom bar (dock):** a launcher on the Ubuntu dock that opens the island,
  with right-click actions for the same items.
- **Keys:** a key for each action, all changeable (start teleprompter, start
  assistant, stop and save, open records), alongside the current `Super+A`,
  `Super+Alt+N`, `Super+Alt+Up`/`Down` and `Super+Alt+P`.
- **Settings:** a small settings window to choose which of these are shown
  (island, top bar icon, dock launcher) and to change the keys, so nothing
  has to be edited by hand.

## Close the remaining security issues

The open risks from the security review in
[docs/privacy-and-security.md](docs/privacy-and-security.md):

- **Phone page over HTTPS.** Traffic is plain HTTP today, so someone on the
  same Wi-Fi who captures it can read answers, the transcript and the key.
  Options: a local certificate the phone trusts once (install it on the phone
  from the Phone tab), or end-to-end encrypt the messages in the page with a
  key carried in the link's `#fragment` (never sent over the network).
- **Keep sensitive screens out of the AI.** Anything on screen is sent during
  an assistant session. Add a pause key, skip analysis while chosen apps are
  in front (password manager, banking, private chats), and optionally blur
  areas that look like passwords or card numbers before sending.
- **Prompt injection.** Text on screen can still try to steer the answer.
  Mark answers that look steered (for example ones that repeat instructions
  from the screen) and keep the AI tools without any tools or write access.
- **Restrict who can call the helper.** Any program running as you can use
  the D-Bus interface. Accept calls only from GNOME Shell and the preview,
  by checking the caller's process.
- **Encrypt records at rest.** Sessions are plain files (owner-only).
  Optionally encrypt each session folder with a key from the GNOME keyring.
- **Consent.** Show a clear recording mark in the island while a session
  records, and add an optional spoken or chat notice that the meeting is
  being transcribed.
