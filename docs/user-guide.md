# User guide

Backstage puts a small island at the top centre of the screen, just under the
top bar. Click it (or press `Super+Alt+N`) to open it. It has four tabs.

The island is see-through while the pointer is away, so you can read what is
behind it, and turns solid black when you move the pointer onto it. To move
it, drag it by its top strip (the part with the name and timer) to any spot
on the screen. It stays there, open or closed, and after a restart. To put it
back at the top centre:

```bash
gsettings --schemadir ~/.local/share/gnome-shell/extensions/backstage@saiftherehman.github.io/schemas \
  reset org.gnome.shell.extensions.backstage island-position
```

Then turn the extension off and on, or log out and back in.

## Island or top bar

Backstage can live in one of two places. Pick it in the Extensions app
(Backstage > Settings) or from **Settings** in the top bar menu:

- **Island, always on screen** (the default): the island stays at the top.
- **Top bar icon, island only during a session**: a microphone icon sits in
  the top bar and turns red while a session records. Its menu starts and stops
  sessions, shows or hides the island, and opens the records. The island
  appears when a session starts and goes away once you dismiss the
  "Saved" notice after it ends. `Super+Alt+N` still opens it at any time.

The same setting from a terminal:

```bash
gsettings --schemadir ~/.local/share/gnome-shell/extensions/backstage@saiftherehman.github.io/schemas \
  set org.gnome.shell.extensions.backstage display top-bar   # or island
```

## Teleprompter

For presentations and prepared talks.

1. Load a script, either way:
   - copy the text anywhere, then press **Paste script**
   - press **Open document** and pick a file: `.pptx`, `.docx`, `.pdf`, `.txt`
     or `.md`. For slides, each slide's speaker notes are used when it has
     them (that is what you say), otherwise the text on the slide.
2. Press **Start teleprompter**. The current line is shown large in amber,
   with one line before and three after. As you speak, the highlight moves
   along with your voice.
3. If it loses you, press **Back** / **Next** (or `Super+Alt+Up` / `Down`),
   or **Restart** to go back to the top.
4. Press **Stop and save** when you are done.

The last loaded script is kept in `scripts/current.txt` and loads again next
time.

## Assistant

For meetings, calls and anything on screen you want explained or answered.

1. Press **Start assistant**, or `Super+A` from anywhere.
2. Backstage takes a screenshot every 2 seconds. When the screen has changed
   and stopped moving, it sends that screenshot, with the last few minutes of
   the meeting conversation, to your AI tool. The answer appears in the
   Assistant tab (and on the phone) in about 3 to 10 seconds:

   ```
   About: Team quiz with two questions and a sales table
   1. 17 x 23 = 391
   2. Jupiter, about 9 hours 56 minutes
   - South grew 39%, North fell 21%, total flat at 4.40M
   ```

   It answers every question it sees, explains data with the real numbers,
   and never asks you anything back.
3. If someone asks a question out loud, the next screenshot is analysed
   straight away and the spoken question is answered too.
4. `Super+A` or **Analyse now** while a session runs analyses the screen
   immediately, even if nothing changed.
5. The last answer stays readable while the next one loads ("Updating...").
6. **Pause** (or `Super+Alt+H`) stops sending the screen to the AI, for
   example while you type a password; **Resume** starts again. The meeting
   is still transcribed. Screens of password managers and banking are never
   sent anyway (`[privacy]` in `config.toml`).
7. Press **Stop and save** when you are done.

If an answer starts with "Check this answer", text on the screen may have
tried to steer the AI. Read it with care; it is not read aloud.

The **AI** button switches between the AI tools that are installed and signed
in on this computer.

Only one session runs at a time: a teleprompter session or an assistant
session.

## Session

While a session records, the island shows a red dot and **REC**, or **REC
AUDIO** when the meeting's audio is being saved too. If you set
`chat_notice` in `config.toml`, that message is copied when a session starts,
so you can paste it into the meeting chat to let people know.

Shows what is running (Teleprompter session or Assistant session), where its
output is going right now, the last few lines of the live transcript, and a
**Stop and save** button. **Open records** opens the session's folder.

### Saving the meeting's audio

Before a session starts, the **Audio** button on the Session tab chooses
whether the meeting's audio is saved next to the transcript. Click it to step
through:

- **Audio: off**: transcript only (the default).
- **Audio: both sides**: your microphone and the other people, mixed into one
  file at half volume each, so it never distorts when both are loud.
- **Audio: other side only**: just what the computer plays, so the other
  people.

The choice holds for the next sessions until you change it, and can't be
changed while a session runs. The file is `audio.ogg` (Opus), about 11 MB an
hour. While an answer is read aloud, the file gets silence instead, so the
voice is never saved. Without a microphone, **both sides** saves the other
side only. Set the starting choice with `mode` under `[recording]` in
`config.toml`.

