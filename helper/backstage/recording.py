"""Saves the meeting's audio next to the transcript ([recording] in config.toml).

    both     your microphone and the other people, mixed into one file at
             half volume each, so loud moments on both sides never clip
    others   only what the computer plays (the other people)
    off      no audio file, transcript only

The recorders in audio.py hand over 100 ms chunks from their own threads, and
the two sources do not arrive in step. Each source gets a buffer; a chunk is
mixed and written once every source has one. A source that falls more than a
second behind (a microphone that stopped, for example) is filled with silence,
so the file keeps its timing.
"""

import threading

import av
import numpy as np

from .audio import SAMPLE_RATE

MODES = ("off", "both", "others")
FILE_NAME = "audio.ogg"
MAX_LAG_CHUNKS = 10


class AudioFile:
    def __init__(self, path, sources, bitrate_kbps):
        """sources: names passed to feed(), e.g. ("me", "them")."""
        self.path = path
        self._container = av.open(str(path), "w", format="ogg")
        self._stream = self._container.add_stream("libopus", rate=SAMPLE_RATE, layout="mono")
        self._stream.bit_rate = bitrate_kbps * 1000
        self._buffers = {name: [] for name in sources}
        self._samples = 0
        self._lock = threading.Lock()
        self._closed = False

    def feed(self, source, chunk):
        """chunk: int16 numpy array of 100 ms."""
        with self._lock:
            if self._closed:
                return
            self._buffers[source].append(chunk)
            while self._ready():
                self._write_next()

    def _ready(self):
        buffers = self._buffers.values()
        return all(buffers) or max(len(b) for b in buffers) > MAX_LAG_CHUNKS

    def _write_next(self):
        parts = [b.pop(0) for b in self._buffers.values() if b]
        # Each source gets an equal share of the range, so the sum fits.
        mixed = np.sum([p.astype(np.int32) for p in parts], axis=0) // len(self._buffers)
        samples = np.clip(mixed, -32768, 32767).astype(np.int16)
        frame = av.AudioFrame.from_ndarray(samples.reshape(1, -1), format="s16", layout="mono")
        frame.sample_rate = SAMPLE_RATE
        frame.pts = self._samples
        self._samples += len(samples)
        for packet in self._stream.encode(frame):
            self._container.mux(packet)

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            while any(self._buffers.values()):
                self._write_next()
            for packet in self._stream.encode(None):
                self._container.mux(packet)
            self._container.close()

    @property
    def seconds(self):
        return self._samples / SAMPLE_RATE
