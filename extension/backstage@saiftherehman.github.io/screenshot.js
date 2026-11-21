// Screenshots for the assistant, taken inside GNOME Shell so no permission
// prompt appears.
//
// The island is left out of the picture, so the AI sees what is under it and
// never reads its own earlier answers. The shell paints the screenshot into
// memory during the screenshot() call itself, so hiding the island just for
// that call never reaches the real screen and nothing flickers.

import Gio from 'gi://Gio';
import Shell from 'gi://Shell';

Gio._promisify(Shell.Screenshot.prototype, 'screenshot');

export async function captureScreen(path, leaveOut) {
    const file = Gio.File.new_for_path(path);
    const stream = file.replace(null, false, Gio.FileCreateFlags.NONE, null);
    const wasVisible = leaveOut.visible;
    leaveOut.visible = false;
    let done;
    try {
        done = new Shell.Screenshot().screenshot(false, stream);
    } finally {
        leaveOut.visible = wasVisible;
    }
    try {
        await done;
    } finally {
        stream.close(null);
    }
}
