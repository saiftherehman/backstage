// Phone page: QR code and link that open the helper's phone page, a second
// screen for when the whole screen is shared and the island has to hide.

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import St from 'gi://St';

import {wrapLabel} from '../widgets.js';

const QR_SIZE = 168;

export const PhonePage = GObject.registerClass(
class PhonePage extends St.BoxLayout {
    _init() {
        super._init({style_class: 'backstage-page backstage-phone'});
        this._qr = new St.Icon({icon_size: QR_SIZE, style_class: 'backstage-qr'});
        this.add_child(this._qr);

        const text = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, style_class: 'backstage-phone-text', x_expand: true});
        text.add_child(new St.Label({text: 'Use your phone as a second screen', style_class: 'backstage-session-title'}));
        text.add_child(wrapLabel(
            'Scan the code with the phone camera, or open the link in its browser. The phone must be on ' +
            'the same Wi-Fi. It shows answers, the teleprompter and the transcript live, and has an Ask button.',
            'backstage-hint'));
        text.add_child(wrapLabel(
            'When the whole screen is shared the island hides; answers then show on the phone, and are read ' +
            'aloud if the meeting cannot hear your microphone.',
            'backstage-hint'));
        this._url = wrapLabel('', 'backstage-url');
        text.add_child(this._url);
        this.add_child(text);
        this._qrPath = '';
    }

    setState(state) {
        this._url.text = state.phone_url || 'The phone page is turned off in config.toml.';
        this._qr.visible = Boolean(state.phone_qr);
        if (state.phone_qr && state.phone_qr !== this._qrPath) {
            this._qrPath = state.phone_qr;
            this._qr.gicon = new Gio.FileIcon({file: Gio.File.new_for_path(state.phone_qr)});
        }
    }
});
