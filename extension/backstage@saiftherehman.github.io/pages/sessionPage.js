// Session page: what is running (teleprompter or assistant session), where
// its output goes, the live transcript, and where the last one was saved.

import Clutter from 'gi://Clutter';
import GObject from 'gi://GObject';
import St from 'gi://St';

import {button, wrapLabel} from '../widgets.js';

const TRANSCRIPT_LINES = 5;
const KIND_LABELS = {teleprompter: 'Teleprompter session', assistant: 'Assistant session'};

export const SessionPage = GObject.registerClass(
class SessionPage extends St.BoxLayout {
    _init(actions) {
        super._init({orientation: Clutter.Orientation.VERTICAL, style_class: 'backstage-page'});
        this._lines = [];
        this._state = null;
        this._saved = '';

        this._title = new St.Label({style_class: 'backstage-session-title'});
        this.add_child(this._title);
        this._detail = wrapLabel('', 'backstage-hint');
        this.add_child(this._detail);
        this._warning = wrapLabel('', 'backstage-warning');
        this.add_child(this._warning);
        this._transcript = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, style_class: 'backstage-transcript'});
        this.add_child(this._transcript);

        const controls = new St.BoxLayout({style_class: 'backstage-controls'});
        this._stop = button('Stop and save', () => actions.stopSession(), 'backstage-button-primary');
        controls.add_child(this._stop);
        this._dismiss = button('Dismiss', () => actions.dismissSaved());
        controls.add_child(this._dismiss);
        controls.add_child(new St.Widget({x_expand: true}));
        this._open = button('Open records', () => actions.openRecords());
        controls.add_child(this._open);
        this.add_child(controls);
    }

    setState(state) {
        this._state = state;
        this._render();
        const warnings = [];
        if (!state.mic_ok)
            warnings.push('No microphone found, so only other people are transcribed and the ' +
                'teleprompter cannot follow your voice. Check Settings > Sound > Input.');
        this._warning.text = warnings.join('\n');
        this._warning.visible = warnings.length > 0;
        if (state.active && !this._wasActive)
            this._setLines([]);
        this._wasActive = state.active;
    }

    /** Path of the last saved session, or '' once dismissed. */
    setSaved(path) {
        this._saved = path;
        this._render();
    }

    _render() {
        const state = this._state;
        if (!state)
            return;
        this._stop.visible = state.active;
        this._dismiss.visible = !state.active && Boolean(this._saved);
        this._open.label = this._dismiss.visible ? 'Open folder' : 'Open records';
        if (state.active) {
            this._title.text = `${KIND_LABELS[state.kind]}: ${state.title}`;
            this._detail.text = this._where(state);
        } else if (this._saved) {
            this._title.text = 'Session saved';
            this._detail.text = this._saved;
            if (this._saved.endsWith('.backstage'))
                this._detail.text += '\nEncrypted. Open it with tools/records.sh.';
        } else {
            this._title.text = state.status || 'No session running';
            this._detail.text = 'Start a session from the Teleprompter or Assistant tab. ' +
                'Each session is saved as its own folder of records.';
        }
    }

    _where(state) {
        if (state.kind !== 'assistant')
            return 'Recording the meeting. The script line follows your voice.';
        if (state.share_mode === 'screen')
            return 'Whole screen shared: the island is hidden. Answers show on the phone, and are ' +
                'read aloud only while the meeting cannot hear your microphone.';
        return 'Watching the screen and the meeting. Answers show here and on the phone.';
    }

    addTranscript(speaker, text) {
        this._setLines([...this._lines, `${speaker === 'me' ? 'Me' : 'Them'}: ${text}`].slice(-TRANSCRIPT_LINES));
    }

    _setLines(lines) {
        this._lines = lines;
        this._transcript.destroy_all_children();
        for (const line of lines)
            this._transcript.add_child(wrapLabel(line, 'backstage-transcript-line'));
    }
});
