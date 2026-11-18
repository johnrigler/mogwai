#!/usr/bin/env python3
"""Read-only EVM JSON-RPC adapter for trusted local Mogwai commands.

No private keys, signing, broadcasting, or HTTP server routes.
"""
import argparse
import hashlib
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

if __package__:
    from .ledger_config import endpoint_key, load_ledger_config
else:
    from ledger_config import endpoint_key, load_ledger_config

_TXID = re.compile(r"^0x[0-9a-fA-F]{64}$")
_QUANTITY = re.compile(r"^0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)$")
_HEADER = re.compile(r"^[A-Za-z0-9-]+$")
_MAX_RESPONSE = 4 * 1024 * 1024


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _quantity(value, label):
    if not isinstance(value, str) or not _QUANTITY.fullmatch(value):
        raise ValueError("RPC returned invalid " + label)
    return int(value, 16)


def _provider(spec):
    if not isinstance(spec, dict) or spec.get("family") != "evm":
        raise ValueError("Selected ledger is not an EVM network")
    if type(spec.get("chainId")) is not int or spec["chainId"] < 1:
        raise ValueError("EVM ledger requires a positive chainId")
    return spec["read"]


def rpc_read(endpoint, method, params=(), opener=None):
    """Call only the explicitly allowed JSON-RPC read methods."""
    if method not in ("eth_chainId", "eth_blockNumber", "eth_getTransactionByHash",
                      "eth_getTransactionReceipt"):
        raise ValueError("Disallowed JSON-RPC method")
    if method in ("eth_getTransactionByHash", "eth_getTransactionReceipt"):
        if len(params) != 1 or not isinstance(params[0], str) or not _TXID.fullmatch(params[0]):
            raise ValueError("Expected a 0x-prefixed 32-byte transaction hash")
    elif params:
        raise ValueError("This JSON-RPC method takes no parameters")

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    key = endpoint_key(endpoint)
    if endpoint.get("apiKeyEnv") and not key and endpoint.get("apiKeyHeader"):
        raise ValueError("Configured read API key environment variable is unset")
    if key:
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in key):
            raise ValueError("Read API key contains invalid control characters")
        header = endpoint.get("apiKeyHeader", "")
        if not isinstance(header, str) or not _HEADER.fullmatch(header):
            raise ValueError("Read API key needs a valid apiKeyHeader")
        prefix = endpoint.get("apiKeyPrefix", "")
        if not isinstance(prefix, str) or "\r" in prefix or "\n" in prefix:
            raise ValueError("Invalid apiKeyPrefix")
        headers[header] = prefix + key
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                          "params": list(params)}, separators=(",", ":")).encode("utf-8")
    request = Request(endpoint["url"], data=payload, headers=headers, method="POST")
    transport = opener if opener is not None else build_opener(_NoRedirect())
    try:
        with transport.open(request, timeout=15) as response:
            data = response.read(_MAX_RESPONSE + 1)
    except HTTPError as exc:
        raise ValueError("RPC HTTP status " + str(exc.code)) from None
    except (URLError, TimeoutError, OSError):
        raise ValueError("RPC network request failed") from None
    if len(data) > _MAX_RESPONSE:
        raise ValueError("RPC response too large")
    try:
        message = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("RPC returned invalid JSON") from None
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or message.get("id") != 1:
        raise ValueError("RPC returned an invalid response envelope")
    if "error" in message:
        error = message["error"]
        code = error.get("code") if isinstance(error, dict) else None
        raise ValueError("RPC returned an error" + (f" (code {code})" if type(code) is int else ""))
    if "result" not in message:
        raise ValueError("RPC response missing result")
    return message["result"]


def _chain(endpoint, chain_id, opener=None):
    observed = _quantity(rpc_read(endpoint, "eth_chainId", opener=opener), "chainId")
    if observed != chain_id:
        raise ValueError(f"RPC chain mismatch: expected {chain_id}, observed {observed}")
    return observed


def status(config, ledger="polygon", opener=None):
    spec = config["ledgers"].get(ledger)
    endpoint = _provider(spec)
    chain_id = _chain(endpoint, spec["chainId"], opener)
    latest = _quantity(rpc_read(endpoint, "eth_blockNumber", opener=opener), "blockNumber")
    return {"ledger": ledger, "chainId": chain_id, "latestBlock": latest}


def transaction(config, ledger, txid, opener=None):
    if not isinstance(txid, str) or not _TXID.fullmatch(txid):
        raise ValueError("Expected a 0x-prefixed 32-byte transaction hash")
    spec = config["ledgers"].get(ledger)
    endpoint = _provider(spec)
    chain_id = _chain(endpoint, spec["chainId"], opener)
    result = rpc_read(endpoint, "eth_getTransactionByHash", (txid,), opener=opener)
    summary = {"ledger": ledger, "chainId": chain_id, "transactionHash": txid.lower(),
               "found": result is not None}
    if result is None:
        return summary
    if not isinstance(result, dict) or str(result.get("hash", "")).lower() != txid.lower():
        raise ValueError("RPC transaction hash does not match requested hash")
    if result.get("chainId") is not None and _quantity(result["chainId"], "transaction chainId") != chain_id:
        raise ValueError("RPC transaction chainId mismatch")
    raw_input = result.get("input", "0x")
    if not isinstance(raw_input, str) or not re.fullmatch(r"0x(?:[a-fA-F0-9]{2})*", raw_input):
        raise ValueError("RPC returned invalid transaction input")
    binary = bytes.fromhex(raw_input[2:])
    block = result.get("blockNumber")
    summary.update({
        "from": result.get("from"),
        "to": result.get("to"),
        "valueWei": _quantity(result.get("value"), "transaction value"),
        "blockNumber": _quantity(block, "transaction blockNumber") if block is not None else None,
        "input": raw_input,
        "inputBytes": len(binary),
        "inputSha256": hashlib.sha256(binary).hexdigest(),
        "execution": "pending" if block is None else "unknown",
    })
    if block is not None:
        receipt = rpc_read(endpoint, "eth_getTransactionReceipt", (txid,), opener=opener)
        if receipt is not None:
            if not isinstance(receipt, dict) or str(receipt.get("transactionHash", "")).lower() != txid.lower():
                raise ValueError("RPC receipt hash mismatch")
            if _quantity(receipt.get("blockNumber"), "receipt blockNumber") != summary["blockNumber"]:
                raise ValueError("RPC receipt blockNumber mismatch")
            state = _quantity(receipt.get("status"), "receipt status")
            summary["execution"] = "success" if state == 1 else "reverted" if state == 0 else "unknown"
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read Polygon/EVM JSON-RPC without signing")
    parser.add_argument("--config", help="Private ledger config path")
    command = parser.add_subparsers(dest="command", required=True)
    health = command.add_parser("status", help="Check network chain ID and block height")
    health.add_argument("ledger", nargs="?", default="polygon")
    tx = command.add_parser("transaction", help="Read a transaction and receipt")
    tx.add_argument("ledger")
    tx.add_argument("txid")
    args = parser.parse_args(argv)
    try:
        config = load_ledger_config(args.config)
        result = (status(config, args.ledger) if args.command == "status"
                  else transaction(config, args.ledger, args.txid))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print("mogwai-evm: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
