# To do

Planned features, not built yet.

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
- **Pause the saved audio too.** Pause (`Super+Alt+H`) only stops
  screenshots going to the AI tool; `audio.ogg` and the transcript keep
  recording. Add a choice (a setting under `[recording]`, or a second button)
  so pausing also writes silence to the audio file, the same way spoken
  answers are left out in `app.py`, and shows **PAUSED** next to REC AUDIO
  on the island and the phone page while it lasts.

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
