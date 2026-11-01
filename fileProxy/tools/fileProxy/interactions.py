"""Append-only Chisel interaction documents; signatures are verified by readers.

The server validates the signed payload's digest and shape. It does not claim
secp256k1 authentication: a reader must verify the signature and address binding.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit

SCHEMA = "chisel-interaction-v1"
COMMENT_TYPE = "chisel-comment-v1"
DATABASE = "chisel-interactions.sqlite3"
MAX_REQUEST = 32768
KINDS = {"visit", "select", "engage", "comment"}
COINS = {"litecoin", "litecoinTestnet", "digibyte", "ravencoin", "bitcoin", "dogecoin", "ecash", "evm"}
PAYLOAD_KEYS = {"schema", "id", "session", "kind", "at", "mode", "action", "subject", "title", "synopsis", "url", "comment", "author"}


def protected_path(path):
    return Path(path).name == DATABASE or Path(path).name.startswith(DATABASE + "-")


def text(value, maximum, name, empty=True):
    if not isinstance(value, str) or len(value) > maximum or (not empty and not value.strip()):
        raise ValueError("Invalid " + name)
    value.encode("utf-8")  # Reject unpaired surrogate code units.
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise ValueError("Invalid control character in " + name)
    return value


def public_url(value):
    text(value, 2048, "URL")
    if not value:
        return value
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    if (parsed.scheme not in ("http", "https") or not host or parsed.username or parsed.password
            or host == "localhost" or host.endswith((".localhost", ".local"))
            or re.match(r"^(?:0\.|127\.|10\.|192\.168\.|169\.254\.|172\.(?:1[6-9]|2\d|3[01])\.)", host)
            or ":" in host):
        raise ValueError("Interaction URLs must be public HTTP(S) URLs without credentials")
    return value


def subject_key(subject):
    if subject is None:
        return ""
    if not isinstance(subject, dict) or set(subject) != {"coin", "txid", "sourceId", "chainId", "dataUrl"}:
        raise ValueError("Invalid record subject")
    if subject["coin"] not in COINS or not re.fullmatch(r"[0-9a-f]{64}", subject["txid"]):
        raise ValueError("Invalid record identity")
    text(subject["sourceId"], 40, "source")
    text(subject["chainId"], 15, "chain")
    if subject["coin"] == "evm":
        if subject["sourceId"] not in {"evmGomez", "evmJethro", "other"} or not re.fullmatch(r"\d{1,15}", subject["chainId"]):
            raise ValueError("An EVM record needs its source and chain")
    elif subject["chainId"] or subject["sourceId"]:
        raise ValueError("UTXO records use currency and transaction identity")
    if subject["dataUrl"]:
        parsed = urlsplit(public_url(subject["dataUrl"]))
        if parsed.query or parsed.fragment:
            raise ValueError("Record data URL cannot contain query credentials or fragments")
    return ("evm:" + subject["chainId"] + ":" + subject["sourceId"] + ":" if subject["coin"] == "evm" else subject["coin"] + ":") + subject["txid"]


def validate(document):
    if not isinstance(document, dict) or not isinstance(document.get("payload"), dict):
        raise ValueError("Expected an interaction document")
    payload = document["payload"]
    if set(payload) != PAYLOAD_KEYS or payload["schema"] != SCHEMA or payload["kind"] not in KINDS:
        raise ValueError("Invalid interaction payload")
    for field in ("id", "session"):
        if not isinstance(payload[field], str) or not re.fullmatch(r"[0-9a-f]{32}", payload[field]):
            raise ValueError("Invalid " + field)
    if not isinstance(payload["at"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", payload["at"]):
        raise ValueError("Invalid authored timestamp")
    datetime.fromisoformat(payload["at"].replace("Z", "+00:00"))
    if payload["mode"] not in {"portal", "send", "review", "examples", "tools"}:
        raise ValueError("Invalid page mode")
    for field, maximum in (("action", 48), ("title", 200), ("synopsis", 500), ("comment", 4000)):
        text(payload[field], maximum, field)
    public_url(payload["url"])
    key = subject_key(payload["subject"])
    if payload["kind"] != "visit" and not key:
        raise ValueError("A record is required")
    if payload["kind"] == "comment":
        text(payload["comment"], 4000, "comment", empty=False)
    elif payload["comment"] or payload["author"] is not None:
        raise ValueError("Only comments have text and an author")
    signed = document.get("format") == "chisel-signed-v1"
    if signed:
        if set(document) != {"format", "type", "identity", "payload", "proof"} or document["type"] != COMMENT_TYPE or payload["kind"] != "comment":
            raise ValueError("Invalid signed comment envelope")
        identity, proof, author = document["identity"], document["proof"], payload["author"]
        if not isinstance(identity, str) or not re.fullmatch(r"chisel:v1:0[23][0-9a-f]{64}", identity):
            raise ValueError("Invalid signing identity")
        if not isinstance(author, dict) or set(author) != {"identity", "coin", "address"} or author["identity"] != identity or author["coin"] != "litecoin":
            raise ValueError("Invalid signed author")
        if not isinstance(author["address"], str) or not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{26,35}", author["address"]):
            raise ValueError("Invalid author address")
        if not isinstance(proof, dict) or set(proof) != {"algorithm", "digest", "signature"} or proof["algorithm"] != "secp256k1-sha256":
            raise ValueError("Invalid signature proof")
        if not isinstance(proof["signature"], str) or not re.fullmatch(r"[0-9a-f]{128}", proof["signature"]):
            raise ValueError("Invalid signature bytes")
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(("CHISEL-SIGNED-V1\n" + COMMENT_TYPE + "\n" + canonical).encode()).hexdigest()
        if proof["digest"] != digest:
            raise ValueError("Signed comment digest does not match its payload")
    elif set(document) != {"format", "payload"} or document["format"] != SCHEMA or payload["author"] is not None:
        raise ValueError("Unsigned interactions cannot claim an authenticated author")
    # Keep proof last in the downloadable file.
    ordered = {field: document[field] for field in ("format", "type", "identity", "payload", "proof") if field in document}
    encoded = (json.dumps(ordered, ensure_ascii=False, indent=2) + "\n").encode()
    if len(encoded) > MAX_REQUEST:
        raise ValueError("Interaction document is too large")
    return payload, key, encoded


def connect(path):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(target, timeout=5)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS interactions (
            seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
            received_at TEXT NOT NULL, subject TEXT NOT NULL, kind TEXT NOT NULL,
            document TEXT NOT NULL, sha256 BLOB NOT NULL CHECK(length(sha256)=32)
        );
        CREATE INDEX IF NOT EXISTS interactions_subject ON interactions(subject, seq DESC);
        CREATE INDEX IF NOT EXISTS interactions_kind ON interactions(kind, seq DESC);
        CREATE TRIGGER IF NOT EXISTS interactions_no_update BEFORE UPDATE ON interactions
            BEGIN SELECT RAISE(ABORT, 'Interaction history is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS interactions_no_delete BEFORE DELETE ON interactions
            BEGIN SELECT RAISE(ABORT, 'Interaction history is append-only'); END;
    """)
    return db


