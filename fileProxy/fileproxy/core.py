"""Filesystem roots, safe path resolution, and rebuildable hash catalog.

No blockchain dependencies. Daisy and project repositories remain authoritative.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from datetime import datetime, timezone

ROOT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
SKIP_NAMES = {"__pycache__", ".git", ".hg", ".svn"}
DEFAULT_CONFIG = Path(os.environ.get("FILEPROXY_CONFIG", "~/.config/fileproxy/config.json")).expanduser()
DEFAULT_INDEX = os.environ.get("FILEPROXY_INDEX") or None


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_config(path=None):
    path = Path(path or DEFAULT_CONFIG).expanduser()
    if not path.exists():
        return {"version": 1, "roots": {}}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("roots"), dict):
        raise ValueError("Config must be a JSON object containing a roots object")
    for name, root in value["roots"].items():
        if not ROOT_NAME.fullmatch(name) or not isinstance(root, str) or not root.strip():
            raise ValueError("Invalid root mapping: " + str(name))
    return value


def write_config(config, path=None):
    path = Path(path or DEFAULT_CONFIG).expanduser()
    atomic_bytes(path, (json.dumps(config, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return path


def roots_from(config):
    return {name: Path(os.path.expandvars(raw)).expanduser().resolve()
            for name, raw in config["roots"].items()}


def within(base, target):
    return target == base or base in target.parents


def resolve_file(config, name, relative):
    roots = roots_from(config)
    if name not in roots:
        raise ValueError("Unknown root: " + str(name))
    base = roots[name]
    if not isinstance(relative, str) or not relative or "\x00" in relative or "\\" in relative:
        raise ValueError("Invalid relative path")
    part = PurePosixPath(relative)
    if part.is_absolute() or ".." in part.parts or ":" in part.parts[0]:
        raise ValueError("Path must be relative and cannot contain ..")
    destination = (base / Path(*part.parts)).resolve()
    if destination == base or not within(base, destination):
        raise ValueError("Path escapes selected root")
    return destination


def atomic_bytes(destination, data):
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".fileproxy-", dir=str(destination.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def put(config, root, path, data, overwrite=False):
    # Preserve historical paths when reading, but never create whitespace names.
    from .names import require_no_space_path
    require_no_space_path(path)
    if not isinstance(data, bytes):
        raise TypeError("put expects bytes")
    destination = resolve_file(config, root, path)
    if destination.exists() and not overwrite:
        raise FileExistsError(str(destination))
    atomic_bytes(destination, data)
    return {"root": root, "path": path, "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def dated_parts(relative):
    """Read a canonical Daisy ISO year/WWD coordinate, not ALP's old %W%w."""
    from datetime import date
    parts = PurePosixPath(relative).parts
    if parts and parts[0] == "inbox":
        parts = parts[1:]
    if len(parts) >= 3 and re.fullmatch(r"\d{4}", parts[0]) and re.fullmatch(r"\d{3}", parts[1]):
        year, week, weekday = int(parts[0]), int(parts[1][:2]), int(parts[1][2])
        try:
            date.fromisocalendar(year, week, weekday)
        except ValueError:
            return {}
        return {"isoYear": year, "isoWeek": week, "isoDay": weekday,
                "dateConvention": "DAISY:%G/%V%u"}
    return {}


def generated_file(path, excluded=()):
    """Derived catalogs/listings never become source records themselves."""
    return (path.name in {"catalog.sqlite3", "files.txt"}
            or path.name.startswith("catalog.sqlite3-")
            or any(path == target or (path.parent == target.parent
                                      and path.name.startswith(target.name + "-"))
                   for target in excluded))


