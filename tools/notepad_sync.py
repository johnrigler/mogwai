#!/usr/bin/env python3
"""Synchronize Chisel annotations to a private Notepad Git checkout.

Only this operator-run process uses Git credentials. No HTTP request executes Git.
"""
import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

COINS = {"digibyte", "ravencoin", "litecoin", "litecoinTestnet", "bitcoin",
         "bsv", "bsvTestnet", "dogecoin", "ecash", "evm"}

def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          text=True, stdout=subprocess.PIPE).stdout.strip()

def timestamp(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).isoformat()

def annotations(root):
    for folder, dirs, files in os.walk(root, followlinks=False):
        directory = Path(folder)
        dirs[:] = [name for name in dirs if not (directory / name).is_symlink()]
        for name in files:
            if not re.fullmatch(r"[0-9a-f]{64}\.json", name):
                continue
            path = directory / name
            try:
                if path.is_symlink() or path.stat().st_size > 1024 * 1024:
                    continue
                parts = path.relative_to(root).parts
                coin = parts[0]
                if coin not in COINS or len(parts) != (4 if coin == "evm" else 2):
                    continue
                doc = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(doc, dict) or doc.get("schema") != "chisel-transaction-notes-v1":
                    continue
                if doc.get("coin") != coin or doc.get("txid") != path.stem:
                    continue
                identity = {"coin": coin, "txid": path.stem}
                if coin == "evm":
                    if not re.fullmatch(r"[0-9]{1,15}", parts[1]) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", parts[2]):
                        continue
                    if str(doc.get("chainId")) != parts[1] or doc.get("sourceId") != parts[2]:
                        continue
                    identity.update(chainId=parts[1], sourceId=parts[2])
                stamp = doc.get("updatedAt")
                text, metadata = doc.get("note", ""), doc.get("metadata", {})
                if isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or not 0 < stamp < 253402300799000:
                    continue
                if not isinstance(text, str) or not isinstance(metadata, dict):
                    continue
                if not text.strip() and not metadata:
                    continue
                yield "chisel:" + ":".join((*parts[:-1], path.stem)), stamp, text, metadata, identity
            except (OSError, ValueError, TypeError, UnicodeError):
                print("Skipped invalid annotation:", path.name)

def merge(inbox, root):
    if inbox.get("schema") != "notepad-inbox-v1" or not isinstance(inbox.get("notes"), list):
        raise ValueError("Unexpected Notepad inbox schema")
    notes = inbox["notes"]
    by_id = {n["id"]: n for n in notes}
    if len(by_id) != len(notes):
        raise ValueError("Duplicate Notepad IDs")
    changed = 0
    for identifier, stamp, text, metadata, identity in annotations(root):
        old = by_id.get(identifier)
        if old is not None and old.get("sourceUpdatedAt", 0) >= stamp:
            continue  # Keep review decisions made in GitHub until a new Chisel edit.
        row = dict(old or {})
        row.update(id=identifier, createdAt=row.get("createdAt") or timestamp(stamp),
                   updatedAt=timestamp(stamp), sourceUpdatedAt=stamp, source="chisel",
                   text=text, metadata=metadata, status="reviewed" if metadata.get("notepadReview") is False else "pending",
                   **identity)
        if old is None:
            notes.append(row)
        else:
            notes[notes.index(old)] = row
        by_id[identifier] = row
        changed += 1
    return changed

def atomic_write(path, value):
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".notepad-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(value, out, indent=2, ensure_ascii=False)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("CHISEL_NOTEPAD_REPO", "~/notepad"))
    parser.add_argument("--data-root", default=os.environ.get("CHISEL_DATA_ROOT", "~/chisel_data"))
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    root = Path(args.data_root).expanduser().resolve() / "annotations"
    if not root.is_dir():
        raise SystemExit("Annotation directory not found: " + str(root))
    # Refuse to push annotation data to an unexpected remote.
    remote = git(repo, "remote", "get-url", "origin").rstrip("/")
    if remote not in {"https://github.com/johnrigler/notepad.git", "https://github.com/johnrigler/notepad",
                      "git@github.com:johnrigler/notepad.git", "ssh://git@github.com/johnrigler/notepad.git"}:
        raise SystemExit("Unexpected Notepad origin")
    gitdir = Path(git(repo, "rev-parse", "--absolute-git-dir"))
    with (gitdir / "notepad-sync.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if git(repo, "status", "--porcelain"):
            raise SystemExit("Notepad checkout is dirty; refusing to overwrite local work")
        if git(repo, "branch", "--show-current") != "main":
            raise SystemExit("Notepad must be checked out on main")
        git(repo, "pull", "--ff-only", "origin", "main")
        path = repo / "inbox.json"
        inbox = json.loads(path.read_text(encoding="utf-8"))
        changed = merge(inbox, root)
        if changed:
            atomic_write(path, inbox)
            git(repo, "add", "--", "inbox.json")
            git(repo, "commit", "-m", "Sync Chisel review notes")
        # Retry outstanding local commits even when there are no new notes.
        git(repo, "push", "origin", "main")
        print(json.dumps({"changed": changed, "total": len(inbox["notes"]),
                          "pending": sum(n.get("status") == "pending" for n in inbox["notes"])}))

if __name__ == "__main__":
    main()
