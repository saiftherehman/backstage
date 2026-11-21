"""Decides which screenshots are worth analysing, to keep AI use low.

The island sends a screenshot every couple of seconds during an assistant
session. A frame is only analysed when:
- it differs from the last frame analysed (an unchanged screen costs nothing)
- the screen has settled: it looks the same as the frame just before it, so
  nothing is sent while you scroll or type
- no analysis is already running (only the newest frame matters)

Frames are shrunk before sending, since image tokens grow with size. The
island is already left out of each screenshot (see screenshot.js).
"""

import threading

import numpy as np
from PIL import Image

# Thumbnail used to compare frames: small enough to ignore a blinking cursor,
# big enough to notice a new line of text.
THUMB = (96, 54)
PIXEL_TOLERANCE = 24
# Text stays readable at this width; larger only costs more tokens.
SEND_WIDTH = 1280
JPEG_QUALITY = 70


class Frame:
    def __init__(self, path):
        image = Image.open(path).convert("RGB")
        self.image = image
        self.fingerprint = np.asarray(image.convert("L").resize(THUMB), dtype=np.int16)

    def differs_from(self, other, threshold):
        """threshold: share of thumbnail pixels (0 to 1) that must differ."""
        if other is None:
            return True
        moved = np.abs(self.fingerprint - other.fingerprint) > PIXEL_TOLERANCE
        return moved.mean() >= threshold

    def save_jpeg(self, path):
        image = self.image
        if image.width > SEND_WIDTH:
            image = image.resize((SEND_WIDTH, round(image.height * SEND_WIDTH / image.width)), Image.LANCZOS)
        image.save(path, "JPEG", quality=JPEG_QUALITY)
        return path


class ScreenWatcher:
    def __init__(self, min_change, analyse):
        """analyse(frame, reason) runs one analysis and blocks until done."""
        self.min_change = min_change
        self.analyse = analyse
        self._previous = None   # the frame just before, to tell if the screen settled
        self._analysed = None   # the last frame sent to the AI
        self._busy = False
        self._force_next = None   # reason for an analysis asked for while busy

    def reset(self):
        self._previous = None
        self._analysed = None
        self._force_next = None

    def offer(self, path, force=False, reason=""):
        """Called with each new screenshot; returns at once. If an analysis is
        still running the frame is dropped, but a forced request is kept for
        the next frame."""
        if self._busy:
            if force:
                self._force_next = reason
            return
        if self._force_next is not None:
            force, reason, self._force_next = True, self._force_next, None
        self._busy = True
        threading.Thread(target=self._run, args=(path, force, reason), daemon=True).start()

    def _run(self, path, force, reason):
        try:
            frame = Frame(path)
            settled = not frame.differs_from(self._previous, self.min_change)
            self._previous = frame
            new = frame.differs_from(self._analysed, self.min_change)
            if force or (settled and new):
                self._analysed = frame
                self.analyse(frame, reason)
        finally:
            self._busy = False
