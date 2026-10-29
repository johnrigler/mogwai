"""Resolve complete eight-byte paper labels in configured Daisy ISO years.

The source is an ordinary directory with a plain record-id file. Reading a
record neither executes its contents nor rewrites an archive/catalog.
"""
import json
import os
from pathlib import Path
import re

from .core import resolve_file, roots_from, scan_root
from .daisy_dates import daisy_date

IDENTIFIER = re.compile(r"^[0-9a-fA-F]{16}$")
ANNUAL = re.compile(r"^daisy_?(\d{4})$", re.I)


def record_id(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value.strip()):
        raise ValueError("Record ID must be exactly 16 hexadecimal characters")
    return value.strip().upper()


def record_config(config, home_config=None):
    """Import only Daisy paths; keep them out of the general public file API."""
    result = {**config, "roots": dict(config["roots"])}
    home = Path(home_config or Path.home() / "config.json").expanduser()
    if not home.exists():
        return result
    shared = json.loads(home.read_text(encoding="utf-8"))
    if not isinstance(shared, dict):
        raise ValueError("Home config must be an object")
    projects = shared.get("projects", {})
    if not isinstance(projects, dict):
        raise ValueError("Home config projects must be an object")
    explicit = roots_from(result)
    explicit_years = {match.group(1) for name, path in explicit.items()
                      for match in [ANNUAL.fullmatch(name) or ANNUAL.fullmatch(path.name)] if match}
    for name, project in projects.items():
        match = ANNUAL.fullmatch(name)
        if name != "daisy" and not match:
            continue
        if name in explicit or (match and match.group(1) in explicit_years):
            continue
        raw = project.get("path") if isinstance(project, dict) else None
        if isinstance(raw, str) and raw.strip():
            result["roots"][name] = str(Path(raw).expanduser())
    return result


def year_roots(config, current_year):
    candidates = []
    for name, path in roots_from(config).items():
        match = ANNUAL.fullmatch(name) or ANNUAL.fullmatch(path.name)
        if match:
            candidates.append((int(match.group(1)), name, path))
        elif name.lower() == "daisy" and path.is_dir():
            for child in path.iterdir():
                if re.fullmatch(r"\d{4}", child.name) and child.is_dir() and not child.is_symlink():
                    candidates.append((int(child.name), name, child))
    seen = set()
    for year, name, path in sorted(candidates, key=lambda item: -item[0]):
        if year <= current_year and path not in seen:
            seen.add(path)
            yield year, name, path


def record_directories(base, identifier):
    for folder, dirs, files in os.walk(base, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".")
                         and not (Path(folder) / d).is_symlink())
        directory = Path(folder)
        marker = directory / "record-id"
        matches = directory.name.upper() == identifier
        if "record-id" in files:
            # A marker qualifies arbitrary directory names; never execute it.
            matches = False
            if not marker.is_symlink() and marker.is_file() and marker.stat().st_size <= 64:
                try:
                    matches = marker.read_text(encoding="ascii").strip().upper() == identifier
                except UnicodeError:
                    pass
        if matches:
            yield directory


def locate_record(config, identifier, current_year=None):
    identifier = record_id(identifier)
    current_year = current_year or daisy_date()["year"]
    searched, matches = [], []
    selected_year = None
    for year, name, base in year_roots(config, current_year):
        if selected_year is not None and year < selected_year:
            break
        searched.append({"isoYear": year, "root": name,
                         "status": "searched" if base.is_dir() else "unavailable"})
        for directory in record_directories(base, identifier):
            selected_year = year
            matches.append((year, name, directory))
    return identifier, searched, matches


def lookup_record(config, identifier, current_year=None):
    identifier, searched, matches = locate_record(config, identifier, current_year)
    roots = roots_from(config)
    records = []
    for year, name, directory in matches:
        relative = directory.relative_to(roots[name]).as_posix()
        entries = scan_root(name, directory)
        for row in entries:
            row["path"] = (directory / row["path"]).relative_to(roots[name]).as_posix()
            row["id"] = name + ":" + row["path"]
        # A short human-readable description remains a source file, not a manifest.
        description = ""
        readme = directory / "README.md"
        if readme.is_file() and not readme.is_symlink() and readme.stat().st_size <= 65536:
            description = readme.read_text(encoding="utf-8", errors="replace")
        records.append({"isoYear": year, "root": name, "path": relative,
                        "description": description, "entries": entries})
    return {"ok": True, "recordId": identifier, "found": bool(records),
            "searched": searched, "records": records, "source": "local-filesystem"}


def resolve_record_file(config, identifier, root, relative):
    target = resolve_file(config, root, relative)
    _, _, matches = locate_record(config, identifier)
    for _, name, directory in matches:
        if name == root and directory in target.parents:
            # Require membership in the same visible file set shown by lookup.
            part = target.relative_to(directory)
            if any(piece.startswith(".") for piece in part.parts):
                break
            original = roots_from(config)[root] / relative
            cursor = directory
            for piece in original.relative_to(directory).parts:
                cursor = cursor / piece
                if cursor.is_symlink():
                    raise FileNotFoundError("Symlinks are not record files")
            if target.is_file() and target.name not in {"catalog.sqlite3", "files.txt"} and not target.name.startswith("catalog.sqlite3-"):
                return target
    raise FileNotFoundError("File is not in the resolved record")
