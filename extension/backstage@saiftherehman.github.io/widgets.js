// Small building blocks shared by the island pages.

import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Pango from 'gi://Pango';
import St from 'gi://St';

export function button(label, onClick, styleClass = '') {
    const b = new St.Button({label, style_class: `backstage-button ${styleClass}`, can_focus: false});
    b.connect('clicked', onClick);
    return b;
}

/**
 * A saved path short enough for the island: the home folder becomes "~" and,
 * past maxLength characters, the end is cut off with "...".
 */
export function shortPath(path, maxLength) {
    const home = GLib.get_home_dir();
    const short = path.startsWith(`${home}/`) ? `~${path.slice(home.length)}` : path;
    return short.length > maxLength ? `${short.slice(0, maxLength - 1)}\u2026` : short;
}

export function wrapLabel(text, styleClass) {
    const label = new St.Label({text, style_class: styleClass, x_expand: true});
    label.clutter_text.line_wrap = true;
    label.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
    label.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
    return label;
}

export function scrollable(child, styleClass) {
    const view = new St.ScrollView({
        style_class: styleClass,
        hscrollbar_policy: St.PolicyType.NEVER,
        vscrollbar_policy: St.PolicyType.AUTOMATIC,
        overlay_scrollbars: true,
        y_align: Clutter.ActorAlign.START,
    });
    view.set_child(child);
    return view;
}
