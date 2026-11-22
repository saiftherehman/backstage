// Settings window (Extensions app > Backstage > Settings, or Settings in the
// top bar menu).

import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';

import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

// Values of the "display" key, in the order shown.
const DISPLAY_CHOICES = [
    {value: 'island', label: 'Island, always on screen'},
    {value: 'top-bar', label: 'Top bar icon, island only during a session'},
];

export default class BackstagePreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        const page = new Adw.PreferencesPage();
        const group = new Adw.PreferencesGroup({title: 'Display'});
        page.add(group);

        const display = new Adw.ComboRow({
            title: 'Where Backstage lives',
            subtitle: 'In top bar mode, start and stop sessions from the icon menu',
            model: Gtk.StringList.new(DISPLAY_CHOICES.map(c => c.label)),
        });
        const current = DISPLAY_CHOICES.findIndex(c => c.value === settings.get_string('display'));
        display.selected = Math.max(0, current);
        display.connect('notify::selected', () =>
            settings.set_string('display', DISPLAY_CHOICES[display.selected].value));
        group.add(display);

        window.add(page);
    }
}
