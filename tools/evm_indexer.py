#!/usr/bin/env python3
"""Incrementally index configured Polygon contract transactions into FileProxy.

The Etherscan key is read from the existing private etherscan.json. The job
uses Etherscan V2 account/txlist for indexed address discovery and FileProxy's
existing /save-evm-batch route for canonical transaction packets. It does not
sign, broadcast, or expose credentials through FileProxy.
"""
import argparse
import fcntl
import json
import os
import re
import stat
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

if __package__:
    from .etherscan_read import proxy_read
    from .evm_read import _MAX_RESPONSE, _quantity
    from .ledger_config import endpoint_key
    from .migrate_etherscan import _read_source
else:
    from etherscan_read import proxy_read
    from evm_read import _MAX_RESPONSE, _quantity
    from ledger_config import endpoint_key
    from migrate_etherscan import _read_source


ROOT = Path(__file__).resolve().parent
DEFAULT_ROOTS = ROOT / "evm_indexer_roots.json"
DEFAULT_ETHERSCAN_CONFIG = "~/.config/mogwai/etherscan.json"
DEFAULT_STATE = "~/.local/state/mogwai/evm-indexer.json"
DEFAULT_FILEPROXY = "http://127.0.0.1:7799"
ETHERSCAN_CHAIN_ID = 137
PAGE_SIZE = 100
OVERLAP_BLOCKS = 3
CONFIRMATIONS = 2
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
TXID_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
HEX_DATA_RE = re.compile(r"^0x(?:[0-9a-fA-F]{2})*$")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _read_json_file(path, label, private=False):
    target = Path(path).expanduser()
    if target.is_symlink():
        raise ValueError(label + " must not be a symlink")
    info = target.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(label + " must be a regular file")
    if private and os.name == "posix":
        if info.st_mode & 0o077 or info.st_uid != os.geteuid():
            raise ValueError(label + " requires current-user ownership and chmod 600")
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise ValueError(label + " contains invalid JSON") from None
    if not isinstance(value, dict):
        raise ValueError(label + " must contain a JSON object")
    return value


def load_roots(path):
    doc = _read_json_file(path, "Polygon index roots")
    if doc.get("version") != 1 or doc.get("chainId") != ETHERSCAN_CHAIN_ID:
        raise ValueError("Polygon index roots must use version 1 and chainId 137")
    roots = doc.get("contracts")
    if not isinstance(roots, list) or not roots:
        raise ValueError("Polygon index roots need a nonempty contracts list")
    names = set()
    addresses = set()
    checked = []
    for item in roots:
        if not isinstance(item, dict):
            raise ValueError("Each Polygon contract root must be an object")
        name = item.get("name")
        address = item.get("address")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", name):
            raise ValueError("Polygon contract names must be lowercase identifiers")
        if not isinstance(address, str) or not ADDRESS_RE.fullmatch(address):
            raise ValueError("Polygon contract root has an invalid EVM address")
        lower = address.lower()
        if name in names or lower in addresses:
            raise ValueError("Polygon contract roots must have unique names and addresses")
        names.add(name)
        addresses.add(lower)
        try:
            poll_seconds = int(item.get("pollSeconds", 60))
            start_block = int(item.get("startBlock", 0))
        except (TypeError, ValueError):
            raise ValueError("pollSeconds and startBlock must be integers") from None
        if poll_seconds < 60 or start_block < 0:
            raise ValueError("pollSeconds must be at least 60 and startBlock cannot be negative")
        checked.append({"name": name, "address": address,
                        "pollSeconds": poll_seconds, "startBlock": start_block})
    return checked


def load_etherscan_provider(path):
    provider = _read_source(path)
    key = endpoint_key(provider)
    if not key:
        raise ValueError("Etherscan API key is not configured in etherscan.json")
    if any(ord(ch) < 33 or ord(ch) == 127 for ch in key):
        raise ValueError("Etherscan API key contains invalid characters")
    return provider


def _http_json(url, method="GET", payload=None, limit=_MAX_RESPONSE):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    opener = build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=20) as response:
            body = response.read(limit + 1)
    except HTTPError as exc:
        raise ValueError("HTTP request failed with status " + str(exc.code)) from None
    except (URLError, TimeoutError, OSError):
        raise ValueError("HTTP network request failed") from None
    if len(body) > limit:
        raise ValueError("HTTP response exceeded the configured size limit")
    try:
        result = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("HTTP service returned invalid JSON") from None
    if not isinstance(result, dict):
        raise ValueError("HTTP service returned an invalid JSON object")
    return result


def _etherscan_txlist(provider, address, start_block, end_block, page):
    key = endpoint_key(provider)
    query = {
        "chainid": str(ETHERSCAN_CHAIN_ID),
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": str(start_block),
        "endblock": str(end_block),
        "page": str(page),
        "offset": str(PAGE_SIZE),
        "sort": "asc",
        "apikey": key,
    }
    payload = _http_json(provider["url"] + "?" + urlencode(query), limit=16 * 1024 * 1024)
    result = payload.get("result")
    if payload.get("status") == "0":
        message = str(payload.get("message", "")).lower()
        if ((isinstance(result, str) and "no transactions found" in result.lower()) or
                "no transactions found" in message or result == []):
            return []
        # Do not echo provider messages; they can contain request details.
        raise ValueError("Etherscan rejected the account transaction query (check key, plan, and rate limit)")
    if not isinstance(result, list):
        raise ValueError("Etherscan returned an invalid transaction page")
    return result


