"""Prompt wording and the call to the chosen AI tool.

Each analysis is a fresh call with the newest screenshot and the last few
minutes of the meeting, so answers never drift with a long conversation.
"""

from . import providers

# Fixed instructions, identical on every call so the AI service can cache
# them; only the screenshot and the short request below change.
WATCH_SYSTEM = """You are a silent screen assistant for someone in a meeting or presenting. \
Read the screenshot and work out what is on it, whatever it is: questions, a quiz or test, a form, \
code, an error, data, a chart, a table, a document, a slide, a website or a chat. Then give the \
output they need, ready to glance at in a few seconds.

Rules:
- Never ask anything back. No clarifying questions, no offers, no follow-ups. If something is \
unclear, go with the most likely reading.
- If there are questions or tasks on the screen, answer every one directly, in order.
- If there is data, say what it shows and what matters, with the real numbers.
- Plain words. No greeting, no preamble, no closing line, no Markdown headings.
- A black rectangle on the screenshot is the assistant's own panel; ignore it.

Reply in exactly this format:
About: <what the screen is, in one short line>
<the answers or key points, one short line or bullet each>"""

WATCH_REQUEST = """Analyse this screenshot. Under {words} words.{heard}
Recent conversation in the meeting ("Me" is the person you help, "Them" is everyone else):
{transcript}"""

HEARD_PART = '\nSomeone in the meeting just asked: "{question}". Answer that too.'

SUMMARY_SYSTEM = "You write short, factual meeting summaries in Markdown."
SUMMARY_PROMPT = """Here is the transcript of a meeting ("Me" is the person you help). Write a short \
summary with three sections: Summary (a few sentences), Decisions, and Action items (who does what). \
Only include what was actually said.

{transcript}"""


class Assistant:
    def __init__(self, config):
        self.config = config["assistant"]
        self.provider_name = self.config["provider"]

    @property
    def provider(self):
        return providers.ALL.get(self.provider_name)

    def set_provider(self, name):
        if name not in providers.ALL:
            raise ValueError(f"Unknown AI tool {name}")
        self.provider_name = name

    def analyse(self, session, image, question=""):
        """image: absolute path of the JPEG to analyse. Blocking."""
        request = WATCH_REQUEST.format(
            words=self.config["max_answer_words"],
            heard=HEARD_PART.format(question=question) if question else "",
            transcript=session.recent_transcript(self.config["context_seconds"]) or "(nothing yet)")
        return self._run(WATCH_SYSTEM, request, image, session.folder)

    def summarise(self, session):
        """Text for summary.md, or None if nothing was said. Blocking."""
        transcript = session.full_transcript()
        if not transcript:
            return None
        return self._run(SUMMARY_SYSTEM, SUMMARY_PROMPT.format(transcript=transcript), None, session.folder)

    def _run(self, system, prompt, image, folder):
        provider = self.provider
        if not provider or not provider.available():
            raise RuntimeError(f"{self.provider_name} is not installed or not signed in")
        model = self.config["models"].get(provider.name, "")
        return provider.ask(system, prompt, image, str(folder), model, self.config["timeout"])
