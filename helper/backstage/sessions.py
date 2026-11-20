"""Saves each meeting as its own folder of plain files.

sessions/2026-11-20_1430_assistant_weekly-sync/
    session.json      kind, title, start and end time, AI tool used
    transcript.md     everything said, with times
    answers.md        assistant sessions: every screen analysis, with its screenshot
    events.jsonl      the same, one JSON object per line, for scripts
    script.txt        teleprompter sessions: the script used
    summary.md        written when the session ends
    screenshots/      the screenshots that were analysed
"""

import json
import re
import threading
import time
from datetime import datetime
from pathlib import Path


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "meeting"


def clock(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")


class Session:
    def __init__(self, root, kind, title):
        """kind: "teleprompter" or "assistant"."""
        self.kind = kind
        self.title = title or "Meeting"
        self.started = time.time()
        stamp = datetime.fromtimestamp(self.started).strftime("%Y-%m-%d_%H%M")
        self.folder = Path(root) / f"{stamp}_{kind}_{slug(self.title)}"
        self.screenshots = self.folder / "screenshots"
        self.folder.mkdir(parents=True, exist_ok=True)
        if kind == "assistant":
            self.screenshots.mkdir()
        self.lines = []          # (timestamp, speaker, text)
        self._lock = threading.Lock()
        self._write_meta(provider=None, ended=None)
        self._append("transcript.md", f"# {self.title}\n\n"
                     f"Started {datetime.fromtimestamp(self.started):%A %d %B %Y, %H:%M}\n\n")
        if kind == "assistant":
            self._append("answers.md", f"# Screen analysis: {self.title}\n\n")

    @property
    def id(self):
        return self.folder.name

    def add_line(self, speaker, text, timestamp):
        name = "Me" if speaker == "me" else "Them"
        with self._lock:
            self.lines.append((timestamp, speaker, text))
            self._append("transcript.md", f"**{clock(timestamp)} {name}:** {text}\n\n")
            self._event("transcript", speaker=speaker, text=text, time=timestamp)

    def recent_transcript(self, seconds):
        cutoff = time.time() - seconds
        with self._lock:
            lines = [l for l in self.lines if l[0] >= cutoff]
        return "\n".join(f"{'Me' if s == 'me' else 'Them'}: {t}" for _, s, t in lines)

    def full_transcript(self):
        with self._lock:
            return "\n".join(f"[{clock(ts)}] {'Me' if s == 'me' else 'Them'}: {t}"
                             for ts, s, t in self.lines)

    def add_analysis(self, answer, screenshot, reason):
        """reason: why it ran, e.g. "screen changed" or the question heard."""
        now = time.time()
        shot = f"\n\n![screenshot](screenshots/{Path(screenshot).name})"
        with self._lock:
            self._append("answers.md", f"## {clock(now)}, {reason}\n\n{answer}{shot}\n\n")
            self._event("analysis", answer=answer, screenshot=str(screenshot), reason=reason, time=now)

    def save_script(self, text):
        (self.folder / "script.txt").write_text(text)

    def save_summary(self, text):
        (self.folder / "summary.md").write_text(f"# Summary: {self.title}\n\n{text}\n")

    def close(self, provider):
        self._write_meta(provider=provider, ended=time.time())

    def _write_meta(self, provider, ended):
        meta = {"kind": self.kind, "title": self.title, "started": self.started, "ended": ended, "provider": provider}
        (self.folder / "session.json").write_text(json.dumps(meta, indent=2))

    def _event(self, kind, **data):
        self._append("events.jsonl", json.dumps({"type": kind, **data}) + "\n")

    def _append(self, name, text):
        with open(self.folder / name, "a") as f:
            f.write(text)
