#!/usr/bin/env python3
"""Read-only Polygon/EVM queries via the Etherscan V2 proxy API.

Uses a private key under ledgers.<network>.providers.etherscan, not the
network's JSON-RPC read.url. Never signs, broadcasts, or prints API keys.
"""
import argparse
import hashlib
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

if __package__:
    from .ledger_config import endpoint_key, load_ledger_config
    from .evm_read import _NoRedirect, _MAX_RESPONSE, _TXID, _quantity
else:
    from ledger_config import endpoint_key, load_ledger_config
    from evm_read import _NoRedirect, _MAX_RESPONSE, _TXID, _quantity


_ALLOWED = {"eth_blockNumber", "eth_getTransactionByHash", "eth_getTransactionReceipt"}


def _configured(config, ledger):
    spec = config.get("ledgers", {}).get(ledger)
    if not isinstance(spec, dict) or spec.get("family") != "evm":
        raise ValueError("Selected ledger is not an EVM network")
    chain_id = spec.get("chainId")
    if type(chain_id) is not int or chain_id < 1:
        raise ValueError("Selected ledger lacks a valid chainId")
    provider = spec.get("providers", {}).get("etherscan")
    if not isinstance(provider, dict):
        raise ValueError("Etherscan not configured under " + ledger + ".providers")
    if not endpoint_key(provider):
        raise ValueError("Etherscan API key not configured")
    return chain_id, provider


def proxy_read(provider, chain_id, action, txhash=None, opener=None):
    """Query only Etherscan's read-only proxy methods."""
    if action not in _ALLOWED:
        raise ValueError("Disallowed Etherscan action")
    if type(chain_id) is not int or chain_id < 1:
        raise ValueError("Invalid Etherscan chainId")
    if action == "eth_blockNumber":
        if txhash is not None:
            raise ValueError("Block number action takes no transaction hash")
    elif not isinstance(txhash, str) or not _TXID.fullmatch(txhash):
        raise ValueError("Expected a 0x-prefixed 32-byte transaction hash")

    key = endpoint_key(provider)
    if not key:
        raise ValueError("Etherscan API key not configured")
    if any(ord(ch) < 33 or ord(ch) == 127 for ch in key):
        raise ValueError("Etherscan API key contains invalid characters")
    query = {"chainid": str(chain_id), "module": "proxy", "action": action, "apikey": key}
    if txhash is not None:
        query["txhash"] = txhash
    # No URL or key is included in diagnostics; never follow redirects.
    request = Request(provider["url"] + "?" + urlencode(query),
                      headers={"Accept": "application/json"}, method="GET")
    transport = opener if opener is not None else build_opener(_NoRedirect())
    try:
        with transport.open(request, timeout=15) as response:
            body = response.read(_MAX_RESPONSE + 1)
    except HTTPError as exc:
        raise ValueError("Etherscan HTTP status " + str(exc.code)) from None
    except (URLError, TimeoutError, OSError):
        raise ValueError("Etherscan network request failed") from None
    if len(body) > _MAX_RESPONSE:
        raise ValueError("Etherscan response too large")
    try:
        result = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise ValueError("Etherscan returned invalid JSON") from None
    if not isinstance(result, dict):
        raise ValueError("Etherscan returned an invalid response")
    if "error" in result or result.get("status") == "0":
        # Do not include remote-provided message strings in errors.
        raise ValueError("Etherscan rejected the API request (check key, plan, and rate limit)")
    if result.get("jsonrpc") != "2.0" or "result" not in result:
        raise ValueError("Etherscan returned an invalid proxy envelope")
    return result["result"]


def status(config, ledger="polygon", opener=None):
    chain_id, provider = _configured(config, ledger)
    latest = _quantity(proxy_read(provider, chain_id, "eth_blockNumber",
                                  opener=opener), "blockNumber")
    # V2 chainid is a request parameter; this does NOT independently verify
    # the chain identity with eth_chainId.
    return {"ledger": ledger, "provider": "etherscan", "chainId": chain_id,
            "chainIdSource": "configured request parameter", "latestBlock": latest}


def transaction(config, ledger, txid, opener=None):
    if not isinstance(txid, str) or not _TXID.fullmatch(txid):
        raise ValueError("Expected a 0x-prefixed 32-byte transaction hash")
    chain_id, provider = _configured(config, ledger)
    record = proxy_read(provider, chain_id, "eth_getTransactionByHash", txid,
                        opener=opener)
    out = {"ledger": ledger, "provider": "etherscan", "chainId": chain_id,
           "transactionHash": txid.lower(), "found": record is not None}
    if record is None:
        return out
    if not isinstance(record, dict) or str(record.get("hash", "")).lower() != txid.lower():
        raise ValueError("Etherscan transaction hash mismatch")
    if record.get("chainId") is not None and _quantity(record["chainId"], "transaction chainId") != chain_id:
        raise ValueError("Etherscan transaction chainId mismatch")
    tx_input = record.get("input", "0x")
    if not isinstance(tx_input, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", tx_input):
        raise ValueError("Etherscan returned invalid transaction input")
    raw = bytes.fromhex(tx_input[2:])
    block = record.get("blockNumber")
    out.update({"from": record.get("from"), "to": record.get("to"),
                "valueWei": _quantity(record.get("value"), "transaction value"),
                "blockNumber": _quantity(block, "transaction blockNumber") if block is not None else None,
                "inputBytes": len(raw), "inputSha256": hashlib.sha256(raw).hexdigest(),
                "execution": "pending" if block is None else "unknown"})
    if block is not None:
        receipt = proxy_read(provider, chain_id, "eth_getTransactionReceipt", txid,
                             opener=opener)
        if receipt is not None:
            if not isinstance(receipt, dict) or str(receipt.get("transactionHash", "")).lower() != txid.lower():
                raise ValueError("Etherscan receipt hash mismatch")
            if _quantity(receipt.get("blockNumber"), "receipt blockNumber") != out["blockNumber"]:
                raise ValueError("Etherscan receipt block mismatch")
            state = _quantity(receipt.get("status"), "receipt status")
            out["execution"] = "success" if state == 1 else "reverted" if state == 0 else "unknown"
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read EVM ledger data via private Etherscan V2 key")
    parser.add_argument("--config", help="Path to private ledgers.json")
    commands = parser.add_subparsers(dest="command", required=True)
    s = commands.add_parser("status", help="Retrieve Etherscan's latest block")
    s.add_argument("ledger", nargs="?", default="polygon")
    t = commands.add_parser("transaction", help="Retrieve a transaction and receipt")
    t.add_argument("ledger")
    t.add_argument("txid")
    args = parser.parse_args(argv)
    try:
        cfg = load_ledger_config(args.config)
        result = (status(cfg, args.ledger) if args.command == "status"
                  else transaction(cfg, args.ledger, args.txid))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print("mogwai-etherscan: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
