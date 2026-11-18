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
_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
_TOPIC = re.compile(r"^0x[0-9a-fA-F]{64}$")
_HEX_DATA = re.compile(r"^0x(?:[0-9a-fA-F]{2})*$")
_QUANTITY = re.compile(r"^0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)$")
_HEADER = re.compile(r"^[A-Za-z0-9-]+$")
_BLOCK_TAGS = {"latest", "safe", "finalized", "pending", "earliest"}
_MAX_LOG_BLOCK_SPAN = 100000
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


def _validate_log_filter(params):
    if len(params) != 1 or not isinstance(params[0], dict):
        raise ValueError("eth_getLogs requires one filter object")
    log_filter = params[0]
    if set(log_filter) - {"address", "fromBlock", "toBlock", "topics"}:
        raise ValueError("eth_getLogs filter has unsupported fields")
    address = log_filter.get("address")
    if not isinstance(address, str) or not _ADDRESS.fullmatch(address):
        raise ValueError("eth_getLogs requires one valid contract address")
    start = log_filter.get("fromBlock")
    end = log_filter.get("toBlock")
    if not isinstance(start, str) or not _QUANTITY.fullmatch(start):
        raise ValueError("eth_getLogs fromBlock must be a hex block quantity")
    if not isinstance(end, str) or not _QUANTITY.fullmatch(end):
        raise ValueError("eth_getLogs toBlock must be a hex block quantity")
    first, last = int(start, 16), int(end, 16)
    if last < first:
        raise ValueError("eth_getLogs toBlock precedes fromBlock")
    if last - first > _MAX_LOG_BLOCK_SPAN:
        raise ValueError("eth_getLogs block range exceeds the 100000-block limit")
    topics = log_filter.get("topics", [])
    if not isinstance(topics, list) or len(topics) > 4:
        raise ValueError("eth_getLogs topics must be an array of at most four entries")
    for topic in topics:
        values = topic if isinstance(topic, list) else [topic]
        if topic is None:
            continue
        if not values or any(not isinstance(value, str) or not _TOPIC.fullmatch(value)
                             for value in values):
            raise ValueError("eth_getLogs topics must contain 32-byte hashes or null")
    return address.lower(), first, last


def rpc_read(endpoint, method, params=(), opener=None):
    """Call only the explicitly allowed read-only JSON-RPC methods."""
    if method not in ("eth_chainId", "eth_blockNumber", "eth_getTransactionByHash",
                      "eth_getTransactionReceipt", "eth_call", "eth_getLogs"):
        raise ValueError("Disallowed JSON-RPC method")
    if method in ("eth_getTransactionByHash", "eth_getTransactionReceipt"):
        if len(params) != 1 or not isinstance(params[0], str) or not _TXID.fullmatch(params[0]):
            raise ValueError("Expected a 0x-prefixed 32-byte transaction hash")
    elif method == "eth_call":
        if len(params) != 2 or not isinstance(params[0], dict):
            raise ValueError("eth_call requires a call object and block identifier")
        call = params[0]
        if set(call) - {"to", "data"} or not _ADDRESS.fullmatch(str(call.get("to", ""))):
            raise ValueError("eth_call only accepts a valid to address and calldata")
        if not isinstance(call.get("data"), str) or not _HEX_DATA.fullmatch(call["data"]):
            raise ValueError("eth_call data must be 0x-prefixed even-length hex")
        block = params[1]
        if not isinstance(block, str) or (block not in _BLOCK_TAGS and not _QUANTITY.fullmatch(block)):
            raise ValueError("eth_call block must be a valid tag or hex quantity")
    elif method == "eth_getLogs":
        _validate_log_filter(params)
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


def contract_call(config, ledger, to, data, block="latest", opener=None):
    """Read one contract call through eth_call; this never broadcasts."""
    if not isinstance(to, str) or not _ADDRESS.fullmatch(to):
        raise ValueError("Expected a 20-byte contract address")
    if not isinstance(data, str) or not _HEX_DATA.fullmatch(data):
        raise ValueError("Call data must be 0x-prefixed even-length hex")
    spec = config["ledgers"].get(ledger)
    endpoint = _provider(spec)
    chain_id = _chain(endpoint, spec["chainId"], opener)
    result = rpc_read(endpoint, "eth_call", ({"to": to, "data": data}, block), opener=opener)
    if not isinstance(result, str) or not _HEX_DATA.fullmatch(result):
        raise ValueError("RPC returned invalid eth_call data")
    return {"ledger": ledger, "chainId": chain_id, "to": to.lower(),
            "block": block, "result": result.lower()}