def scan_root(name, root, excluded=(), directories=None):
    if not root.is_dir():
        raise FileNotFoundError("Missing data root " + name + ": " + str(root))
    entries = []
    for folder, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP_NAMES
                         and not (Path(folder) / d).is_symlink())
        if directories is not None:
            directories.extend((Path(folder) / d).relative_to(root).as_posix() for d in dirs)
        for filename in sorted(files):
            if filename.startswith(".") or filename in SKIP_NAMES:
                continue
            path = Path(folder) / filename
            if path.is_symlink() or not path.is_file() or generated_file(path, excluded):
                continue
            relative = path.relative_to(root).as_posix()
            meta = path.stat()
            entries.append({
                "id": name + ":" + relative,
                "root": name,
                "path": relative,
                "bytes": meta.st_size,
                "mtimeNs": meta.st_mtime_ns,
                "sha256": sha256_file(path),
                "mime": mimetypes.guess_type(filename)[0] or "application/octet-stream",
                **dated_parts(relative)
            })
    return entries


def load_index(path=None):
    from .sqlite_catalog import load_index as read_sqlite
    return read_sqlite(path or DEFAULT_INDEX or "catalog.sqlite3")


def catalog_paths(config, names=None, path=None):
    roots = roots_from(config)
    selected = list(names) if names is not None else sorted(roots)
    missing = [name for name in selected if name not in roots]
    if missing:
        raise ValueError("Unknown root: " + ", ".join(missing))
    explicit = path or DEFAULT_INDEX
    return {name: (Path(explicit).expanduser().resolve() if explicit
                   else roots[name] / "catalog.sqlite3") for name in selected}


def load_catalog(config, path=None, names=None):
    """Read current on-disk catalogs; no server cache or daemon is required."""
    if path or DEFAULT_INDEX:
        return load_index(path or DEFAULT_INDEX)
    entries, timestamps = [], []
    for name, target in catalog_paths(config, names).items():
        index = load_index(target)
        if index["generatedAt"]:
            timestamps.append(index["generatedAt"])
        # The local alias may differ on another machine using this archive.
        entries.extend({**row, "root": name, "id": name + ":" + row["path"]}
                       for row in index["entries"])
    return {"schemaVersion": 2, "generatedAt": max(timestamps, default=None),
            "entries": entries}


def scan(config, names=None, path=None):
    from .sqlite_catalog import replace_roots
    from .inventory import write_scan_inventory
    roots = roots_from(config)
    targets = catalog_paths(config, names or None, path)
    selected = list(targets)
    excluded = set(catalog_paths(config, path=path).values())
    records, directories = {}, {}
    # Finish reading every requested root before changing any derived output.
    for name in selected:
        inventory = roots[name] / "files.txt"
        if inventory.is_symlink() or (inventory.exists() and not inventory.is_file()):
            raise ValueError("Inventory must be a regular file: " + str(inventory))
        target = targets[name]
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError("Catalog must be a regular file: " + str(target))
        directories[name] = []
        records[name] = scan_root(name, roots[name], excluded, directories[name])
    combined = [row for rows in records.values() for row in rows]
    if path or DEFAULT_INDEX:
        destination = Path(path or DEFAULT_INDEX).expanduser().resolve()
        replace_roots(destination, selected, combined)
    else:
        for name, target in targets.items():
            replace_roots(target, [name], records[name], replace_all=True)
    inventories = {}
    for name in selected:
        inventories[name] = write_scan_inventory(roots[name], records[name], directories[name])
    result = {"roots": selected, "scanned": len(combined),
              "total": len(load_catalog(config, path, selected)["entries"]),
              "indexes": {name: str(target) for name, target in targets.items()},
              "inventories": inventories}
    if path or DEFAULT_INDEX:
        result["index"] = str(Path(path or DEFAULT_INDEX).expanduser().resolve())
    elif len(targets) == 1:
        result["index"] = str(next(iter(targets.values())))
    return result


def query_index(index, root=None, prefix=None, text=None, limit=200):
    rows = index["entries"]
    if root:
        rows = [row for row in rows if row.get("root") == root]
    if prefix:
        rows = [row for row in rows if row.get("path", "").startswith(prefix)]
    if text:
        needle = text.casefold()
        rows = [row for row in rows if needle in row.get("path", "").casefold()
                or needle in row.get("sha256", "").casefold()]
    return rows[:max(0, min(int(limit), 1000))]
