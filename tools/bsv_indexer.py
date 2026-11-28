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
import signal
import sqlite3
import sys
import tempfile
import time
import threading
from types import SimpleNamespace
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API = "https://api.whatsonchain.com/v1/bsv/main"
DEFAULT_DB = "~/.local/state/mogwai/bsv-index.sqlite3"
HASH = re.compile(r"^[0-9a-f]{64}$")
# The creator's Alice in BitcoinLand loader references this exact transaction.
# Its raw transaction hash and block were checked before adding this anchor.
ALICE_TXID = "b742886801560f57b4dc824ce3a1719613d8b2d38530909fe988c1ca04cc82af"
ALICE_HEIGHT = 566492
# Recovered apollo.jpeg, published 2022-02-02 UTC.
APOLLO_TXID = "269fd1238dca49c491a723c5bcce89b3dc3cf92e6f4b73c32d8538821643cea2"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def checked_hash(value):
    value = str(value or "").lower()
    if not HASH.fullmatch(value):
        raise ValueError("Provider returned an invalid hash")
    return value


class WhatsOnChain:
    """Provider-specific reads. A POST to /txs retrieves details, never broadcasts."""
    def __init__(self, delay=0.5, stop=None):
        self.delay = delay
        self.last_request = 0
        self.page_cache = {}
        self.stop = stop

    def pause(self, seconds):
        if self.stop is not None:
            if self.stop.wait(seconds):
                raise InterruptedError("Scanner stopping")
        else:
            time.sleep(seconds)

    def request(self, path, payload=None):
        # Callers construct paths; never follow page URLs supplied by a provider.
        for attempt in range(4):
            self.pause(max(0, self.delay - (time.monotonic() - self.last_request)))
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
                self.pause(min(max(delay, 1), 30))
            except (URLError, TimeoutError, OSError):
                if self.stop is not None and self.stop.is_set():
                    raise InterruptedError("Scanner stopping") from None
                if attempt == 3:
                    raise ValueError("WhatsOnChain network request failed") from None
                self.pause(2 ** (attempt + 1))
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


