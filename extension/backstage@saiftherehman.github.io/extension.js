// Backstage: wires the island UI and the top bar icon to the helper,
// hotkeys, the screen watcher loop and the document picker.

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
import {TopBarIcon} from './topBar.js';

Gio._promisify(Gio.Subprocess.prototype, 'communicate_utf8_async');

const DOCUMENT_TYPES = '*.pptx *.docx *.pdf *.txt *.md';
const SEALED_SUFFIX = '.backstage';

export default class BackstageIslandExtension extends Extension {
    enable() {
        this._state = null;
        this._watchId = 0;
        this._capturing = false;
        this._privateWindow = '';
        this._shareMode = '';
        this._dismissedSaved = '';
        // null, or 'shown' / 'hidden' when the island was opened or closed
        // by hand. Cleared when a session starts or stops.
        this._userChoice = null;
        this._topBar = null;
        this._settings = this.getSettings();
        this._island = new Island(this._settings, {
            pasteScript: () => this._pasteScript(),
            openDocument: () => this._openDocument(),
            jump: line => this._call(this._client.jumpPrompter(line)),
            startSession: kind => this._startSession(kind),
            stopSession: () => this._call(this._client.stopSession()),
            analyseNow: () => this._call(this._client.analyseNow()),
            setProvider: name => this._call(this._client.setProvider(name)),
            setPaused: paused => this._call(this._client.setPaused(paused)),
            setRecording: mode => this._call(this._client.setRecording(mode)),
            openRecords: () => this._openRecords(),
            dismissSaved: () => this._dismissSaved(),
        });
        Main.layoutManager.addTopChrome(this._island);

        this._client = new HelperClient({
            onConnected: state => this._applyState(state),
            onDisconnected: () => {
                this._topBar?.setState(null);
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
            'toggle-island': () => this._toggleIslandKey(),
            'ask-now': () => this._assistantKey(),
            'prompter-back': () => this._call(this._client.jumpPrompter(this._island.prompter.current - 1)),
            'prompter-next': () => this._call(this._client.jumpPrompter(this._island.prompter.current + 1)),
            'pause-assistant': () => this._call(this._client.setPaused(!this._state?.paused)),
        };
        for (const [name, handler] of Object.entries(bindings)) {
            Main.wm.addKeybinding(name, this._settings, Meta.KeyBindingFlags.NONE,
                Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW, handler);
        }
        this._bindingNames = Object.keys(bindings);

        this._displayId = this._settings.connect('changed::display', () => this._applyDisplay());
        this._applyDisplay();
    }

    disable() {
        this._stopWatching();
        this._settings.disconnect(this._displayId);
        this._topBar?.destroy();
        this._topBar = null;
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
        this._topBar?.setState(state);
        if (state.active !== Boolean(previous?.active))
            this._userChoice = null;
        if (!previous || previous.script_lines.join('\n') !== state.script_lines.join('\n'))
            island.prompter.setScript(state.script_lines, state.prompter_line);
        island.setSessionStart(state.active ? state.started : 0, state.recording_audio);
        const saved = state.last_saved ?? '';
        island.setSaved(!state.active && savedKey(saved) !== this._dismissedSaved ? saved : '');
        island.setMessage(state.status || 'Backstage');
        if (state.active && !previous?.active)
            this._copyChatNotice(state.chat_notice);
        this._applyShareMode(state.share_mode);
        if (state.active && state.kind === 'assistant')
            this._startWatching(state.watch_interval);
        else
            this._stopWatching();
    }

    // A full screen share copies everything drawn on screen, so the island
    // hides itself. A window or tab share never includes it.
    _applyShareMode(mode) {
        this._shareMode = mode;
        this._updateVisibility();
    }

    // Where Backstage lives, from the "display" setting:
    //   island   the island is always on screen
    //   top-bar  an icon in the top bar; the island shows during a session,
    //            while a saved notice is up, or when opened by hand
    _applyDisplay() {
        if (this._topBarMode() && !this._topBar) {
            this._topBar = new TopBarIcon({
                startSession: kind => this._startSession(kind),
                startTeleprompter: () => this._startTeleprompter(),
                stopSession: () => this._call(this._client.stopSession()),
                toggleIsland: () => this._setIslandShown(!this._island.visible),
                openRecords: () => this._openRecords(),
                openSettings: () => this.openPreferences(),
            });
            this._topBar.setState(this._client.connected ? this._state : null);
            Main.panel.addToStatusArea(this.uuid, this._topBar);
        } else if (!this._topBarMode() && this._topBar) {
            this._topBar.destroy();
            this._topBar = null;
        }
        this._updateVisibility();
    }

    _topBarMode() {
        return this._settings.get_string('display') === 'top-bar';
    }

    _updateVisibility() {
        let wanted = !this._topBarMode() || this._state?.active || Boolean(this._island.saved);
        if (this._userChoice)
            wanted = this._userChoice === 'shown';
        this._island.visible = wanted && this._shareMode !== 'screen';
        this._topBar?.setIslandShown(this._island.visible);
    }

    _setIslandShown(shown) {
        this._userChoice = shown ? 'shown' : 'hidden';
        this._island.setExpanded(shown);
        this._updateVisibility();
    }

    // Super+Alt+N: opens a hidden island, otherwise opens or closes its
    // pages. In top bar mode, closing an island opened by hand hides it.
    _toggleIslandKey() {
        if (!this._island.visible)
            this._setIslandShown(true);
        else if (!this._island.expanded)
            this._island.setExpanded(true);
        else if (this._topBarMode() && this._userChoice === 'shown')
            this._setIslandShown(false);
        else
            this._island.setExpanded(false);
    }

    _dismissSaved() {
        this._dismissedSaved = savedKey(this._island.saved);
        this._island.setSaved('');
        this._updateVisibility();
    }

    // A teleprompter needs a script, so without one the island opens on the
    // Teleprompter tab to load it.
    _startTeleprompter() {
        if (this._state?.script_lines.length) {
            this._startSession('teleprompter');
            return;
        }
        this._setIslandShown(true);
        this._island.showTab('prompter');
        this._island.setMessage('Load a script first');
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
        if (this._capturing || !this._state || this._state.paused)
            return;
        const privateWindow = this._privateWindowInFront();
        if (privateWindow !== this._privateWindow) {
            this._privateWindow = privateWindow;
            this._island.assistant.showPrivate(privateWindow);
        }
        if (privateWindow)
            return;
        this._capturing = true;
        try {
            await captureScreen(this._state.live_frame, this._island);
            await this._client.offerFrame(this._state.live_frame);
        } catch (e) {
            console.warn(`Backstage: screenshot failed: ${e.message}`);
        } finally {
            this._capturing = false;
        }
    }

    // The focused window's app name or title if it matches an entry in
    // [privacy] private_windows, else ''. Such screens are never captured.
    _privateWindowInFront() {
        const window = global.display.focus_window;
        if (!window)
            return '';
        const app = Shell.WindowTracker.get_default().get_window_app(window);
        const names = [app?.get_name(), app?.get_id(), window.get_wm_class(), window.get_title()]
            .filter(Boolean).map(n => n.toLowerCase());
        const match = (this._state.private_windows ?? [])
            .some(entry => names.some(n => n.includes(entry.toLowerCase())));
        return match ? (app?.get_name() ?? window.get_wm_class() ?? 'a private window') : '';
    }

    // A note for the meeting chat that the meeting is being transcribed.
    _copyChatNotice(notice) {
        if (!notice)
            return;
        St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, notice);
        Main.notify('Backstage', 'Recording notice copied. Paste it into the meeting chat.');
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
        if (!this._island.visible)
            Main.notify('Backstage', message);
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

    // The running session's folder, else the last saved one (unless it is
    // an encrypted file), else the records folder.
    _openRecords() {
        const saved = this._island.saved.endsWith(SEALED_SUFFIX) ? '' : this._island.saved;
        const folder = this._state?.folder || saved || this._state?.records;
        if (folder)
            Gio.AppInfo.launch_default_for_uri(Gio.File.new_for_path(folder).get_uri(), null);
    }
}

// The same key for a session folder and the encrypted file it becomes, so
// a dismissed notice stays dismissed after encryption.
function savedKey(path) {
    return path.endsWith(SEALED_SUFFIX) ? path.slice(0, -SEALED_SUFFIX.length) : path;
}
