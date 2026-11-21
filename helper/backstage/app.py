"""Ties the parts together. There are two kinds of session:

- teleprompter: records the meeting, the script line follows your voice
- assistant: records the meeting and analyses the screen whenever it changes

Everything here may be called from worker threads. Updates go out through
emit(): to the island over D-Bus, and mirrored to the phone page.

Where assistant output shows up depends on how the screen is shared:
- no share, or one window or tab: the island and the phone page
- the entire screen: the island hides, so only the phone page, and it is
  read aloud when the meeting cannot hear the microphone

While the assistant is paused nothing is sent to the AI. The island also
skips screenshots while a private window (config [privacy]) is in front.
"""

import json
import threading
import time
from pathlib import Path

from . import providers, vault
from .assistant import STEERED_WARNING, Assistant, looks_steered
from .audio import Recorder, microphone_available, microphone_live
from .config import SCRIPTS_DIR
from .documents import read_text
from .phone import STATE_DIR, PhoneServer
from .prompter import Prompter, VoiceFollower
from .questions import QuestionDetector
from .sessions import Session
from .share_watch import ShareWatcher
from .speaker import Speaker, speakable
from .transcriber import Segmenter, Transcriber
from .watcher import ScreenWatcher

LAST_SCRIPT = SCRIPTS_DIR / "current.txt"
# The island overwrites this screenshot every few seconds during an assistant session.
LIVE_FRAME = STATE_DIR / "live-frame.png"
KINDS = ("teleprompter", "assistant")

# How each D-Bus signal is passed on to the phone page.
PHONE_EVENTS = {
    "StateChanged": lambda state: ("state", {"state": json.loads(state)}),
    "Transcript": lambda speaker, text: ("transcript", {"speaker": speaker, "text": text}),
    "PrompterMoved": lambda line: ("prompter", {"line": line}),
    "AnswerStarted": lambda reason: ("thinking", {"question": reason}),
    "Answer": lambda reason, answer: ("answer", {"question": reason, "answer": answer}),
    "Error": lambda message: ("error", {"message": message}),
}


