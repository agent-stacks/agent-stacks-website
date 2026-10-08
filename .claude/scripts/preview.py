#!/usr/bin/env python3
"""
preview.py — serve site/ for local review, and receive DevTools edits back.

    python3 .claude/scripts/preview.py [port]      # default 8137

Three jobs:

  GET  /__dump.js    serves browser-dump.js, which lives outside the docroot
                     so it never ships. Run it in the page with:
                         eval(await (await fetch('/__dump.js')).text())
  GET  anything else serves site/, with caching off so an edit shows up on
                     reload instead of you debugging a problem you already fixed
  POST /__pull       writes the JSON body to .claude/scratch/dump.json

The POST endpoint is what makes browser-dump.js a one-step workflow: run the
snapshot in the page, it posts itself here, and pull-from-browser.py reads it
off disk. Nothing leaves the machine; the server binds to loopback only.

The third job is autosave, so DevTools edits survive a stray click:

  GET  / or /index.html  is served with one extra <script> before </body>,
                         pointing at /__autosave.js. The file on disk is not
                         touched, and site/ still deploys verbatim.
  GET  /__autosave.js    serves browser-autosave.js, also outside the docroot
  POST /__autosave       writes the JSON body to .claude/scratch/autosave.json

A snapshot from an earlier page load is moved to autosave.prev.json before it
is overwritten, so starting to edit again after an accident does not destroy
the copy of what was lost.
"""
import http.server
import json
import pathlib
import socketserver
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
OUT = ROOT / ".claude" / "scratch" / "dump.json"
DUMP_JS = ROOT / ".claude" / "scripts" / "browser-dump.js"
AUTOSAVE_JS = ROOT / ".claude" / "scripts" / "browser-autosave.js"
AUTOSAVE = OUT.with_name("autosave.json")
AUTOSAVE_PREV = OUT.with_name("autosave.prev.json")
INJECT = b'<script src="/__autosave.js"></script>\n'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8137


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(SITE), **kw)

    def end_headers(self):
        # the whole point of a preview server is to never serve a stale file
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def _send(self, body: bytes, ctype: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/__dump.js":
            self._send(DUMP_JS.read_bytes(), "text/javascript; charset=utf-8")
            return
        if path == "/__autosave.js":
            self._send(AUTOSAVE_JS.read_bytes(), "text/javascript; charset=utf-8")
            return
        if path in ("/", "/index.html"):
            # the page, plus the autosave script. Only in what is served here.
            page = (SITE / "index.html").read_bytes()
            head, sep, tail = page.rpartition(b"</body>")
            self._send(head + INJECT + sep + tail if sep else page,
                       "text/html; charset=utf-8")
            return
        super().do_GET()

    def do_POST(self):
        if self.path not in ("/__pull", "/__autosave"):
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        if length > 8 * 1024 * 1024:
            self.send_error(413, "dump too large")
            return
        body = self.rfile.read(length)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        if self.path == "/__pull":
            OUT.write_bytes(body)
            print(f"  <- pulled {len(body)} bytes into {OUT.relative_to(ROOT)}")
        else:
            self._autosave(body)
        self._send(f"wrote {len(body)} bytes\n".encode(), "text/plain")

    @staticmethod
    def _loaded_at(raw: bytes) -> str:
        try:
            return json.loads(raw).get("loadedAt", "")
        except (ValueError, AttributeError):
            return ""

    def _autosave(self, body: bytes) -> None:
        # A snapshot from a different page load is somebody's lost work until
        # proven otherwise. Keep it one generation back instead of replacing it.
        if AUTOSAVE.exists() and self._loaded_at(AUTOSAVE.read_bytes()) != self._loaded_at(body):
            AUTOSAVE.replace(AUTOSAVE_PREV)
        AUTOSAVE.write_bytes(body)

    def log_message(self, fmt, *args):
        if "__pull" in (args[0] if args else ""):
            super().log_message(fmt, *args)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with Server(("127.0.0.1", PORT), Handler) as httpd:
        print(f"serving {SITE.relative_to(ROOT)}/ at http://localhost:{PORT}")
        print(f"POST /__pull writes to {OUT.relative_to(ROOT)}")
        print(f"autosave writes to {AUTOSAVE.relative_to(ROOT)}")
        httpd.serve_forever()
