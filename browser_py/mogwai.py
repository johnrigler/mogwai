#!/usr/bin/env python3
"""Tiny local SB Shell / Mogwai filesystem browser.

No external dependencies. Start it from a directory you want to expose:

    python3 /path/to/sbshell/mogwai/server.py .

Then browse http://127.0.0.1:8765/
"""

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
import argparse
import json
import mimetypes
import os
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ordinal import parse_name  # noqa: E402


class MogwaiHandler(SimpleHTTPRequestHandler):
    root = Path.cwd().resolve()

    def _json(self, payload, status=200):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _safe_path(self, raw_path):
        raw_path = unquote(raw_path or "").lstrip("/")
        candidate = (self.root / raw_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError:
            raise PermissionError("path escapes root")
        return candidate

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            data = (HERE / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if parsed.path == "/api/list":
            query = parse_qs(parsed.query)
            rel = query.get("path", [""])[0]
            try:
                target = self._safe_path(rel)
                if not target.is_dir():
                    return self._json({"error": "not a directory"}, 400)

                entries = []
                for child in sorted(target.iterdir(), key=lambda p: p.name):
                    info = parse_name(child.name)
                    info.update({
                        "path": str(child.relative_to(self.root)),
                        "type": "dir" if child.is_dir() else "file",
                        "size": child.stat().st_size if child.is_file() else None,
                    })
                    entries.append(info)

                return self._json({
                    "root": str(self.root),
                    "path": str(target.relative_to(self.root)) if target != self.root else "",
                    "entries": entries,
                })
            except (PermissionError, FileNotFoundError) as exc:
                return self._json({"error": str(exc)}, 404)

        if parsed.path == "/api/load":
            query = parse_qs(parsed.query)
            rel = query.get("path", [""])[0]
            try:
                target = self._safe_path(rel)
                if not target.is_file():
                    return self._json({"error": "not a file"}, 400)
                text = target.read_text(encoding="utf-8")
                return self._json({
                    "path": str(target.relative_to(self.root)),
                    "mime": mimetypes.guess_type(target.name)[0] or "text/plain",
                    "content": text,
                })
            except UnicodeDecodeError:
                return self._json({"error": "file is not UTF-8 text"}, 415)
            except (PermissionError, FileNotFoundError) as exc:
                return self._json({"error": str(exc)}, 404)

        return self._json({"error": "not found"}, 404)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    MogwaiHandler.root = Path(args.root).resolve()
    os.chdir(MogwaiHandler.root)

    server = ThreadingHTTPServer((args.host, args.port), MogwaiHandler)
    print(f"Mogwai root: {MogwaiHandler.root}")
    print(f"http://{args.host}:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
