# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Serve the siting dashboard at http://localhost:8770/app/ and open the browser.

Run from anywhere: uv run --script app/serve.py [--port 8770] [--no-browser]
The project root is served (read only, localhost only) so the dashboard can link to deliverables/ and
data/processed/sites/METHOD.md. Build the app data first with uv run --script pipeline/build_app.py.
"""
import argparse
import functools
import http.server
import socketserver
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".geojson": "application/geo+json", ".json": "application/json", ".md": "text/markdown; charset=utf-8",
                      ".js": "text/javascript", ".css": "text/css",
                      ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        if self.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/app/")
            self.end_headers()
            return
        super().do_GET()

    def log_message(self, fmt, *args):
        if args and str(args[1]) not in ("200", "304", "302"):
            sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    if not (ROOT / "app" / "data" / "layers.json").exists():
        print("app/data/layers.json is missing. Run: uv run --script pipeline/build_app.py")
        sys.exit(1)
    handler = functools.partial(Handler, directory=str(ROOT))
    with Server(("127.0.0.1", a.port), handler) as httpd:
        url = f"http://localhost:{a.port}/app/"
        print(f"Southwest siting dashboard: {url}  (Ctrl+C to stop)")
        if not a.no_browser:
            threading.Timer(0.6, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("stopped")


if __name__ == "__main__":
    main()
