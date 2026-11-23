#!/usr/bin/env python3
"""Classify BSV candidates offline. Dry-run by default; --apply is reversible.

Reads the existing Mogwai scanner SQLite database. No network requests or
changes to scanner checkpoints. Only records without OP_RETURN data are pruned;
unknown and truncated payloads are retained for later inspection.
"""
import argparse
from collections import Counter
import fcntl
import os
import json
import re
import sqlite3
from pathlib import Path

from bsv_indexer import DEFAULT_DB, atomic_json, connect, export, inspect_files, now

CID = re.compile(r"\b(?:Qm[1-9A-HJ-NP-Za-km-z]{44}|baf[a-z2-7]{20,})\b")
LINK = re.compile(r"(?:https?://|ipfs://)", re.IGNORECASE)
B_PROTOCOL = b"19HxigV4QyBv3tHpQVcUEQyq1pzZVdoAut"
MAP_PROTOCOL = b"1PuQa7K62MiKCtssSLKy1kh56WWU7MtUR5"


def pushed_data(tx):
    """Return observed OP_RETURN pushes, completeness, and output count."""
    parts, outputs, truncated = [], 0, False
    for output in tx.get("vout", []):
        script = output.get("scriptPubKey") or {}
        value = str(script.get("hex", ""))
        match = re.match(r"^(?:[0-9a-fA-F]{2})*", value)
        raw = bytes.fromhex(match.group(0))
        position = 2 if raw.startswith(b"\x00\x6a") else 1 if raw.startswith(b"\x6a") else -1
        if position < 0:
            truncated |= bool(script.get("isTruncated"))
            continue
        outputs += 1
        truncated |= bool(script.get("isTruncated"))
        while position < len(raw):
            op = raw[position]
            position += 1
            if op <= 75:
                length = op
            elif op in (76, 77, 78):
                n = 1 << (op - 76)
                if position + n > len(raw):
                    truncated = True
                    break
                length = int.from_bytes(raw[position:position + n], "little")
                position += n
            else:
                truncated = True
                break
            chunk = raw[position:position + length]
            if len(chunk) < length:
                truncated = True
            parts.append(chunk)
            position += length
    return parts, outputs, truncated


def sniff_mime(data):
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith((b"PK\x03\x04", b"PK\x05\x06")):
        return "application/zip"
    if data[4:8] == b"ftyp":
        return "video/mp4"
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm-or-matroska"
    if data.startswith(b"ID3"):
        return "audio/mpeg"
    if data.startswith(b"RIFF") and data[8:12] == b"WAVE":
        return "audio/wav"
    if data.startswith(b"\x1f\x8b"):
        return "application/gzip"
    lead = data[:256].lstrip().lower()
    if lead.startswith((b"<svg", b"<?xml")) and b"<svg" in data[:2048].lower():
        return "image/svg+xml"
    if lead.startswith((b"<!doctype html", b"<html")):
        return "text/html"
    return None


def readable_payload(data):
    if not 8 <= len(data) <= 16384:
        return False
    text = data.decode("utf-8", "replace")
    return (text.count("\ufffd") < 0.05 * len(text)
            and sum(c.isprintable() or c in "\r\n\t" for c in text) >= 0.9 * len(text))


def classify(tx):
    """Classification reflects evidence, not transaction byte size."""
    parts, outputs, truncated = pushed_data(tx)
    files = inspect_files(tx)
    protocols = []
    if B_PROTOCOL in parts:
        protocols.append("B")
    if MAP_PROTOCOL in parts:
        protocols.append("MAP")
    found = [v for v in (sniff_mime(p) for p in parts) if v]
    declared = [f["mime"] for f in files if f.get("mime")]
    mimes = sorted(set(found + declared))
    sample = " ".join(p[:2048].decode("utf-8", "replace") for p in parts[:16])[:8192]
    has_link = bool(CID.search(sample) or LINK.search(sample))
    readable = any(readable_payload(p) for p in parts)
    if mimes:
        kind, reason = "artifact", "mime-signature-or-declaration"
    elif has_link or protocols or readable:
        kind, reason = "metadata", "protocol-link-or-text"
    elif truncated:
        kind, reason = "unknown", "incomplete-script"
    elif outputs and any(parts):
        kind, reason = "unknown", "unrecognized-payload"
    else:
        kind, reason = "discard", "no-observed-op-return-payload"
    return {"classification": kind, "reason": reason, "mimeTypes": mimes,
            "protocols": protocols, "opReturnOutputs": outputs,
            "observedPayloadBytes": sum(map(len, parts)), "complete": not truncated,
            "hasLink": has_link, "files": files}