def inspect_files(tx):
    """Recognize B:// files, including typed prefixes in truncated outputs."""
    files = []
    for index, output in enumerate(tx.get("vout", [])):
        script = output.get("scriptPubKey") or {}
        value = str(script.get("hex", ""))
        raw = bytes.fromhex(re.match(r"^(?:[0-9a-fA-F]{2})*", value).group(0))
        pos = 2 if raw.startswith(b"\x00\x6a") else 1 if raw.startswith(b"\x6a") else -1
        if pos < 0:
            continue
        parts = []
        while pos < len(raw):
            op = raw[pos]
            pos += 1
            length = op
            if 76 <= op <= 78:
                count = 1 << (op - 76)
                if pos + count > len(raw):
                    break
                length = int.from_bytes(raw[pos:pos + count], "little")
                pos += count
            elif op > 75:
                break
            data = raw[pos:pos + length]
            parts.append((data, length, len(data) == length))
            pos += length
        for i, (marker, _, complete) in enumerate(parts):
            if not complete or marker != b"19HxigV4QyBv3tHpQVcUEQyq1pzZVdoAut" or i + 1 >= len(parts):
                continue
            data, length, complete = parts[i + 1]
            text = lambda offset: parts[i + offset][0].decode("utf-8", "replace") if i + offset < len(parts) and parts[i + offset][2] else ""
            declared = text(2).strip().lower()
            mime = declared if re.fullmatch(r"[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+", declared) else ""
            source = "declared" if mime else "signature"
            if not mime:
                if data.startswith(b"\xff\xd8\xff"):
                    mime = "image/jpeg"
                elif data.startswith(b"\x89PNG\r\n\x1a\n"):
                    mime = "image/png"
                elif data[:6] in (b"GIF87a", b"GIF89a"):
                    mime = "image/gif"
                elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
                    mime = "image/webp"
            if mime:
                files.append({"protocol": "B", "output": output.get("n", index), "part": i + 1,
                              "mime": mime, "mimeSource": source, "bytes": length,
                              "availableBytes": len(data), "complete": complete,
                              "encoding": text(3)[:40], "name": text(4)[:200]})
    return files


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
            "coinbase": bool(coinbase), "files": inspect_files(tx)}


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
        CREATE TABLE IF NOT EXISTS scan_jobs (
            name TEXT PRIMARY KEY, direction TEXT NOT NULL,
            anchor_height INTEGER NOT NULL, next_height INTEGER NOT NULL,
            stop_height INTEGER, anchor_txid TEXT NOT NULL DEFAULT '',
            updated_at TEXT, error TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS scan_discoveries (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            job TEXT NOT NULL REFERENCES scan_jobs(name) ON DELETE CASCADE,
            height INTEGER NOT NULL, tx_index INTEGER NOT NULL,
            FOREIGN KEY(height,tx_index) REFERENCES transactions(height,tx_index) ON DELETE CASCADE);
        CREATE INDEX IF NOT EXISTS scan_discoveries_job_seq ON scan_discoveries(job,seq DESC);
    """)
    # Upgrade an existing single-cursor database without dropping its history.
    if not db.execute("SELECT 1 FROM scan_jobs LIMIT 1").fetchone() and meta(db, "next_height") is not None:
        db.execute("INSERT INTO scan_jobs(name,direction,anchor_height,next_height,stop_height,updated_at) VALUES ('history','backward',?,?,0,?)",
                   (int(meta(db, "anchor_height") or meta(db, "next_height")), int(meta(db, "next_height")), meta(db, "updated_at")))
        db.commit()
    return db


def meta(db, key, value=None):
    if value is None:
        row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None
    db.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (key, str(value)))
    return value


def job_name(args):
    return getattr(args, "job", None) or ("early" if getattr(args, "direction", "backward") == "forward" else "history")


def record_error(db, name, message):
    with db:
        meta(db, "last_error", message)
        db.execute("UPDATE scan_jobs SET error=? WHERE name=?", (message, name))
        job = db.execute("SELECT next_height FROM scan_jobs WHERE name=?", (name,)).fetchone()
        if job:
            db.execute("UPDATE blocks SET error=? WHERE height=? AND status!='complete'", (message, job[0]))


def scan(db, provider, args, stop=None):
    direction = getattr(args, "direction", "backward")
    name = job_name(args)
    data_root = getattr(args, "data_root", None)
    if data_root:
        (Path(data_root).expanduser() / "transactions/bsv").mkdir(parents=True, exist_ok=True)
    if direction not in ("forward", "backward") or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", name):
        raise ValueError("Invalid scan direction or job name")
    step = 1 if direction == "forward" else -1
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
    job = db.execute("SELECT * FROM scan_jobs WHERE name=?", (name,)).fetchone()
    if job and job["direction"] != direction:
        raise ValueError("A saved job cannot change direction; choose another --job")
    boundary = args.stop_height
    if boundary is None and job:
        boundary = job["stop_height"]
    if boundary is None and direction == "backward":
        boundary = 0
    if start is not None and start > safe:
        raise ValueError("Start height exceeds the confirmed scan head")
    if not job and start is None and direction == "forward":
        raise ValueError("A new forward scan needs --start-height or an anchor transaction")
    if not job or (start is not None and start != job["anchor_height"]):
        anchor = safe if start is None else start
        if boundary is not None and (step < 0 and anchor < boundary or step > 0 and anchor > boundary):
            raise ValueError("Start height is outside this job's scan boundary")
        db.execute("INSERT OR REPLACE INTO scan_jobs(name,direction,anchor_height,next_height,stop_height,anchor_txid) VALUES (?,?,?,?,?,?)",
                   (name, direction, anchor, anchor, boundary, getattr(args, "anchor_tx", None) or ""))
    else:
        db.execute("UPDATE scan_jobs SET stop_height=? WHERE name=?", (boundary, name))
    db.execute("UPDATE scan_jobs SET error='' WHERE name=?", (name,))
    meta(db, "provider", API)
    meta(db, "tip", tip)
    meta(db, "confirmations", args.confirmations)
    meta(db, "last_error", "")
    db.commit()
    checked, completed = 0, 0
    blocks_this_run = []
    while checked < args.max_transactions and completed < args.blocks and not (stop and stop.is_set()):
        job = db.execute("SELECT * FROM scan_jobs WHERE name=?", (name,)).fetchone()
        height = job["next_height"]
        if height < 0 or height > safe or (boundary is not None and (step < 0 and height < boundary or step > 0 and height > boundary)):
            break
        # Keep legacy status fields usable for older consumers of this database.
        with db:
            meta(db, "anchor_height", job["anchor_height"])
            meta(db, "next_height", height)
        block = provider.block(height)
        old = db.execute("SELECT * FROM blocks WHERE height=?", (height,)).fetchone()
        with db:
            if old and old["hash"] != block["hash"]:
                # A changed ancestor invalidates its descendants as well.
                db.execute("DELETE FROM blocks WHERE height>=?", (height,))
                db.execute("DELETE FROM meta WHERE key='ranges_joined'")
                db.execute("UPDATE scan_jobs SET next_height=? WHERE direction='forward' AND next_height>?", (height, height))
                db.execute("UPDATE scan_jobs SET next_height=MIN(anchor_height,?) WHERE direction='backward' AND anchor_height>=?", (safe, height))
                if step < 0 and min(job["anchor_height"], safe) != height:
                    continue
                old = None
            if old is None:
                db.execute("INSERT INTO blocks(height,hash,bytes,time,tx_count,updated_at) VALUES (?,?,?,?,?,?)",
                           (height, block["hash"], int(block["size"]), int(block["time"]), int(block["txcount"]), now()))
            elif old["tx_count"] != int(block["txcount"]):
                raise ValueError("Transaction count changed for the same block hash")
        row = db.execute("SELECT * FROM blocks WHERE height=?", (height,)).fetchone()
        cursor = row["checked"]
        start_cursor = cursor
        while cursor < row["tx_count"] and checked < args.max_transactions and not (stop and stop.is_set()):
            batch = provider.transactions(block, cursor, min(20, args.max_transactions - checked, row["tx_count"] - cursor))
            if not batch or len(batch) > min(20, args.max_transactions - checked, row["tx_count"] - cursor):
                raise ValueError("Invalid transaction batch length")
            candidates = []
            with db:
                for offset, tx in enumerate(batch):
                    if tx.get("blockhash") != block["hash"]:
                        raise ValueError("Transaction block hash does not match the scanned block")
                    info = inspect_transaction(tx, int(meta(db, "min_tx_bytes")), int(meta(db, "min_data_bytes")))
                    selected = bool(info["selectionReasons"])
                    if selected:
                        candidates.append(tx)
                    db.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?)", (
                        height, cursor + offset, tx["txid"], info["transactionBytes"], info["dataBytes"],
                        int(info["dataComplete"]), int(selected), json.dumps(info) if selected else None,
                        json.dumps(tx, separators=(",", ":")) if selected else None, now()))
                    if selected:
                        db.execute("INSERT INTO scan_discoveries(job,height,tx_index) VALUES (?,?,?)",
                                   (name, height, cursor + offset))
                if candidates:
                    db.execute("""DELETE FROM scan_discoveries WHERE job=? AND seq NOT IN
                        (SELECT seq FROM scan_discoveries WHERE job=? ORDER BY seq DESC LIMIT 20)""", (name, name))
                cursor += len(batch)
                checked += len(batch)
                db.execute("UPDATE blocks SET checked=?,updated_at=?,error='' WHERE height=?", (cursor, now(), height))
                meta(db, "updated_at", now())
                db.execute("UPDATE scan_jobs SET updated_at=?,error='' WHERE name=?", (now(), name))
            # Publish only committed candidates, without waiting for the block
            # or daemon pass to finish. TXID filenames deduplicate both jobs.
            if data_root:
                for tx in candidates:
                    archive_transaction(data_root, tx)
        blocks_this_run.append({"height": height, "startTransactionIndex": start_cursor,
                                "nextTransactionIndex": cursor, "transactionsTotal": row["tx_count"],
                                "checkedThisRun": cursor - start_cursor,
                                "complete": cursor == row["tx_count"]})
        if cursor == row["tx_count"]:
            with db:
                db.execute("UPDATE blocks SET status='complete' WHERE height=?", (height,))
                meta(db, "next_height", height + step)
                db.execute("UPDATE scan_jobs SET next_height=?,updated_at=? WHERE name=?", (height + step, now(), name))
            completed += 1
        else:
            break
    return {"job": name, "direction": direction, "checkedThisRun": checked,
            "completedThisRun": completed, "blocksThisRun": blocks_this_run}


def resolve_anchor(provider, txid):
    txid = checked_hash(txid)
    tx = provider.request("/tx/hash/" + txid)
    if tx.get("txid") != txid or not tx.get("blockhash"):
        raise ValueError("Anchor transaction is missing or unconfirmed")
    block = provider.request("/block/hash/" + checked_hash(tx["blockhash"]))
    if block.get("hash") != tx["blockhash"] or int(block.get("height", -1)) < 0:
        raise ValueError("Anchor block could not be resolved")
    if "tx" in block and int(block.get("txcount", 0)) == len(block["tx"]) and txid not in block["tx"]:
        raise ValueError("Anchor is absent from its reported block")
    if txid == ALICE_TXID and int(block["height"]) != ALICE_HEIGHT:
        raise ValueError("Provider changed the known Alice anchor height")
    return int(block["height"])


def daemon_jobs(db, provider, args):
    saved = db.execute("SELECT * FROM scan_jobs WHERE name='early'").fetchone()
    anchor_tx = args.anchor_tx
    if args.anchor_height is not None:
        anchor = args.anchor_height
    elif saved and not anchor_tx:
        anchor, anchor_tx = saved["anchor_height"], saved["anchor_txid"]
    else:
        anchor_tx = anchor_tx or ALICE_TXID
        anchor = resolve_anchor(provider, anchor_tx)
    if saved and (saved["anchor_height"] != anchor or anchor_tx and saved["anchor_txid"] != anchor_tx):
        raise ValueError("Daemon anchor changed; use a separate --db to keep both histories explicit")
    recent = db.execute("SELECT * FROM scan_jobs WHERE name='recent'").fetchone()
    if saved and saved["direction"] != "forward" or recent and recent["direction"] != "backward":
        raise ValueError("Daemon jobs have incompatible saved directions")
    # Create both cursor records before either job performs network work, so a
    # failure at the first tip request is still visible in the public report.
    if recent is None:
        safe = provider.tip() - args.confirmations
        if anchor > safe:
            raise ValueError("Historical anchor exceeds the confirmed scan head")
        with db:
            db.execute("INSERT INTO scan_jobs(name,direction,anchor_height,next_height,stop_height) VALUES ('recent','backward',?,?,?)", (safe, safe, anchor))
    if saved is None:
        with db:
            db.execute("INSERT INTO scan_jobs(name,direction,anchor_height,next_height,anchor_txid) VALUES ('early','forward',?,?,?)", (anchor, anchor, anchor_tx or ""))
    jobs = []
    for name, direction, start, boundary in [("recent", "backward", None, anchor), ("early", "forward", anchor, None)]:
        values = dict(vars(args), job=name, direction=direction, start_height=start, stop_height=boundary, anchor_tx=anchor_tx if name == "early" else None)
        jobs.append(SimpleNamespace(**values))
    return jobs


def apollo_jobs(db, provider, args):
    """Add two cursors without changing the original Alice/recent anchors."""
    txid = getattr(args, "apollo_anchor_tx", None)
    if not txid:
        return []
    txid = checked_hash(txid)
    specs = [("apollo-forward", "forward", None), ("apollo-backward", "backward", 0)]
    saved = [db.execute("SELECT * FROM scan_jobs WHERE name=?", (name,)).fetchone()
             for name, _, _ in specs]
    existing = [row for row in saved if row is not None]
    anchor = existing[0]["anchor_height"] if existing else resolve_anchor(provider, txid)
    for row, (_, direction, boundary) in zip(saved, specs):
        if row is not None and (row["anchor_txid"] != txid or row["anchor_height"] != anchor
                                or row["direction"] != direction or row["stop_height"] != boundary):
            raise ValueError("Apollo cursor anchor or direction changed; existing checkpoints retained")
    if not all(row is not None for row in saved) and anchor > provider.tip() - args.confirmations:
        raise ValueError("Apollo anchor exceeds the confirmed scan head")
    with db:
        for row, (name, direction, boundary) in zip(saved, specs):
            if row is None:
                db.execute("INSERT INTO scan_jobs(name,direction,anchor_height,next_height,stop_height,anchor_txid) VALUES (?,?,?,?,?,?)",
                           (name, direction, anchor, anchor, boundary, txid))
    return [SimpleNamespace(**dict(vars(args), job=name, direction=direction, start_height=anchor,
                                  stop_height=boundary, anchor_tx=txid))
            for name, direction, boundary in specs]


def join_completed_ranges(db):
    recent = db.execute("SELECT * FROM scan_jobs WHERE name='recent'").fetchone()
    early = db.execute("SELECT * FROM scan_jobs WHERE name='early'").fetchone()
    if not recent or not early or early["next_height"] <= recent["next_height"]:
        return False
    low, high = early["anchor_height"], recent["anchor_height"]
    count = db.execute("SELECT COUNT(*) FROM blocks WHERE height BETWEEN ? AND ? AND status='complete'", (low, high)).fetchone()[0]
    if high < low or count != high - low + 1:
        return False
    with db:
        db.execute("UPDATE scan_jobs SET next_height=? WHERE name='recent'", (low - 1,))
        db.execute("UPDATE scan_jobs SET next_height=MAX(next_height,?) WHERE name='early'", (high + 1,))
        if meta(db, "ranges_joined") is None:
            meta(db, "ranges_joined", now())
    return True


def daemon_pass(db, provider, args, jobs, stop):
    results = []
    supplemental = []
    if not stop.is_set():
        try:
            supplemental = apollo_jobs(db, provider, args)
            with db:
                meta(db, "apollo_error", "")
        except InterruptedError:
            if not stop.is_set():
                raise
        except (ValueError, sqlite3.Error, OSError, KeyError, TypeError) as exc:
            with db:
                meta(db, "apollo_error", str(exc))
            results.append({"job": "apollo-anchor", "error": str(exc), "checkpointRetained": True})
    for job in [*jobs, *supplemental]:
        if stop.is_set():
            break
        try:
            results.append(scan(db, provider, job, stop))
        except InterruptedError:
            if not stop.is_set():
                raise
        except (ValueError, sqlite3.Error, OSError, KeyError, TypeError) as exc:
            record_error(db, job_name(job), str(exc))
            results.append({"job": job_name(job), "error": str(exc), "checkpointRetained": True})
    join_completed_ranges(db)
    with db:
        meta(db, "daemon_heartbeat", now())
    result = {"jobs": results, "heartbeatAt": meta(db, "daemon_heartbeat")}
    result.update(export(db, args.export_dir, args.limit, getattr(args, "data_root", None)))
    return result


def daemon(db, provider, args, stop):
    if getattr(args, "data_root", None):
        archive_saved(db, args.data_root)
    jobs = daemon_jobs(db, provider, args)
    with db:
        meta(db, "daemon_state", "running")
    try:
        while not stop.is_set():
            result = daemon_pass(db, provider, args, jobs, stop)
            print(json.dumps(result), flush=True)
            if args.once:
                return int(any("error" in job for job in result["jobs"]))
            if stop.wait(args.interval):
                break
    finally:
        with db:
            meta(db, "daemon_state", "stopped")
        export(db, args.export_dir, args.limit, getattr(args, "data_root", None))
    return 0


def status(db):
    blocks = [dict(row) for row in db.execute("""
        SELECT b.*, COALESCE(SUM(t.selected),0) AS selected,
        COALESCE(SUM(t.bytes),0) AS checked_bytes, COALESCE(SUM(t.data_bytes),0) AS data_bytes,
        COALESCE(MAX(t.bytes),0) AS largest_transaction
        FROM blocks b LEFT JOIN transactions t ON b.height=t.height
        GROUP BY b.height ORDER BY b.height DESC
    """)]
    jobs = []
    has_discoveries = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='scan_discoveries'").fetchone()
    confirmations = meta(db, "confirmations")
    safe = int(meta(db, "tip") or 0) - int(confirmations if confirmations is not None else 6)
    saved_jobs = db.execute("SELECT * FROM scan_jobs ORDER BY name") if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='scan_jobs'").fetchone() else []
    for saved in saved_jobs:
        direction, height, boundary = saved["direction"], saved["next_height"], saved["stop_height"]
        done = height < 0 or boundary is not None and (direction == "backward" and height < boundary or direction == "forward" and height > boundary)
        phase = "error" if saved["error"] else "complete" if done else "waiting-for-blocks" if height > safe else "scanning"
        block = db.execute("SELECT checked,tx_count FROM blocks WHERE height=?", (height,)).fetchone()
        current_block = None
        if block is not None and not done and height <= safe:
            current_block = {"height": height, "transactionsChecked": block["checked"],
                             "transactionsTotal": block["tx_count"], "nextTransactionIndex": block["checked"],
                             "remainingTransactions": block["tx_count"] - block["checked"]}
            progress = ("Block %d: %d/%d transactions checked; next transaction index %d. "
                        "Height advances when this block is complete." %
                        (height, block["checked"], block["tx_count"], block["checked"]))
        elif done:
            progress = "Scan boundary reached."
        elif height > safe:
            progress = "Waiting for confirmed block %d." % height
        else:
            progress = "Block %d has not been checked yet." % height
        jobs.append({"name": saved["name"], "direction": direction, "anchorHeight": saved["anchor_height"],
                     "nextHeight": height, "stopHeight": boundary, "anchorTxid": saved["anchor_txid"],
                     "currentBlock": current_block, "progress": progress,
                     "lastCheckedAt": saved["updated_at"], "lastError": saved["error"], "phase": phase})
        if has_discoveries:
            jobs[-1]["recentRecords"] = [
                {"txid": row["txid"], "blockHeight": row["height"], "checkedAt": row["checked_at"]}
                for row in db.execute("""SELECT t.txid,t.height,t.checked_at FROM scan_discoveries d
                    JOIN transactions t ON t.height=d.height AND t.tx_index=d.tx_index
                    WHERE d.job=? AND t.selected=1 ORDER BY d.seq DESC LIMIT 20""", (saved["name"],))]
    errors = "; ".join(j["name"] + ": " + j["lastError"] for j in jobs if j["lastError"])
    if meta(db, "apollo_error"):
        errors = "; ".join(filter(None, [errors, "apollo-anchor: " + meta(db, "apollo_error")]))
    return {"kind": "bsv-block-scan", "version": 1, "coin": "bsv", "network": "mainnet",
            "provider": API, "generatedAt": now(), "lastCheckedAt": meta(db, "updated_at"),
            "nextHeight": int(meta(db, "next_height")) if meta(db, "next_height") is not None else None,
            "lastError": errors or meta(db, "last_error") or "", "jobs": jobs,
            "runner": {"lastReportedState": meta(db, "daemon_state") or "manual",
                       "heartbeatAt": meta(db, "daemon_heartbeat"), "rangesJoinedAt": meta(db, "ranges_joined")},
            "minTransactionBytes": int(meta(db, "min_tx_bytes") if meta(db, "min_tx_bytes") is not None else 1024),
            "minDataBytes": int(meta(db, "min_data_bytes") if meta(db, "min_data_bytes") is not None else 128),
            "blocksChecked": len(blocks), "blocksComplete": sum(b["status"] == "complete" for b in blocks),
            "transactionsChecked": sum(b["checked"] for b in blocks),
            "candidates": sum(b["selected"] for b in blocks),
            "blocks": blocks,
            "topBlocks": sorted(blocks, key=lambda b: (b["data_bytes"], b["largest_transaction"]), reverse=True)[:20]}


def atomic_json(path, value, overwrite=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite and path.is_file():
        return None
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
        if overwrite:
            os.replace(name, path)
        else:
            # An exclusive atomic create also preserves a file concurrently
            # written by FileProxy. Existing archive files keep their mtimes.
            try:
                os.link(name, path)
            except FileExistsError:
                pass
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return hashlib.sha256(data).hexdigest()


def archive_transaction(data_root, raw):
    path = Path(data_root).expanduser() / "transactions/bsv" / (checked_hash(raw.get("txid")) + ".json")
    atomic_json(path, raw, overwrite=False)


def archive_saved(db, data_root):
    directory = Path(data_root).expanduser() / "transactions/bsv"
    directory.mkdir(parents=True, exist_ok=True)
    for row in db.execute("SELECT height,tx_index,txid FROM transactions WHERE selected=1"):
        if not (directory / (row["txid"] + ".json")).is_file():
            raw = db.execute("SELECT raw FROM transactions WHERE height=? AND tx_index=?", (row["height"], row["tx_index"])).fetchone()[0]
            archive_transaction(data_root, json.loads(raw))


def export(db, directory, limit, data_root=None):
    root = Path(directory).expanduser()
    archive_root = Path(data_root).expanduser() if data_root else root
    if data_root and root.resolve() == archive_root.resolve():
        raise ValueError("Use a separate BSV feed directory such as <data-root>/bsv; the general data-root manifest is preserved")
    archive_saved(db, archive_root)
    # A feed under chisel_data references its sibling transaction archive.
    # Exports outside that root remain self-contained for static/IPFS copies.
    shared_archive = root.resolve().is_relative_to(archive_root.resolve())
    raw_base = Path(os.path.relpath(archive_root / "transactions/bsv", root)).as_posix() if shared_archive else "transactions/bsv"
    report = status(db)
    records = []
    has_curation = bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='bsv_curation'").fetchone())
    for row in db.execute("""SELECT t.*, b.hash, b.time FROM transactions t
        JOIN blocks b ON b.height=t.height WHERE selected=1
        ORDER BY t.bytes DESC, t.height DESC, t.tx_index LIMIT ?""", (limit,)):
        txid = row["txid"]
        raw_path = raw_base + "/" + txid + ".json"
        raw = json.loads(row["raw"])
        if not shared_archive:
            archive_transaction(root, raw)
        summary = json.loads(row["summary"])
        # Reclassify saved bytes so existing scan databases gain file search tags
        # without another network scan or any change to checked coverage.
        summary["files"] = inspect_files(raw)
        if has_curation:
            curated = db.execute("SELECT details FROM bsv_curation WHERE txid=?", (txid,)).fetchone()
            if curated:
                summary["curation"] = json.loads(curated["details"])
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
    return {"exported": len(records), "manifest": str(root / "manifest.json"),
            "transactionDirectory": str(archive_root / "transactions/bsv")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["scan", "daemon", "status", "export", "note"])
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--data-root", default=os.environ.get("CHISEL_DATA_ROOT", "~/chisel_data"),
                        help="Canonical Chisel data root; candidates are saved under transactions/bsv (default: ~/chisel_data)")
    parser.add_argument("--start-height", type=int, help="First block for scan; omit to resume")
    parser.add_argument("--stop-height", type=int, help="Inclusive last block; defaults to zero for backward scans")
    parser.add_argument("--direction", choices=["backward", "forward"], default="backward")
    parser.add_argument("--job", help="Independent named scan cursor")
    anchor = parser.add_mutually_exclusive_group()
    anchor.add_argument("--anchor-tx", help="Confirmed transaction defining the historical starting block")
    anchor.add_argument("--anchor-height", type=int, help="Override the daemon's historical anchor block")
    parser.add_argument("--apollo-anchor-tx", default=APOLLO_TXID,
                        help="Supplemental bidirectional daemon anchor (default: recovered Apollo JPEG)")
    parser.add_argument("--interval", type=float, default=60, help="Seconds between bounded daemon passes")
    parser.add_argument("--once", action="store_true", help="Run one daemon pass and export, then exit")
    parser.add_argument("--blocks", type=int, default=5, help="Completed blocks per run, at most")
    parser.add_argument("--max-transactions", type=int, default=200,
                        help="Transaction budget per run (default: 200); partial blocks resume at the saved transaction index")
    parser.add_argument("--min-tx-bytes", type=int)
    parser.add_argument("--min-data-bytes", type=int)
    parser.add_argument("--confirmations", type=int, default=6, help="Blocks behind the tip")
    parser.add_argument("--request-delay", type=float, default=0.5)
    parser.add_argument("--export-dir", help="BSV feed directory (default: <data-root>/bsv); keeps the main data-root manifest intact")
    parser.add_argument("--limit", type=int, default=1000, help="Largest selected records to export")
    parser.add_argument("--height", type=int, help="Previously visited block to annotate")
    parser.add_argument("--text", help="Public scan note; exported with coverage")
    args = parser.parse_args(argv)
    if args.command in ("scan", "daemon", "export") and not args.export_dir:
        args.export_dir = str(Path(args.data_root).expanduser() / "bsv")
    for name in ["start_height", "stop_height", "anchor_height", "min_tx_bytes", "min_data_bytes", "confirmations"]:
        value = getattr(args, name)
        if value is not None and value < 0:
            parser.error(name.replace("_", "-") + " cannot be negative")
    if min(args.blocks, args.max_transactions, args.limit) < 1 or args.request_delay < 0.34 or not args.interval >= 1:
        parser.error("Budgets must be positive, request-delay at least 0.34 seconds, and interval at least 1 second")
    if args.start_height is not None and args.stop_height is not None and (args.direction == "backward" and args.start_height < args.stop_height or args.direction == "forward" and args.start_height > args.stop_height):
        parser.error("start-height is outside the requested direction and stop-height")
    if args.command == "daemon" and (args.start_height is not None or args.stop_height is not None or args.job):
        parser.error("daemon manages recent/early cursors; use --anchor-tx or --anchor-height")
    path = Path(args.db).expanduser()
    if args.command == "status":
        if not path.is_file():
            print(json.dumps({"kind": "bsv-block-scan", "coin": "bsv", "jobs": [], "runner": {"lastReportedState": "not-started"}}))
            return 0
        # Observe the live service without taking its exclusive process lock or
        # performing a schema migration. SQLite supplies a committed snapshot.
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        try:
            report = status(db)
            report.pop("blocks")
            print(json.dumps(report, indent=2))
        finally:
            db.close()
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + ".lock", "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"skipped": "Another BSV indexer run holds the lock"}))
            return 0
        db = connect(path)
        result = {}
        stop = threading.Event()
        provider = WhatsOnChain(args.request_delay, stop)
        previous_signals = {}
        try:
            if args.command == "daemon":
                for signum in (signal.SIGTERM, signal.SIGINT):
                    previous_signals[signum] = signal.signal(signum, lambda *_: stop.set())
                return daemon(db, provider, args, stop)
            if args.command == "scan":
                archive_saved(db, args.data_root)
                if args.anchor_height is not None:
                    if args.start_height is not None:
                        raise ValueError("Use either --start-height or --anchor-height")
                    args.start_height = args.anchor_height
                if args.anchor_tx:
                    if args.start_height is not None:
                        raise ValueError("Use either --start-height or --anchor-tx")
                    args.start_height = resolve_anchor(provider, args.anchor_tx)
                result.update(scan(db, provider, args))
            elif args.command == "note":
                if args.height is None or args.text is None:
                    parser.error("note needs --height and --text (public export)")
                with db:
                    changed = db.execute("UPDATE blocks SET note=? WHERE height=?", (args.text, args.height)).rowcount
                if not changed:
                    raise ValueError("That block has not been visited")
            if args.export_dir:
                result.update(export(db, args.export_dir, args.limit, args.data_root))
            report = status(db)
            report.pop("blocks")
            result.update(report)
            print(json.dumps(result, indent=2))
            return 0
        except InterruptedError:
            if not stop.is_set():
                raise
            return 0
        except (ValueError, sqlite3.Error, OSError, KeyError, TypeError) as exc:
            message = str(exc)
            record_error(db, job_name(args), message)
            error_report = {"error": message, "checkpointRetained": True}
            if args.export_dir:
                try:
                    export(db, args.export_dir, args.limit, args.data_root)
                except (ValueError, sqlite3.Error, OSError, KeyError, TypeError) as export_exc:
                    error_report["exportError"] = str(export_exc)
            print(json.dumps(error_report), file=sys.stderr)
            return 1
        finally:
            for signum, handler in previous_signals.items():
                signal.signal(signum, handler)
            db.close()


if __name__ == "__main__":
    sys.exit(main())
