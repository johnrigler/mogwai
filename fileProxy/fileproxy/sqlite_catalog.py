"""Git-publishable SQLite catalog. File bytes stay in registered roots."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    root TEXT NOT NULL,
    path TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    sha256 BLOB NOT NULL CHECK(length(sha256) = 32),
    mime TEXT NOT NULL,
    iso_year INTEGER,
    iso_week INTEGER,
    iso_day INTEGER,
    date_convention TEXT,
    PRIMARY KEY (root, path)
);
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

def replace_roots(path, names, records, replace_all=False):
    """Replace selected roots atomically, preserving rows for other roots."""
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(target)) as db:
        db.execute("PRAGMA journal_mode=DELETE")
        db.executescript(SCHEMA)
        with db:
            if replace_all:
                db.execute("DELETE FROM files")
            else:
                db.executemany("DELETE FROM files WHERE root = ?", ((name,) for name in names))
            db.executemany(
                """INSERT INTO files
                   (root, path, bytes, mtime_ns, sha256, mime,
                    iso_year, iso_week, iso_day, date_convention)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ((r["root"], r["path"], r["bytes"], r["mtimeNs"],
                  bytes.fromhex(r["sha256"]), r["mime"],
                  r.get("isoYear"), r.get("isoWeek"), r.get("isoDay"),
                  r.get("dateConvention")) for r in records)
            )
            db.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
                ("generatedAt", datetime.now(timezone.utc).isoformat(timespec="seconds"))
            )
            db.execute("PRAGMA user_version=1")

def load_index(path):
    """Return the existing API shape, rendering binary hashes as hex at the edge."""
    target = Path(path).expanduser()
    if not target.is_file():
        return {"schemaVersion": 2, "generatedAt": None, "entries": []}
    with closing(sqlite3.connect(target.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        rows = db.execute(
            """SELECT root, path, bytes, mtime_ns, sha256, mime,
                      iso_year, iso_week, iso_day, date_convention
               FROM files ORDER BY root, path"""
        ).fetchall()
        timestamp = db.execute(
            "SELECT value FROM metadata WHERE key = 'generatedAt'"
        ).fetchone()
    entries = []
    for root, path, size, mtime, digest, mime, year, week, day, convention in rows:
        entry = {"id": root + ":" + path, "root": root, "path": path,
                 "bytes": size, "mtimeNs": mtime, "sha256": digest.hex(), "mime": mime}
        if year is not None:
            entry.update(isoYear=year, isoWeek=week, isoDay=day,
                         dateConvention=convention)
        entries.append(entry)
    return {"schemaVersion": 2, "generatedAt": timestamp[0] if timestamp else None,
            "entries": entries}
