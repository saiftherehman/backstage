# Architecture

Backstage is two programs that talk over D-Bus:

```
 GNOME Shell (your desktop)                  Background helper (Python, systemd user service)
 +-----------------------------+   D-Bus     +-----------------------------------------------+
 | Extension: the island       | <---------> | app.py: sessions, routing                     |
 |  - tabs and buttons         |  methods    |  - audio.py ---- pw-record (mic, output)       |
 |  - hotkeys                  |  signals    |  - transcriber.py (Whisper)                    |
 |  - screenshot every 2 s     |             |  - prompter.py (Vosk, follows your voice)      |
 |  - file picker (zenity)     |             |  - watcher.py (which screenshots to analyse)   |
 +-----------------------------+             |  - assistant.py + providers.py --> AI CLI     |
                                             |  - speaker.py (Piper) ---- pw-play             |
                                             |  - share_watch.py <---- dbus-monitor           |
                                             |  - phone.py (HTTP + live events) <---- phone   |
                                             |  - sessions.py --> sessions/<folder>/          |
                                             +-----------------------------------------------+
```

Why two programs: GNOME Shell extensions run inside the desktop's own process.
Heavy or blocking work there (speech recognition, waiting on an AI tool)
would freeze the whole desktop, so the extension only draws the island, takes
screenshots and forwards clicks. Everything else runs in the helper.

Why the extension takes the screenshots: on Wayland, an app that wants a
screenshot has to ask through a permission dialog. Code inside GNOME Shell can
take one directly.

## Session kinds

| | Teleprompter session | Assistant session |
| --- | --- | --- |
| Records microphone and output | Yes | Yes |
| Transcript (Whisper) | Yes | Yes |
| Voice following (Vosk) | Yes | No |
| Screenshots and AI analysis | No | Yes |
| Questions heard out loud | Recorded | Recorded and answered |
| Saved | transcript, script, summary | transcript, answers, screenshots, summary |

## How a screen analysis happens

1. Every `watch_interval` seconds the extension saves a screenshot to
   `~/.local/state/backstage/live-frame.png` and calls `OfferFrame` with the
   island's position.
2. `watcher.py` blacks out the island's area, makes a 96x54 greyscale
   fingerprint and compares it with:
   - the frame just before (has the screen settled?)
   - the last frame analysed (did anything change?)
   It only continues if the screen settled, changed, and no analysis is
   running. `AnalyseNow` and questions heard out loud skip the checks.
3. The frame is shrunk to 1280 px wide and saved as JPEG in the session's
   `screenshots/`.
4. `assistant.py` builds a short request (word limit, a heard question if any,
   the last few minutes of transcript). The fixed instructions go in the
   system prompt, which is identical on every call so the AI service caches
   it.
5. `providers.py` runs the AI tool. For Claude Code the call is stripped down:
   image sent inline as stream JSON, no tools, no MCP servers, no skills, no
   settings, no session saved. Measured: about 1,700 tokens per call, against
   about 44,000 for a plain `claude -p` call that opens the image with a tool.
6. The answer is saved to `answers.md` and `events.jsonl`, sent to the island
   and the phone, and read aloud if the screen-sharing rules say so.

## Where output goes

`share_watch.py` runs `dbus-monitor` on the session bus and watches the calls
that screen sharing makes to GNOME's screen cast service
(`org.gnome.Mutter.ScreenCast.Session`). `RecordMonitor` or `RecordArea` means
the entire screen is shared; `RecordWindow` means one window. GNOME's own share
indicator does not tell these apart, which is why this is needed.

Then, for every answer:
- the phone always gets it
- the island shows it unless the entire screen is shared (then it is hidden)
- it is read aloud only during an entire-screen share, and only when
  `audio.microphone_live()` says the meeting cannot hear the microphone: no
  microphone, muted, or no other app recording from an input

## D-Bus interface

Bus name and interface `io.github.saiftherehman.Backstage`, object path
`/io/github/saiftherehman/Backstage`, on the session bus. Defined in
`helper/backstage/service.py`; the extension keeps a copy of the same XML in
`helperClient.js`.

