#!/usr/bin/env python3
"""Cron-friendly, incremental Base artifact discovery.

Run once before scheduling:
    python3 tools/base_scan.py
Use --config ~/.config/mogwai/ledgers.json for a configured Base provider.
Outputs private JSONL batches; does not write to FileProxy or broadcast.
"""
import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

from base_probe import CHAIN, rpc, scan
from ledger_config import load_ledger_config


def atomic_json(path, value):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     dir=path.parent, delete=False) as out:
        tmp = Path(out.name)
        try:
            json.dump(value, out)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)


def run(args):
    os.umask(0o077)
    state_dir = Path(args.state_dir).expanduser()
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    out_dir = Path(args.output).expanduser() if args.output else state_dir / "batches"
    out_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (state_dir / "scan.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Base scan already running")
            return 0
        endpoint = {"url": "https://base.drpc.org"}
        if args.config:
            spec = load_ledger_config(args.config)["ledgers"]["base"]
            if spec.get("family") != "evm" or spec.get("chainId") != CHAIN:
                raise ValueError("Base config must specify chain 8453")
            endpoint = spec["read"]
        if int(rpc(endpoint, "eth_chainId", []), 16) != CHAIN:
            raise ValueError("Wrong RPC chain")
        # Prefer the provider's finalized head; do not silently substitute latest.
        finalized = rpc(endpoint, "eth_getBlockByNumber", ["finalized", False])
        safe = int(finalized["number"], 16)
        checkpoint = state_dir / "checkpoint.json"
        if checkpoint.exists():
            state = json.loads(checkpoint.read_text())
            if state.get("chainId") != CHAIN or type(state.get("lastBlock")) is not int:
                raise ValueError("Invalid Base checkpoint")
            start = state["lastBlock"] + 1
        else:
            start = args.start_block if args.start_block is not None else max(0, safe - args.blocks + 1)
        if start > safe:
            print("Base caught up through", safe)
            return 0
        end = min(safe, start + args.blocks - 1)
        target = out_dir / f"base-{start}-{end}.jsonl"
        options = SimpleNamespace(end_block=end, blocks=end-start+1,
                                  min_bytes=args.min_bytes, delay=args.delay,
                                  net_logs=not args.no_net_logs)
        # Write complete batches atomically; a failed scan never advances state.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=out_dir, delete=False) as out:
            tmp = Path(out.name)
            try:
                with contextlib.redirect_stdout(out):
                    scan(options, endpoint)
                out.flush()
                os.fsync(out.fileno())
                os.replace(tmp, target)
            finally:
                tmp.unlink(missing_ok=True)
        atomic_json(checkpoint, {"chainId": CHAIN, "lastBlock": end})
        print(f"Base saved {start}-{end}; finalized={safe}; backlog={safe-end}; file={target}")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config")
    p.add_argument("--state-dir", default="~/.local/state/mogwai/base-scan")
    p.add_argument("--output")
    p.add_argument("--blocks", type=int, default=100)
    p.add_argument("--start-block", type=int, help="Initial block only; ignored after checkpoint exists")
    p.add_argument("--min-bytes", type=int, default=512)
    p.add_argument("--delay", type=float, default=0.2)
    p.add_argument("--no-net-logs", action="store_true")
    args = p.parse_args()
    if not 1 <= args.blocks <= 10000 or args.min_bytes < 1 or args.delay < 0.1 or (args.start_block is not None and args.start_block < 0):
        p.error("Invalid block count, size threshold, delay or start block")
    try:
        return run(args)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print("Base scan failed: " + type(exc).__name__ + "; checkpoint not advanced for an incomplete batch", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
