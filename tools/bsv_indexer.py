#!/usr/bin/env python3
"""Read BSV history, checkpoint every batch, and export a static Chisel feed.

Only public read endpoints are used. SQLite, previews and JSON exports are
off-chain working data; no wallet, keys, signing or broadcast path exists.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API = "https://api.whatsonchain.com/v1/bsv/main"
DEFAULT_DB = "~/.local/state/mogwai/bsv-index.sqlite3"
HASH = re.compile(r"^[0-9a-f]{64}$")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def checked_hash(value):
    value = str(value or "").lower()
    if not HASH.fullmatch(value):
        raise ValueError("Provider returned an invalid hash")
    return value


class WhatsOnChain:
    """Provider-specific reads. A POST to /txs retrieves details, never broadcasts."""
    def __init__(self, delay=0.5):
        self.delay = delay
        self.last_request = 0
        self.page_cache = {}

    def request(self, path, payload=None):
        # Callers construct paths; never follow page URLs supplied by a provider.
        for attempt in range(4):
            time.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            data = None if payload is None else json.dumps(payload).encode()
            req = Request(API + path, data=data, headers={
                "Accept": "application/json", "Content-Type": "application/json",
                "User-Agent": "Mogwai-BSV-reader/1"})
            try:
                with urlopen(req, timeout=30) as response:
                    body = response.read(32 * 1024 * 1024 + 1)
                if len(body) > 32 * 1024 * 1024:
                    raise ValueError("Provider response exceeded 32 MiB; checkpoint retained")
                return json.loads(body)
            except HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                    raise ValueError("WhatsOnChain HTTP " + str(exc.code)) from None
                try:
                    delay = float(exc.headers.get("Retry-After", 2 ** (attempt + 1)))
                except (TypeError, ValueError):
                    delay = 2 ** (attempt + 1)
                time.sleep(min(max(delay, 1), 30))
            except (URLError, TimeoutError, OSError):
                if attempt == 3:
                    raise ValueError("WhatsOnChain network request failed") from None
                time.sleep(2 ** (attempt + 1))
        raise ValueError("WhatsOnChain request failed")

    def tip(self):
        return int(self.request("/chain/info")["blocks"])

    def block(self, height):
        block = self.request("/block/height/" + str(height))
        if int(block.get("height", -1)) != height:
            raise ValueError("Provider returned the wrong block height")
        checked_hash(block.get("hash"))
        if int(block.get("txcount", 0)) < 1:
            raise ValueError("Block has no declared transaction count")
        return block

    def transactions(self, block, start, limit):
        count = int(block["txcount"])
        preview = block.get("tx", [])
        if start < len(preview):
            ids = preview[start:start + min(limit, len(preview) - start)]
        else:
            # WoC pages contain the remaining IDs AFTER the initial 100.
            # Verified against mainnet block 892006: 100 + 32792 = 32892.
            page_size = int((block.get("pages") or {}).get("size", 0))
            if page_size < 1:
                # The independent index endpoint remains usable if pages vanish.
                return [self.request("/block/height/%d/txindex/%d" %
                                     (block["height"], start))]
            page_no, offset = divmod(start - len(preview), page_size)
            key = (block["hash"], page_no + 1)
            if key not in self.page_cache:
                page = self.request("/block/hash/%s/page/%d" % key)
                if not isinstance(page, list):
                    raise ValueError("Invalid block transaction page")
                expected = min(page_size, count - len(preview) - page_no * page_size)
                if len(page) != expected:
                    raise ValueError("Incomplete block transaction page; checkpoint retained")
                self.page_cache = {key: page}
            ids = self.page_cache[key][offset:offset + min(limit, page_size - offset)]
        if not ids:
            raise ValueError("Incomplete block transaction list; checkpoint retained")
        ids = [checked_hash(txid) for txid in ids]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate transaction IDs in provider page")
        txs = self.request("/txs", {"txids": ids})
        if not isinstance(txs, list):
            raise ValueError("Invalid bulk transaction response")
        by_id = {checked_hash(tx.get("txid")): tx for tx in txs if isinstance(tx, dict)}
        if len(txs) != len(ids) or set(by_id) != set(ids):
            raise ValueError("Provider omitted transactions; checkpoint retained")
        return [by_id[txid] for txid in ids]


def inspect_transaction(tx, min_tx_bytes, min_data_bytes):
    checked_hash(tx.get("txid"))
    size = int(tx.get("size", 0))
    if size < 1 or not isinstance(tx.get("vout"), list):
        raise ValueError("Transaction lacks size or outputs")
    data_bytes, data_outputs, texts = 0, 0, []
    complete = True
    for output in tx["vout"]:
        script = output.get("scriptPubKey") or {}
        complete = complete and not bool(script.get("isTruncated"))
        value = str(script.get("hex", ""))
        # Retain provider-truncated scripts as previews, never complete files.
        match = re.match(r"^(?:[0-9a-fA-F]{2})*", value)
        raw = bytes.fromhex(match.group(0))
        if raw.startswith(b"\x00\x6a"):
            pos = 2
        elif raw.startswith(b"\x6a"):
            pos = 1
        else:
            continue
        data_outputs += 1
        while pos < len(raw):
            op = raw[pos]
            pos += 1
            if op <= 75:
                length = op
            elif op in (76, 77, 78):
                n = 1 << (op - 76)
                if pos + n > len(raw):
                    complete = False
                    break
                length = int.from_bytes(raw[pos:pos + n], "little")
                pos += n
            else:
                continue
            part = raw[pos:pos + length]
            data_bytes += len(part)
            pos += length
            if len(part) < length:
                complete = False
            preview = part[:512].decode("utf-8", errors="replace")
            if preview and sum(ch.isprintable() or ch in "\n\r\t" for ch in preview) / len(preview) > 0.9 and preview.count("\ufffd") < len(preview) / 20:
                texts.append(preview)
    coinbase = any(vin.get("coinbase") for vin in tx.get("vin", []))
    reasons = []
    if not coinbase and size >= min_tx_bytes:
        reasons.append("transaction-size")
    if not coinbase and data_outputs and data_bytes >= min_data_bytes:
        reasons.append("data-output")
    return {"transactionBytes": size, "dataBytes": data_bytes,
            "dataComplete": complete, "dataOutputs": data_outputs,
            "selectionReasons": reasons, "opReturnText": "\n".join(texts)[:1024],
            "coinbase": bool(coinbase)}


def connect(path):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS blocks (
            height INTEGER PRIMARY KEY, hash TEXT NOT NULL, bytes INTEGER NOT NULL,
            time INTEGER NOT NULL, tx_count INTEGER NOT NULL, checked INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'partial', updated_at TEXT NOT NULL,
            error TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS transactions (
            height INTEGER NOT NULL REFERENCES blocks(height) ON DELETE CASCADE,
            tx_index INTEGER NOT NULL, txid TEXT NOT NULL, bytes INTEGER NOT NULL,
            data_bytes INTEGER NOT NULL, data_complete INTEGER NOT NULL,
            selected INTEGER NOT NULL, summary TEXT, raw TEXT, checked_at TEXT NOT NULL,
            PRIMARY KEY(height, tx_index), UNIQUE(height, txid));
    """)
    return db


