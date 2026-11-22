# Backstage

<img src="extension/backstage@saiftherehman.github.io/icons/backstage-symbolic.svg" alt="Backstage logo" width="64">

A meeting and presentation helper for GNOME on Linux. A small island at the
top of the screen gives you:

- **Teleprompter**: paste a script or open a presentation (.pptx, .docx, .pdf,
  .txt, .md). The highlighted line follows your voice.
- **Assistant**: watches the screen and, whenever it changes, says what it is
  about and answers or explains what is on it. Plain answers, no questions
  back. Questions asked out loud in the meeting are answered too.
- **Phone**: the assistant's output on your phone, as a second screen. When
  you share your entire screen the island hides and the phone takes over; with
  your microphone off, answers are also read aloud.
- **Records**: every session saved as files in `~/Downloads/Backstage`:
  transcript, answers with screenshots, summary and action items, and the
  meeting's audio if you choose. Optionally encrypted with a key in the GNOME
  keyring.

Speech recognition, the voice and the records run on your computer. Screen
analysis uses a command line AI tool you are already signed in to (Claude Code;
Codex and Gemini CLI are supported but untested), with each call trimmed to
about 1,700 tokens.

## Requirements

- GNOME Shell 50 on Wayland (tested on Ubuntu 26.04)
- PipeWire, Python 3.11 or newer (tested with 3.14), `zenity`, `curl`
- A signed-in command line AI tool, for the assistant

## Install

```bash
git clone git@github.com:saiftherehman/backstage.git ~/Scripts/Backstage
cd ~/Scripts/Backstage
./install.sh
```

Then log out and back in once (GNOME on Wayland loads new extensions at
login). To try it before that, press `Super+Alt+P` for the preview window.

Remove it with `./uninstall.sh`. Your records in `~/Downloads/Backstage/` are kept.

## Keys

| Keys | Action |
| --- | --- |
| `Super+A` | Start the assistant, or analyse now |
| `Super+Alt+N` | Open or close the island |
| `Super+Alt+Up` / `Down` | Teleprompter line back / forward |
| `Super+Alt+H` | Pause or resume sending the screen to the AI |
| `Super+Alt+P` | Preview window |

## Documentation

- [User guide](docs/user-guide.md): every tab, screen sharing, keys, records
- [Configuration](docs/configuration.md): every setting in `config.toml`
- [Privacy and security](docs/privacy-and-security.md): what goes where, the
  security review, the firewall
- [Architecture](docs/architecture.md): how it works, D-Bus interface, layout
- [Development](docs/development.md): running and testing parts, extending it
- [Troubleshooting](docs/troubleshooting.md)
- [To do](TODO.md): planned features

## Where to change common things

| What | Where |
| --- | --- |
| AI tool, model, how often the screen is checked | `[assistant]` in `config.toml` |
| When answers are read aloud, voice | `[voice]` in `config.toml` |
| Saving the meeting's audio, its quality | `[recording]` in `config.toml` |
| Phone page on or off, port | `[phone]` in `config.toml` |
| Apps never sent to the AI, chat notice, encrypted records | `[privacy]`, `[consent]`, `[sessions]` in `config.toml` |
| Which programs may call the helper | `ALLOWED_PROGRAMS` in `helper/backstage/service.py` |
| Phone certificates | `helper/backstage/certificates.py`, files in `~/.local/state/backstage/tls/` |
| Answer wording | top of `helper/backstage/assistant.py` |
| Hotkeys | `extension/backstage@saiftherehman.github.io/schemas/` |
| Look of the island | `extension/backstage@saiftherehman.github.io/stylesheet.css` |
| Logo (also the top bar icon) | `extension/backstage@saiftherehman.github.io/icons/backstage-symbolic.svg` |
| How see-through the island is | `IDLE_OPACITY` in `island.js` and `.backstage` in `stylesheet.css` |
| Island always on screen, or top bar icon | Extensions app > Backstage > Settings, or `display` in the schema |

After editing `config.toml`: `systemctl --user restart backstage-helper`.

## License

MIT, see [LICENSE](LICENSE).
