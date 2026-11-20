"""Tells whether the whole screen or just a window is being shared.

GNOME's own share indicator does not say what is shared, so this watches the
screen cast requests that apps (through the desktop portal) send to the
compositor. RecordMonitor and RecordArea capture the screen, including the
island. RecordWindow captures one window, which the island never appears in.
"""

import re
import subprocess
import threading

SCREEN_METHODS = {"RecordMonitor", "RecordArea"}
WINDOW_METHODS = {"RecordWindow"}
STOP_MEMBERS = {"Stop", "Closed"}
LINE = re.compile(r"path=(\S+); interface=org\.gnome\.Mutter\.ScreenCast\.Session; member=(\w+)")


class ShareWatcher:
    def __init__(self, on_change):
        self.on_change = on_change
        self.mode = "none"
        self._casts = {}   # session path -> "screen" or "window"
        self._process = None

    def start(self):
        self._process = subprocess.Popen(
            ["dbus-monitor", "--session",
             "type='method_call',interface='org.gnome.Mutter.ScreenCast.Session'",
             "type='signal',interface='org.gnome.Mutter.ScreenCast.Session',member='Closed'"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        threading.Thread(target=self._read, daemon=True).start()

    def stop(self):
        if self._process:
            self._process.terminate()

    def _read(self):
        for line in self._process.stdout:
            match = LINE.search(line)
            if not match:
                continue
            path, member = match.groups()
            if member in SCREEN_METHODS:
                self._casts[path] = "screen"
            elif member in WINDOW_METHODS:
                self._casts.setdefault(path, "window")
            elif member in STOP_MEMBERS:
                self._casts.pop(path, None)
            else:
                continue
            self._update()

    def _update(self):
        kinds = set(self._casts.values())
        mode = "screen" if "screen" in kinds else "window" if kinds else "none"
        if mode != self.mode:
            self.mode = mode
            self.on_change(mode)
