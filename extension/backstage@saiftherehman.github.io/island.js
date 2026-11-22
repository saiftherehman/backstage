// The island: a small pill at the top centre that opens into four pages.
// It stays see-through until the pointer is on it, and can be dragged
// anywhere by its pill; the spot is remembered. After a session it shows
// where the records were saved until that notice is dismissed.

import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Pango from 'gi://Pango';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {AssistantPage} from './pages/assistantPage.js';
import {PhonePage} from './pages/phonePage.js';
import {PrompterPage} from './pages/prompterPage.js';
import {SessionPage} from './pages/sessionPage.js';
import {shortPath} from './widgets.js';

// Gap between the top bar and the island, in pixels.
const TOP_GAP = 6;

// Opacity (0-255) of the whole island while the pointer is away from it.
// The background is also lighter then, see .backstage in stylesheet.css.
const IDLE_OPACITY = 170;
const FADE_MS = 150;

// How far the pointer must move, in pixels, before a press on the pill
// becomes a drag instead of a click.
const DRAG_THRESHOLD = 6;

// Longest saved path the pill shows before cutting it short, so the
// collapsed island stays narrow.
const PILL_PATH_LENGTH = 40;

// Saved position meaning "top centre".
const NO_POSITION = -1;

const TABS = [
    {id: 'prompter', label: 'Teleprompter'},
    {id: 'assistant', label: 'Assistant'},
    {id: 'session', label: 'Session'},
    {id: 'phone', label: 'Phone'},
];

