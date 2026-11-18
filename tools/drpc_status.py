#!/usr/bin/env python3
"""Read-only Polygon status and transaction lookup from private drpc.json.

Expected local JSON: {"polygon": "<dRPC Polygon HTTPS RPC URL>", "api": "<key>"}.
The URL may already embed the key; do not echo the URL or the key.
No credentials, broadcasts, or FileProxy routes are written.
"""
import argparse
import json
import os
import re
from pathlib import Path
import stat
import sys
from urllib.parse import parse_qs, urlsplit

if __package__:
    from .evm_read import status as evm_status, transaction as evm_transaction
else:
    from evm_read import status as evm_status, transaction as evm_transaction

DEFAULT_PATH = "~/.config/mogwai/drpc.json"


def _private_config(path=None):
    target = Path(path or DEFAULT_PATH).expanduser()
    if target.is_symlink():
        raise ValueError("dRPC config must not be a symlink")
    info = target.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("dRPC config must be a regular file")
    if os.name == "posix":
        if info.st_mode & 0o077:
            raise ValueError("dRPC config permissions are too broad; use chmod 600")
        if info.st_uid != os.geteuid():
            raise ValueError("dRPC config must belong to the current user")
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("dRPC config must be a JSON object")
    if not isinstance(data.get("polygon"), str):
        raise ValueError("dRPC config needs a polygon URL string")
    if not isinstance(data.get("api", ""), str):
        raise ValueError("dRPC config api must be a string")
    # Other fields, such as an unrelated Data & Wallet endpoint, are ignored.
    return data


def _safe_endpoint(data):
    url = data["polygon"]
    key = data.get("api", "")
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    # Fail closed before sending credentials or making any network request.
    if (parsed.scheme != "https" or parsed.username or parsed.password or
            parsed.fragment or parsed.port not in (None, 443) or
            host not in ("lb.drpc.live", "lb.drpc.org", "polygon.drpc.org")):
        raise ValueError("polygon must be an HTTPS dRPC RPC endpoint")
    path = parsed.path.rstrip("/")
    if "/lambda" in path.lower():
        raise ValueError("Data & Wallet URL is not a Polygon JSON-RPC endpoint")
    segments = path.strip("/").split("/") if path else []
    query = parse_qs(parsed.query, keep_blank_values=True)
    # Standard per-chain URL: https://lb.drpc.live/polygon/<key>.
    # The documented query form uses network=polygon and dkey=<key>.
    if host == "polygon.drpc.org":
        if segments:
            raise ValueError("Unexpected path on public Polygon dRPC URL")
    elif not ((segments and segments[0].lower() == "polygon") or
              query.get("network") == ["polygon"]):
        raise ValueError("The dRPC URL must select the Polygon network")
    if len(segments) > 2 and host != "polygon.drpc.org":
        raise ValueError("Unexpected Polygon RPC endpoint path")

    # Never place the same API key in a header when the URL has a credential.
    # dRPC's own dashboard URL commonly embeds it after /polygon/.
    url_has_credential = ((host != "polygon.drpc.org" and len(segments) == 2
                           and bool(segments[1])) or bool(query.get("dkey")))
    if key and any(ord(ch) < 33 or ord(ch) == 127 for ch in key):
        raise ValueError("dRPC api contains invalid characters")
    endpoint = {"url": url}
    if url_has_credential:
        mode = "url"
    elif key:
        endpoint["apiKey"] = key
        endpoint["apiKeyHeader"] = "Drpc-Key"
        mode = "header"
    else:
        mode = "none"
    return endpoint, mode


def check(path=None):
    endpoint, mode = _safe_endpoint(_private_config(path))
    # Do not print endpoint.url: it may contain a credential.
    return {"provider": "drpc", "ledger": "polygon", "expectedChainId": 137,
            "authentication": mode, "configured": bool(endpoint["url"])}


def status(path=None, opener=None):
    endpoint, mode = _safe_endpoint(_private_config(path))
    temporary_config = {"ledgers": {"polygon": {
        "family": "evm", "chainId": 137, "read": endpoint
    }}}
    result = evm_status(temporary_config, "polygon", opener=opener)
    result["provider"] = "drpc"
    result["authentication"] = mode
    return result


def transaction(txid, path=None, opener=None):
    """Read a Polygon transaction and receipt from the private dRPC endpoint."""
    endpoint, mode = _safe_endpoint(_private_config(path))
    temporary_config = {"ledgers": {"polygon": {
        "family": "evm", "chainId": 137, "read": endpoint
    }}}
    result = evm_transaction(temporary_config, "polygon", txid, opener=opener)
    result["provider"] = "drpc"
    result["authentication"] = mode
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check private dRPC Polygon RPC; never print keys")
    parser.add_argument("command", choices=("check", "status", "transaction"))
    parser.add_argument("txid", nargs="?", help="0x-prefixed 32-byte transaction hash (transaction only)")
    parser.add_argument("--config", help="Override private ~/.config/mogwai/drpc.json path")
    args = parser.parse_args(argv)
    try:
        if args.command == "transaction":
            if args.txid is None:
                parser.error("transaction requires a 0x-prefixed 32-byte transaction hash")
            result = transaction(args.txid, args.config)
        elif args.txid is not None:
            parser.error("transaction hash is only valid with transaction")
        else:
            result = check(args.config) if args.command == "check" else status(args.config)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        # A configured URL can contain secrets. Only echo tightly allowlisted
        # diagnostics known to contain numbers or fixed status text.
        detail = str(exc)
        if detail.startswith("RPC HTTP status ") and detail[len("RPC HTTP status "):].isdigit():
            message = detail
        elif detail in ("RPC network request failed", "RPC response missing result",
                        "RPC returned invalid JSON", "RPC returned an invalid response envelope"):
            message = detail
        elif re.fullmatch(r"RPC chain mismatch: expected [0-9]+, observed [0-9]+", detail):
            message = detail
        else:
            message = "check private dRPC config, provider URL and access"
        print("mogwai-drpc: " + message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
