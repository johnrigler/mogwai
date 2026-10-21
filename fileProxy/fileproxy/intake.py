"""Paste-to-inbox processing for FileProxy, independent of Chisel.

A paste is classified and reviewed locally. Import preserves original bytes,
URL, time and SHA-256. No blockchain or Git publication is performed here.
"""
from __future__ import annotations

import hashlib
import http.client
import ipaddress
import json
import mimetypes
from pathlib import Path
import re
import socket
import ssl
from datetime import datetime, timezone
from urllib.parse import urlsplit, urljoin, unquote

from .core import atomic_bytes, resolve_file, roots_from, scan
from .daisy_dates import daisy_date
from .names import canonical_filename as safe_filename, require_no_space_path
from .routing import daisy_destination

MAX_PASTE = 65536
MAX_LINKS = 5
MAX_DOCUMENT = 12 * 1024 * 1024
URL_RE = re.compile(r"https://[^\s<>\[\]{}\"']+", re.I)
PDF_MAGIC = b"%PDF-"


def extract_urls(text):
    seen = set()
    result = []
    for match in URL_RE.findall(text):
        candidate = match.rstrip(".,;)]}>")
        if candidate not in seen:
            seen.add(candidate)
            result.append(candidate)
    return result[:MAX_LINKS]


def classify(source):
    value = str(source).casefold()
    if any(term in value for term in (
        "registration", "application", "ordinance", "tax", "licens",
        "legal", "court", "statute", "regulation", "form-211", "pueblo"
    )):
        if "business" in value and ("registration" in value or "form-211" in value):
            return {"root": "certledger", "category": "regulatory/business-registration",
                    "reason": "Business registration form found in the source URL or text"}
        return {"root": "certledger", "category": "legal/regulatory",
                "reason": "Legal or administrative terminology found"}
    return {"root": "daisy", "category": "inbox/unclassified",
            "reason": "No specific domain classification matched"}


def proposed_records(text):
    if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > MAX_PASTE:
        raise ValueError("Paste must contain 1 to 65536 UTF-8 bytes")
    urls = extract_urls(text)
    if len(URL_RE.findall(text)) > MAX_LINKS:
        raise ValueError("Limit each intake to five URLs")
    if urls:
        return [{"kind": "url", "source": url, **classify(url)} for url in urls]
    return [{"kind": "text", "source": "", **classify(text)}]


def url_details(url):
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("Only HTTPS URLs are accepted")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Credentials and nonstandard ports are not supported")
    host = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
    if len(host) > 253 or host == "localhost" or "." not in host:
        raise ValueError("Invalid public hostname")
    if not re.fullmatch(r"[a-z0-9.-]+", host):
        raise ValueError("Invalid hostname")
    try:
        ipaddress.ip_address(host)
        raise ValueError("IP-literal URLs are not supported")
    except ValueError as exc:
        if "not supported" in str(exc):
            raise
    path = parsed.path or "/"
    if len(url) > 4096:
        raise ValueError("URL is too long")
    return parsed, host, path