def collect(db, root):
    count, sizes, examples, decisions = Counter(), Counter(), {}, []
    folder = root / "transactions/bsv"
    for row in db.execute("SELECT txid,raw FROM transactions WHERE selected=1 ORDER BY height,tx_index"):
        if not row["raw"]:
            continue
        tx = json.loads(row["raw"])
        detail = classify(tx)
        kind, txid = detail["classification"], row["txid"]
        count[kind] += 1
        path = folder / (txid + ".json")
        disk_bytes = path.stat().st_size if path.is_file() and not path.is_symlink() else 0
        sizes[kind] += disk_bytes
        if len(examples.setdefault(kind, [])) < 5:
            examples[kind].append({"txid": txid, "reason": detail["reason"],
                                   "mimeTypes": detail["mimeTypes"], "diskBytes": disk_bytes})
        decisions.append((txid, detail))
    previously = 0
    if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bsv_curation'").fetchone():
        previously = db.execute("SELECT COUNT(*) FROM bsv_curation WHERE pruned=1").fetchone()[0]
    report = {"generatedAt": now(), "selectedExamined": len(decisions),
              "byClass": dict(count), "diskBytesByClass": dict(sizes),
              "prunableBytes": sizes["discard"], "previouslyPruned": previously,
              "examples": examples, "policy": "only complete records without useful OP_RETURN data are prunable"}
    return report, decisions


def curation_table(db):
    db.execute("""CREATE TABLE IF NOT EXISTS bsv_curation (
        txid TEXT PRIMARY KEY, classification TEXT NOT NULL,
        details TEXT NOT NULL, pruned INTEGER NOT NULL DEFAULT 0,
        classified_at TEXT NOT NULL)""")


def remove_safe(root, txid):
    path = root / "transactions/bsv" / (txid + ".json")
    if not path.is_file() or path.is_symlink():
        return False
    try:
        if json.loads(path.read_text()).get("txid") != txid:
            return False
    except (OSError, ValueError, UnicodeError):
        return False
    path.unlink()
    return True


def operate(db, root, directory, limit, restore=False, prune=True):
    curation_table(db)
    if restore:
        rows = db.execute("SELECT txid FROM bsv_curation WHERE pruned=1").fetchall()
        with db:
            for row in rows:
                db.execute("UPDATE transactions SET selected=1 WHERE txid=? AND raw IS NOT NULL", (row["txid"],))
                db.execute("UPDATE bsv_curation SET pruned=0 WHERE txid=?", (row["txid"],))
        report, _ = collect(db, root)
        report.update({"mode": "restore", "restored": len(rows)})
    else:
        report, decisions = collect(db, root)
        pruned_ids = []
        with db:
            for txid, detail in decisions:
                kind = detail["classification"]
                db.execute("""INSERT INTO bsv_curation(txid,classification,details,pruned,classified_at)
                    VALUES(?,?,?,?,?) ON CONFLICT(txid) DO UPDATE SET
                    classification=excluded.classification, details=excluded.details,
                    classified_at=excluded.classified_at""",
                    (txid, kind, json.dumps(detail, separators=(",", ":")), 0, now()))
                if prune and kind == "discard":
                    db.execute("UPDATE transactions SET selected=0 WHERE txid=? AND selected=1", (txid,))
                    db.execute("UPDATE bsv_curation SET pruned=1 WHERE txid=?", (txid,))
                    pruned_ids.append(txid)
        removed = sum(remove_safe(root, txid) for txid in pruned_ids)
        report.update({"mode": "apply" if prune else "enrich", "prunedRecords": len(pruned_ids), "archiveFilesRemoved": removed})
    # Keep scanner's existing manifest/index publication and backfill semantics.
    export(db, directory, limit, root)
    atomic_json(directory / "curation.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--export-dir", default=None)
    parser.add_argument("--limit", type=int, default=1000)
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--apply", action="store_true", help="Classify, suppress uninteresting files, and republish feed (stop scanner first)")
    choice.add_argument("--enrich", action="store_true", help="Persist classifications and update feed without pruning")
    choice.add_argument("--restore", action="store_true", help="Restore records previously pruned by the curator")
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be positive")
    db_path = Path(args.db).expanduser().resolve()
    if not db_path.is_file():
        parser.error("scanner database not found: " + str(db_path))
    root = Path(args.data_root or os.environ.get("CHISEL_DATA_ROOT", "~/chisel_data")).expanduser().resolve()
    directory = Path(args.export_dir or os.environ.get("BSV_EXPORT_DIR", str(root / "bsv"))).expanduser().resolve()
    if args.apply or args.enrich or args.restore:
        # The same exclusive lock used by the BSV daemon. Never mutate a live scan.
        with open(str(db_path) + ".lock", "a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                parser.error("BSV scanner holds the database lock; stop it before --apply or --restore")
            db = connect(db_path)
            try:
                report = operate(db, root, directory, args.limit, restore=args.restore, prune=args.apply)
            finally:
                db.close()
    else:
        db = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        try:
            report, _ = collect(db, root)
            report["mode"] = "dry-run"
        finally:
            db.close()
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
