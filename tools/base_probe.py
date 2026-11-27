#!/usr/bin/env python3
"""Read-only Base discovery probe. Writes JSON Lines to stdout; no FileProxy writes.

Run: python3 tools/base_probe.py --blocks 100 > base-probe.jsonl
Optional: --config ~/.config/mogwai/ledgers.json (requires a Base entry)
Optional: --end-block HEIGHT, --min-bytes 512, --net-logs
Without --config, uses the official public Base RPC, subject to rate limits.
"""
import argparse
import collections
import json
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from evm_read import _NoRedirect
from ledger_config import endpoint_key, load_ledger_config
from drpc_status import _private_config, _safe_endpoint
from urllib.parse import parse_qs, quote, unquote, urlsplit

CHAIN = 8453
DEFAULT_RPC_URL = "https://mainnet.base.org"
NET = "0x00000000b24d62781db359b07880a105cd0b64e6"
NET_STORAGE = "0x00000000db40fcb9f4466330982372e27fd7bbf5"
KNOWN = {NET: "net", NET_STORAGE: "net-storage"}
MAX_RESPONSE = 64 * 1024 * 1024
TEXT = re.compile(rb"[ -~]{24,}")
SIGNATURES = {
    "jpeg": bytes.fromhex("ffd8ff"), "png": bytes.fromhex("89504e470d0a1a0a"),
    "gif87": b"GIF87a", "gif89": b"GIF89a", "svg": b"<svg",
    "html": b"<html", "data-uri": b"data:", "ipfs": b"ipfs://",
    "json-object": b'{"', "pdf": b"%PDF-", "gzip": bytes.fromhex("1f8b08"),
}


def emit(record):
    print(json.dumps(record, ensure_ascii=True, separators=(",", ":")), flush=True)


class RPCError(ValueError):
    """Safe diagnostic: never includes endpoint URL or provider error text."""


def base_endpoint(config=None, drpc=False):
    if config and drpc:
        raise RPCError("Select either --config or --drpc, not both")
    if config:
        spec = load_ledger_config(config)["ledgers"]["base"]
        if spec.get("family") != "evm" or spec.get("chainId") != CHAIN:
            raise RPCError("Config base entry must be EVM chain 8453")
        return spec["read"]
    if drpc:
        try:
            private = _private_config()
            polygon, mode = _safe_endpoint(private)
            parsed = urlsplit(polygon["url"])
            parts = parsed.path.strip("/").split("/")
            query = parse_qs(parsed.query)
            key = None
            if mode == "url":
                if parsed.hostname in ("lb.drpc.live", "lb.drpc.org") and len(parts) == 2 and parts[0].lower() == "polygon":
                    key = unquote(parts[1])
                elif query.get("dkey"):
                    key = query["dkey"][0]
            elif mode == "header":
                key = polygon.get("apiKey")
            if not key or any(ord(ch) < 33 or ord(ch) == 127 for ch in key):
                raise ValueError("Missing usable dRPC key")
            return {"url": "https://lb.drpc.live/base/" + quote(key, safe="")}
        except (ValueError, OSError, KeyError, TypeError):
            raise RPCError("Cannot load a usable key from private drpc.json") from None
    return {"url": DEFAULT_RPC_URL}


def rpc(endpoint, method, params):
    context = method
    if method == "eth_getBlockByNumber" and params:
        context += " block=" + str(params[0])
    elif method == "eth_getLogs" and params:
        context += " blocks=" + str(params[0].get("fromBlock")) + ".." + str(params[0].get("toBlock"))
    if method not in {"eth_chainId", "eth_blockNumber", "eth_getBlockByNumber", "eth_getLogs"}:
        raise ValueError("Disallowed RPC method")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    key = endpoint_key(endpoint)
    if endpoint.get("apiKeyEnv") and not key:
        raise ValueError("Configured RPC API key environment variable is unset")
    if key:
        header = endpoint.get("apiKeyHeader")
        if not header:
            raise ValueError("Configured RPC API key needs apiKeyHeader")
        headers[header] = endpoint.get("apiKeyPrefix", "") + key
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    request = Request(endpoint["url"], data=body, headers=headers, method="POST")
    for attempt in range(3):
        try:
            with build_opener(_NoRedirect()).open(request, timeout=30) as response:
                raw = response.read(MAX_RESPONSE + 1)
            break
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RPCError(context + ": HTTP " + str(exc.code)) from None
        except (URLError, TimeoutError, OSError):
            if attempt == 2:
                raise RPCError(context + ": network request failed") from None
        time.sleep(2 ** attempt)
    if len(raw) > MAX_RESPONSE:
        raise RPCError(context + ": response too large")
    try:
        response = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RPCError(context + ": invalid JSON response") from None
    if not isinstance(response, dict):
        raise RPCError(context + ": invalid JSON-RPC envelope")
    if "error" in response:
        error = response["error"]
        code = error.get("code") if isinstance(error, dict) else None
        raise RPCError(context + ": JSON-RPC error code " + (str(code) if type(code) is int else "unknown"))
    if response.get("jsonrpc") != "2.0" or response.get("id") != 1 or "result" not in response:
        raise RPCError(context + ": invalid JSON-RPC envelope")
    if response["result"] is None:
        raise RPCError(context + ": null result")
    return response["result"]


