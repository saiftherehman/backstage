"""Removes the other people's voices from the microphone ([audio] echo_cancel).

Without headphones the microphone also hears the speakers, so the other side
would end up in the "Me" transcript and twice in audio.ogg. During a session
this runs a small PipeWire process with its echo-cancel module (WebRTC). It
uses what the speakers play as the reference and offers the cleaned
microphone as a separate input, which the helper records from instead of the
raw one. The system's default microphone is left as it is, so meeting apps
are not affected.
"""

import subprocess
import time

from .audio import node_id
from .phone import STATE_DIR

SOURCE_NODE = "backstage.echo-cancel.source"
CONFIG_FILE = STATE_DIR / "echo-cancel.conf"
START_TIMEOUT = 3.0

CONFIG = """\
context.properties = {{ log.level = 0 }}
context.spa-libs = {{
    audio.convert.* = audioconvert/libspa-audioconvert
    support.*       = support/libspa-support
}}
context.modules = [
    {{ name = libpipewire-module-rt args = {{ }} flags = [ ifexists nofail ] }}
    {{ name = libpipewire-module-protocol-native }}
    {{ name = libpipewire-module-client-node }}
    {{ name = libpipewire-module-adapter }}
    {{ name = libpipewire-module-echo-cancel
        args = {{
            library.name = aec/libspa-aec-webrtc
            # Use what the speakers play as the reference, so meeting apps
            # need no rerouting.
            monitor.mode = true
            audio.channels = 1
            audio.position = [ MONO ]
            capture.props = {{ node.name = "backstage.echo-cancel.capture" {target} }}
            source.props = {{
                node.name = "{source}"
                node.description = "Backstage microphone (echo removed)"
                # Never chosen as the system's default microphone.
                priority.session = 0
                priority.driver = 0
            }}
            sink.props = {{ node.name = "backstage.echo-cancel.sink" }}
            playback.props = {{ node.name = "backstage.echo-cancel.playback" }}
        }}
    }}
]
"""


class EchoCanceller:
    def __init__(self):
        self._process = None

    def start(self, mic_target):
        """mic_target: PipeWire node name of the microphone, or empty for the
        default. Returns the node to record the cleaned microphone from, or
        "" if PipeWire could not set it up."""
        target = f'target.object = "{mic_target}"' if mic_target else ""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(CONFIG.format(target=target, source=SOURCE_NODE))
        self._process = subprocess.Popen(["pipewire", "-c", str(CONFIG_FILE)],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + START_TIMEOUT
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                break
            if node_id(SOURCE_NODE):
                return SOURCE_NODE
            time.sleep(0.1)
        self.stop()
        return ""

    @property
    def pid(self):
        return str(self._process.pid) if self._process else ""

    def stop(self):
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