When a session stops, the island shows **Saved:** and the session's folder,
shortened so it fits (for example `~/Downloads/Backstage/2026-11-22_1045_a…`),
and the Session tab shows a longer version of it, with **Open folder** and **Dismiss**. The small cross next to the pill dismisses it too. A summary with
decisions and action items is written to the folder a few seconds later.

## Phone

A second screen for the assistant.

1. Open the **Phone** tab and scan the QR code with your phone's camera, or
   type the link shown into the phone's browser. The phone must be on the same
   Wi-Fi as the laptop. The first time, the phone warns that the connection is
   not private: check the fingerprint against the Phone tab and continue, or
   install the laptop's certificate once so it never warns again (steps in
   [privacy and security](privacy-and-security.md#phone-page)).
2. The page shows the latest analysis, the teleprompter and the transcript,
   updates live, and buzzes when a new answer arrives.
3. **Analyse now** on the phone does the same as `Super+A`.

The link contains a private key. Anyone with the link can read your session,
so do not share it. The key changes every time a session stops, so scan the
code again before the next session; the old link stops working and the phone
says so. See [privacy and security](privacy-and-security.md#the-phone-key).

## Screen sharing

What happens depends on what you share in Meet, Zoom, Teams or any other app.

| You share | Island | Assistant output goes to |
| --- | --- | --- |
| Nothing | Visible | Island and phone |
| One window or browser tab | Visible (a window share never includes it) | Island and phone |
| Entire screen, microphone on | Hidden | Phone only |
| Entire screen, microphone off | Hidden | Phone, and read aloud on your speakers |

Why the island hides: GNOME shares the entire screen as one finished image, and
nothing can be left out of it. So during a full screen share the island steps
aside and the phone takes over.

"Microphone off" means the meeting cannot hear you: there is no microphone,
it is muted in GNOME (keyboard microphone key or the sound menu), or no app is
using it. Muting with the button inside the meeting app usually keeps the
microphone open, so Backstage treats it as on and stays quiet. This errs on
the safe side: it never talks while the meeting might be listening.

While an answer is read aloud, recording pauses so the voice does not end up
in the transcript. If you tick "share system audio" in the meeting app, the
others hear the voice too.

## Keys

| Keys | Action |
| --- | --- |
| `Super+A` | Start an assistant session, or analyse now if one is running |
| `Super+Alt+N` | Open or close the island |
| `Super+Alt+Up` / `Down` | Teleprompter one line back / forward |
| `Super+Alt+H` | Pause or resume sending the screen to the AI |
| `Super+Alt+P` | Open the preview window (a test desktop, not the island) |

Super is the Windows key. GNOME normally uses `Super+A` for the app grid;
install.sh turns that off so Backstage can use it (press Super on its own and
click the grid button to reach the app grid instead).

## Preview window

`Super+Alt+P` (or `tools/preview.sh`) opens a separate GNOME desktop in a
window, with the island running. Use it to try Backstage or test changes
without logging out. Click inside the window before using the keys.

It has its own home folder (`~/.cache/backstage-preview`), settings and
session bus, so your real desktop is not touched. While it is open the real
helper is paused, so the island on your real desktop says "Helper not
running"; it starts again when you close the window. Sessions you
record in it are saved to the normal `~/Downloads/Backstage/` folder.

## Records

Each session is a folder in `~/Downloads/Backstage/`, readable only by you. A
second session started in the same minute with the same title gets `-2` on the
end of its folder name, then `-3`. Change
the place with `folder` under `[sessions]` in `config.toml`.

```
~/Downloads/Backstage/2026-11-21_1430_assistant_weekly-sync/
    session.json      kind, title, start and end time, AI tool
    transcript.md     everything said, with times
    answers.md        assistant sessions: every analysis, with its screenshot
    script.txt        teleprompter sessions: the script used
    audio.ogg         the meeting's audio, if chosen on the Session tab
    summary.md        summary, decisions and action items
    events.jsonl      all of the above as JSON lines, for scripts
    screenshots/      the screenshots that were analysed (JPEG)
```

The session is named after the window that had focus when it started, which
is usually the meeting.

With `encrypt = true` under `[sessions]`, each folder becomes one encrypted
`.backstage` file when the session ends. Open one with
`tools/records.sh open ~/Downloads/Backstage/<name>.backstage`; see
[encrypted records](privacy-and-security.md#encrypted-records).

In the transcript, "Me" is your microphone and "Them" is whatever the computer
plays (the other people). Through speakers your microphone also hears the
others, so during a session Backstage removes what the speakers play from your
microphone (PipeWire's echo removal). It catches most of it, not all, so
headphones are still the cleanest. Your system microphone and meeting apps are
not changed by this.
