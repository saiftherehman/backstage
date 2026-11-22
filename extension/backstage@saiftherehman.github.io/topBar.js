// Top bar icon with a menu, used when the "display" setting is "top-bar".
// The island then only shows during a session, or when opened from here.

import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import St from 'gi://St';

import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

// The Backstage logo (curtain, light, performer). The "-symbolic" name lets
// GNOME recolor it to match the top bar.
const ICON_FILE = Gio.File.new_for_uri(import.meta.url).get_parent()
    .get_child('icons').get_child('backstage-symbolic.svg');
const KIND_LABELS = {teleprompter: 'Teleprompter session', assistant: 'Assistant session'};

export const TopBarIcon = GObject.registerClass(
class TopBarIcon extends PanelMenu.Button {
    _init(actions) {
        super._init(0.5, 'Backstage');
        this._icon = new St.Icon({gicon: new Gio.FileIcon({file: ICON_FILE}), style_class: 'system-status-icon'});
        this.add_child(this._icon);

        const menu = this.menu;
        this._status = new PopupMenu.PopupMenuItem('Backstage', {reactive: false});
        menu.addMenuItem(this._status);
        menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._startAssistant = menu.addAction('Start assistant', () => actions.startSession('assistant'));
        this._startPrompter = menu.addAction('Start teleprompter', () => actions.startTeleprompter());
        this._stop = menu.addAction('Stop and save', () => actions.stopSession());
        menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._toggleIsland = menu.addAction('Show island', () => actions.toggleIsland());
        menu.addAction('Open records', () => actions.openRecords());
        menu.addAction('Settings', () => actions.openSettings());
        this.setState(null);
    }

    /** state: the helper's state, or null while it is not running. */
    setState(state) {
        const active = Boolean(state?.active);
        if (!state)
            this._status.label.text = 'Helper not running';
        else if (active)
            this._status.label.text = `${KIND_LABELS[state.kind]}: ${state.title}`;
        else
            this._status.label.text = 'No session running';
        this._startAssistant.visible = Boolean(state) && !active;
        this._startPrompter.visible = Boolean(state) && !active;
        this._stop.visible = active;
        if (active)
            this._icon.add_style_class_name('backstage-indicator-active');
        else
            this._icon.remove_style_class_name('backstage-indicator-active');
    }

    setIslandShown(shown) {
        this._toggleIsland.label.text = shown ? 'Hide island' : 'Show island';
    }
});
