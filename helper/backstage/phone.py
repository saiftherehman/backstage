"""Phone page: a second screen for the island on the local network.

Open the link (or scan the QR code on the island's Phone page) on a phone
connected to the same Wi-Fi. The page shows answers, the teleprompter and the
transcript live, and has an Analyse now button.

Protection:
- HTTPS with a certificate made on this computer (see certificates.py), so
  others on the same Wi-Fi cannot read the traffic or the key
- every request needs the random key from the link (kept in
  ~/.local/state/backstage/phone-key, readable only by you)
- only devices on a private network (home or office Wi-Fi) are answered
- at most MAX_PHONES connections, and Analyse now at most every few seconds
- the page cannot be framed, cached or leak its link through a referrer

/ca.crt needs no key: it is the public half of the certificate authority,
for installing on the phone so it stops warning about the certificate.
"""

import ipaddress
import json
import queue
import secrets
import socket
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import segno

from .certificates import Certificates

STATE_DIR = Path.home() / ".local/state/backstage"
KEY_FILE = STATE_DIR / "phone-key"
QR_FILE = STATE_DIR / "phone-qr.png"
TLS_DIR = STATE_DIR / "tls"
PAGE = Path(__file__).with_name("phone_page.html")
MAX_PHONES = 4
ASK_GAP_SECONDS = 3
# Seconds a phone may take to finish the TLS handshake or send a request.
CONNECTION_TIMEOUT = 30
SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'self'; script-src 'unsafe-inline'; "
                               "style-src 'unsafe-inline'; frame-ancestors 'none'",
}
# Events every new phone needs to catch up on, by type.
REMEMBERED = ("state", "answer", "prompter")


def lan_address():
    """The address other devices on the network reach this machine at."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("192.0.2.1", 9))   # no packet is sent; this just picks the route
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def load_key():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not KEY_FILE.exists():
        KEY_FILE.write_text(secrets.token_urlsafe(18))
        KEY_FILE.chmod(0o600)
    return KEY_FILE.read_text().strip()


class PhoneServer:
    qr_file = QR_FILE

    def __init__(self, port, on_ask):
        self.port = port
        self.on_ask = on_ask
        self.key = load_key()
        self._clients = set()
        self._latest = {}
        self._lock = threading.Lock()
        self._url = ""
        self._last_ask = 0.0
        self.certificates = Certificates(TLS_DIR)
        self.fingerprint = ""
        self._tls = None
        self.url   # makes the certificate before the first phone connects
        server = TLSServer(("0.0.0.0", port), self._handler(), lambda: self._tls)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()

    @property
    def url(self):
        """Link for the phone. The certificate and QR code are remade when
        the address changes."""
        address = lan_address()
        url = f"https://{address}:{self.port}/?key={self.key}"
        if url != self._url:
            self._tls, self.fingerprint = self.certificates.context(address)
            segno.make(url, error="m").save(QR_FILE, scale=8, border=2, dark="#111111", light="#ffffff")
            self._url = url
        return url

    @property
    def ca_url(self):
        return f"https://{lan_address()}:{self.port}/ca.crt"

    @property
    def connected(self):
        return len(self._clients)

    def send(self, kind, data):
        message = json.dumps({"type": kind, **data})
        with self._lock:
            if kind in REMEMBERED:
                self._latest[kind] = message
            for client in list(self._clients):
                client.put(message)

    def _ask(self):
        now = time.monotonic()
        if now - self._last_ask >= ASK_GAP_SECONDS:
            self._last_ask = now
            self.on_ask()

    def _subscribe(self):
        """Returns a queue of messages for a new phone, or None if full."""
        client = queue.Queue()
        with self._lock:
            if len(self._clients) >= MAX_PHONES:
                return None
            for message in self._latest.values():
                client.put(message)
            self._clients.add(client)
        return client

    def _unsubscribe(self, client):
        with self._lock:
            self._clients.discard(client)

    def _handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            timeout = CONNECTION_TIMEOUT

            def log_message(self, *args):
                pass

            def end_headers(self):
                for name, value in SECURITY_HEADERS.items():
                    self.send_header(name, value)
                super().end_headers()

            def _private(self):
                if ipaddress.ip_address(self.client_address[0]).is_private:
                    return True
                self.send_error(403)
                return False

            def _allowed(self):
                if not self._private():
                    return False
                key = parse_qs(urlparse(self.path).query).get("key", [""])[0]
                if secrets.compare_digest(key, server.key):
                    return True
                self.send_error(403)
                return False

            def do_GET(self):
                path = urlparse(self.path).path
                if path == "/ca.crt":
                    if self._private():
                        self._send_ca()
                    return
                if not self._allowed():
                    return
                if path == "/":
                    body = PAGE.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif path == "/events":
                    self._stream()
                else:
                    self.send_error(404)

            def do_POST(self):
                if not self._allowed():
                    return
                if urlparse(self.path).path == "/ask":
                    server._ask()
                    self.send_response(204)
                    self.end_headers()
                else:
                    self.send_error(404)

            def _send_ca(self):
                body = server.certificates.ca_bytes
                self.send_response(200)
                self.send_header("Content-Type", "application/x-x509-ca-cert")
                self.send_header("Content-Disposition", 'attachment; filename="backstage-ca.crt"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _stream(self):
                client = server._subscribe()
                if client is None:
                    self.send_error(503, "Too many phones connected")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                try:
                    while True:
                        try:
                            message = client.get(timeout=15)
                            self.wfile.write(f"data: {message}\n\n".encode())
                        except queue.Empty:
                            self.wfile.write(b": still here\n\n")   # keeps Wi-Fi sleep from dropping it
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    server._unsubscribe(client)

        return Handler


class TLSServer(ThreadingHTTPServer):
    """Does the TLS handshake in each connection's own thread, so a slow or
    broken phone never holds up the others. tls() returns the current
    settings, which change when the network address does."""

    def __init__(self, address, handler, tls):
        super().__init__(address, handler)
        self._tls = tls

    def finish_request(self, request, client_address):
        request.settimeout(CONNECTION_TIMEOUT)
        try:
            request = self._tls().wrap_socket(request, server_side=True)
        except (ssl.SSLError, OSError):
            request.close()   # plain HTTP, a refused certificate, or a dropped connection
            return
        try:
            super().finish_request(request, client_address)
        finally:
            request.close()

    def handle_error(self, request, client_address):
        pass   # a phone going away mid-request is normal
