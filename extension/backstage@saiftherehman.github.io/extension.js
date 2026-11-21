// Backstage: wires the island UI to the helper, hotkeys, the screen
// watcher loop and the document picker.

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

import {HelperClient} from './helperClient.js';
import {Island} from './island.js';
import {captureScreen} from './screenshot.js';

Gio._promisify(Gio.Subprocess.prototype, 'communicate_utf8_async');

const DOCUMENT_TYPES = '*.pptx *.docx *.pdf *.txt *.md';

export default class BackstageIslandExtension extends Extension {
    enable() {
        this._state = null;
        this._watchId = 0;
        this._capturing = false;
        this._settings = this.getSettings();
        this._island = new Island(this._settings, {
            pasteScript: () => this._pasteScript(),
            openDocument: () => this._openDocument(),
            jump: line => this._call(this._client.jumpPrompter(line)),
            startSession: kind => this._startSession(kind),
            stopSession: () => this._call(this._client.stopSession()),
            analyseNow: () => this._call(this._client.analyseNow()),
            setProvider: name => this._call(this._client.setProvider(name)),
            openRecords: () => this._openRecords(),
        });
        Main.layoutManager.addTopChrome(this._island);

        this._client = new HelperClient({
            onConnected: state => this._applyState(state),
            onDisconnected: () => {
                this._island.setMessage('Helper not running');
                this._island.setSessionStart(0);
                this._stopWatching();
            },
            onStateChanged: json => this._applyState(JSON.parse(json)),
            onTranscript: (speaker, text) => this._island.session.addTranscript(speaker, text),
            onPrompterMoved: line => this._island.prompter.setLine(line),
            onAnswerStarted: reason => this._island.assistant.showUpdating(reason),
            onAnswer: (reason, answer) => this._showAnswer(reason, answer),
            onShareModeChanged: mode => this._applyShareMode(mode),
            onError: message => this._showError(message),
        });

        const bindings = {
            'toggle-island': () => this._island.setExpanded(!this._island.expanded),
            'ask-now': () => this._assistantKey(),
            'prompter-back': () => this._call(this._client.jumpPrompter(this._island.prompter.current - 1)),
            'prompter-next': () => this._call(this._client.jumpPrompter(this._island.prompter.current + 1)),
        };
        for (const [name, handler] of Object.entries(bindings)) {
            Main.wm.addKeybinding(name, this._settings, Meta.KeyBindingFlags.NONE,
                Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW, handler);
        }
        this._bindingNames = Object.keys(bindings);
    }

    disable() {
        this._stopWatching();
        for (const name of this._bindingNames)
            Main.wm.removeKeybinding(name);
        this._client.destroy();
        this._client = null;
        this._island.destroy();
        this._island = null;
        this._settings = null;
        this._state = null;
    }

    _applyState(state) {
        const previous = this._state;
        this._state = state;
        const island = this._island;
        island.prompter.setState(state);
        island.assistant.setState(state);
        island.session.setState(state);
        island.phone.setState(state);
        if (!previous || previous.script_lines.join('\n') !== state.script_lines.join('\n'))
            island.prompter.setScript(state.script_lines, state.prompter_line);
        island.setSessionStart(state.active ? state.started : 0);
        island.setMessage(state.status || 'Backstage');
        this._applyShareMode(state.share_mode);
        if (state.active && state.kind === 'assistant')
            this._startWatching(state.watch_interval);
        else
            this._stopWatching();
    }

    // A full screen share copies everything drawn on screen, so the island
    // hides itself. A window or tab share never includes it.
    _applyShareMode(mode) {
        this._island.visible = mode !== 'screen';
    }

    // Screen watcher: a screenshot every few seconds while an assistant
    // session runs. The helper decides which ones are worth analysing.

    _startWatching(seconds) {
        if (this._watchId)
            return;
        this._watchId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, seconds, () => {
            this._sendFrame();
            return GLib.SOURCE_CONTINUE;
        });
        this._sendFrame();
    }

    _stopWatching() {
        if (this._watchId)
            GLib.source_remove(this._watchId);
        this._watchId = 0;
    }

    async _sendFrame() {
        if (this._capturing || !this._state)
            return;
        this._capturing = true;
        try {
            await captureScreen(this._state.live_frame);
            const island = this._island;
            const area = island.visible
                ? [island.x, island.y, island.width, island.height].map(Math.round)
                : [0, 0, 0, 0];
            await this._client.offerFrame(this._state.live_frame, area);
        } catch (e) {
            console.warn(`Backstage: screenshot failed: ${e.message}`);
        } finally {
            this._capturing = false;
        }
    }

    // Super+A: start an assistant session, or analyse right now if one runs.
    _assistantKey() {
        if (this._state?.active && this._state.kind === 'assistant') {
            this._call(this._client.analyseNow());
        } else if (!this._state?.active) {
            this._startSession('assistant');
        } else {
            this._island.setExpanded(true);
            this._island.showTab('session');
        }
    }

    async _startSession(kind) {
        try {
            const focused = global.display.focus_window;
            await this._client.startSession(kind, focused?.get_title() ?? 'Meeting');
            this._island.showTab(kind === 'assistant' ? 'assistant' : 'prompter');
        } catch (e) {
            this._showError(e);
        }
    }

    _showAnswer(reason, answer) {
        this._island.assistant.showAnswer(reason, answer);
        this._island.setMessage('Answer ready');
    }

    _showError(error) {
        const message = (error?.message ?? String(error)).replace(/^GDBus\.Error:[\w.]+:\s*/, '');
        console.warn(`Backstage: ${message}`);
        this._island.assistant.showError(message);
        this._island.setMessage(message.length > 40 ? 'Something went wrong' : message);
    }

    _call(promise) {
        promise.catch(e => this._showError(e));
    }

    _pasteScript() {
        St.Clipboard.get_default().get_text(St.ClipboardType.CLIPBOARD, (clipboard, text) => {
            if (!text?.trim()) {
                this._island.setMessage('Clipboard is empty');
                return;
            }
            this._call(this._client.loadScript(text));
        });
    }

    // GNOME Shell cannot show a file dialog itself, so zenity does it.
    async _openDocument() {
        try {
            const picker = Gio.Subprocess.new(
                ['zenity', '--file-selection', '--title=Open a script or presentation',
                    `--file-filter=Documents | ${DOCUMENT_TYPES}`, '--file-filter=All files | *'],
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
            const [path] = await picker.communicate_utf8_async(null, null);
            if (path?.trim())
                await this._client.loadDocument(path.trim());
        } catch (e) {
            this._showError(e);
        }
    }

    _openRecords() {
        const folder = this._state?.folder || this._state?.records;
        if (folder)
            Gio.AppInfo.launch_default_for_uri(Gio.File.new_for_path(folder).get_uri(), null);
    }
}