def meta(db, key, value=None):
    if value is None:
        row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None
    db.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (key, str(value)))
    return value


def scan(db, provider, args):
    tip = provider.tip()
    safe = tip - args.confirmations
    if safe < 0:
        raise ValueError("No block has the requested confirmations")
    for key, wanted, default in [("min_tx_bytes", args.min_tx_bytes, 1024),
                                 ("min_data_bytes", args.min_data_bytes, 128)]:
        old = meta(db, key)
        if old is not None and wanted is not None and int(old) != wanted:
            raise ValueError("Selection thresholds changed; use a separate --db to rescan")
        meta(db, key, int(old) if old is not None else (wanted if wanted is not None else default))
    start = args.start_height
    if start is not None and start > safe:
        raise ValueError("Start height exceeds the confirmed scan head")
    if meta(db, "next_height") is None or (start is not None and str(start) != meta(db, "anchor_height")):
        meta(db, "anchor_height", safe if start is None else start)
        meta(db, "next_height", safe if start is None else start)
    meta(db, "provider", API)
    meta(db, "tip", tip)
    meta(db, "last_error", "")
    db.commit()
    checked, completed = 0, 0
    while checked < args.max_transactions and completed < args.blocks:
        height = int(meta(db, "next_height"))
        if height < args.stop_height:
            break
        block = provider.block(height)
        old = db.execute("SELECT * FROM blocks WHERE height=?", (height,)).fetchone()
        with db:
            if old and old["hash"] != block["hash"]:
                # A changed ancestor invalidates its descendants as well.
                db.execute("DELETE FROM blocks WHERE height>=?", (height,))
                old = None
            if old is None:
                db.execute("INSERT INTO blocks(height,hash,bytes,time,tx_count,updated_at) VALUES (?,?,?,?,?,?)",
                           (height, block["hash"], int(block["size"]), int(block["time"]), int(block["txcount"]), now()))
            elif old["tx_count"] != int(block["txcount"]):
                raise ValueError("Transaction count changed for the same block hash")
        row = db.execute("SELECT * FROM blocks WHERE height=?", (height,)).fetchone()
        cursor = row["checked"]
        while cursor < row["tx_count"] and checked < args.max_transactions:
            batch = provider.transactions(block, cursor, min(20, args.max_transactions - checked, row["tx_count"] - cursor))
            if not batch or len(batch) > min(20, args.max_transactions - checked, row["tx_count"] - cursor):
                raise ValueError("Invalid transaction batch length")
            with db:
                for offset, tx in enumerate(batch):
                    if tx.get("blockhash") != block["hash"]:
                        raise ValueError("Transaction block hash does not match the scanned block")
                    info = inspect_transaction(tx, int(meta(db, "min_tx_bytes")), int(meta(db, "min_data_bytes")))
                    selected = bool(info["selectionReasons"])
                    db.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?)", (
                        height, cursor + offset, tx["txid"], info["transactionBytes"], info["dataBytes"],
                        int(info["dataComplete"]), int(selected), json.dumps(info) if selected else None,
                        json.dumps(tx, separators=(",", ":")) if selected else None, now()))
                cursor += len(batch)
                checked += len(batch)
                db.execute("UPDATE blocks SET checked=?,updated_at=?,error='' WHERE height=?", (cursor, now(), height))
                meta(db, "updated_at", now())
        if cursor == row["tx_count"]:
            with db:
                db.execute("UPDATE blocks SET status='complete' WHERE height=?", (height,))
                meta(db, "next_height", height - 1)
            completed += 1
        else:
            break
    return {"checkedThisRun": checked, "completedThisRun": completed}


