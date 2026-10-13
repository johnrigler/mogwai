#!/usr/bin/env python3
"""Read-only, stdlib-only public-source change detector for Mogwai.

This is NOT a court-document crawler or a proof of a legally material event.
Use FileProxy for reviewed ingest; retain original bytes before ledger anchoring.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
MAX_BYTES = 16 * 1024 * 1024


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=".watch-", delete=False) as f:
        tmp = Path(f.name)
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def append_event(path, event):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")


def snapshot(directory, source_id, digest, body, content_type):
    extension = ".pdf" if "application/pdf" in content_type.lower() else ".bin"
    dest = directory / "blobs" / source_id / (digest + extension)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Immutable snapshot name: never silently replace previously captured bytes.
    try:
        with dest.open("xb") as f:
            f.write(body)
    except FileExistsError:
        if dest.stat().st_size != len(body):
            raise RuntimeError("snapshot hash path has unexpected size: " + str(dest))
    return str(dest)


def poll_source(source, previous, out, timeout, limit, archive, agent):
    sid = source["id"]
    url = source["url"]
    if not ID.fullmatch(sid):
        raise ValueError("invalid source ID: " + str(sid))
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost")
    ):
        raise ValueError("only HTTPS sources (or local HTTP fixtures) are allowed")
    headers = {"User-Agent": agent, "Accept": "*/*"}
    if previous.get("etag"):
        headers["If-None-Match"] = previous["etag"]
    if previous.get("lastModified"):
        headers["If-Modified-Since"] = previous["lastModified"]
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        response = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 304 and previous.get("sha256"):
            return {**previous, "lastCheckedAt": now()}, "unchanged", None
        raise
    with response:
        if response.status == 304 and previous.get("sha256"):
            return {**previous, "lastCheckedAt": now()}, "unchanged", None
        # Do not silently follow an HTTPS->HTTP downgrade.
        final = urllib.parse.urlsplit(response.geturl())
        if final.scheme != "https" and not (
            final.scheme == "http" and final.hostname in ("localhost", "127.0.0.1")
        ):
            raise ValueError("insecure redirect target")
        body = response.read(limit + 1)
        if len(body) > limit:
            raise ValueError("response exceeds --max-mib limit")
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        etag = response.headers.get("ETag")
        modified = response.headers.get("Last-Modified")
    digest = hashlib.sha256(body).hexdigest()
    prior = previous.get("sha256")
    status = "baseline" if prior is None else ("changed" if prior != digest else "unchanged")
    record = {
        "sourceId": sid, "uri": url, "resolvedUri": response.geturl(),
        "sha256": digest, "byteLength": len(body), "contentType": content_type,
        "etag": etag, "lastModified": modified, "lastCheckedAt": now(),
        "firstSeenAt": previous.get("firstSeenAt") or now(),
        "verification": "bytes-captured" if archive else "hash-observed-only",
        "snapshot": previous.get("snapshot") if digest == prior else None
    }
    if archive and (status != "unchanged" or not record["snapshot"]):
        record["snapshot"] = snapshot(out, sid, digest, body, content_type)
    event = None
    if status != "unchanged":
        event = {
            "type": "source-baseline" if status == "baseline" else "source-byte-change",
            "sourceId": sid, "uri": url, "observedAt": record["lastCheckedAt"],
            "sha256": digest, "previousSha256": prior,
            "byteLength": len(body), "snapshot": record["snapshot"],
            "materiality": "unreviewed",
            "note": "Change in retrieved bytes; NOT a new filing or legal finding."
        }
    return record, status, event


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True, type=Path, help="JSON watch sources config")
    ap.add_argument("--state-dir", type=Path, default=Path(
        os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))
    ) / "mogwai" / "watch")
    ap.add_argument("--archive", action="store_true", help="save exact retrieved bytes on disk")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--max-mib", type=int, default=12)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    if not isinstance(cfg.get("sources"), list) or not cfg.get("subjectId"):
        ap.error("config must have subjectId and sources array")
    if not (1 <= args.max_mib <= 16) or args.timeout < 1:
        ap.error("limits must be 1..16 MiB and timeout >= 1 second")
    args.state_dir.mkdir(parents=True, exist_ok=True)
    state_path = args.state_dir / ("state-" + re.sub(r"[^A-Za-z0-9._-]", "-", cfg["subjectId"]) + ".json")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    data = state.get("sources", {})
    agent = os.environ.get("MOGWAI_WATCH_USER_AGENT", "MogwaiSourceWatch/0.1 (local operator)")
    failures = 0
    for source in cfg["sources"]:
        sid = source.get("id", "?")
        if not source.get("enabled", True):
            print(f"{sid}: disabled")
            continue
        try:
            record, status, event = poll_source(
                source, data.get(sid, {}), args.state_dir, args.timeout,
                args.max_mib * 1024 * 1024, args.archive, agent)
            data[sid] = record
            print(f"{sid}: {status} sha256={record['sha256'][:16]}")
            if event is not None:
                event["subjectId"] = cfg["subjectId"]
                append_event(args.state_dir / "events.jsonl", event)
        except Exception as exc:
            failures += 1
            print(f"{sid}: ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
            append_event(args.state_dir / "errors.jsonl", {
                "subjectId": cfg["subjectId"], "sourceId": sid,
                "checkedAt": now(), "error": f"{type(exc).__name__}: {exc}",
                "note": "Fetch failure is NOT evidence of a new event."
            })
    atomic_json(state_path, {"version": 1, "subjectId": cfg["subjectId"], "sources": data})
    return 2 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