| Method | Arguments | Result |
| --- | --- | --- |
| `GetState` | | JSON string with everything the island shows (below) |
| `StartSession` | `kind` (`teleprompter` or `assistant`), `title` | session id (folder name) |
| `StopSession` | | |
| `OfferFrame` | `path`, `x`, `y`, `width`, `height` (island area to black out) | |
| `AnalyseNow` | | |
| `SetProvider` | `name` | |
| `LoadScript` | `text` | |
| `LoadDocument` | `path` | |
| `JumpPrompter` | `line` | |

| Signal | Arguments | When |
| --- | --- | --- |
| `StateChanged` | state JSON | Session started or stopped, script loaded, share mode or settings changed |
| `Transcript` | `speaker` (`me` or `them`), `text` | A sentence was transcribed |
| `PrompterMoved` | `line` | The teleprompter moved |
| `AnswerStarted` | `reason` | An analysis began |
| `Answer` | `reason`, `answer` | An analysis finished |
| `ShareModeChanged` | `none`, `window` or `screen` | Screen sharing started, changed or stopped |
| `Error` | `message` | Something failed (shown in the island) |

State JSON fields: `active`, `kind`, `title`, `started` (Unix time), `folder`,
`records`, `live_frame`, `watch_interval`, `providers` (list of `name`,
`label`), `provider`, `script_lines`, `prompter_line`, `share_mode`, `mic_ok`,
`phone_url`, `phone_qr`, `status`.

Try it from a terminal:

```bash
gdbus call --session -d io.github.saiftherehman.Backstage \
  -o /io/github/saiftherehman/Backstage -m io.github.saiftherehman.Backstage.GetState
gdbus monitor --session -d io.github.saiftherehman.Backstage   # watch the signals
```

## Phone page protocol

`phone.py` serves three addresses on `0.0.0.0:<port>`, each needing
`?key=<phone key>`:

| Request | Answer |
| --- | --- |
| `GET /` | The page (`phone_page.html`) |
| `GET /events` | Server-sent events: one JSON object per message with a `type` of `state`, `prompter`, `transcript`, `thinking`, `answer` or `error`. A new phone first gets the latest `state`, `answer` and `prompter` |
| `POST /ask` | Same as Analyse now (at most once every 3 seconds). Answers 204 |

## Files outside the project

| Path | What |
| --- | --- |
| `~/.config/systemd/user/backstage-helper.service` | The helper service, written by install.sh from `systemd/backstage-helper.service` |
| `~/.local/share/gnome-shell/extensions/backstage@saiftherehman.github.io` | Link to the extension folder |
| `~/.local/state/backstage/` | Phone key, QR code, live screenshot (folder readable only by you) |
| `~/.cache/backstage-preview/` | Home folder of the preview window |
| GNOME settings | Extension enabled, `Super+A` freed from the app grid, `Super+Alt+P` custom shortcut |

## Project layout

```
config.toml                 all settings
install.sh / uninstall.sh   set up / remove
tools/preview.sh            isolated preview window
helper/backstage/           the helper (run as: python -m backstage)
    __main__.py             start, signal handling, private file permissions
    app.py                  sessions, routing, read-aloud rules
    service.py              D-Bus interface
    config.py               reads config.toml
    audio.py                pw-record recorders, microphone checks
    transcriber.py          pause detection, Whisper
    prompter.py             script lines, voice following with Vosk
    documents.py            .pptx, .docx, .pdf, .txt, .md to text
    watcher.py              frame comparison, masking, shrinking
    assistant.py            prompts, summaries
    providers.py            Claude Code, Codex and Gemini command line calls
    questions.py            spots spoken questions
    speaker.py              Piper voice, pw-play
    share_watch.py          window share or entire screen share
    phone.py                phone page server
    phone_page.html         phone page
    sessions.py             session folders
extension/backstage@saiftherehman.github.io/
    extension.js            wiring: helper, hotkeys, screenshot loop, file picker
    helperClient.js         D-Bus client
    island.js               pill, tabs, position, dragging, see-through fade
    pages/                  teleprompter, assistant, session and phone tabs
    widgets.js              shared buttons and labels
    screenshot.js           screenshots inside GNOME Shell
    stylesheet.css          look of the island
    schemas/                hotkey settings, saved island position
systemd/backstage-helper.service   service template
docs/                       this documentation
models/                     speech and voice models (not in git)
sessions/                   meeting records (not in git)
scripts/current.txt         last loaded script (not in git)
```