export const Island = GObject.registerClass(
class Island extends St.BoxLayout {
    _init(settings, actions) {
        super._init({
            orientation: Clutter.Orientation.VERTICAL,
            style_class: 'backstage',
            reactive: true,
            track_hover: true,
        });
        this._settings = settings;
        this._expanded = false;
        this._startedAt = 0;
        this._message = 'Backstage';
        this._saved = '';

        // Collapsed pill
        const pill = new St.BoxLayout({style_class: 'backstage-pill'});
        this._dot = new St.Widget({style_class: 'backstage-dot', y_align: Clutter.ActorAlign.CENTER});
        this._pillLabel = new St.Label({style_class: 'backstage-pill-label', y_align: Clutter.ActorAlign.CENTER, x_expand: true});
        this._pillLabel.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
        this._timer = new St.Label({style_class: 'backstage-pill-timer', y_align: Clutter.ActorAlign.CENTER});
        this._rec = new St.Label({text: 'REC', style_class: 'backstage-rec', y_align: Clutter.ActorAlign.CENTER, visible: false});
        pill.add_child(this._dot);
        pill.add_child(this._pillLabel);
        pill.add_child(this._rec);
        pill.add_child(this._timer);
        const pillButton = new St.Button({child: pill, can_focus: false, x_expand: true});
        pillButton.connect('clicked', () => this.setExpanded(!this._expanded));
        pillButton.connect('captured-event', (actor, event) => this._onPillEvent(actor, event));
        this._dismiss = new St.Button({
            style_class: 'backstage-dismiss',
            child: new St.Icon({icon_name: 'window-close-symbolic', icon_size: 14}),
            can_focus: false,
            visible: false,
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._dismiss.connect('clicked', () => actions.dismissSaved());
        const header = new St.BoxLayout();
        header.add_child(pillButton);
        header.add_child(this._dismiss);
        this.add_child(header);

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

        this._drag = null;
        this._dragGrab = null;
        [this._anchorX, this._anchorY] = settings.get_value('island-position').deepUnpack();
        this.connect('notify::hover', () => this._updateLook());
        this._updateLook();

        this.connect('notify::width', () => this._reposition());
        this._monitorsId = Main.layoutManager.connect('monitors-changed', () => this._reposition());
        this._tickId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, () => {
            this._updatePill();
            return GLib.SOURCE_CONTINUE;
        });
        this.connect('destroy', () => {
            this._dragGrab?.dismiss();
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

    get saved() {
        return this._saved;
    }

    /** Path of the last saved session to point at, or '' for none. */
    setSaved(path) {
        this._saved = path;
        this._dismiss.visible = Boolean(path);
        this.session.setSaved(path);
        this._updatePill();
    }

    /** savingAudio: the meeting's audio is being saved, not only the transcript. */
    setSessionStart(startedAt, savingAudio = false) {
        this._startedAt = startedAt;
        this._rec.visible = Boolean(startedAt);
        this._rec.text = savingAudio ? 'REC AUDIO' : 'REC';
        if (startedAt)
            this._dot.add_style_pseudo_class('active');
        else
            this._dot.remove_style_pseudo_class('active');
        this._updatePill();
    }

    _updatePill() {
        this._pillLabel.text = this._saved
            ? `Saved: ${shortPath(this._saved, PILL_PATH_LENGTH)}`
            : this._message;
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

    // See-through while idle, solid while the pointer is on it or dragging.
    _updateLook() {
        const solid = this.hover || this._drag?.moving;
        if (solid)
            this.add_style_pseudo_class('solid');
        else
            this.remove_style_pseudo_class('solid');
        this.ease({
            opacity: solid ? 255 : IDLE_OPACITY,
            duration: FADE_MS,
            mode: Clutter.AnimationMode.EASE_OUT_QUAD,
        });
    }

    // Dragging by the pill. A press that moves less than DRAG_THRESHOLD is
    // left to the button as a normal click.
    _onPillEvent(button, event) {
        const type = event.type();
        if (type === Clutter.EventType.BUTTON_PRESS && event.get_button() === Clutter.BUTTON_PRIMARY) {
            const [x, y] = event.get_coords();
            this._drag = {startX: x, startY: y, fromX: this.x, fromY: this.y, moving: false};
            return Clutter.EVENT_PROPAGATE;
        }
        if (!this._drag)
            return Clutter.EVENT_PROPAGATE;

        if (type === Clutter.EventType.MOTION) {
            const [x, y] = event.get_coords();
            const dx = x - this._drag.startX;
            const dy = y - this._drag.startY;
            if (!this._drag.moving) {
                if (Math.hypot(dx, dy) < DRAG_THRESHOLD)
                    return Clutter.EVENT_PROPAGATE;
                this._drag.moving = true;
                button.fake_release();
                this._dragGrab = global.stage.grab(button);
                this._updateLook();
            }
            this._moveTo(this._drag.fromX + dx, this._drag.fromY + dy);
            return Clutter.EVENT_STOP;
        }

        if (type === Clutter.EventType.BUTTON_RELEASE) {
            const moved = this._drag.moving;
            this._drag = null;
            if (!moved)
                return Clutter.EVENT_PROPAGATE;
            this._dragGrab?.dismiss();
            this._dragGrab = null;
            this._settings.set_value('island-position',
                new GLib.Variant('(ii)', [this._anchorX, this._anchorY]));
            this._updateLook();
            return Clutter.EVENT_STOP;
        }
        return Clutter.EVENT_PROPAGATE;
    }

    // Places the island's top left corner, kept fully on screen, and
    // remembers it as centre x and top y so opening and closing the island
    // grows it around the same spot.
    _moveTo(x, y) {
        const maxX = Math.max(0, global.stage.width - this.width);
        const maxY = Math.max(0, global.stage.height - this.height);
        x = Math.round(Math.min(Math.max(x, 0), maxX));
        y = Math.round(Math.min(Math.max(y, 0), maxY));
        this.set_position(x, y);
        this._anchorX = Math.round(x + this.width / 2);
        this._anchorY = y;
    }

    _reposition() {
        if (this._drag?.moving)
            return;
        const monitor = Main.layoutManager.primaryMonitor;
        if (!monitor)
            return;
        if (this._anchorX === NO_POSITION) {
            this.set_position(
                Math.floor(monitor.x + (monitor.width - this.width) / 2),
                monitor.y + Main.panel.height + TOP_GAP);
            return;
        }
        // Clamp without overwriting the saved spot, so a screen that comes
        // back later puts the island where it was.
        const x = Math.min(Math.max(this._anchorX - this.width / 2, 0), Math.max(0, global.stage.width - this.width));
        const y = Math.min(Math.max(this._anchorY, 0), Math.max(0, global.stage.height - this.height));
        this.set_position(Math.round(x), Math.round(y));
    }
});
