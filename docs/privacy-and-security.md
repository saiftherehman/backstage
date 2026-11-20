# Privacy and security

Backstage records meetings and reads your screen, so it handles sensitive
material by design. This page says what goes where, what protects it, and what
the remaining risks are.

## What leaves the computer

| Data | Goes to | When |
| --- | --- | --- |
| Screenshots (shrunk, island blacked out) | The AI service behind your command line AI tool | Each analysis in an assistant session |
| Last few minutes of transcript | Same | Each analysis |
| Full transcript | Same | Once, for the summary when a session ends (turn off with `summary_on_stop = false`) |
| Answers, transcript, script | Your phone, over your Wi-Fi | While a phone is connected |

Everything else stays on the laptop: audio is never uploaded (speech is turned
into text locally), and the teleprompter, voice and records are all local.

**Anything visible on screen during an assistant session can be sent**,
including passwords, private messages and other people's data. Stop the
session, or keep sensitive windows off screen, when that matters. What the AI
service keeps and for how long is set by that service and your account, not
by Backstage.

## What stays on the computer

- `sessions/`: transcripts, answers, screenshots, summaries
- `~/.local/state/backstage/`: phone key, QR code, the latest screenshot

The helper creates every file with owner-only permissions (`umask 077`), so
other accounts on the computer cannot read them even if your home folder were
open. Nothing is encrypted at rest; use disk encryption for that.

## Recording other people

Backstage records what others say in a meeting. In many places and companies
you need their consent. Check the rules that apply to you before recording.

## Security review

Reviewed on 2026-11-21. Findings and how they were handled:

| # | Finding | Risk | Status |
| --- | --- | --- | --- |
| 1 | Records and the live screenshot were created readable by other local accounts (umask 002) | Medium | Fixed: helper sets umask 077; existing files tightened |
| 2 | Phone page listened on every network interface, including virtual machine bridges, and answered any address | Medium | Fixed: only private network addresses (home or office LAN, loopback) are answered, on top of the key |
| 3 | Phone page had no browser security headers | Low | Fixed: `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, a strict Content Security Policy, `nosniff` |
| 4 | Unlimited live connections could tie up the helper | Low | Fixed: at most 4 phones |
| 5 | Repeated Analyse now from the phone could burn AI usage | Low | Fixed: at most one every 3 seconds |
| 6 | Text on screen can try to instruct the AI (prompt injection), e.g. a web page saying "ignore your instructions" | Medium | Limited: Claude Code runs with no tools at all, so injected text can only change the answer, never run commands or read files. Codex runs in a read-only sandbox. Gemini CLI does not run tools that need approval in this mode. Treat answers as suggestions |
| 7 | Phone traffic is plain HTTP; someone else on the same Wi-Fi who captures traffic can read it and the key | Medium | Accepted and documented: HTTPS with a self-made certificate makes phones show warnings. Use the phone page only on networks you trust, or set `[phone] enabled = false` |
| 8 | Any program running as you can call the helper's D-Bus methods (start a session, load a file as a script) | Low | Accepted: such a program can already read your files and screen; D-Bus adds no new access |
| 9 | Read-aloud answers could be heard by the meeting | Low | Limited: only during an entire-screen share and only when the microphone is not live; muting inside the meeting app counts as live |

Not found: no shell commands built from strings (all subprocesses use argument
lists), no secrets in the project, no network access other than the phone
page and the AI tool.

## The phone key

The key is 18 random bytes from Python's `secrets` module (about 144 bits),
compared in constant time. It is stored in
`~/.local/state/backstage/phone-key` (owner-only). To make a new one, which
disconnects every phone using the old link:

```bash
rm ~/.local/state/backstage/phone-key
systemctl --user restart backstage-helper
```

## Firewall

With ufw enabled, the phone page is blocked until you allow it. Allow only
your own network, for example for a home network on 192.168.1.x:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 8765 proto tcp comment 'Backstage phone page'
```

Check your network's range with `ip -4 -br addr`.

## Reporting a problem

See [SECURITY.md](../SECURITY.md).