def payload(tx):
    value = tx.get("input", "0x")
    if not isinstance(value, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", value):
        raise ValueError("Invalid transaction input")
    return bytes.fromhex(value[2:])


def classify(data):
    lower = data.lower()
    hints = [name for name, marker in SIGNATURES.items()
             if (marker if name in ("jpeg", "png", "gif87", "gif89", "pdf", "gzip") else marker.lower())
             in (data if name in ("jpeg", "png", "gif87", "gif89", "pdf", "gzip") else lower)]
    runs = sorted(TEXT.findall(data), key=len, reverse=True)
    return hints, [part[:200].decode("ascii") for part in runs[:3]]


def scan(args, endpoint):
    if int(rpc(endpoint, "eth_chainId", []), 16) != CHAIN:
        raise ValueError("RPC is not Base mainnet (8453)")
    head = int(rpc(endpoint, "eth_blockNumber", []), 16)
    end = args.end_block if args.end_block is not None else max(0, head - 20)
    if end > head:
        raise ValueError("Requested end block exceeds current head")
    start = max(0, end - args.blocks + 1)
    groups = collections.defaultdict(lambda: {"count": 0, "bytes": 0, "largest": 0})
    totals = collections.Counter()
    emit({"type": "scan-start", "chainId": CHAIN, "fromBlock": start, "toBlock": end,
          "minBytes": args.min_bytes, "head": head, "knownContracts": KNOWN})
    for height in range(end, start - 1, -1):
        block = rpc(endpoint, "eth_getBlockByNumber", [hex(height), True])
        if not isinstance(block, dict) or int(block["number"], 16) != height:
            raise ValueError("Missing or mismatched block")
        rows = block["transactions"]
        block_bytes = max_bytes = candidates = 0
        for tx in rows:
            data = payload(tx)
            size = len(data)
            block_bytes += size
            max_bytes = max(max_bytes, size)
            totals["transactions"] += 1
            if tx.get("type") == "0x7e":
                totals["depositTransactions"] += 1
                continue
            destination = (tx.get("to") or "").lower()
            known = KNOWN.get(destination)
            hints, preview = classify(data) if size >= 24 else ([], [])
            if known:
                totals["knownDirectTransactions"] += 1
            if not (known or size >= args.min_bytes or hints or preview):
                continue
            selector = "0x" + data[:4].hex() if len(data) >= 4 else ""
            group = groups[(destination or "contract-creation", selector)]
            group["count"] += 1
            group["bytes"] += size
            group["largest"] = max(group["largest"], size)
            candidates += 1
            totals["candidates"] += 1
            emit({"type": "candidate", "chainId": CHAIN, "blockNumber": height,
                  "hash": tx["hash"], "from": tx.get("from"), "to": tx.get("to"),
                  "inputBytes": size, "selector": selector, "knownProtocol": known,
                  "blindSizeHit": size >= args.min_bytes, "contentHints": hints,
                  "asciiPreview": preview, "transaction": tx})
        emit({"type": "block", "height": height, "hash": block["hash"],
              "sizeBytes": int(block["size"], 16) if block.get("size") else None,
              "transactionCount": len(rows), "totalInputBytes": block_bytes,
              "largestInputBytes": max_bytes, "candidates": candidates})
        totals["blocks"] += 1
        time.sleep(args.delay)
    if args.net_logs:
        for low in range(start, end + 1, 100):
            high = min(end, low + 99)
            logs = rpc(endpoint, "eth_getLogs", [{"address": NET, "fromBlock": hex(low),
                                                "toBlock": hex(high)}])
            for log in logs:
                emit({"type": "net-log", "chainId": CHAIN, "log": log})
                totals["netLogs"] += 1
            time.sleep(args.delay)
    emit({"type": "summary", "chainId": CHAIN, "totals": dict(totals),
          "groups": [{"to": k[0], "selector": k[1], **v}
                     for k, v in sorted(groups.items(), key=lambda item: item[1]["bytes"], reverse=True)[:100]]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blocks", type=int, default=100)
    parser.add_argument("--end-block", type=int)
    parser.add_argument("--min-bytes", type=int, default=512)
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--config")
    parser.add_argument("--drpc", action="store_true", help="Use the existing private dRPC key for Base")
    parser.add_argument("--net-logs", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.blocks <= 10000 or args.min_bytes < 1 or args.delay < 0.1 or (args.end_block is not None and args.end_block < 0):
        parser.error("Use 1-10000 blocks, positive min-bytes, delay >= 0.1, and nonnegative end-block")
    try:
        endpoint = base_endpoint(args.config, args.drpc)
        scan(args, endpoint)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        # Never echo provider URLs or credentials.
        print("Base probe failed: " + type(exc).__name__ + "; check configuration, RPC limits and partial output.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
