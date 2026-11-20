// The island: a small pill at the top centre that opens into three pages.

import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {AssistantPage} from './pages/assistantPage.js';
import {PhonePage} from './pages/phonePage.js';
import {PrompterPage} from './pages/prompterPage.js';
import {SessionPage} from './pages/sessionPage.js';

// Gap between the top bar and the island, in pixels.
const TOP_GAP = 6;

const TABS = [
    {id: 'prompter', label: 'Teleprompter'},
    {id: 'assistant', label: 'Assistant'},
    {id: 'session', label: 'Session'},
    {id: 'phone', label: 'Phone'},
];

export const Island = GObject.registerClass(
class Island extends St.BoxLayout {
    _init(actions) {
        super._init({
            orientation: Clutter.Orientation.VERTICAL,
            style_class: 'backstage',
            reactive: true,
        });
        this._expanded = false;
        this._startedAt = 0;
        this._message = 'Backstage';

        // Collapsed pill
        const pill = new St.BoxLayout({style_class: 'backstage-pill'});
        this._dot = new St.Widget({style_class: 'backstage-dot', y_align: Clutter.ActorAlign.CENTER});
        this._pillLabel = new St.Label({style_class: 'backstage-pill-label', y_align: Clutter.ActorAlign.CENTER, x_expand: true});
        this._timer = new St.Label({style_class: 'backstage-pill-timer', y_align: Clutter.ActorAlign.CENTER});
        pill.add_child(this._dot);
        pill.add_child(this._pillLabel);
        pill.add_child(this._timer);
        const pillButton = new St.Button({child: pill, can_focus: false, x_expand: true});
        pillButton.connect('clicked', () => this.setExpanded(!this._expanded));
        this.add_child(pillButton);

        // Expanded body
        this._body = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, style_class: 'backstage-body'});
        const tabs = new St.BoxLayout({style_class: 'backstage-tabs'});
        this._tabButtons = {};
        for (const tab of TABS) {
            const b = new St.Button({label: tab.label, style_class: 'backstage-tab', can_focus: false});
            b.connect('clicked', () => this.showTab(tab.id));
            tabs.add_child(b);
            this._tabButtons[tab.id] = b;
        }
        this._body.add_child(tabs);

        this.prompter = new PrompterPage(actions);
        this.assistant = new AssistantPage(actions);
        this.session = new SessionPage(actions);
        this.phone = new PhonePage();
        this._pages = {prompter: this.prompter, assistant: this.assistant, session: this.session, phone: this.phone};
        for (const page of Object.values(this._pages))
            this._body.add_child(page);
        this.add_child(this._body);

        this.showTab('prompter');
        this.setExpanded(false);
        this._updatePill();

        this.connect('notify::width', () => this._reposition());
        this._monitorsId = Main.layoutManager.connect('monitors-changed', () => this._reposition());
        this._tickId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, () => {
            this._updatePill();
            return GLib.SOURCE_CONTINUE;
        });
        this.connect('destroy', () => {
            GLib.source_remove(this._tickId);
            Main.layoutManager.disconnect(this._monitorsId);
        });
    }

    get expanded() {
        return this._expanded;
    }

    setExpanded(expanded) {
        this._expanded = expanded;
        this._body.visible = expanded;
        if (expanded)
            this.add_style_pseudo_class('expanded');
        else
            this.remove_style_pseudo_class('expanded');
    }

    showTab(id) {
        for (const [tab, page] of Object.entries(this._pages)) {
            page.visible = tab === id;
            if (tab === id)
                this._tabButtons[tab].add_style_pseudo_class('checked');
            else
                this._tabButtons[tab].remove_style_pseudo_class('checked');
        }
    }

    /** Short text in the pill, e.g. "Answer ready". */
    setMessage(text) {
        this._message = text;
        this._updatePill();
    }

    setSessionStart(startedAt) {
        this._startedAt = startedAt;
        if (startedAt)
            this._dot.add_style_pseudo_class('active');
        else
            this._dot.remove_style_pseudo_class('active');
        this._updatePill();
    }

    _updatePill() {
        this._pillLabel.text = this._message;
        if (!this._startedAt) {
            this._timer.text = '';
            return;
        }
        const seconds = Math.max(0, Math.floor(Date.now() / 1000 - this._startedAt));
        const h = Math.floor(seconds / 3600);
        const m = Math.floor(seconds / 60) % 60;
        const s = String(seconds % 60).padStart(2, '0');
        this._timer.text = h ? `${h}:${String(m).padStart(2, '0')}:${s}` : `${m}:${s}`;
    }

    _reposition() {
        const monitor = Main.layoutManager.primaryMonitor;
        if (!monitor)
            return;
        this.set_position(
            Math.floor(monitor.x + (monitor.width - this.width) / 2),
            monitor.y + Main.panel.height + TOP_GAP);
    }
});
