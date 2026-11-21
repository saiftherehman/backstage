# Configuration

All settings live in `config.toml` in the project folder. After editing it:

```bash
systemctl --user restart backstage-helper
```

Settings marked with an asterisk need `./install.sh` afterwards, because a new
model or voice has to be downloaded.

## [assistant]

| Setting | Default | What it does |
| --- | --- | --- |
| `provider` | `"claude"` | AI tool that analyses the screen: `claude`, `codex` or `gemini`. Must be installed and signed in. Can also be switched with the AI button on the Assistant tab (until the helper restarts) |
| `watch_interval` | `2` | Seconds between screenshots during an assistant session |
| `min_screen_change` | `0.02` | Share of the screen (0 to 1) that must change before it is analysed again. Higher means fewer analyses and lower AI use |
| `question_cooldown` | `15` | Seconds between analyses started by questions heard out loud |
| `max_answer_words` | `120` | Upper limit on answer length |
| `timeout` | `90` | Seconds before one analysis is given up on |
| `context_seconds` | `180` | How much of the meeting conversation is sent with each analysis |

### [assistant.models]

Model passed to each tool. Empty means the tool's own default.

| Setting | Default |
| --- | --- |
| `claude` | `"sonnet"` (`"haiku"` is cheaper, `"opus"` is stronger and slower) |
| `codex` | `""` |
| `gemini` | `""` |

## [audio]

| Setting | Default | What it does |
| --- | --- | --- |
| `mic` | `""` | PipeWire node name of the microphone. Empty means the default input. List nodes with `wpctl status` |
| `system` | `""` | Output to record the other people from. Empty means the default output |
| `speech_level` | `0.01` | Loudness (0 to 1) above which a 100 ms chunk counts as speech. Raise it in a noisy room |

## [speech]

| Setting | Default | What it does |
| --- | --- | --- |
| `whisper_model`* | `"small.en"` | Transcript model: `tiny.en`, `base.en`, `small.en`, `medium.en`. Bigger is more accurate and slower. `small.en` gives sentences about 1.5 s after they are spoken on an 8-core laptop |
| `whisper_threads` | `4` | CPU threads for Whisper |
| `vosk_model`* | `"vosk-model-small-en-us-0.15"` | Fast model that follows your voice through the script |
| `silence_seconds` | `0.7` | A pause this long ends a sentence |
| `max_segment_seconds` | `12` | Long speech without a pause is cut into pieces of this length |

## [prompter]

| Setting | Default | What it does |
| --- | --- | --- |
| `line_width` | `52` | Characters per teleprompter line |
| `lookahead_words` | `40` | How far ahead in the script to look for what you just said |
| `match_score` | `72` | How closely spoken words must match the script (0 to 100). Lower follows more loosely but may jump ahead |

## [voice]

| Setting | Default | What it does |
| --- | --- | --- |
| `speak_answers` | `"auto"` | Read answers aloud during a full screen share. `auto`: only when the meeting cannot hear your microphone. `never`: stay silent. `always`: always read aloud during a full screen share |
| `voice`* | `"en_US-lessac-medium"` | Piper voice. Others: <https://huggingface.co/rhasspy/piper-voices> (use the file name without `.onnx`) |

## [phone]

| Setting | Default | What it does |
| --- | --- | --- |
| `enabled` | `true` | Run the phone page. Set to `false` on networks you do not trust |
| `port` | `8765` | Port of the phone page. If you change it, open the new port in the firewall |

## [sessions]

| Setting | Default | What it does |
| --- | --- | --- |
| `folder` | `"sessions"` | Where records are saved, relative to the project folder (or an absolute path) |
| `summary_on_stop` | `true` | Write `summary.md` when a session ends. Costs one AI call per session |

## Keys

Hotkeys are GNOME settings, defined in
`extension/backstage@saiftherehman.github.io/schemas/org.gnome.shell.extensions.backstage.gschema.xml`.
Change the defaults there and run `./install.sh`, or override one without
touching the file:

```bash
gsettings --schemadir ~/.local/share/gnome-shell/extensions/backstage@saiftherehman.github.io/schemas \
  set org.gnome.shell.extensions.backstage ask-now "['<Control><Alt>a']"
```

The preview shortcut (`Super+Alt+P`) is a normal GNOME custom shortcut and can
be changed in Settings > Keyboard > Keyboard Shortcuts > Custom Shortcuts.

## Look

Colours and sizes of the island are in
`extension/backstage@saiftherehman.github.io/stylesheet.css`. How see-through
it is while the pointer is away is set in two places: the background of
`.backstage` in the stylesheet, and `IDLE_OPACITY` at the top of `island.js`
(0 to 255, for the text and everything else). The phone page has
its own styles at the top of `helper/backstage/phone_page.html`.
