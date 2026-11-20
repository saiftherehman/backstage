# Development

## Running pieces by hand

Stop the service first so two helpers do not fight over the D-Bus name and
the phone port:

```bash
systemctl --user stop backstage-helper
cd helper
../.venv/bin/python -m backstage          # Ctrl+C to stop
systemctl --user start backstage-helper   # when done
```

Drive it from another terminal:

```bash
B="gdbus call --session -d io.github.saiftherehman.Backstage -o /io/github/saiftherehman/Backstage -m io.github.saiftherehman.Backstage"
$B.StartSession assistant "Test"
cp some-screenshot.png ~/.local/state/backstage/live-frame.png
$B.AnalyseNow
gdbus monitor --session -d io.github.saiftherehman.Backstage   # see the Answer signal
$B.StopSession
```

## Trying extension changes

GNOME on Wayland cannot reload an extension in the running desktop. Either
log out and back in, or use the preview window, which loads the extension
fresh every time it opens:

```bash
tools/preview.sh        # or Super+Alt+P
```

Extension errors show up in the journal:

```bash
journalctl --user -b /usr/bin/gnome-shell | grep -i backstage
```

## Testing without a display

The same isolation trick as the preview, with `gnome-shell --headless
--virtual-monitor 1920x1080` instead of `--devkit`, runs GNOME Shell with no
window at all. A small test extension inside it can open the island's tabs and
save screenshots with `Shell.Screenshot`. This is how the island's layout was
checked while building it.

One rule when doing this: set `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`,
`XDG_CACHE_HOME` and `XDG_RUNTIME_DIR` **before** `dbus-run-session`, never
inside it. Services that the private bus starts (like the settings store)
inherit the environment of `dbus-run-session` itself, and would otherwise
write test settings into your real GNOME settings.

## Checking AI usage

Each provider call can be timed and measured outside Backstage:

```bash
claude -p --input-format stream-json --output-format stream-json --verbose \
  --tools "" --strict-mcp-config --disable-slash-commands --no-session-persistence \
  --setting-sources "" --system-prompt "test" < message.json | grep '"type":"result"'
```

The `usage` field of the result line shows input, cache and output tokens.
Any change to `providers.py` or `assistant.py` should keep a call near 1,700
input tokens for a 1280 px screenshot.

## Adding an AI tool

Add a class to `helper/backstage/providers.py` with `name`, `label`,
`binary`, `login_files` and an `ask(system, prompt, image, cwd, model,
timeout)` method that returns the answer text, then add it to `ALL`. Keep
calls small (no tools, no extra context) and make sure the tool cannot run
commands, since screen content goes into the prompt. Add a model entry under
`[assistant.models]` in `config.toml`.

## Adding a document type

Add a branch to `read_text()` in `helper/backstage/documents.py` and the
extension to `SUPPORTED`, plus the file pattern to `DOCUMENT_TYPES` in
`extension.js`.

## Changing the D-Bus interface

The XML is in two places: `helper/backstage/service.py` and
`extension/.../helperClient.js`. Change both, plus the `_on_call` dispatch and
`SIGNAL_TYPES` in `service.py`, and the method wrappers in `helperClient.js`.

## Style

- Python: standard library style, one job per module, comments only where the
  reason is not obvious.
- JavaScript: GNOME Shell extension style (ES modules, GObject classes, four
  spaces).
- Text: plain words, no em dashes.
