# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Serve the v2 siting dashboard at http://localhost:8772/app-v2/ and open the browser.

Run from anywhere: uv run --script app-v2/serve.py [--port 8772] [--no-browser]
The project root is served (read only, localhost only) because v2 reads its data from ../app/data/ and links to
../deliverables/ and v1's document viewer. The project server on 8770 also serves v2 at http://localhost:8770/app-v2/.
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
                      ".js": "text/javascript", ".css": "text/css", ".woff2": "font/woff2",
                      ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        if self.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/app-v2/")
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
    ap.add_argument("--port", type=int, default=8772)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    if not (ROOT / "app" / "data" / "layers.json").exists():
        print("app/data/layers.json is missing. Run: uv run --script pipeline/build_app.py")
        sys.exit(1)
    handler = functools.partial(Handler, directory=str(ROOT))
    with Server(("127.0.0.1", a.port), handler) as httpd:
        url = f"http://localhost:{a.port}/app-v2/"
        print(f"Southwest siting dashboard v2: {url}  (Ctrl+C to stop)")
        if not a.no_browser:
            threading.Timer(0.6, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("stopped")


if __name__ == "__main__":
    main()
