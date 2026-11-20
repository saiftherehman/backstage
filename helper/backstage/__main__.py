"""Starts the helper: python -m backstage (run from the helper folder)."""

import os
import signal

import gi

gi.require_version("GLibUnix", "2.0")
from gi.repository import GLib, GLibUnix  # noqa: E402

from . import config
from .app import BackstageApp
from .service import Service


def main():
    # Everything the helper writes (screenshots, transcripts, the phone key)
    # is private to this user.
    os.umask(0o077)
    settings = config.load()
    loop = GLib.MainLoop()
    service = Service(lambda emit: BackstageApp(settings, emit))

    def quit_cleanly():
        if service.app:
            service.app.shutdown()
        loop.quit()
        return GLib.SOURCE_REMOVE

    for sig in (signal.SIGINT, signal.SIGTERM):
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, sig, quit_cleanly)
    loop.run()


if __name__ == "__main__":
    main()
