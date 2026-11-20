"""Reads answers aloud with Piper, an offline voice, through pw-play."""

import re
import subprocess
import threading

from .config import MODELS_DIR


def speakable(answer):
    """The part of an answer worth saying: everything after the "About:"
    line, without bullet markers or Markdown symbols."""
    lines = [l for l in answer.splitlines() if not l.strip().lower().startswith("about:")]
    text = "\n".join(lines)
    text = re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s+", "", text, flags=re.M)   # bullet markers
    text = re.sub(r"[*_`#>]", "", text)
    lines = [l.strip().rstrip(".") for l in text.splitlines() if l.strip()]
    return ". ".join(lines) + "." if lines else ""


class Speaker:
    def __init__(self, voice, on_start, on_end):
        """on_start/on_end let the app ignore its own voice in the recording."""
        self.voice_path = MODELS_DIR / "piper" / f"{voice}.onnx"
        self.on_start = on_start
        self.on_end = on_end
        self._voice = None
        self._lock = threading.Lock()
        self._player = None

    def say(self, text):
        if text:
            threading.Thread(target=self._say, args=(text,), daemon=True).start()

    def stop(self):
        if self._player:
            self._player.terminate()

    def _say(self, text):
        with self._lock:   # one answer at a time, never two voices at once
            if self._voice is None:
                from piper import PiperVoice
                self._voice = PiperVoice.load(str(self.voice_path))
            chunks = list(self._voice.synthesize(text))
            if not chunks:
                return
            rate = chunks[0].sample_rate
            self.on_start()
            try:
                self._player = subprocess.Popen(
                    ["pw-play", "--raw", "--rate", str(rate), "--channels", "1", "--format", "s16", "-"],
                    stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
                for chunk in chunks:
                    self._player.stdin.write(chunk.audio_int16_bytes)
                self._player.stdin.close()
                self._player.wait()
            except BrokenPipeError:
                pass   # stopped part way through
            finally:
                self._player = None
                self.on_end()
