"""Idempotent catalog of external video references, separate from file hashes.

The original shared URL is retained. No YouTube download or ledger write occurs.
"""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import os
import re
import sqlite3
from urllib.parse import parse_qs, urlsplit

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
SCHEMA = """
CREATE TABLE IF NOT EXISTS url_resources (
    key TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    source_url TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(provider, provider_id)
);
"""


def normalize_youtube_url(url):
    if not isinstance(url, str) or len(url) > 4096:
        raise ValueError("Expected a YouTube URL up to 4096 characters")
    url = url.strip()
    parts = urlsplit(url)
    if parts.scheme.lower() != "https" or not parts.hostname or parts.username or parts.password or parts.port not in (None, 443):
        raise ValueError("Expected a public HTTPS YouTube URL without credentials or custom port")
    host = parts.hostname.lower().rstrip(".")
    if host in ("youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"):
        path = parts.path.rstrip("/")
        if path == "/watch":
            ids = parse_qs(parts.query).get("v", [])
            video_id = ids[0] if len(ids) == 1 else ""
        elif path.startswith(("/shorts/", "/live/", "/embed/")):
            segments = path.split("/")
            video_id = segments[2] if len(segments) == 3 else ""
        else:
            video_id = ""
    elif host == "youtu.be":
        segments = parts.path.strip("/").split("/")
        video_id = segments[0] if len(segments) == 1 else ""
    else:
        raise ValueError("Unsupported video host")
    if not VIDEO_ID.fullmatch(video_id):
        raise ValueError("Invalid YouTube video ID")
    return {"key": "youtube:" + video_id, "provider": "youtube",
            "providerId": video_id,
            "canonicalUrl": "https://www.youtube.com/watch?v=" + video_id}


def database_path(config_path):
    override = os.environ.get("FILEPROXY_URL_CATALOG")
    if override:
        return Path(override).expanduser()
    return Path(config_path).expanduser().parent / "urls.sqlite3"


def lookup(path, url):
    reference = normalize_youtube_url(url)
    db_path = Path(path).expanduser()
    if not db_path.is_file():
        return None
    with closing(sqlite3.connect(db_path)) as db:
        row = db.execute(
            "SELECT key, provider, provider_id, canonical_url, source_url, created_at "
            "FROM url_resources WHERE key = ?", (reference["key"],)
        ).fetchone()
    return record(row) if row else None


def record(row):
    return dict(zip(("key", "provider", "providerId", "canonicalUrl",
                     "sourceUrl", "createdAt"), row))


def resolve(path, url):
    reference = normalize_youtube_url(url)
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise ValueError("URL catalog must not be a symlink")
    with closing(sqlite3.connect(target, timeout=15)) as db:
        db.execute("PRAGMA busy_timeout=15000")
        with db:
            db.executescript(SCHEMA)
            created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            cursor = db.execute(
                "INSERT OR IGNORE INTO url_resources "
                "(key, provider, provider_id, canonical_url, source_url, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (reference["key"], reference["provider"], reference["providerId"],
                 reference["canonicalUrl"], url.strip(), created_at)
            )
            created = cursor.rowcount == 1
            row = db.execute(
                "SELECT key, provider, provider_id, canonical_url, source_url, created_at "
                "FROM url_resources WHERE key = ?", (reference["key"],)
            ).fetchone()
    return {"ok": True, "created": created, "resource": record(row)}
