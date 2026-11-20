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