def _fileproxy_get(base, path, params):
    query = urlencode(params)
    result = _http_json(base.rstrip("/") + path + "?" + query)
    if result.get("ok") is False:
        raise ValueError("FileProxy rejected the status request")
    return result


def _fileproxy_save(base, contract, txs, start_block, end_block):
    if not txs:
        return 0
    saved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    packets = []
    for raw in txs:
        tx_hash = raw.get("hash")
        if not isinstance(tx_hash, str) or not TXID_RE.fullmatch(tx_hash):
            raise ValueError("Etherscan returned a transaction with an invalid hash")
        tx_input = raw.get("input", "0x")
        if not isinstance(tx_input, str) or not HEX_DATA_RE.fullmatch(tx_input):
            raise ValueError("Etherscan returned invalid transaction input")
        try:
            block = int(raw.get("blockNumber", "0"))
            timestamp = int(raw.get("timeStamp", "0"))
        except (TypeError, ValueError):
            raise ValueError("Etherscan returned invalid block metadata") from None
        txid = tx_hash[2:].lower()
        input_bytes = (len(tx_input) - 2) // 2
        method_id = tx_input[:10] if len(tx_input) >= 10 else ""
        tx = dict(raw)
        packet = {
            "txid": txid,
            "hash": tx_hash.lower(),
            "coin": "evm",
            "chainId": str(ETHERSCAN_CHAIN_ID),
            "chainName": "Polygon Mainnet",
            "contract": {
                "name": contract["name"],
                "address": contract["address"],
                "queriedAddress": contract["address"],
            },
            "source": {
                "kind": "etherscan-v2-account-txlist",
                "generatedBy": "mogwai-tools/evm_indexer.py",
                "savedAt": saved_at,
                "sort": "asc",
                "startBlock": str(start_block),
                "endBlock": str(end_block),
            },
            "tx": tx,
            "decoded": {"kind": "evm", "methodId": method_id},
            "summary": {
                "txid": txid,
                "hash": tx_hash.lower(),
                "title": contract["name"].upper() + " transaction",
                "methodId": method_id,
                "from": raw.get("from", ""),
                "to": raw.get("to", ""),
                "contractAddress": contract["address"],
                "blockNumber": block,
                "blockHeight": block,
                "blockTime": timestamp,
                "date": datetime.fromtimestamp(timestamp, timezone.utc).isoformat().replace("+00:00", "Z") if timestamp else "",
                "value": raw.get("value", "0"),
                "gasUsed": raw.get("gasUsed", ""),
                "inputBytes": input_bytes,
                "kind": "evm",
                "transactionIndex": int(raw.get("transactionIndex", "0") or 0),
            },
        }
        packets.append(packet)
    response = _http_json(
        base.rstrip("/") + "/save-evm-batch",
        method="POST",
        payload={
            "chainId": str(ETHERSCAN_CHAIN_ID),
            "chainName": "Polygon Mainnet",
            "contractName": contract["name"],
            "contractAddress": contract["address"],
            "source": {"kind": "etherscan-v2-account-txlist", "savedAt": saved_at},
            "transactions": packets,
            "filenameMode": "base58",
        },
        limit=32 * 1024 * 1024,
    )
    if response.get("ok") is not True:
        raise ValueError("FileProxy did not confirm the EVM transaction batch")
    if response.get("errors"):
        raise ValueError("FileProxy rejected one or more EVM transaction packets")
    return int(response.get("saved", len(packets)))


def _load_state(path):
    target = Path(path).expanduser()
    if not target.exists():
        return {"version": 1, "chainId": ETHERSCAN_CHAIN_ID, "contracts": {}}
    state = _read_json_file(target, "Polygon index state", private=True)
    if state.get("version") != 1 or state.get("chainId") != ETHERSCAN_CHAIN_ID:
        raise ValueError("Polygon index state has an unsupported version or chainId")
    if not isinstance(state.get("contracts"), dict):
        raise ValueError("Polygon index state has an invalid contracts map")
    return state


def _write_state(path, state):
    target = Path(path).expanduser()
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".evm-index-", dir=str(target.parent))
    try:
        if os.name == "posix":
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _root_key(contract):
    return contract["name"] + ":" + contract["address"].lower()


def status(roots_path, state_path):
    roots = load_roots(roots_path)
    state = _load_state(state_path)
    out = []
    for contract in roots:
        entry = state["contracts"].get(_root_key(contract), {})
        out.append({"name": contract["name"], "address": contract["address"],
                    "pollSeconds": contract["pollSeconds"],
                    "lastScannedBlock": entry.get("lastScannedBlock"),
                    "lastPoll": entry.get("lastPoll")})
    print(json.dumps({"chainId": ETHERSCAN_CHAIN_ID, "provider": "etherscan-v2",
                      "fileProxy": "configured at scan time", "contracts": out},
                     indent=2, sort_keys=True))


