"""Spots questions in what other people say."""

import time

QUESTION_STARTS = {
    "what", "what's", "whats", "how", "why", "when", "where", "who", "which", "whose",
    "can", "could", "would", "will", "should", "shall", "do", "does", "did",
    "is", "are", "was", "were", "have", "has", "tell", "explain", "walk", "describe",
}
# "Do you mind" or "is that right" on their own are not worth an answer.
MIN_WORDS = 4


def looks_like_question(text):
    text = text.strip()
    words = text.lower().split()
    if len(words) < MIN_WORDS:
        return False
    if text.endswith("?"):
        return True
    return words[0].strip(",.") in QUESTION_STARTS


class QuestionDetector:
    def __init__(self, cooldown_seconds):
        self.cooldown = cooldown_seconds
        self._last = 0.0

    def check(self, speaker, text):
        """Returns the question text if this line should get an automatic answer."""
        if speaker != "them" or not looks_like_question(text):
            return None
        now = time.time()
        if now - self._last < self.cooldown:
            return None
        self._last = now
        return text
