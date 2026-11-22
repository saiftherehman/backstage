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

Done: a top bar icon with a menu (start, stop and save, show island, open
records, settings), and a settings window to choose between the island
always on screen and the top bar icon. Left to do:

- **Top bar menu:** add the phone link.
- **Bottom bar (dock):** a launcher on the Ubuntu dock that opens the island,
  with right-click actions for the same items.
- **Keys:** a key for each action, all changeable (start teleprompter, start
  assistant, stop and save, open records), alongside the current `Super+A`,
  `Super+Alt+N`, `Super+Alt+Up`/`Down` and `Super+Alt+P`.
- **Settings:** the settings window (`prefs.js`) only has the island or top
  bar choice. Add the dock launcher and the keys, so nothing has to be edited
  by hand.

## Security: what is left

From the security review in
[docs/privacy-and-security.md](docs/privacy-and-security.md). The rest is done.

- **Blur passwords and card numbers.** Before a screenshot is sent, find
  areas that look like password fields, card numbers or one-time codes and
  blur them. Needs text recognition on the laptop (for example Tesseract),
  which is not installed yet; the pause key and private windows cover it
  until then.
- **Spoken recording notice.** The chat notice works; a spoken one would have
  to play into the meeting's audio, which only happens when the meeting app
  shares system audio. Possible with a virtual microphone (PipeWire
  loopback) that mixes the notice into what the meeting hears.
- **Check Codex and Gemini CLI for tool access.** Claude Code runs with no
  tools. Codex (read-only sandbox) can still read files, and Gemini CLI runs
  its read-only tools without asking. Neither is installed here to test;
  find each tool's flag to turn tools off completely and use it in
  `providers.py`.

## Island position and see-through: loose ends

The island can now be dragged anywhere and is see-through until the pointer
is on it. Left to do:

- **Reset without a terminal.** Putting it back at the top centre needs a
  `gsettings` command and an extension restart. Add a "Back to top centre"
  item (in the settings window, or on a right-click of the pill), and
  have the island listen for changes to `island-position` so it moves at once.
- **One setting for see-through.** The amount is set in two places today
  (`IDLE_OPACITY` in `island.js` and the `.backstage` background in
  `stylesheet.css`). Make it one slider in the settings window, with an
  option to keep the island always solid.
- **Several screens.** The position is kept inside the whole desktop area, so
  with two screens of different sizes the island can end up in the empty
  corner between them. Keep it inside the screen it was dropped on.