def entry(row):
    return {"seq": row["seq"], "receivedAt": row["received_at"], "sha256": bytes(row["sha256"]).hex(), "document": json.loads(row["document"])}


def append(path, document):
    payload, key, encoded = validate(document)
    digest = hashlib.sha256(encoded).digest()
    db = connect(path)
    try:
        with db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM interactions WHERE id=?", (payload["id"],)).fetchone()
            if old:
                if bytes(old["sha256"]) != digest:
                    raise FileExistsError("That interaction ID already contains different content")
                return {"ok": True, "duplicate": True, "entry": entry(old)}
            received = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            cursor = db.execute("INSERT INTO interactions(id,received_at,subject,kind,document,sha256) VALUES(?,?,?,?,?,?)",
                                (payload["id"], received, key, payload["kind"], encoded.decode(), digest))
            row = db.execute("SELECT * FROM interactions WHERE seq=?", (cursor.lastrowid,)).fetchone()
            return {"ok": True, "duplicate": False, "entry": entry(row)}
    finally:
        db.close()


def read(path, query):
    limit = max(1, min(100, int(query.get("limit", ["20"])[0])))
    conditions, values = [], []
    for field, operator in (("before", "<"), ("after", ">")):
        value = query.get(field, [""])[0]
        if value:
            if not re.fullmatch(r"\d{1,19}", value) or int(value) > 9223372036854775807:
                raise ValueError("Invalid history cursor")
            conditions.append("seq " + operator + " ?"); values.append(int(value))
    for field in ("subject", "kind"):
        value = query.get(field, [""])[0]
        if value:
            if field == "kind" and value not in KINDS or len(value) > 180:
                raise ValueError("Invalid history filter")
            conditions.append(field + " = ?"); values.append(value)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    db = connect(path)
    try:
        rows = db.execute("SELECT * FROM interactions" + where + " ORDER BY seq DESC LIMIT ?", values + [limit + 1]).fetchall()
        page = rows[:limit]
        return {"ok": True, "entries": [entry(row) for row in page], "hasMore": len(rows) > limit,
                "before": page[-1]["seq"] if page else None}
    finally:
        db.close()


def download(path, identifier):
    if not re.fullmatch(r"[0-9a-f]{32}", identifier):
        raise ValueError("Invalid interaction ID")
    db = connect(path)
    try:
        row = db.execute("SELECT document FROM interactions WHERE id=?", (identifier,)).fetchone()
        if not row:
            raise FileNotFoundError("Interaction not found")
        return row["document"].encode()
    finally:
        db.close()