def scan(roots_path, etherscan_config, state_path, fileproxy_url):
    roots = load_roots(roots_path)
    provider = load_etherscan_provider(etherscan_config)
    state = _load_state(state_path)
    latest = _quantity(proxy_read(provider, ETHERSCAN_CHAIN_ID, "eth_blockNumber"), "blockNumber")
    safe_head = max(0, latest - CONFIRMATIONS)
    state["contracts"] = state.get("contracts", {})
    results = []
    for contract in roots:
        key = _root_key(contract)
        prior = state["contracts"].get(key, {})
        last_poll = float(prior.get("lastPollEpoch", 0) or 0)
        now = time.time()
        if now - last_poll < contract["pollSeconds"]:
            continue
        if "lastScannedBlock" in prior:
            last_scanned = int(prior["lastScannedBlock"])
        else:
            cached = _fileproxy_get(fileproxy_url, "/evm-stream-status", {
                "chainId": str(ETHERSCAN_CHAIN_ID),
                "contractName": contract["name"],
                "contractAddress": contract["address"],
            })
            last_scanned = max(contract["startBlock"] - 1,
                               int(cached.get("latestBlock", 0) or 0))
        start_block = max(contract["startBlock"], last_scanned - OVERLAP_BLOCKS + 1)
        if start_block > safe_head:
            state["contracts"][key] = {
                **prior,
                "lastScannedBlock": last_scanned,
                "lastPollEpoch": now,
                "lastPoll": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
            _write_state(state_path, state)
            results.append({"contract": contract["name"], "saved": 0,
                            "fromBlock": start_block, "toBlock": safe_head,
                            "checkpoint": last_scanned})
            continue
        page = 1
        seen = set()
        saved_count = 0
        while True:
            rows = _etherscan_txlist(provider, contract["address"], start_block, safe_head, page)
            unique = []
            for row in rows:
                tx_hash = row.get("hash") if isinstance(row, dict) else None
                if not isinstance(tx_hash, str) or not TXID_RE.fullmatch(tx_hash):
                    raise ValueError("Etherscan returned an invalid transaction row")
                normalized = tx_hash.lower()
                if normalized not in seen:
                    seen.add(normalized)
                    unique.append(row)
            if unique:
                saved_count += _fileproxy_save(fileproxy_url, contract, unique, start_block, safe_head)
            if len(rows) < PAGE_SIZE:
                break
            page += 1
            if page > 10000:
                raise ValueError("Etherscan transaction pagination exceeded the safety limit")
        completed = datetime.now(timezone.utc)
        state["contracts"][key] = {
            "lastScannedBlock": safe_head,
            "lastPollEpoch": completed.timestamp(),
            "lastPoll": completed.isoformat().replace("+00:00", "Z"),
            "lastFetched": len(seen),
            "lastSaved": saved_count,
        }
        _write_state(state_path, state)
        results.append({"contract": contract["name"], "saved": saved_count,
                        "transactions": len(seen), "fromBlock": start_block,
                        "toBlock": safe_head, "checkpoint": safe_head})
    print(json.dumps({"chainId": ETHERSCAN_CHAIN_ID, "provider": "etherscan-v2",
                      "latestBlock": latest, "safeBlock": safe_head,
                      "results": results}, indent=2, sort_keys=True))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Incremental Polygon contract indexer for Mogwai FileProxy")
    parser.add_argument("command", choices=("scan", "status"))
    parser.add_argument("--roots", default=str(DEFAULT_ROOTS), help="Public Polygon contract root list")
    parser.add_argument("--etherscan-config", default=DEFAULT_ETHERSCAN_CONFIG,
                        help="Existing private etherscan.json path")
    parser.add_argument("--state", default=DEFAULT_STATE, help="Private scan checkpoint path")
    parser.add_argument("--fileproxy-url", default=os.environ.get("FILEPROXY_URL", DEFAULT_FILEPROXY),
                        help="Local FileProxy base URL")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            status(args.roots, args.state)
            return 0
        state_path = Path(args.state).expanduser()
        state_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        lock_path = state_path.with_suffix(state_path.suffix + ".lock")
        if lock_path.is_symlink():
            raise ValueError("Polygon index lock must not be a symlink")
        with lock_path.open("a", encoding="utf-8") as lock:
            if os.name == "posix":
                os.chmod(lock_path, 0o600)
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print("evm-indexer: another scan is already running")
                return 0
            return scan(args.roots, args.etherscan_config, args.state, args.fileproxy_url)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        message = str(exc)
        # Provider and HTTP adapters use fixed diagnostics; guard against an
        # unexpected exception containing the credential-bearing URL.
        if "apikey=" in message.lower() or "etherscan.io" in message.lower():
            message = "provider request failed; inspect private configuration and connectivity"
        print("evm-indexer: " + message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
