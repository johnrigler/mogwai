#!/usr/bin/env python3
"""Read-only BSV inventory audit and chronological catalog publisher."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

TXID = re.compile(r"[0-9a-f]{64}\Z")


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=True, separators=(",", ":")) + "\n").encode()
    fd, tmp = tempfile.mkstemp(prefix=".custodian-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
            os.fchmod(out.fileno(), 0o644)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return hashlib.sha256(data).hexdigest()


def audit(db, root, feed, limit=5000, verify=200):
    db.row_factory = sqlite3.Row
    db.execute("BEGIN")
    counts = dict(db.execute("""
        SELECT COUNT(*) AS scanned,
          COALESCE(SUM(t.selected=1),0) AS selected,
          COALESCE(SUM(t.selected=1 AND b.time>0),0) AS dated,
          COALESCE(SUM(t.selected=1 AND (b.time IS NULL OR b.time<=0)),0) AS undated,
          COALESCE(SUM(t.selected=1 AND t.data_complete=0),0) AS incomplete_payloads,
          COALESCE(SUM(t.selected=1 AND (t.raw IS NULL OR t.summary IS NULL)),0) AS missing_db_payloads,
          MAX(CASE WHEN t.selected=1 THEN t.height END) AS newest_selected_block,
          MAX(t.height) AS newest_scanned_block
        FROM transactions t LEFT JOIN blocks b ON b.height=t.height
    """).fetchone())
    counts["duplicate_selected_txids"] = db.execute("""
        SELECT COUNT(*) FROM (SELECT txid FROM transactions WHERE selected=1
        GROUP BY txid HAVING COUNT(*)>1)
    """).fetchone()[0]
    counts["orphan_transactions"] = db.execute("""
        SELECT COUNT(*) FROM transactions t LEFT JOIN blocks b ON b.height=t.height
        WHERE b.height IS NULL
    """).fetchone()[0]
    has_curation = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='bsv_curation'").fetchone()
    counts["classified"] = db.execute("""
        SELECT COUNT(*) FROM transactions t WHERE t.selected=1 AND EXISTS
        (SELECT 1 FROM bsv_curation c WHERE c.txid=t.txid)
    """).fetchone()[0] if has_curation else 0
    records, seen = [], set()
    missing_files = invalid_files = invalid_summaries = sampled = 0
    raw_dir = root / "transactions" / "bsv"
    raw_base = Path(os.path.relpath(raw_dir, feed)).as_posix()
    for row in db.execute("""
        SELECT t.txid,t.height,t.tx_index,t.bytes,t.data_bytes,t.data_complete,
               t.summary,b.time FROM transactions t JOIN blocks b ON b.height=t.height
        WHERE t.selected=1 ORDER BY t.height DESC,t.tx_index DESC
    """):
        if len(records) >= limit:
            break
        txid = row["txid"]
        if not isinstance(txid, str) or not TXID.fullmatch(txid) or txid in seen:
            continue
        seen.add(txid)
        path = raw_dir / (txid + ".json")
        if not path.is_file():
            missing_files += 1
            continue
        if sampled < verify:
            sampled += 1
            try:
                with path.open(encoding="utf-8") as handle:
                    raw = json.load(handle)
                if not isinstance(raw, dict) or raw.get("txid") != txid:
                    raise ValueError("transaction identity mismatch")
            except (OSError, ValueError, UnicodeError):
                invalid_files += 1
                continue
        try:
            summary = json.loads(row["summary"] or "{}")
            if not isinstance(summary, dict):
                raise ValueError("summary is not an object")
        except (ValueError, TypeError):
            invalid_summaries += 1
            summary = {}
        summary = {key: summary[key] for key in (
            "files", "dataOutputs", "selectionReasons", "opReturnText", "title",
            "recordType", "metadata", "curation", "imageCount"
        ) if key in summary}
        summary.update(txid=txid, coin="bsv", ticker="BSV",
                       blockHeight=row["height"], transactionIndex=row["tx_index"],
                       blockTime=max(0, row["time"] or 0), blockTimeEstimated=False,
                       bytes=row["bytes"], dataBytes=row["data_bytes"],
                       dataComplete=bool(row["data_complete"]))
        summary.setdefault("title", "BSV data output" if row["data_bytes"] else "BSV large transaction")
        records.append({"txid": txid, "coin": "bsv", "ticker": "BSV", "sourceId": "bsv",
                        "rawPath": raw_base + "/" + txid + ".json", "summary": summary,
                        "streamLabel": "BSV Custodian", "discoverySource": "custodian"})
    db.rollback()
    report = {"kind": "bsv-custodian", "version": 1,
              "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
              **counts, "catalog_records": len(records), "catalog_limit": limit,
              "archive_files_missing_in_examined_rows": missing_files,
              "archive_files_verified": sampled,
              "archive_files_invalid_in_sample": invalid_files,
              "invalid_summaries_in_examined_rows": invalid_summaries,
              "catalog_newest_block": records[0]["summary"]["blockHeight"] if records else None,
              "catalog_oldest_block": records[-1]["summary"]["blockHeight"] if records else None}
    return report, records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["audit", "publish", "status"])
    parser.add_argument("--db", default=os.environ.get("BSV_DB", "~/.local/state/mogwai/bsv-index.sqlite3"))
    parser.add_argument("--data-root", default=os.environ.get("CHISEL_DATA_ROOT", "~/chisel_data"))
    parser.add_argument("--feed-dir", help="Default: <data-root>/bsv/custodian")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--verify", type=int, default=200)
    args = parser.parse_args(argv)
    if args.limit < 1 or args.limit > 100000 or args.verify < 0:
        parser.error("limit must be 1..100000; verify must be nonnegative")
    root = Path(args.data_root).expanduser().resolve()
    feed = Path(args.feed_dir).expanduser().resolve() if args.feed_dir else root / "bsv" / "custodian"
    if args.command == "status":
        print((feed / "status.json").read_text(), end="")
        return
    if args.command == "publish":
        if feed == root or feed == root / "bsv" or not feed.is_relative_to(root):
            parser.error("publish only to a separate feed directory under data-root")
        feed.mkdir(parents=True, exist_ok=True)
    dbpath = Path(args.db).expanduser().resolve()
    def run():
        with sqlite3.connect(dbpath.as_uri() + "?mode=ro", uri=True, timeout=5) as db:
            db.execute("PRAGMA query_only=ON")
            report, records = audit(db, root, feed, args.limit, args.verify)
        if args.command == "publish":
            if report["selected"] and not records:
                raise RuntimeError("No selected records could be published; prior catalog preserved")
            index = {"version": 1, "transactions": records}
            digest = hashlib.sha256((json.dumps(index, ensure_ascii=True, separators=(",", ":")) + "\n").encode()).hexdigest()
            relative = "index/portal-" + digest + ".json"
            checksum = atomic_json(feed / relative, index)
            atomic_json(feed / "manifest.json", {"version": 1, "title": "BSV Custodian",
                        "defaultIndex": relative, "records": len(records),
                        "generatedAt": report["generatedAt"], "generatedBy": "mogwai/tools/bsv_custodian.py",
                        "hashes": {relative: "sha256-" + checksum}})
            atomic_json(feed / "status.json", report)
        print(json.dumps(report, indent=2))
    if args.command == "publish":
        with (feed / ".custodian.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            run()
    else:
        run()


if __name__ == "__main__":
    main()