def status(db):
    blocks = [dict(row) for row in db.execute("""
        SELECT b.*, COALESCE(SUM(t.selected),0) AS selected,
        COALESCE(SUM(t.bytes),0) AS checked_bytes, COALESCE(SUM(t.data_bytes),0) AS data_bytes,
        COALESCE(MAX(t.bytes),0) AS largest_transaction
        FROM blocks b LEFT JOIN transactions t ON b.height=t.height
        GROUP BY b.height ORDER BY b.height DESC
    """)]
    return {"kind": "bsv-block-scan", "version": 1, "coin": "bsv", "network": "mainnet",
            "provider": API, "generatedAt": now(), "lastCheckedAt": meta(db, "updated_at"),
            "nextHeight": int(meta(db, "next_height")) if meta(db, "next_height") is not None else None,
            "lastError": meta(db, "last_error") or "",
            "minTransactionBytes": int(meta(db, "min_tx_bytes") or 1024),
            "minDataBytes": int(meta(db, "min_data_bytes") or 128),
            "blocksChecked": len(blocks), "blocksComplete": sum(b["status"] == "complete" for b in blocks),
            "transactionsChecked": sum(b["checked"] for b in blocks),
            "candidates": sum(b["selected"] for b in blocks),
            "blocks": blocks,
            "topBlocks": sorted(blocks, key=lambda b: (b["data_bytes"], b["largest_transaction"]), reverse=True)[:20]}


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    if path.is_file() and path.read_bytes() == data:
        return hashlib.sha256(data).hexdigest()
    fd, name = tempfile.mkstemp(prefix=".bsv-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            os.fchmod(handle.fileno(), 0o644)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return hashlib.sha256(data).hexdigest()


def export(db, directory, limit):
    root = Path(directory).expanduser()
    report = status(db)
    records = []
    for row in db.execute("""SELECT t.*, b.hash, b.time FROM transactions t
        JOIN blocks b ON b.height=t.height WHERE selected=1
        ORDER BY t.bytes DESC, t.height DESC, t.tx_index LIMIT ?""", (limit,)):
        txid = row["txid"]
        raw_path = "transactions/bsv/" + txid + ".json"
        atomic_json(root / raw_path, json.loads(row["raw"]))
        summary = json.loads(row["summary"])
        summary.update({"txid": txid, "coin": "bsv", "ticker": "BSV",
                        "title": "BSV data output" if summary["dataOutputs"] else "BSV large transaction",
                        "blockHeight": row["height"], "blockTime": row["time"],
                        "transactionIndex": row["tx_index"], "explorerUrl": "https://whatsonchain.com/tx/" + txid})
        records.append({"txid": txid, "coin": "bsv", "ticker": "BSV", "sourceId": "bsv",
                        "rawPath": raw_path, "summary": summary, "streamLabel": "BSV public history",
                        "discoverySource": "block-scan"})
    # Immutable index snapshots make the manifest the single atomic publication
    # point. A browser holding the old manifest can still fetch its old index.
    index = {"version": 1, "transactions": records, "scan": report}
    digest = hashlib.sha256((json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n").encode()).hexdigest()
    index_path = "index/portal-" + digest + ".json"
    index_hash = atomic_json(root / index_path, index)
    atomic_json(root / "scan.json", report)
    atomic_json(root / "manifest.json", {"version": 1, "title": "BSV public history scan",
                "defaultIndex": index_path, "records": len(records), "generatedAt": report["generatedAt"],
                "generatedBy": "mogwai/tools/bsv_indexer.py", "hashes": {index_path: "sha256-" + index_hash}})
    return {"exported": len(records), "manifest": str(root / "manifest.json")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["scan", "status", "export", "note"])
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--start-height", type=int, help="First block of a backward scan; omit to resume")
    parser.add_argument("--stop-height", type=int, default=0)
    parser.add_argument("--blocks", type=int, default=5, help="Completed blocks per run, at most")
    parser.add_argument("--max-transactions", type=int, default=200, help="Transaction budget per run")
    parser.add_argument("--min-tx-bytes", type=int)
    parser.add_argument("--min-data-bytes", type=int)
    parser.add_argument("--confirmations", type=int, default=6, help="Blocks behind the tip")
    parser.add_argument("--request-delay", type=float, default=0.5)
    parser.add_argument("--export-dir", help="Separate public BSV dataset directory")
    parser.add_argument("--limit", type=int, default=1000, help="Largest selected records to export")
    parser.add_argument("--height", type=int, help="Previously visited block to annotate")
    parser.add_argument("--text", help="Public scan note; exported with coverage")
    args = parser.parse_args(argv)
    for name in ["start_height", "stop_height", "min_tx_bytes", "min_data_bytes", "confirmations"]:
        value = getattr(args, name)
        if value is not None and value < 0:
            parser.error(name.replace("_", "-") + " cannot be negative")
    if min(args.blocks, args.max_transactions, args.limit) < 1 or args.request_delay < 0.34:
        parser.error("Budgets must be positive and request-delay must be at least 0.34 seconds")
    if args.start_height is not None and args.start_height < args.stop_height:
        parser.error("start-height must be at or above stop-height")
    path = Path(args.db).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + ".lock", "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"skipped": "Another BSV indexer run holds the lock"}))
            return 0
        db = connect(path)
        result = {}
        try:
            if args.command == "scan":
                result.update(scan(db, WhatsOnChain(args.request_delay), args))
            elif args.command == "note":
                if args.height is None or args.text is None:
                    parser.error("note needs --height and --text (public export)")
                with db:
                    changed = db.execute("UPDATE blocks SET note=? WHERE height=?", (args.text, args.height)).rowcount
                if not changed:
                    raise ValueError("That block has not been visited")
            if args.command == "export" and not args.export_dir:
                parser.error("export needs --export-dir")
            if args.export_dir:
                result.update(export(db, args.export_dir, args.limit))
            report = status(db)
            report.pop("blocks")
            result.update(report)
            print(json.dumps(result, indent=2))
            return 0
        except (ValueError, sqlite3.Error, OSError, KeyError, TypeError) as exc:
            message = str(exc)
            with db:
                meta(db, "last_error", message)
                db.execute("UPDATE blocks SET error=? WHERE height=? AND status!='complete'", (message, meta(db, "next_height")))
            if args.export_dir:
                export(db, args.export_dir, args.limit)
            print(json.dumps({"error": message, "checkpointRetained": True}), file=sys.stderr)
            return 1
        finally:
            db.close()


if __name__ == "__main__":
    sys.exit(main())
