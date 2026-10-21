"""One HTTP process: original Chisel API plus opt-in general FileProxy routes.

Chisel Handler is intentionally inherited unchanged for every legacy URL.
"""
import base64
import binascii
import hmac
import ipaddress
import json
import mimetypes
import os
import ssl
from pathlib import Path
import sys
from urllib.parse import parse_qs, quote, unquote, urlparse

from .core import load_config, load_catalog, put, query_index, resolve_file, roots_from, scan
from .daisy_dates import daisy_date
from .routing import daisy_destination

_LEGACY_DIR = Path(__file__).resolve().parents[1] / "tools" / "fileProxy"
sys.path.insert(0, str(_LEGACY_DIR))
import proxy as chisel  # noqa: E402: bundled unmodified Chisel service


def make_handler(config_path, index_path, local=False):
    class Handler(chisel.Handler):
        def local_write_allowed(self):
            if not local:
                return False
            try:
                for address in (self.client_address[0], self.server.server_address[0]):
                    ip = ipaddress.ip_address(address)
                    if not (getattr(ip, "ipv4_mapped", None) or ip).is_loopback:
                        return False
            except ValueError:
                return False
            # A proxy must not turn a remote request into a tokenless local one.
            if any(self.headers.get(key) for key in ("Forwarded", "X-Forwarded-For", "X-Real-IP", "X-Forwarded-Host", "Via")):
                return False
            if self.headers.get("Sec-Fetch-Site", "") not in ("", "none", "same-origin"):
                return False
            host = self.headers.get("Host", "").strip().lower()
            port = self.server.server_address[1]
            scheme = "https" if isinstance(self.connection, ssl.SSLSocket) else "http"
            hosts = {name + ":" + str(port) for name in ("127.0.0.1", "localhost", "[::1]")}
            if port == (443 if scheme == "https" else 80):
                hosts.update(("127.0.0.1", "localhost", "[::1]"))
            if host not in hosts:
                return False
            origin = self.headers.get("Origin")
            return origin is None or origin.lower() == scheme + "://" + host

        def do_OPTIONS(self):
            if urlparse(self.path).path.startswith("/v1/"):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-FileProxy-Token")
                self.end_headers()
            else:
                super().do_OPTIONS()

        def response(self, payload, status=200):
            chisel.send_json(self, payload, status)

        def error(self, exc):
            if isinstance(exc, FileNotFoundError):
                status = 404
            elif isinstance(exc, ModuleNotFoundError):
                status = 503
            elif isinstance(exc, FileExistsError):
                status = 409
            elif isinstance(exc, (ValueError, KeyError, TypeError, binascii.Error, json.JSONDecodeError)):
                status = 400
            else:
                status = 500
            self.response({"ok": False, "error": str(exc)}, status)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/index.html", "/catalog", "/packet"):
                page_name = {"/catalog": "catalog.html", "/packet": "packet.html"}.get(parsed.path, "index.html")
                page = (Path(__file__).resolve().parents[1] / "web" / page_name).read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(page)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(page)
                return
            if not parsed.path.startswith("/v1/"):
                return super().do_GET()
            query = parse_qs(parsed.query)
            folder_file = parsed.path.startswith("/v1/fs/")
            if folder_file:
                parts = unquote(parsed.path[len("/v1/fs/"):]).split("/", 1)
                query["root"] = [parts[0]]
                query["path"] = [parts[1] if len(parts) > 1 else "index.html"]
            try:
                if parsed.path == "/v1/health":
                    names = sorted(roots_from(load_config(config_path)))
                    self.response({"ok": True, "service": "fileproxy", "version": 1, "roots": names,
                                   "defaultDaisyRoot": daisy_destination(names, daisy_date()["year"]),
                                   "writeMode": "local" if local else "token",
                                   "writeTokenRequired": not self.local_write_allowed()})
                elif parsed.path == "/v1/roots":
                    self.response({"ok": True, "roots": sorted(roots_from(load_config(config_path)))})
                elif parsed.path == "/v1/folders":
                    from .management import list_folders
                    self.response(list_folders(load_config(config_path), query.get("root", [""])[0]))
                elif parsed.path == "/v1/index":
                    root = query.get("root", [None])[0]
                    rows = query_index(
                        load_catalog(load_config(config_path), index_path, [root] if root else None),
                        root=root,
                        prefix=query.get("prefix", [None])[0],
                        text=query.get("q", [None])[0],
                        limit=int(query.get("limit", ["200"])[0])
                    )
                    self.response({"ok": True, "entries": rows, "count": len(rows)})
                elif parsed.path == "/v1/thumbnail":
                    from .management import checked_file
                    from .packets import pdf_thumbnail
                    target = checked_file(load_config(config_path), query.get("root", [""])[0],
                                          query.get("path", [""])[0], query.get("sha256", [None])[0])
                    if target.suffix.lower() != ".pdf":
                        raise ValueError("Choose a PDF for a first-page thumbnail")
                    stat = target.stat()
                    data = pdf_thumbnail(str(target), stat.st_mtime_ns, stat.st_size)
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "private, max-age=300" if query.get("sha256") else "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    self.wfile.write(data)
                elif parsed.path == "/v1/file" or folder_file:
                    root = query.get("root", [""])[0]
                    relative = query.get("path", [""])[0]
                    target = resolve_file(load_config(config_path), root, relative)
                    if folder_file and target.is_dir():
                        if not parsed.path.endswith("/"):
                            self.send_response(302)
                            self.send_header("Location", parsed.path + "/")
                            self.send_header("Content-Length", "0")
                            self.end_headers()
                            return
                        relative = relative.rstrip("/") + "/index.html"
                        target = resolve_file(load_config(config_path), root, relative)
                    if not target.is_file():
                        raise FileNotFoundError(relative)
                    data = target.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    if target.suffix.lower() in (".html", ".htm", ".svg", ".xhtml"):
                        policy = ("sandbox allow-same-origin allow-modals; default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data: blob:"
                                  if folder_file else "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data: blob:")
                        self.send_header("Content-Security-Policy", policy)
                    if query.get("download") == ["1"]:
                        self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + quote(target.name, safe=""))
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self.response({"ok": False, "error": "Unknown endpoint"}, 404)
            except Exception as exc:
                self.error(exc)

        def do_POST(self):
            parsed = urlparse(self.path)
            if not parsed.path.startswith("/v1/"):
                return super().do_POST()
            secret = os.environ.get("FILEPROXY_WRITE_TOKEN", "")
            supplied = self.headers.get("X-FileProxy-Token", "")
            auth = self.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                supplied = auth[len("Bearer "):]
            if not self.local_write_allowed() and (not secret or not hmac.compare_digest(secret, supplied)):
                self.response({"ok": False, "error": "Write token required"}, 403)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0 or length > 12 * 1024 * 1024:
                    self.response({"ok": False, "error": "Request too large"}, 413)
                    return
                body = json.loads(self.rfile.read(length)) if length else {}
                if not isinstance(body, dict):
                    raise ValueError("Expected a JSON object")
                if parsed.path == "/v1/ingest":
                    from .intake import intake
                    from .routing import split_paste
                    content, tag = split_paste(body.get("text", ""))
                    dest = body.get("destination", "auto")
                    if tag and dest not in ("auto", tag):
                        raise ValueError("Selected destination conflicts with #" + tag)
                    payload = intake(load_config(config_path), content,
                                     tag or dest, body.get("note", ""), index_path=index_path)
                    self.response(payload)
                elif parsed.path == "/v1/scan":
                    names = body.get("roots")
                    if names is not None and not isinstance(names, list):
                        raise ValueError("roots must be an array")
                    result = scan(load_config(config_path), names, index_path)
                    self.response({"ok": True, **result})
                elif parsed.path == "/v1/put":
                    if "base64" in body:
                        data = base64.b64decode(body["base64"], validate=True)
                    elif isinstance(body.get("text"), str):
                        data = body["text"].encode("utf-8")
                    else:
                        raise ValueError("Specify text or base64")
                    result = put(load_config(config_path), body.get("root", ""),
                                 body.get("path", ""), data, bool(body.get("overwrite", False)))
                    self.response({"ok": True, **result})
                elif parsed.path == "/v1/trash":
                    from .management import trash_file
                    self.response(trash_file(load_config(config_path), body.get("root", ""),
                                             body.get("path", ""), body.get("sha256"), index_path))
                elif parsed.path == "/v1/restore":
                    from .management import restore_file
                    self.response(restore_file(load_config(config_path), body.get("root", ""),
                                               body.get("trashId", ""), index_path))
                elif parsed.path == "/v1/mkdir":
                    from .management import make_directory
                    self.response(make_directory(load_config(config_path), body.get("root", ""),
                                                 body.get("path", ""), index_path))
                elif parsed.path == "/v1/transfer":
                    from .management import transfer_files
                    self.response(transfer_files(load_config(config_path), body.get("root", ""),
                                                 body.get("destination", ""), body.get("files"),
                                                 body.get("operation", "copy"), body.get("numbered", False), index_path))
                elif parsed.path == "/v1/packet":
                    from .packets import build_packet
                    self.response(build_packet(load_config(config_path), body, index_path))
                else:
                    self.response({"ok": False, "error": "Unknown endpoint"}, 404)
            except Exception as exc:
                self.error(exc)
    return Handler


def main(config_path=None, index_path=None, local=False):
    chisel.Handler = make_handler(config_path, index_path, local=local)
    if local:
        chisel.HOST = "127.0.0.1"
        print("FileProxy local mode: same-origin loopback writes do not require a token")
    print("FileProxy Inbox: http://127.0.0.1:%s/" % chisel.PORT)
    print("FileProxy v1: /v1/health /v1/roots /v1/index /v1/file /v1/ingest /v1/scan /v1/put")
    print("Chisel legacy API preserved; bind to loopback unless protected by a trusted reverse proxy")
    chisel.main()


if __name__ == "__main__":
    main()
