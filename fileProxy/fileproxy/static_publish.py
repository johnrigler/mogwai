"""Publish portable public artifacts for direct static HTTP reads, without FileProxy.

This is a local command, never a public upload endpoint or blockchain verifier.
It writes immutable SHA-256 objects before atomically replacing a small index.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

FORMAT = "chisel-static-artifacts-v1"
MIME_EXT = {
    "image/svg+xml": ".svg",
    "application/octet-stream": ".bin",
    "text/plain": ".txt",
    "application/json": ".json",
}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}(?:/[a-z0-9][a-z0-9._-]{0,79}){0,5}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_BYTES = 8 * 1024 * 1024


def _valid_id(value):
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ValueError("Invalid public artifact ID")
    if any(part in (".", "..") for part in value.split("/")):
        raise ValueError("Relative directory segments are forbidden")
    return value


def _atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".pending-", delete=False) as tmp:
            name = tmp.name
            tmp.write(payload)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def _manifest(root):
    path = root / "manifest.json"
    if not path.exists():
        return {"format": FORMAT, "artifacts": {}}
    document = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(document, dict) or document.get("format") != FORMAT
            or not isinstance(document.get("artifacts"), dict)):
        raise ValueError("Unsupported static artifact manifest")
    return document


def _object_path(digest, media_type):
    return "objects/sha256/" + digest[:2] + "/" + digest + MIME_EXT[media_type]


def publish(root, artifact_id, source, media_type, *, replace=False, hint=""):
    """Publish an existing file; provenance is explicitly NOT established."""
    root = Path(root).expanduser().resolve()
    artifact_id = _valid_id(artifact_id)
    if media_type not in MIME_EXT:
        raise ValueError("Unsupported public media type")
    source = Path(source).expanduser().resolve(strict=True)
    if not source.is_file() or source.stat().st_size > MAX_BYTES:
        raise ValueError("Missing or oversized artifact")
    data = source.read_bytes()
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Empty or oversized artifact")
    digest = hashlib.sha256(data).hexdigest()
    relative = _object_path(digest, media_type)
    root.mkdir(parents=True, exist_ok=True)
    index = _manifest(root)
    current = index["artifacts"].get(artifact_id)
    if current is not None and current.get("sha256") != digest and not replace:
        raise FileExistsError("ID already points to different bytes (use --replace explicitly)")
    object_file = root / relative
    if object_file.exists():
        if object_file.is_symlink() or hashlib.sha256(object_file.read_bytes()).hexdigest() != digest:
            raise ValueError("Existing content-addressed object is corrupted")
    else:
        # Never overwrite a content-addressed object after it has been created.
        # The temporary file is private to the static publication directory.
        object_file.parent.mkdir(parents=True, exist_ok=True)
        if object_file.parent.is_symlink():
            raise ValueError("Refusing a symlinked object directory")
        _atomic_write(object_file, data)
    entry = {
        "path": relative,
        "sha256": digest,
        "bytes": len(data),
        "mediaType": media_type,
        "provenance": "unverified",
    }
    if hint:
        if len(hint) > 256:
            raise ValueError("Source hint too long")
        entry["sourceHint"] = hint
    index["artifacts"][artifact_id] = entry
    _atomic_write(root / "manifest.json",
                  (json.dumps(index, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return entry


def verify(root):
    """Read and hash every referenced object without contacting FileProxy or Polygon."""
    root = Path(root).expanduser().resolve(strict=True)
    index = _manifest(root)
    count = 0
    for identifier, entry in index["artifacts"].items():
        _valid_id(identifier)
        if not isinstance(entry, dict):
            raise ValueError("Malformed entry: " + identifier)
        digest = entry.get("sha256")
        media_type = entry.get("mediaType")
        if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest) or media_type not in MIME_EXT:
            raise ValueError("Malformed digest/type: " + identifier)
        relative = _object_path(digest, media_type)
        if entry.get("path") != relative:
            raise ValueError("Non-canonical object path: " + identifier)
        target = root / relative
        if target.is_symlink() or not target.is_file():
            raise ValueError("Missing or symlinked object: " + identifier)
        content = target.read_bytes()
        if len(content) != entry.get("bytes") or hashlib.sha256(content).hexdigest() != digest:
            raise ValueError("Object bytes do not match index: " + identifier)
        count += 1
    return count


def main(argv=None):
    parser = argparse.ArgumentParser(description="Publish static, content-addressed Chisel artifacts")
    parser.add_argument("--root", required=True, help="Apache-served directory, outside Git checkout")
    actions = parser.add_subparsers(dest="action", required=True)
    add = actions.add_parser("publish")
    add.add_argument("--id", required=True)
    add.add_argument("--file", required=True)
    add.add_argument("--media-type", required=True, choices=sorted(MIME_EXT))
    add.add_argument("--source-hint", default="", help="Informational only; never establishes provenance")
    add.add_argument("--replace", action="store_true")
    actions.add_parser("verify")
    args = parser.parse_args(argv)
    if args.action == "verify":
        print(json.dumps({"ok": True, "verifiedObjects": verify(args.root)}))
    else:
        print(json.dumps(publish(args.root, args.id, args.file, args.media_type,
                                 replace=args.replace, hint=args.source_hint), sort_keys=True))


if __name__ == "__main__":
    main()
