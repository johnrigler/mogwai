#!/usr/bin/env python3
"""Private, host-local ledger provider settings for trusted Mogwai tools.

This module only loads and checks endpoint configuration. It never signs,
broadcasts, makes HTTP requests, or exposes credentials through FileProxy.
"""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import urlsplit

DEFAULT_PATH = "~/.config/mogwai/ledgers.json"
_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")
_ENV = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_HEADER = re.compile(r"^[A-Za-z0-9-]+$")
_REPO = Path(__file__).resolve().parents[1]


def _path(path=None):
    return Path(path or os.environ.get("MOGWAI_LEDGER_CONFIG") or DEFAULT_PATH).expanduser()


def _endpoint(value, ledger, operation):
    if not isinstance(value, dict) or not isinstance(value.get("url"), str):
        raise ValueError(f"{ledger}.{operation} needs a url")
    if set(value) - {"url", "apiKey", "apiKeyEnv", "apiKeyHeader", "apiKeyPrefix"}:
        raise ValueError(f"{ledger}.{operation} has unrecognized fields")
    url = urlsplit(value["url"])
    if url.scheme not in ("https", "http") or not url.hostname:
        raise ValueError(f"{ledger}.{operation} needs an HTTP(S) URL")
    if url.username or url.password:
        raise ValueError(f"{ledger}.{operation} must not put credentials in URL userinfo")
    if url.scheme == "http" and url.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError(f"{ledger}.{operation} requires HTTPS except for loopback")
    for field in ("apiKey", "apiKeyEnv"):
        if field in value and not isinstance(value[field], str):
            raise ValueError(f"{ledger}.{operation}.{field} must be a string")
    if value.get("apiKey") and value.get("apiKeyEnv"):
        raise ValueError(f"{ledger}.{operation}: use apiKey or apiKeyEnv, not both")
    if value.get("apiKeyEnv") and not _ENV.fullmatch(value["apiKeyEnv"]):
        raise ValueError(f"{ledger}.{operation}.apiKeyEnv is invalid")
    if "apiKeyHeader" in value and (not isinstance(value["apiKeyHeader"], str)
                                    or not _HEADER.fullmatch(value["apiKeyHeader"])):
        raise ValueError(f"{ledger}.{operation}.apiKeyHeader is invalid")
    if "apiKeyPrefix" in value and (not isinstance(value["apiKeyPrefix"], str)
                                    or chr(13) in value["apiKeyPrefix"] or chr(10) in value["apiKeyPrefix"]):
        raise ValueError(f"{ledger}.{operation}.apiKeyPrefix is invalid")


def _provider(value, ledger, name):
    """Validate optional indexed API providers such as Etherscan V2.

    These are not EVM JSON-RPC endpoints and are not used by evm_read.py.
    """
    if not isinstance(value, dict):
        raise ValueError(f"{ledger}.providers.{name} must be an object")
    if set(value) - {"url", "apiKey", "apiKeyEnv"}:
        raise ValueError(f"{ledger}.providers.{name} has unrecognized fields")
    url = value.get("url")
    if not isinstance(url, str):
        raise ValueError(f"{ledger}.providers.{name} needs a URL")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f"{ledger}.providers.{name} requires an HTTPS URL without userinfo")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{ledger}.providers.{name} must not include query credentials or fragments")
    for field in ("apiKey", "apiKeyEnv"):
        if field in value and not isinstance(value[field], str):
            raise ValueError(f"{ledger}.providers.{name}.{field} must be a string")
    if value.get("apiKey") and value.get("apiKeyEnv"):
        raise ValueError(f"{ledger}.providers.{name}: use apiKey or apiKeyEnv, not both")
    if value.get("apiKeyEnv") and not _ENV.fullmatch(value["apiKeyEnv"]):
        raise ValueError(f"{ledger}.providers.{name}.apiKeyEnv is invalid")


def load_ledger_config(path=None):
    """Load credentials into trusted local code only, never an HTTP handler."""
    target = _path(path)
    if target.is_symlink():
        raise ValueError("Ledger config must not be a symlink")
    resolved = target.resolve(strict=True)
    if resolved == _REPO or _REPO in resolved.parents:
        raise ValueError("Ledger config must live outside the Mogwai checkout")
    info = target.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("Ledger config must be a regular file")
    if os.name == "posix":
        if info.st_mode & 0o077:
            raise ValueError("Ledger config permissions are too broad; run chmod 600 on the file")
        if info.st_uid != os.geteuid():
            raise ValueError("Ledger config must be owned by the current user")
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Ledger config must be an object with version 1")
    ledgers = data.get("ledgers")
    if not isinstance(ledgers, dict) or not ledgers:
        raise ValueError("Ledger config needs a nonempty ledgers object")
    for name, spec in ledgers.items():
        if not isinstance(name, str) or not _NAME.fullmatch(name):
            raise ValueError("Invalid ledger identifier")
        if not isinstance(spec, dict) or not isinstance(spec.get("family"), str) or not spec["family"]:
            raise ValueError(f"{name} needs a family")
        if set(spec) - {"family", "chainId", "network", "read", "broadcast", "providers"}:
            raise ValueError(f"{name} has unrecognized fields")
        if spec["family"] == "evm" and (type(spec.get("chainId")) is not int or spec["chainId"] < 1):
            raise ValueError(f"{name} needs a positive EVM chainId")
        if "network" in spec and not isinstance(spec["network"], str):
            raise ValueError(f"{name}.network must be a string")
        if "read" not in spec:
            raise ValueError(f"{name} needs a read endpoint")
        for operation in ("read", "broadcast"):
            if operation in spec:
                _endpoint(spec[operation], name, operation)
        providers = spec.get("providers", {})
        if not isinstance(providers, dict):
            raise ValueError(f"{name}.providers must be an object")
        for provider_name, provider in providers.items():
            if not isinstance(provider_name, str) or not _NAME.fullmatch(provider_name):
                raise ValueError(f"{name}.providers has an invalid name")
            _provider(provider, name, provider_name)
    return data


def endpoint_key(endpoint):
    """Resolve an API key for a trusted adapter; never print the return value."""
    if endpoint.get("apiKeyEnv"):
        return os.environ.get(endpoint["apiKeyEnv"], "")
    return endpoint.get("apiKey", "")


def check(path=None):
    config = load_ledger_config(path)
    for name, spec in sorted(config["ledgers"].items()):
        parts = [name, spec["family"]]
        if "chainId" in spec:
            parts.append("chainId=" + str(spec["chainId"]))
        if "network" in spec:
            parts.append("network=" + spec["network"])
        for operation in ("read", "broadcast"):
            if operation in spec:
                endpoint = spec[operation]
                key = "key set" if endpoint_key(endpoint) else "no key"
                parts.append(operation + " configured (" + key + ")")
            else:
                parts.append(operation + " not configured")
        for provider_name, provider in sorted(spec.get("providers", {}).items()):
            key = "key set" if endpoint_key(provider) else "no key"
            parts.append("provider " + provider_name + " configured (" + key + ")")
        print(" | ".join(parts))
    print("Configuration only: no ledger requests, signing, or broadcasts performed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate private Mogwai ledger providers without printing secrets")
    parser.add_argument("command", choices=["check"])
    parser.add_argument("--config", help="Override MOGWAI_LEDGER_CONFIG")
    args = parser.parse_args()
    try:
        check(args.config)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("mogwai-ledgers: " + str(exc), file=sys.stderr)
        sys.exit(1)
