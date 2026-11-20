"""Command line AI tools that are already signed in on this machine.

No API keys are stored here: each tool uses its own saved login. Every call
is kept as small as the tool allows, because it runs many times a session.
"""

import base64
import json
import shutil
import subprocess
from pathlib import Path

HOME = Path.home()


class Provider:
    name = ""
    label = ""
    binary = ""
    login_files = ()

    def available(self):
        if not shutil.which(self.binary):
            return False
        return any((HOME / f).exists() for f in self.login_files)

    def ask(self, system, prompt, image, cwd, model, timeout):
        """Returns the answer text. image is an absolute JPEG path, or None."""
        raise NotImplementedError


class ClaudeCode(Provider):
    name = "claude"
    label = "Claude Code"
    binary = "claude"
    login_files = (".claude/.credentials.json",)

    # No tools at all, so text on the screen that tries to instruct the AI
    # can only change the answer, never run anything.
    #
    # A plain call carries the tool's own system prompt, tool list, settings,
    # connectors and skills (about 44,000 tokens) and needs a second round
    # trip to open the image. This keeps only what the answer needs: a short
    # system prompt and the image sent inline (about 1,700 tokens).
    LEAN = ["--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
            "--tools", "", "--strict-mcp-config", "--disable-slash-commands",
            "--no-session-persistence", "--setting-sources", ""]

    def ask(self, system, prompt, image, cwd, model, timeout):
        content = [{"type": "text", "text": prompt}]
        if image:
            data = base64.b64encode(Path(image).read_bytes()).decode()
            content.insert(0, {"type": "image",
                               "source": {"type": "base64", "media_type": "image/jpeg", "data": data}})
        message = {"type": "user", "message": {"role": "user", "content": content}}
        cmd = [self.binary, "-p", *self.LEAN, "--system-prompt", system]
        if model:
            cmd += ["--model", model]
        out = run(cmd, cwd, timeout, json.dumps(message) + "\n")
        for line in reversed(out.splitlines()):
            if '"type":"result"' in line:
                result = json.loads(line)
                if result.get("is_error"):
                    raise RuntimeError(result.get("result") or "the AI tool reported an error")
                return result.get("result", "").strip()
        raise RuntimeError("no answer from the AI tool")


class Codex(Provider):
    name = "codex"
    label = "Codex"
    binary = "codex"
    login_files = (".codex/auth.json",)

    def ask(self, system, prompt, image, cwd, model, timeout):
        answer_file = Path(cwd) / ".codex-answer.txt"
        # Read-only sandbox: text on the screen must never get the tool to run commands.
        cmd = [self.binary, "exec", "--skip-git-repo-check", "--sandbox", "read-only",
               "--output-last-message", str(answer_file)]
        if model:
            cmd += ["-m", model]
        if image:
            cmd += ["-i", image]
        run(cmd + [f"{system}\n\n{prompt}"], cwd, timeout)
        answer = answer_file.read_text().strip()
        answer_file.unlink()
        return answer


class Gemini(Provider):
    name = "gemini"
    label = "Gemini"
    binary = "gemini"
    login_files = (".gemini/oauth_creds.json", ".gemini/settings.json")

    def ask(self, system, prompt, image, cwd, model, timeout):
        text = f"{system}\n\n{prompt}"
        if image:
            text += f"\n\nScreenshot: @{Path(image).relative_to(cwd)}"
        cmd = [self.binary, "-p", text]
        if model:
            cmd += ["-m", model]
        return run(cmd, cwd, timeout).strip()


ALL = {p.name: p for p in (ClaudeCode(), Codex(), Gemini())}


def available():
    return [p for p in ALL.values() if p.available()]


def run(cmd, cwd, timeout, stdin=None):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                            input=stdin, stdin=None if stdin is not None else subprocess.DEVNULL)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise RuntimeError(detail[-1] if detail else f"{cmd[0]} exited with {result.returncode}")
    return result.stdout