def contract_logs(config, ledger, address, from_block, to_block, topics=None, opener=None):
    """Fetch bounded logs for one contract address through eth_getLogs."""
    if not isinstance(address, str) or not _ADDRESS.fullmatch(address):
        raise ValueError("Expected a 20-byte contract address")
    if type(from_block) is not int or type(to_block) is not int or from_block < 0 or to_block < from_block:
        raise ValueError("Log block bounds must be ordered nonnegative integers")
    if to_block - from_block > _MAX_LOG_BLOCK_SPAN:
        raise ValueError("Log block range exceeds the 100000-block limit")
    filter_value = {"address": address, "fromBlock": hex(from_block), "toBlock": hex(to_block)}
    if topics is not None:
        filter_value["topics"] = topics
    spec = config["ledgers"].get(ledger)
    endpoint = _provider(spec)
    chain_id = _chain(endpoint, spec["chainId"], opener)
    result = rpc_read(endpoint, "eth_getLogs", (filter_value,), opener=opener)
    if not isinstance(result, list):
        raise ValueError("RPC returned invalid eth_getLogs data")
    checked = []
    for item in result:
        if not isinstance(item, dict) or str(item.get("address", "")).lower() != address.lower():
            raise ValueError("RPC returned a log for an unexpected contract")
        block_number = _quantity(item.get("blockNumber"), "log blockNumber")
        if block_number < from_block or block_number > to_block:
            raise ValueError("RPC returned a log outside the requested block range")
        if not isinstance(item.get("data"), str) or not _HEX_DATA.fullmatch(item["data"]):
            raise ValueError("RPC returned invalid log data")
        log_topics = item.get("topics")
        if not isinstance(log_topics, list) or len(log_topics) > 4 or any(
            not isinstance(topic, str) or not _TOPIC.fullmatch(topic) for topic in log_topics
        ):
            raise ValueError("RPC returned invalid log topics")
        checked.append(item)
    return {"ledger": ledger, "chainId": chain_id, "address": address.lower(),
            "fromBlock": from_block, "toBlock": to_block,
            "count": len(checked), "logs": checked}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read Polygon/EVM JSON-RPC without signing")
    parser.add_argument("--config", help="Private ledger config path")
    command = parser.add_subparsers(dest="command", required=True)
    health = command.add_parser("status", help="Check network chain ID and block height")
    health.add_argument("ledger", nargs="?", default="polygon")
    tx = command.add_parser("transaction", help="Read a transaction and receipt")
    tx.add_argument("ledger")
    tx.add_argument("txid")
    call = command.add_parser("call", help="Call a contract read method without broadcasting")
    call.add_argument("ledger")
    call.add_argument("to", help="Contract address")
    call.add_argument("data", help="ABI-encoded calldata")
    call.add_argument("--block", default="latest", help="Block tag or 0x quantity")
    logs_parser = command.add_parser("logs", help="Read bounded event logs for one contract")
    logs_parser.add_argument("ledger")
    logs_parser.add_argument("address", help="Contract address")
    logs_parser.add_argument("from_block", type=int, help="Inclusive start block")
    logs_parser.add_argument("to_block", type=int, help="Inclusive end block (max span 100000)")
    logs_parser.add_argument("--topic", action="append", default=[],
                             help="32-byte topic filter by position; use * for wildcard")
    args = parser.parse_args(argv)
    try:
        config = load_ledger_config(args.config)
        if args.command == "status":
            result = status(config, args.ledger)
        elif args.command == "transaction":
            result = transaction(config, args.ledger, args.txid)
        elif args.command == "call":
            result = contract_call(config, args.ledger, args.to, args.data, args.block)
        else:
            topics = [None if topic == "*" else topic for topic in args.topic]
            result = contract_logs(config, args.ledger, args.address,
                                   args.from_block, args.to_block,
                                   topics if args.topic else None)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print("mogwai-evm: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
