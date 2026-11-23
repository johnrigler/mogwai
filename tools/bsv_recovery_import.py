#!/usr/bin/env python3
"""Merge a Git-published FileProxy recovery root into the existing BSV archive.

Reads the actual catalog.sqlite3, checks every source byte before writing,
and refreshes FileProxy's existing transaction index. Scanner coverage and its
SQLite checkpoints are not changed by a targeted address/subject discovery.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fileProxy"))
from fileproxy.core import atomic_bytes, resolve_file, sha256_file
from fileproxy.names import require_no_space_path


def entries(source):
    source = Path(source).expanduser().resolve(strict=True)
    catalog = source / "catalog.sqlite3"
    if catalog.is_symlink():
        raise ValueError("Recovery catalog must be a regular file")
    with sqlite3.connect(catalog.as_uri() + "?mode=ro", uri=True) as db:
        rows = db.execute("SELECT path,bytes,sha256 FROM files ORDER BY path").fetchall()
    result = []
    config = {"roots": {"recovery": str(source)}}
    for relative, length, digest in rows:
        require_no_space_path(relative)
        if not isinstance(digest, bytes) or len(digest) != 32:
            raise ValueError("Catalog SHA-256 must be a 32-byte BLOB")
        path = resolve_file(config, "recovery", relative)
        if source.joinpath(relative).is_symlink() or not path.is_file():
            raise ValueError("Missing or linked source: " + relative)
        if path.stat().st_size != length or sha256_file(path) != digest.hex():
            raise ValueError("Recovery checksum mismatch: " + relative)
        if relative.startswith(("transactions/bsv/", "artifacts/bsv/", "bsv/discoveries/")):
            result.append((relative, path, digest.hex()))
    if not result:
        raise ValueError("Recovery contains no canonical BSV files")
    return result


def install(source, data_root, reindex=True):
    verified = entries(source)
    root = Path(data_root).expanduser().resolve()
    config = {"roots": {"archive": str(root)}}
    pending, streams, unchanged = [], [], 0
    # Validate all destinations first; never overwrite a different artifact.
    for relative, source_path, digest in verified:
        target = resolve_file(config, "archive", relative)
        if root.joinpath(relative).is_symlink():
            raise ValueError("Destination is a symlink: " + relative)
        payload = None
        if relative.startswith("bsv/discoveries/"):
            discovery = json.loads(source_path.read_text())
            for stream in discovery.get("streams", []):
                if stream.get("coin") != "bsv" or not isinstance(stream.get("address"), str):
                    raise ValueError("Invalid BSV discovery stream")
                streams.append(stream)
        if relative.startswith("transactions/bsv/"):
            incoming = json.loads(source_path.read_text())
            txid = incoming.get("txid", "")
            if len(txid) != 64 or source_path.name != txid + ".json" or any(c not in "0123456789abcdef" for c in txid):
                raise ValueError("Transaction filename/ID mismatch: " + relative)
            if target.exists():
                old = json.loads(target.read_text())
                if old.get("txid") != txid:
                    raise ValueError("Existing transaction ID mismatch: " + relative)
                # Preserve local extension fields while replacing provider fields
                # with the complete recovered transaction for the same ID.
                payload = (json.dumps({**old, **incoming}, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
        if target.exists():
            if sha256_file(target) == digest or payload is not None and target.read_bytes() == payload:
                unchanged += 1
                continue
            if payload is None:
                raise FileExistsError("Different file already exists: " + relative)
        pending.append((target, payload if payload is not None else source_path.read_bytes()))
    for target, payload in pending:
        atomic_bytes(target, payload)
    result = {"copied": len(pending), "unchanged": unchanged, "dataRoot": str(root), "scannerCheckpointsChanged": False}
    if reindex or streams:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fileProxy/tools/fileProxy"))
        import proxy
        proxy.configure_data_root(root)
        for stream in streams:
            previous = proxy.read_json_object(proxy.stream_manifest_path("bsv", stream["address"]))
            body = {**stream}
            if previous.get("label"):
                body["label"] = previous["label"]
            proxy.write_main_stream(body)
        result["streamsMerged"] = len(streams)
        if reindex:
            result["indexRefresh"] = proxy.refresh_all_indexes("bsv")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Recovery root containing the published catalog.sqlite3")
    parser.add_argument("--data-root", default=os.environ.get("CHISEL_DATA_ROOT", "~/chisel_data"))
    args = parser.parse_args(argv)
    try:
        result = install(args.source, args.data_root)
        print(json.dumps(result, indent=2))
        return 0 if result.get("indexRefresh", {}).get("ok", True) else 1
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
