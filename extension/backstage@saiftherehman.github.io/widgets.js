// Small building blocks shared by the island pages.

import Clutter from 'gi://Clutter';
import Pango from 'gi://Pango';
import St from 'gi://St';

export function button(label, onClick, styleClass = '') {
    const b = new St.Button({label, style_class: `backstage-button ${styleClass}`, can_focus: false});
    b.connect('clicked', onClick);
    return b;
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