def public_addresses(host):
    try:
        info = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Could not resolve hostname: " + host) from exc
    results = []
    for entry in info:
        addr = ipaddress.ip_address(entry[4][0])
        if not addr.is_global:
            raise ValueError("URL resolves to a non-public address")
        results.append(str(addr))
    if not results:
        raise ValueError("No public IP addresses found")
    return list(dict.fromkeys(results))


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout=12):
        super().__init__(host, 443, context=ssl.create_default_context(), timeout=timeout)
        self._address = address

    def connect(self):
        raw = socket.create_connection((self._address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def download_https(url):
    current = url
    for _ in range(4):
        parts, host, path = url_details(current)
        addresses = public_addresses(host)
        target = path + (("?" + parts.query) if parts.query else "")
        conn = PinnedHTTPS(host, addresses[0])
        try:
            conn.request("GET", target, headers={
                "Host": host, "User-Agent": "FileProxy/1.1 (document capture)",
                "Accept": "application/pdf,text/plain,text/html,application/octet-stream;q=0.5",
                "Connection": "close"
            })
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location:
                    raise ValueError("Redirect response has no Location")
                current = urljoin(current, location)
                continue
            if response.status != 200:
                raise ValueError("Remote server returned HTTP " + str(response.status))
            declared = response.getheader("Content-Length")
            if declared and int(declared) > MAX_DOCUMENT:
                raise ValueError("Remote document exceeds 12 MiB")
            payload = bytearray()
            while True:
                chunk = response.read(min(65536, MAX_DOCUMENT + 1 - len(payload)))
                if not chunk:
                    break
                payload.extend(chunk)
                if len(payload) > MAX_DOCUMENT:
                    raise ValueError("Remote document exceeds 12 MiB")
            if not payload:
                raise ValueError("Remote document is empty")
            return bytes(payload), current, (response.getheader("Content-Type", "").split(";")[0].strip().lower())
        finally:
            conn.close()
    raise ValueError("Too many redirects")


def canonical_filename(source, kind, mimetype, raw):
    if kind == "text":
        return "pasted-text.txt"
    parsed = urlsplit(source)
    base = unquote(parsed.path.rsplit("/", 1)[-1]) or "document"
    base = safe_filename(base, max_length=100)
    if raw.startswith(PDF_MAGIC):
        if not base.lower().endswith(".pdf"):
            base += ".pdf"
    elif "." not in base:
        base += mimetypes.guess_extension(mimetype) or ".bin"
    return safe_filename(base, max_length=120)


def pdf_pages(payload):
    if not payload.startswith(PDF_MAGIC):
        return None
    try:
        from io import BytesIO
        from pypdf import PdfReader
        return len(PdfReader(BytesIO(payload)))
    except Exception:
        return None


def intake(config, pasted, root_override="auto", note="", index_path=None, downloader=download_https):
    proposals = proposed_records(pasted)
    roots = roots_from(config)
    if len(str(note)) > 4096:
        raise ValueError("Note is too long")
    if root_override != "auto" and root_override not in roots:
        raise ValueError("Destination root is not registered: " + root_override)
    now = datetime.now(timezone.utc)
    dated = daisy_date(now)
    iso_year, week, weekday = dated["year"], dated["week"], dated["weekday"]
    if root_override == "auto":
        for row in proposals:
            if row["root"] == "daisy":
                row["root"] = daisy_destination(roots, iso_year)
    required = {root_override if root_override != "auto" else row["root"] for row in proposals}
    missing = sorted(required - set(roots))
    if missing:
        raise ValueError("Missing destination root(s): " + ", ".join(missing))
    stored = []
    for row in proposals:
        kind = row["kind"]
        if kind == "url":
            raw, resolved_url, mime = downloader(row["source"])
            if not mime:
                mime = mimetypes.guess_type(urlsplit(resolved_url).path)[0] or "application/octet-stream"
            if raw.startswith(PDF_MAGIC):
                mime = "application/pdf"
        else:
            raw = pasted.encode("utf-8")
            resolved_url = ""
            mime = "text/plain"
        if kind == "url" and (urlsplit(resolved_url).path.lower().endswith(".pdf") or mime == "application/pdf"):
            if not raw.startswith(PDF_MAGIC):
                raise ValueError("The source returned non-PDF data for a PDF URL")
        sha = hashlib.sha256(raw).hexdigest()
        root = root_override if root_override != "auto" else row["root"]
        fname = canonical_filename(resolved_url or row["source"], kind, mime, raw)
        # An annual Daisy repo omits the ISO year from its root path.
        # E.g. daisy2026 -> 421/inbox; the multi-year daisy root -> 2026/421/inbox.
        annual = re.fullmatch(r"daisy_?(20[0-9]{2})", root, flags=re.I)
        if annual:
            if int(annual.group(1)) != iso_year:
                raise ValueError("Annual Daisy root year does not match capture year")
            prefix = f"{dated['wwd']}/inbox"
        elif root == "daisy":
            prefix = f"{dated['path']}/inbox"
        else:
            prefix = f"inbox/{dated['path']}"
        path = f"{prefix}/{sha[:20]}-{fname}"
        meta_path = path + ".record.json"
        require_no_space_path(path)
        require_no_space_path(meta_path)
        dst = resolve_file(config, root, path)
        meta_dst = resolve_file(config, root, meta_path)
        if dst.exists():
            if not dst.is_file() or hashlib.sha256(dst.read_bytes()).hexdigest() != sha:
                raise FileExistsError("Hash/path collision: " + path)
            duplicate = True
        else:
            atomic_bytes(dst, raw)
            duplicate = False
        metadata = {
            "schemaVersion": 1,
            "kind": "fileproxy-ingest",
            "project": root,
            "category": row["category"],
            "classificationReason": row["reason"],
            "sourceUrl": row["source"],
            "sourceFilename": (unquote(urlsplit(row["source"]).path.rsplit("/", 1)[-1]) if kind == "url" else ""),
            "submittedText": pasted if kind == "url" and pasted.strip() != row["source"] else "",
            "resolvedUrl": resolved_url,
            "capturedAt": now.isoformat(timespec="seconds"),
            "dateConvention": dated["convention"],
            "localDate": dated["localDate"],
            "archiveTimezone": dated["timezone"],
            "sha256": sha,
            "mime": mime,
            "bytes": len(raw),
            "path": path,
            "note": str(note),
            "title": ("Pueblo of Laguna Form 211: Business Registration Application"
                      if "form-211-business-registration" in row["source"].lower()
                      else fname),
            "pdfPages": pdf_pages(raw),
            "sourceType": kind,
            "reviewStatus": "unreviewed"
        }
        if not meta_dst.exists():
            atomic_bytes(meta_dst, (json.dumps(metadata, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        stored.append({"ok": True, "root": root, "path": path, "metadataPath": meta_path,
                       "sha256": sha, "bytes": len(raw), "mime": mime,
                       "title": metadata["title"], "category": row["category"],
                       "duplicate": duplicate, "pdfPages": metadata["pdfPages"]})
    scan(config, sorted({row["root"] for row in stored}), index_path)
    return {"ok": True, "items": stored, "count": len(stored)}
