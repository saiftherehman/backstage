"""Turns speech into text with Whisper.

A Segmenter per audio channel cuts the stream at pauses. Finished pieces go
into one shared queue, and a single worker thread runs Whisper on them so the
two channels never compete for the CPU at the same time.
"""

import queue
import threading
import time

import numpy as np

from .audio import SAMPLE_RATE, level
from .config import MODELS_DIR

CHUNK_SECONDS = 0.1
# Short bursts (a cough, a click) are not worth transcribing.
MIN_SPEECH_SECONDS = 0.6


class Segmenter:
    def __init__(self, speaker, speech_level, silence_seconds, max_seconds, on_segment):
        self.speaker = speaker
        self.speech_level = speech_level
        self.silence_chunks = int(silence_seconds / CHUNK_SECONDS)
        self.max_chunks = int(max_seconds / CHUNK_SECONDS)
        self.on_segment = on_segment
        self._chunks = []
        self._speech_chunks = 0
        self._quiet_run = 0
        self._started_at = None

    def feed(self, chunk):
        loud = level(chunk) >= self.speech_level
        if not self._chunks and not loud:
            return
        if not self._chunks:
            self._started_at = time.time()
        self._chunks.append(chunk)
        if loud:
            self._speech_chunks += 1
            self._quiet_run = 0
        else:
            self._quiet_run += 1
        if self._quiet_run >= self.silence_chunks or len(self._chunks) >= self.max_chunks:
            self._flush()

    def _flush(self):
        if self._speech_chunks * CHUNK_SECONDS >= MIN_SPEECH_SECONDS:
            audio = np.concatenate(self._chunks).astype(np.float32) / 32768.0
            self.on_segment(self.speaker, audio, self._started_at)
        self._chunks = []
        self._speech_chunks = 0
        self._quiet_run = 0


class Transcriber:
    def __init__(self, model_name, threads, on_text):
        self.model_name = model_name
        self.threads = threads
        self.on_text = on_text
        self._queue = queue.Queue()
        self._model = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def add(self, speaker, audio, started_at):
        self._queue.put((speaker, audio, started_at))

    def clear(self):
        while not self._queue.empty():
            self._queue.get_nowait()

    def _load(self):
        # Imported here so the helper starts fast and only pays for Whisper
        # once a meeting begins.
        from faster_whisper import WhisperModel
        self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8",
                                   cpu_threads=self.threads,
                                   download_root=str(MODELS_DIR / "whisper"))

    def _run(self):
        while True:
            speaker, audio, started_at = self._queue.get()
            if self._model is None:
                self._load()
            segments, _ = self._model.transcribe(audio, beam_size=1,
                                                 condition_on_previous_text=False,
                                                 vad_filter=True)
            text = " ".join(s.text.strip() for s in segments).strip()
            if text:
                self.on_text(speaker, text, started_at)
