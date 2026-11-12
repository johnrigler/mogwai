"""Litecoin P2PKH signed-request identities for isolated FileProxy records.

Uses Chisel's elliptic bundle via Node.js. No token fallback here.
Only legacy Litecoin P2PKH addresses (L...) are supported initially.
"""
import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path
import sqlite3
import time

PREFIX = b"\x19Litecoin Signed Message:\n"
ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
MAX_SKEW = 300

def sha256d(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def varint(n):
    if n < 253:
        return bytes([n])
    if n <= 65535:
        return b"\xfd" + n.to_bytes(2, "little")
    raise ValueError("Signed message too long")

def b58check(data):
    number = int.from_bytes(data + sha256d(data)[:4], "big")
    chars = ""
    while number:
        number, digit = divmod(number, 58)
        chars = ALPHABET[digit] + chars
    return "1" * (len(data + sha256d(data)[:4]) - len((data + sha256d(data)[:4]).lstrip(b"\0"))) + chars

def address_for_pubkey(public_key):
    payload = b"\x30" + hashlib.new("ripemd160", hashlib.sha256(public_key).digest()).digest()
    return b58check(payload)

def canonical_message(method, path, timestamp, nonce, body):
    if method != "POST" or path != "/v1/identity/records":
        raise ValueError("Unsupported signed operation")
    if not isinstance(timestamp, int) or isinstance(timestamp, bool):
        raise ValueError("Invalid timestamp")
    if not isinstance(nonce, str) or not (16 <= len(nonce) <= 128) or not nonce.isascii() or not nonce.isalnum():
        raise ValueError("Invalid nonce")
    if not isinstance(body, dict):
        raise ValueError("Invalid body")
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return ("FileProxy Litecoin Identity v1\nPOST\n/v1/identity/records\n"
            + str(timestamp) + "\n" + nonce + "\n" + digest).encode("ascii")

def recover_address(message, signature):
    if not isinstance(signature, str) or len(signature) > 128:
        raise ValueError('Invalid Litecoin signature')
    verifier = Path(__file__).resolve().parents[1] / 'tools' / 'verify_litecoin.js'
    if not os.environ.get('CHISEL_ELLIPTIC_PATH'):
        raise RuntimeError('CHISEL_ELLIPTIC_PATH must point to Chisel chisel.js')
    try:
        result = subprocess.run(['node', str(verifier)],
            input=json.dumps({'message': message.decode('utf-8'), 'signature': signature}),
            capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError('Litecoin verifier unavailable') from exc
    if result.returncode != 0:
        raise ValueError('Invalid Litecoin signature')
    try:
        address = json.loads(result.stdout)['address']
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError('Invalid verifier response') from exc
    if not isinstance(address, str):
        raise ValueError('Invalid verifier address')
    return address

def authenticate(envelope, method, path, now=None):
    if not isinstance(envelope, dict) or set(envelope) != {"address", "timestamp", "nonce", "body", "signature"}:
        raise ValueError("Invalid signed envelope")
    timestamp = envelope["timestamp"]
    message = canonical_message(method, path, timestamp, envelope["nonce"], envelope["body"])
    current = int(time.time()) if now is None else int(now)
    if abs(current - timestamp) > MAX_SKEW:
        raise ValueError("Expired signed request")
    address = recover_address(message, envelope["signature"])
    if address != envelope["address"]:
        raise ValueError("Signature does not match Litecoin address")
    return address

def identity_root(base, address):
    # Address comes from signature recovery, never from a client path.
    if not isinstance(address, str) or not (26 <= len(address) <= 35) or not address.startswith("L") or any(c not in ALPHABET for c in address):
        raise ValueError("Unsupported Litecoin identity")
    return Path(base) / "litecoin" / address

def is_blocked(base, address):
    policy = Path(base) / "blacklist.json"
    if not policy.exists():
        return False
    data = json.loads(policy.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("addresses"), list):
        raise ValueError("Invalid blacklist policy")
    return address in data["addresses"]

def write_record(base, address, nonce, body, timestamp):
    """Append-only per-identity JSON records, with replay rejection.

    The root and identity folders must be controlled by the FileProxy operator.
    Filesystem sandboxing of arbitrary user paths is deliberately not offered.
    """
    base = Path(base).expanduser().resolve()
    if is_blocked(base, address):
        raise PermissionError("Identity blocked")
    folder = identity_root(base, address)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    if folder.is_symlink() or folder.resolve() != folder:
        raise ValueError("Unsafe identity directory")
    database = folder / "records.sqlite3"
    if database.is_symlink():
        raise ValueError("Unsafe identity database")
    with sqlite3.connect(database, timeout=15) as db:
        db.execute("CREATE TABLE IF NOT EXISTS records (nonce TEXT PRIMARY KEY, timestamp INTEGER NOT NULL, body TEXT NOT NULL)")
        try:
            with db:
                db.execute("INSERT INTO records VALUES (?, ?, ?)",
                           (nonce, timestamp, json.dumps(body, sort_keys=True, separators=(",", ":"))))
        except sqlite3.IntegrityError as exc:
            raise FileExistsError("Replay: nonce already used") from exc
    return {"ok": True, "identity": "litecoin:" + address, "nonce": nonce}
