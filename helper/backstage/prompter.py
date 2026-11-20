"""Follows the user's voice through a script.

Vosk gives fast partial results from the microphone. The last few heard
words are matched against the next stretch of the script, and the position
only moves forward, so a stray word never jumps the script backwards.
"""

import json
import re
import textwrap

from rapidfuzz import fuzz

from .audio import SAMPLE_RATE
from .config import MODELS_DIR

# How many of the latest spoken words are matched at once.
MATCH_WORDS = 4


def normalise(word):
    return re.sub(r"[^a-z0-9']", "", word.lower())


class Prompter:
    def __init__(self, line_width, lookahead_words, match_score):
        self.line_width = line_width
        self.lookahead = lookahead_words
        self.match_score = match_score
        self.lines = []
        self._words = []      # (normalised word, line index)
        self.position = 0     # index of the next word to be read

    def load(self, text):
        self.lines = []
        for paragraph in text.splitlines():
            wrapped = textwrap.wrap(paragraph, self.line_width) or [""]
            self.lines.extend(wrapped)
        self._words = [(normalise(w), i) for i, line in enumerate(self.lines)
                       for w in line.split() if normalise(w)]
        self.position = 0

    @property
    def line(self):
        if not self._words:
            return 0
        if self.position >= len(self._words):
            return len(self.lines) - 1
        return self._words[self.position][1]

    def jump_to_line(self, line):
        for i, (_, word_line) in enumerate(self._words):
            if word_line >= line:
                self.position = i
                return

    def hear(self, spoken):
        """Feed recently spoken words. Returns True if the position moved."""
        heard = [w for w in (normalise(s) for s in spoken) if w][-MATCH_WORDS:]
        if not heard or not self._words:
            return False
        best_score, best_end = 0, None
        last_start = min(self.position + self.lookahead, len(self._words) - len(heard))
        for start in range(self.position, last_start + 1):
            window = self._words[start:start + len(heard)]
            score = sum(fuzz.ratio(h, w) for h, (w, _) in zip(heard, window)) / len(heard)
            # Prefer the nearest match when scores tie.
            if score > best_score:
                best_score, best_end = score, start + len(heard)
        if best_end is not None and best_score >= self.match_score and best_end > self.position:
            self.position = best_end
            return True
        return False


class VoiceFollower:
    """Feeds microphone audio to Vosk and passes heard words to a Prompter."""

    def __init__(self, model_name, prompter, on_moved):
        import vosk
        vosk.SetLogLevel(-1)
        self._recognizer = vosk.KaldiRecognizer(vosk.Model(str(MODELS_DIR / model_name)), SAMPLE_RATE)
        self.prompter = prompter
        self.on_moved = on_moved

    def feed(self, chunk):
        if self._recognizer.AcceptWaveform(chunk.tobytes()):
            text = json.loads(self._recognizer.Result()).get("text", "")
        else:
            text = json.loads(self._recognizer.PartialResult()).get("partial", "")
        if text and self.prompter.hear(text.split()):
            self.on_moved()
