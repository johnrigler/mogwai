#!/usr/bin/env python3
"""Read-only, loopback-only browser for a private Daisy checkout; no PHP."""
import argparse
import html
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

STYLE = """
body{margin:0 auto;padding:20px;max-width:1000px;font:16px/1.55 system-ui,sans-serif;color:#182b3a;background:#fff}
header{border-bottom:1px solid #ccd5db;margin-bottom:18px;padding-bottom:12px}
h1{font-size:25px;overflow-wrap:anywhere}a{color:#145b86;overflow-wrap:anywhere}
ul{padding-left:23px}li{padding:5px 0}small{color:#526776}
pre{white-space:pre-wrap;overflow-wrap:anywhere}
@media print{header,.files{display:none}body{padding:0;max-width:none}}
"""
CSP = ("default-src 'none'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; font-src 'self'; media-src 'self'; "
       "script-src 'none'; connect-src 'none'; object-src 'none'; "
       "frame-src 'none'; frame-ancestors 'none'; form-action 'none'; base-uri 'none'")
BLOCKED = {"catalog.sqlite3", "files.txt"}
PART = re.compile(r"1_[0-9]+\.html\Z", re.I)
MEDIA = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".pdf",
         ".mp3", ".wav", ".ogg", ".mp4", ".webm"}

def allowed(name):
    return bool(name) and not name.startswith(".") and name not in BLOCKED and not name.startswith("catalog.sqlite3-")

def resolve(root, request):
    path = unquote(urlsplit(request).path, errors="strict")
    if not path.startswith("/") or "\\" in path or "\x00" in path:
        raise ValueError("Invalid path")
    parts = [part for part in path.split("/") if part]
    if any(not allowed(part) for part in parts):
        raise ValueError("Hidden or restricted path")
    candidate = root
    for part in parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError("Symlinks are not served")
    candidate = candidate.resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("Path outside archive")
    return candidate

def url_for(root, path):
    return "/" + "/".join(quote(p, safe="") for p in path.relative_to(root).parts) + ("/" if path != root and path.is_dir() else "")

def link(root, path, label=None):
    return '<a href="' + html.escape(url_for(root, path), quote=True) + '">' + html.escape(label or path.name) + '</a>'

def page(root, directory):
    crumbs = [link(root, root, "Daisy 2026")]
    cursor = root
    for part in directory.relative_to(root).parts:
        cursor = cursor / part
        crumbs.append(link(root, cursor, part))
    entries = sorted((p for p in directory.iterdir() if allowed(p.name) and not p.is_symlink()
                      and (p.is_dir() or p.is_file())),
                     key=lambda p: (not p.is_dir(), p.name.casefold()))
    parts = [p for p in entries if p.is_file() and PART.fullmatch(p.name)]
    # The archive contains trusted-by-owner HTML fragments. Render in order,
    # with scripts, forms, external resources and frames blocked by CSP.
    sections = []
    for part in parts:
        if part.stat().st_size > 2 * 1024 * 1024:
            sections.append("<p>Large HTML part: " + link(root, part) + "</p>")
        else:
            sections.append(part.read_text(encoding="utf-8", errors="replace"))
    rows = "".join("<li>" + link(root, p, p.name + ("/" if p.is_dir() else "")) + "</li>" for p in entries)
    return ("<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Daisy 2026</title><style>" + STYLE + "</style><body>"
            "<header>" + " / ".join(crumbs) + "<br><small>Private local archive · read only</small></header>"
            "<h1>" + html.escape(directory.name) + "</h1>" + "".join(sections) +
            "<details class='files'" + ("" if sections else " open") +
            "><summary>Files and directories (" + str(len(entries)) + ")</summary><ul>" +
            rows + "</ul></details></body></html>").encode("utf-8")

class Handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def do_GET(self):
        self.serve(False)

    def do_HEAD(self):
        self.serve(True)

    def serve(self, head):
        # Do not accept arbitrary DNS names pointing at loopback.
        port = self.server.server_port
        if self.headers.get("Host", "") not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
            self.send_error(403)
            return
        root = self.server.root
        try:
            path = resolve(root, self.path)
            if path.is_dir():
                if not urlsplit(self.path).path.endswith("/"):
                    self.send_response(301)
                    self.send_header("Location", url_for(root, path))
                    self.end_headers()
                    return
                data = page(root, path)
                mime = "text/html; charset=utf-8"
            elif path.is_file():
                suffix = path.suffix.lower()
                if suffix in {".html", ".htm"}:
                    mime = "text/html; charset=utf-8"
                elif suffix in MEDIA:
                    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                else:
                    # Source files, including legacy PHP, are not executed.
                    mime = "text/plain; charset=utf-8"
                with path.open("rb") as stream:
                    self.send_response(200)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Length", str(path.stat().st_size))
                    self.end_headers()
                    if not head:
                        while chunk := stream.read(65536):
                            self.wfile.write(chunk)
                return
            else:
                self.send_error(404)
                return
        except (ValueError, UnicodeError, OSError):
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if not head:
            self.wfile.write(data)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default="~/daisy_2026")
    parser.add_argument("--port", type=int, default=39692)
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve(strict=True)
    if not root.is_dir() or root == Path.home().resolve() or root == Path("/"):
        parser.error("Choose a specific archive directory, not the home or filesystem root")
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        server.root = root
        print(f"Daisy local browser: http://127.0.0.1:{server.server_port}/", flush=True)
        server.serve_forever()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
