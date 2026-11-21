// Assistant page: run an assistant session that analyses the screen, and
// show the latest analysis. The last answer stays while the next one loads.

import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';

import {button, scrollable, wrapLabel} from '../widgets.js';

export const AssistantPage = GObject.registerClass(
class AssistantPage extends St.BoxLayout {
    _init(actions) {
        super._init({orientation: Clutter.Orientation.VERTICAL, style_class: 'backstage-page'});
        this._actions = actions;
        this._providers = [];
        this._provider = '';
        this._running = false;
        this._paused = false;

        this._status = wrapLabel('', 'backstage-question');
        this.add_child(this._status);

        const answerBox = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL});
        this._answer = wrapLabel('', 'backstage-answer');
        answerBox.add_child(this._answer);
        this.add_child(scrollable(answerBox, 'backstage-answer-scroll'));

        const controls = new St.BoxLayout({style_class: 'backstage-controls'});
        this._startStop = button('', () => (this._running
            ? actions.stopSession() : actions.startSession('assistant')), 'backstage-button-primary');
        controls.add_child(this._startStop);
        this._analyseButton = button('Analyse now', () => actions.analyseNow());
        controls.add_child(this._analyseButton);
        this._pauseButton = button('', () => actions.setPaused(!this._paused));
        controls.add_child(this._pauseButton);
        controls.add_child(new St.Widget({x_expand: true}));
        this._providerButton = button('', () => this._nextProvider());
        controls.add_child(this._providerButton);
        this.add_child(controls);

        this._status.text = 'Press Start assistant (or Super+A). It watches the screen and ' +
            'explains or answers whatever is on it, with no questions back.';
    }

    setState(state) {
        const wasRunning = this._running;
        this._running = state.active && state.kind === 'assistant';
        this._startStop.label = this._running ? 'Stop and save' : 'Start assistant';
        this._startStop.reactive = this._running || !state.active;
        this._startStop.opacity = this._startStop.reactive ? 255 : 110;
        const wasPaused = this._paused;
        this._paused = state.paused;
        this._analyseButton.visible = this._running && !this._paused;
        this._pauseButton.visible = this._running;
        this._pauseButton.label = this._paused ? 'Resume' : 'Pause';
        if (this._running && !wasRunning) {
            this._status.text = 'Watching the screen...';
            this._answer.text = '';
        }
        if (this._running && this._paused)
            this._status.text = 'Paused: nothing is sent to the AI. Press Resume (or Super+Alt+H).';
        else if (this._running && wasPaused)
            this._status.text = 'Watching the screen...';
        this._providers = state.providers;
        this._provider = state.provider;
        const current = this._providers.find(p => p.name === this._provider);
        this._providerButton.label = current ? `AI: ${current.label}` : 'No AI tool signed in';
    }

    _nextProvider() {
        if (this._providers.length < 2)
            return;
        const index = this._providers.findIndex(p => p.name === this._provider);
        this._actions.setProvider(this._providers[(index + 1) % this._providers.length].name);
    }

    showUpdating(reason) {
        this._status.text = `Updating (${reason})...`;
    }

    showAnswer(reason, answer) {
        const time = GLib.DateTime.new_now_local().format('%H:%M:%S');
        this._status.text = `Updated ${time}, ${reason}`;
        this._answer.text = answer;
    }

    showError(message) {
        this._status.text = message;
    }

    /** name: the private window in front, or '' once it is gone. */
    showPrivate(name) {
        if (name)
            this._status.text = `Not sending the screen: ${name} is in front.`;
        else if (this._running && !this._paused)
            this._status.text = 'Watching the screen...';
    }
});
