#!/usr/bin/env python3
"""Mogwai local IMAP watcher: match selected incoming messages to local actions.

Python standard library. Designed for Termux and other personal workstations.
Does not store message bodies, passwords or verification codes on disk.
"""
import argparse
import datetime as dt
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from html.parser import HTMLParser
import imaplib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

IDENT = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_MESSAGE = 2 * 1024 * 1024


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_config(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if config.get("version") != 1 or not isinstance(config.get("accounts"), list) or not config["accounts"]:
        raise ValueError("configuration requires version=1 and nonempty accounts array")
    ids = set()
    for account in config["accounts"]:
        aid = account.get("id", "")
        if not IDENT.fullmatch(aid) or aid in ids:
            raise ValueError("account IDs must be unique ASCII identifiers")
        ids.add(aid)
        for field in ("host", "username", "passwordEnv"):
            if not isinstance(account.get(field), str) or not account[field]:
                raise ValueError(f"{aid}: missing {field}")
        if not ENV_NAME.fullmatch(account["passwordEnv"]):
            raise ValueError(f"{aid}: invalid passwordEnv")
        port = account.get("port", 993)
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError(f"{aid}: invalid port")
        if not isinstance(account.get("mailbox", "INBOX"), str):
            raise ValueError(f"{aid}: invalid mailbox")
        rules = account.get("rules")
        if not isinstance(rules, list) or not rules:
            raise ValueError(f"{aid}: needs at least one rule")
        rids = set()
        for rule in rules:
            rid = rule.get("id", "")
            if not IDENT.fullmatch(rid) or rid in rids:
                raise ValueError(f"{aid}: invalid or duplicate rule id")
            rids.add(rid)
            senders = rule.get("from")
            if not isinstance(senders, list) or not senders or any(
                not isinstance(s, str) or "@" not in s or parseaddr(s)[1].casefold() != s.casefold()
                for s in senders
            ):
                raise ValueError(f"{aid}/{rid}: 'from' must list exact sender addresses")
            if not isinstance(rule.get("subjectContains", ""), str):
                raise ValueError(f"{aid}/{rid}: invalid subjectContains")
            if rule.get("action", "clipboard") != "clipboard":
                raise ValueError(f"{aid}/{rid}: unsupported action")
            expression = rule.get("codeRegex", r"(?<!\d)(\d{6})(?!\d)")
            if not isinstance(expression, str) or len(expression) > 250:
                raise ValueError(f"{aid}/{rid}: invalid codeRegex")
            pattern = re.compile(expression)
            if pattern.groups != 1:
                raise ValueError(f"{aid}/{rid}: codeRegex must have exactly one capture group")
    return config


class HtmlText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignore = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.ignore += 1
        if tag in ("p", "div", "br", "td", "li"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.ignore = max(0, self.ignore - 1)
        if tag in ("p", "div", "td", "li"):
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.ignore:
            self.parts.append(data)


def body_text(message):
    plain, html = [], []
    for part in message.walk():
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue
        kind = part.get_content_type()
        if kind not in ("text/plain", "text/html"):
            continue
        try:
            value = part.get_content()
        except (LookupError, UnicodeError):
            continue
        if kind == "text/plain":
            plain.append(value)
        else:
            parser = HtmlText()
            parser.feed(value)
            html.append("".join(parser.parts))
    return "\n".join(plain if any(p.strip() for p in plain) else html)[:MAX_MESSAGE]


def matching_rule(raw, rules):
    if len(raw) > MAX_MESSAGE:
        return None
    message = BytesParser(policy=policy.default).parsebytes(raw)
    sender = parseaddr(str(message.get("From", "")))[1].casefold()
    subject = str(message.get("Subject", ""))
    text = body_text(message)
    for rule in rules:
        if sender not in {s.casefold() for s in rule["from"]}:
            continue
        if rule.get("subjectContains", "").casefold() not in subject.casefold():
            continue
        pattern = re.compile(rule.get("codeRegex", r"(?<!\d)(\d{6})(?!\d)"))
        codes = {m.group(1) for m in pattern.finditer(text)}
        if len(codes) == 1 and re.fullmatch(r"\d{6}", next(iter(codes))):
            return rule["id"], next(iter(codes))
    return None


def atomic_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=".mail-", delete=False) as f:
        name = f.name
        os.chmod(name, 0o600)
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(name, path)


def clipboard_write(code):
    if not shutil.which("termux-clipboard-set"):
        raise RuntimeError("termux-clipboard-set not found; install Termux:API and pkg install termux-api")
    subprocess.run(["termux-clipboard-set"], input=code, text=True,
                   check=True, timeout=12, capture_output=True)


def notify_ready():
    if shutil.which("termux-notification"):
        subprocess.run(["termux-notification", "--title", "Mogwai Mail",
                        "--content", "Verification code copied to clipboard"],
                       check=False, timeout=12, capture_output=True)


def uid_validity(connection, mailbox):
    typ, data = connection.status(mailbox, "(UIDVALIDITY)")
    if typ != "OK":
        raise RuntimeError("IMAP UIDVALIDITY query failed")
    item = b" ".join(x for x in data if isinstance(x, bytes))
    match = re.search(rb"UIDVALIDITY\s+(\d+)", item)
    if not match:
        raise RuntimeError("IMAP server omitted UIDVALIDITY")
    return match.group(1).decode("ascii")


def search_uids(connection, minimum=None):
    criterion = "ALL" if minimum is None else f"UID {minimum}:*"
    typ, data = connection.uid("SEARCH", None, criterion)
    if typ != "OK":
        raise RuntimeError("IMAP UID SEARCH failed")
    return [int(value) for value in (data[0] or b"").split() if value.isdigit()]


def read_uid(connection, uid):
    typ, data = connection.uid("FETCH", str(uid), "(BODY.PEEK[])")
    if typ != "OK":
        raise RuntimeError(f"IMAP UID FETCH failed for UID {uid}")
    return next((item[1] for item in data if isinstance(item, tuple)
                 and isinstance(item[1], bytes)), None)


def poll_account(account, state_file, dry_run=False, notify=False):
    aid = account["id"]
    password = os.environ.get(account["passwordEnv"])
    if not password:
        raise RuntimeError(f"{aid}: unset environment variable {account['passwordEnv']}")
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    mailbox = account.get("mailbox", "INBOX")
    with imaplib.IMAP4_SSL(account["host"], account.get("port", 993), timeout=20) as con:
        con.login(account["username"], password)
        status, _ = con.select(mailbox, readonly=True)
        if status != "OK":
            raise RuntimeError(f"{aid}: cannot select IMAP mailbox")
        validity = uid_validity(con, mailbox)
        if state.get("uidValidity") != validity or "lastUid" not in state:
            current = search_uids(con)
            atomic_state(state_file, {"uidValidity": validity,
                                      "lastUid": max(current, default=0)})
            print(f"{aid}: baseline established; old messages skipped")
            return
        last = int(state["lastUid"])
        current = sorted(set(x for x in search_uids(con, last + 1) if x > last))
        for uid in current:
            raw = read_uid(con, uid)
            if raw is not None:
                match = matching_rule(raw, account["rules"])
                if match:
                    rule_id, code = match
                    if not dry_run:
                        clipboard_write(code)
                        if notify:
                            notify_ready()
                    print(f"{aid}/{rule_id}: {'matched (dry run)' if dry_run else 'copied'} at {timestamp()}")
            if not dry_run:
                atomic_state(state_file, {"uidValidity": validity, "lastUid": uid})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--state-dir", type=Path, default=Path(os.environ.get(
        "XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "mogwai" / "mail")
    ap.add_argument("--check", action="store_true", help="validate JSON configuration without connecting")
    ap.add_argument("--once", action="store_true", help="perform a single poll and exit")
    ap.add_argument("--interval", type=int, default=10, help="poll interval in seconds, min 5")
    ap.add_argument("--dry-run", action="store_true", help="match mail without updating clipboard")
    ap.add_argument("--notify", action="store_true", help="notify after copying (without revealing code)")
    args = ap.parse_args(argv)
    os.umask(0o077)
    try:
        cfg = load_config(args.config)
    except (OSError, ValueError, re.error) as exc:
        ap.error(str(exc))
    if args.check:
        print(f"Valid configuration: {len(cfg['accounts'])} mailbox account(s)")
        return 0
    if args.interval < 5:
        ap.error("--interval must be at least 5 seconds")
    args.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    while True:
        errors = 0
        for account in cfg["accounts"]:
            try:
                poll_account(account, args.state_dir / (account["id"] + ".json"),
                             dry_run=args.dry_run, notify=args.notify)
            except (OSError, ValueError, RuntimeError, imaplib.IMAP4.error,
                    subprocess.SubprocessError) as exc:
                errors += 1
                print(f"{account['id']}: {type(exc).__name__}: {exc}", file=sys.stderr)
        if args.once:
            return 2 if errors else 0
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("Watcher stopped")
            return 0


if __name__ == "__main__":
    sys.exit(main())
