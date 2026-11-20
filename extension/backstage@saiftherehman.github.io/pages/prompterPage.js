// Teleprompter page: load a script (paste or document), run a teleprompter
// session, and see the current line large with a little context around it.

import Clutter from 'gi://Clutter';
import GObject from 'gi://GObject';
import St from 'gi://St';

import {button, wrapLabel} from '../widgets.js';

const LINES_BEFORE = 1;
const LINES_AFTER = 3;

export const PrompterPage = GObject.registerClass(
class PrompterPage extends St.BoxLayout {
    _init(actions) {
        super._init({orientation: Clutter.Orientation.VERTICAL, style_class: 'backstage-page'});
        this._actions = actions;
        this._lines = [];
        this._current = 0;
        this._running = false;

        this._text = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, style_class: 'backstage-prompter'});
        this.add_child(this._text);

        const controls = new St.BoxLayout({style_class: 'backstage-controls'});
        this._startStop = button('', () => (this._running
            ? actions.stopSession() : actions.startSession('teleprompter')), 'backstage-button-primary');
        controls.add_child(this._startStop);
        controls.add_child(button('Paste script', () => actions.pasteScript()));
        controls.add_child(button('Open document', () => actions.openDocument()));
        controls.add_child(new St.Widget({x_expand: true}));
        controls.add_child(button('Restart', () => actions.jump(0)));
        controls.add_child(button('Back', () => actions.jump(this._current - 1)));
        controls.add_child(button('Next', () => actions.jump(this._current + 1)));
        this.add_child(controls);
        this.setState({active: false});
        this._render();
    }

    get current() {
        return this._current;
    }

    setState(state) {
        this._running = state.active && state.kind === 'teleprompter';
        this._startStop.label = this._running ? 'Stop and save' : 'Start teleprompter';
        // Only one session at a time.
        this._startStop.reactive = this._running || !state.active;
        this._startStop.opacity = this._startStop.reactive ? 255 : 110;
    }

    setScript(lines, current) {
        this._lines = lines;
        this._current = current;
        this._render();
    }

    setLine(line) {
        this._current = line;
        this._render();
    }

    _render() {
        this._text.destroy_all_children();
        if (!this._lines.length) {
            this._text.add_child(wrapLabel(
                'No script yet. Copy your script and press Paste script, or open a document ' +
                '(.pptx, .docx, .pdf, .txt or .md). Then press Start teleprompter: the highlighted ' +
                'line follows your voice.',
                'backstage-hint'));
            return;
        }
        const first = Math.max(0, this._current - LINES_BEFORE);
        const last = Math.min(this._lines.length - 1, this._current + LINES_AFTER);
        for (let i = first; i <= last; i++) {
            const style = i === this._current ? 'backstage-line-current'
                : i < this._current ? 'backstage-line-done' : 'backstage-line-next';
            this._text.add_child(new St.Label({text: this._lines[i] || ' ', style_class: `backstage-line ${style}`}));
        }
    }
});