class BackstageApp:
    def __init__(self, config, emit):
        self.config = config
        self._bus_emit = emit
        self.session = None
        self.status = ""
        self._recorders = []
        self._follower = None
        self._speaking = False
        self._last_spoken = ""
        self._heard_question = ""
        self.paused = False
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        speech, prompter, assistant = config["speech"], config["prompter"], config["assistant"]
        self.prompter = Prompter(prompter["line_width"], prompter["lookahead_words"], prompter["match_score"])
        self.script = LAST_SCRIPT.read_text() if LAST_SCRIPT.exists() else ""
        self.prompter.load(self.script)
        self.transcriber = Transcriber(speech["whisper_model"], speech["whisper_threads"], self._on_text)
        self.detector = QuestionDetector(assistant["question_cooldown"])
        self.assistant = Assistant(config)
        self.watcher = ScreenWatcher(assistant["min_screen_change"], self._analyse)
        self.share = ShareWatcher(self._on_share_mode)
        self.share.start()
        self.speaker = Speaker(config["voice"]["voice"],
                               lambda: self._set_speaking(True), lambda: self._set_speaking(False))
        self.phone = None
        if config["phone"]["enabled"]:
            self.phone = PhoneServer(config["phone"]["port"], lambda: self.analyse_now("asked from the phone"))
        if config["sessions"]["encrypt"]:
            threading.Thread(target=self._seal_leftovers, daemon=True).start()

    def emit(self, signal, *args):
        self._bus_emit(signal, *args)
        if self.phone and signal in PHONE_EVENTS:
            self.phone.send(*PHONE_EVENTS[signal](*args))

    def _on_share_mode(self, mode):
        self.emit("ShareModeChanged", mode)
        self._changed()

    # State shown in the island and on the phone

    def state(self):
        session = self.session
        return json.dumps({
            "active": session is not None,
            "kind": session.kind if session else "",
            "title": session.title if session else "",
            "started": session.started if session else 0,
            "folder": str(session.folder) if session else "",
            "records": str(self.config["sessions"]["folder"]),
            "live_frame": str(LIVE_FRAME),
            "watch_interval": self.config["assistant"]["watch_interval"],
            "providers": [{"name": p.name, "label": p.label} for p in providers.available()],
            "provider": self.assistant.provider_name,
            "script_lines": self.prompter.lines,
            "prompter_line": self.prompter.line,
            "share_mode": self.share.mode,
            "mic_ok": microphone_available(self.config["audio"]["mic"]),
            "paused": self.paused,
            "private_windows": self.config["privacy"]["private_windows"],
            "chat_notice": self.config["consent"]["chat_notice"],
            "phone_url": self.phone.url if self.phone else "",
            "phone_qr": str(self.phone.qr_file) if self.phone else "",
            "phone_ca_url": self.phone.ca_url if self.phone else "",
            "phone_fingerprint": self.phone.fingerprint if self.phone else "",
            "status": self.status,
        })

    def _changed(self):
        self.emit("StateChanged", self.state())

    def _set_status(self, text):
        self.status = text
        self._changed()

    # Sessions

    def start_session(self, kind, title):
        if kind not in KINDS:
            raise ValueError(f"Unknown session kind {kind}")
        if self.session:
            raise RuntimeError(f"A {self.session.kind} session is already running")
        if kind == "teleprompter" and not self.prompter.lines:
            raise RuntimeError("Load a script first")
        self.session = Session(self.config["sessions"]["folder"], kind, title)
        if kind == "teleprompter":
            self.session.save_script(self.script)
            self.prompter.position = 0
        self.watcher.reset()
        self.paused = False
        self._last_spoken = ""
        self._start_recording()
        self._set_status("Watching the screen" if kind == "assistant" else "Following your voice")
        return self.session.id

    def stop_session(self):
        session = self.session
        if not session:
            return
        self._stop_recording()
        self.speaker.stop()
        self.transcriber.clear()
        self.session = None
        session.close(self.assistant.provider_name)
        self._set_status("Saved to " + session.folder.name)
        threading.Thread(target=self._finish, args=(session,), daemon=True).start()

    def _finish(self, session):
        """After a session: write the summary, then encrypt the folder."""
        if self.config["sessions"]["summary_on_stop"]:
            try:
                summary = self.assistant.summarise(session)
                if summary:
                    session.save_summary(summary)
            except Exception as error:
                self.emit("Error", f"Summary failed: {error}")
        if self.config["sessions"]["encrypt"]:
            try:
                vault.seal(session.folder)
            except Exception as error:
                self.emit("Error", f"Could not encrypt {session.folder.name}: {error}")

    def _seal_leftovers(self):
        """Encrypts session folders left plain: from before encryption was
        turned on, or from a session that ended in a crash."""
        try:
            for file in vault.seal_all(self.config["sessions"]["folder"]):
                print(f"Encrypted {file.name}", flush=True)
        except Exception as error:
            print(f"Could not encrypt the records: {error}", flush=True)

    def _start_recording(self):
        audio, speech = self.config["audio"], self.config["speech"]

        def segmenter(speaker):
            return Segmenter(speaker, audio["speech_level"], speech["silence_seconds"],
                             speech["max_segment_seconds"], self.transcriber.add)

        me, them = segmenter("me"), segmenter("them")
        if self.session.kind == "teleprompter":
            self._follower = VoiceFollower(speech["vosk_model"], self.prompter,
                                           lambda: self.emit("PrompterMoved", self.prompter.line))

        # While an answer is read aloud, both inputs hear it. Skip that audio so
        # the voice never lands in the transcript or triggers another answer.
        def on_mic(chunk):
            if self._speaking:
                return
            me.feed(chunk)
            if self._follower:
                self._follower.feed(chunk)

        def on_output(chunk):
            if not self._speaking:
                them.feed(chunk)

        self._recorders = [Recorder(audio["system"], True, on_output)]
        if microphone_available(audio["mic"]):
            self._recorders.append(Recorder(audio["mic"], False, on_mic))
        for recorder in self._recorders:
            recorder.start()

    def _stop_recording(self):
        for recorder in self._recorders:
            recorder.stop()
        self._recorders = []
        self._follower = None

    def _on_text(self, speaker, text, timestamp):
        session = self.session
        if not session:
            return
        session.add_line(speaker, text, timestamp)
        self.emit("Transcript", speaker, text)
        if session.kind == "assistant" and self.detector.check(speaker, text):
            # A question was asked out loud: analyse the next frame even if
            # the screen has not changed, and answer the question with it.
            self._heard_question = text
            self.analyse_now(f'heard "{text}"')

    # Assistant: screen analysis

    def offer_frame(self, path):
        """A new screenshot from the island, taken without the island in it."""
        if self.session and self.session.kind == "assistant" and not self.paused:
            self.watcher.offer(path, reason="screen changed")

    def analyse_now(self, reason="asked with the hotkey"):
        if not (self.session and self.session.kind == "assistant"):
            self.emit("Error", "Start an assistant session first")
            return
        if self.paused:
            self.emit("Error", "Paused: nothing is sent to the AI. Press Resume (or Super+Alt+H).")
            return
        if LIVE_FRAME.exists():
            self.watcher.offer(str(LIVE_FRAME), force=True, reason=reason)

    def _analyse(self, frame, reason):
        session = self.session
        if not session:
            return
        question, self._heard_question = self._heard_question, ""
        shot = session.screenshots / f"shot-{time.strftime('%H%M%S')}.jpg"
        frame.save_jpeg(shot)
        self.emit("AnswerStarted", reason)
        try:
            answer = self.assistant.analyse(session, str(shot), question)
        except Exception as error:   # a failed answer must never stop the session
            self.emit("Error", f"{self.assistant.provider_name}: {error}")
            return
        if self.session is not session:
            return   # stopped while the AI was working
        steered = looks_steered(answer)
        if steered:
            answer = f"{STEERED_WARNING}\n{answer}"
        session.add_analysis(answer, shot, reason, steered)
        self.emit("Answer", reason, answer)
        if not steered:   # never read a possibly steered answer into the meeting
            self._maybe_speak(answer)

    def _maybe_speak(self, answer):
        """Read aloud during a full screen share when the meeting cannot hear
        the microphone. Skips an answer that says the same as the last one."""
        mode = self.config["voice"]["speak_answers"]
        if mode == "never" or self.share.mode != "screen" or self._speaking:
            return
        own = {r.pid for r in self._recorders}
        if mode != "always" and microphone_live(self.config["audio"]["mic"], own):
            return
        text = speakable(answer)
        if text and text != self._last_spoken:
            self._last_spoken = text
            self.speaker.say(text)

    def _set_speaking(self, speaking):
        self._speaking = speaking

    # Settings changed from the island

    def set_paused(self, paused):
        self.paused = paused
        if self.session and self.session.kind == "assistant":
            self._set_status("Paused: nothing is sent to the AI" if paused else "Watching the screen")
        else:
            self._changed()

    def set_provider(self, name):
        self.assistant.set_provider(name)
        self._changed()

    def load_script(self, text):
        self.script = text.strip()
        SCRIPTS_DIR.mkdir(exist_ok=True)
        LAST_SCRIPT.write_text(self.script)
        self.prompter.load(self.script)
        if self.session and self.session.kind == "teleprompter":
            self.session.save_script(self.script)
        self._changed()

    def load_document(self, path):
        text = read_text(path)
        if not text.strip():
            raise ValueError(f"No text found in {Path(path).name}")
        self.load_script(text)

    def jump_prompter(self, line):
        self.prompter.jump_to_line(max(0, line))
        self.emit("PrompterMoved", self.prompter.line)

    def shutdown(self):
        self.speaker.stop()
        self.stop_session()
        self.share.stop()
