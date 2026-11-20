// Screenshots for the assistant, taken inside GNOME Shell so no permission
// prompt appears. The island stays on screen (hiding it every two seconds
// would flicker); the helper blacks out its area instead.

import Gio from 'gi://Gio';
import Shell from 'gi://Shell';

Gio._promisify(Shell.Screenshot.prototype, 'screenshot');

export async function captureScreen(path) {
    const file = Gio.File.new_for_path(path);
    const stream = file.replace(null, false, Gio.FileCreateFlags.NONE, null);
    try {
        await new Shell.Screenshot().screenshot(false, stream);
    } finally {
        stream.close(null);
    }
}
