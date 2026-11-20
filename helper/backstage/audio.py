"""Records the microphone and the system output through PipeWire.

Each recorder runs pw-record in raw mode and hands 100 ms chunks of
16 kHz mono audio to a callback, from its own thread.
"""

import json
import subprocess
import threading

import numpy as np

SAMPLE_RATE = 16000
CHUNK_SAMPLES = SAMPLE_RATE // 10
CHUNK_BYTES = CHUNK_SAMPLES * 2


class Recorder:
    def __init__(self, target, capture_output, on_chunk):
        """target: PipeWire node name, or empty for the default.
        capture_output: record what the speakers play instead of a microphone.
        on_chunk: called with an int16 numpy array per chunk."""
        self.target = target
        self.capture_output = capture_output
        self.on_chunk = on_chunk
        self._process = None
        self._thread = None

    def start(self):
        cmd = ["pw-record", "--raw", "--rate", str(SAMPLE_RATE),
               "--channels", "1", "--format", "s16"]
        if self.capture_output:
            cmd += ["-P", "{ stream.capture.sink=true }"]
        if self.target:
            cmd += ["--target", self.target]
        cmd.append("-")
        self._process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._thread = threading.Thread(target=self._read, daemon=True)
        self._thread.start()

    def _read(self):
        stream = self._process.stdout
        while True:
            data = stream.read(CHUNK_BYTES)
            if len(data) < CHUNK_BYTES:
                break
            self.on_chunk(np.frombuffer(data, dtype=np.int16))

    @property
    def pid(self):
        return str(self._process.pid) if self._process else ""

    def stop(self):
        if self._process:
            self._process.terminate()
            self._process.wait(timeout=5)
            self._process = None


def microphone_available(target):
    """True if the chosen (or default) input is a real microphone.

    When a sound card has no input profile, PipeWire falls back to the
    speaker output as the default source, which would make the other
    people's voices look like the user's."""
    node = target or "@DEFAULT_AUDIO_SOURCE@"
    result = subprocess.run(["wpctl", "inspect", node], capture_output=True, text=True)
    return 'media.class = "Audio/Source"' in result.stdout


def microphone_live(target, own_pids):
    """True if the meeting could be hearing the user's microphone right now:
    a microphone exists, it is not muted, and some app other than this
    helper is recording from an input.

    Muting inside a meeting app usually keeps its recording stream open, so
    that still counts as live. That errs on the safe side: answers are only
    read aloud when nobody in the meeting can hear them."""
    if not microphone_available(target):
        return False
    volume = subprocess.run(["wpctl", "get-volume", target or "@DEFAULT_AUDIO_SOURCE@"],
                            capture_output=True, text=True).stdout
    if "MUTED" in volume:
        return False
    dump = subprocess.run(["pw-dump"], capture_output=True, text=True).stdout
    for node in json.loads(dump or "[]"):
        props = node.get("info", {}).get("props", {})
        if (props.get("media.class") == "Stream/Input/Audio"
                and props.get("stream.capture.sink") not in (True, "true")
                and str(props.get("application.process.id")) not in own_pids):
            return True
    return False


def level(chunk):
    """Loudness of an int16 chunk from 0 to 1 (RMS)."""
    samples = chunk.astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(samples * samples)))
