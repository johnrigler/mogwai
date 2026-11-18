#!/usr/bin/env python3
"""Safely copy an existing private Etherscan config into Polygon's providers map.

This is a local migration only. It does not access networks, log API keys,
delete the source file, or modify other ledger entries.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

if __package__:
    from .ledger_config import load_ledger_config, _path, _provider
else:
    from ledger_config import load_ledger_config, _path, _provider


DEFAULT_SOURCE = "~/.config/mogwai/etherscan.json"


def _read_source(path):
    target = Path(path).expanduser()
    if target.is_symlink():
        raise ValueError("Etherscan source must not be a symlink")
    info = target.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("Etherscan source must be a regular file")
    if os.name == "posix" and (info.st_mode & 0o077 or info.st_uid != os.geteuid()):
        raise ValueError("Etherscan source requires current-user ownership and chmod 600")
    document = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("version") != 1:
        raise ValueError("Etherscan source needs version 1")
    legacy = document.get("etherscan")
    if not isinstance(legacy, dict) or set(legacy) - {"url", "chainId", "apiKey", "apiKeyEnv"}:
        raise ValueError("Unsupported Etherscan source format")
    if legacy.get("chainId") != 137 or type(legacy.get("chainId")) is not int:
        raise ValueError("Legacy Etherscan config must specify Polygon chainId 137")
    migrated = {name: legacy[name] for name in ("url", "apiKey", "apiKeyEnv") if name in legacy}
    if not migrated.get("apiKey") and not migrated.get("apiKeyEnv"):
        raise ValueError("Etherscan source does not contain an API key or environment reference")
    _provider(migrated, "polygon", "etherscan")
    return migrated


def _write_private(path, document):
    """Atomically replace the current-user private ledger file."""
    payload = (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    destination = Path(path).expanduser()
    fd, tmp_name = tempfile.mkstemp(prefix=".mogwai-ledgers-", dir=str(destination.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as writer:
            writer.write(payload)
            writer.flush()
            os.fsync(writer.fileno())
        os.replace(tmp_name, destination)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def migrate(source=DEFAULT_SOURCE, destination=None, apply=False):
    destination = _path(destination)
    if Path(source).expanduser().resolve() == destination.resolve():
        raise ValueError("Source and destination must be different files")
    legacy = _read_source(source)
    current = load_ledger_config(destination)
    polygon = current.get("ledgers", {}).get("polygon")
    if not isinstance(polygon, dict) or polygon.get("family") != "evm" or polygon.get("chainId") != 137:
        raise ValueError("Target must contain a Polygon EVM ledger for chain 137")
    providers = polygon.get("providers", {})
    if not isinstance(providers, dict):
        raise ValueError("Target Polygon providers must be an object")
    existing = providers.get("etherscan")
    if existing is not None:
        if not isinstance(existing, dict):
            raise ValueError("Existing Etherscan provider is invalid")
        # An empty example placeholder may be filled. Never replace a real key.
        if existing.get("apiKey") or existing.get("apiKeyEnv"):
            if existing == legacy:
                print("Etherscan is already configured; no changes made.")
                return False
            raise ValueError("Target already has Etherscan credentials; refusing to overwrite")
        if existing.get("url") and existing["url"] != legacy["url"]:
            raise ValueError("Etherscan URL differs; edit the private file manually")
    updated = copy.deepcopy(current)
    updated["ledgers"]["polygon"].setdefault("providers", {})["etherscan"] = legacy
    if not apply:
        print("Dry run: Etherscan can be added under ledgers.polygon.providers.etherscan.")
        print("Run with --apply to write; source will remain unchanged.")
        return True
    _write_private(destination, updated)
    # Verify new destination, including permissions, without displaying credentials.
    load_ledger_config(destination)
    print("Imported Etherscan into private Polygon provider configuration.")
    print("Original etherscan.json retained. No credentials printed.")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="Migrate private Polygon Etherscan provider (no secrets printed)")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="Legacy private etherscan.json")
    parser.add_argument("--config", help="Private target ledgers.json")
    parser.add_argument("--apply", action="store_true", help="Write change after validation; default is dry-run")
    args = parser.parse_args(argv)
    try:
        migrate(args.source, args.config, apply=args.apply)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("mogwai-etherscan-migrate: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
