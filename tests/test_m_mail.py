"""Offline tests for Mogwai's IMAP-to-clipboard adapter."""
import importlib.util
from email.message import EmailMessage
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("m_mail", ROOT / "scripts" / "m.mail.py")
mail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mail)


def message(sender="sender@agency.example", subject="Code", text="Your code is 123456"):
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = "you@example.net"
    msg["Subject"] = subject
    msg.set_content(text)
    return msg.as_bytes()


RULE = [{"id": "verify", "from": ["sender@agency.example"], "codeRegex": r"(?<!\d)(\d{6})(?!\d)"}]


class FakeIMAP:
    uids = [1, 2]
    data = {1: message(text="old code 111111"), 2: message()}
    validity = b"77"

    def __init__(self, *_args, **_kwargs):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        pass
    def login(self, *_args):
        return ("OK", [])
    def select(self, *_args, **_kwargs):
        return ("OK", [b"2"])
    def status(self, *_args):
        return ("OK", [b"INBOX (UIDVALIDITY " + self.validity + b")"])
    def uid(self, command, *_args):
        if command == "SEARCH":
            criteria = _args[-1]
            values = self.uids if criteria == "ALL" else [v for v in self.uids if v >= int(criteria.split()[1].split(':')[0])]
            return ("OK", [b" ".join(str(x).encode() for x in values)])
        if command == "FETCH":
            return ("OK", [(b"RFC822", self.data[int(_args[0])]), b")"])
        raise AssertionError(command)


class MailTests(unittest.TestCase):
    def test_sender_and_ambiguous_codes(self):
        self.assertEqual(mail.matching_rule(message(), RULE), ("verify", "123456"))
        self.assertIsNone(mail.matching_rule(message(sender="other@example.net"), RULE))
        self.assertIsNone(mail.matching_rule(message(text="Codes 123456 654321"), RULE))
        self.assertIsNone(mail.matching_rule(message(text="1234567"), RULE))

    def test_html_fallback(self):
        msg = EmailMessage()
        msg["From"] = "sender@agency.example"
        msg["Subject"] = "Code"
        msg.set_content("<div>Code: <strong>987654</strong></div>", subtype="html")
        self.assertEqual(mail.matching_rule(msg.as_bytes(), RULE), ("verify", "987654"))

    def test_config(self):
        with tempfile.TemporaryDirectory() as temp:
            source = ROOT / "config/mail.example.json"
            cfg = mail.load_config(source)
            self.assertEqual(len(cfg["accounts"]), 1)
            cfg["accounts"][0]["rules"][0]["from"] = []
            out = Path(temp) / "bad.json"
            out.write_text(json.dumps(cfg))
            with self.assertRaises(ValueError):
                mail.load_config(out)

    def test_baseline_then_one_copy_and_persist(self):
        acc = {"id": "personal", "host": "test", "username": "user",
               "passwordEnv": "MOGWAI_MAIL_PASSWORD", "rules": RULE}
        with tempfile.TemporaryDirectory() as temp, \
                mock.patch.object(mail.imaplib, "IMAP4_SSL", FakeIMAP), \
                mock.patch.dict(mail.os.environ, {"MOGWAI_MAIL_PASSWORD": "test"}), \
                mock.patch.object(mail, "clipboard_write") as clipboard:
            state = Path(temp) / "state.json"
            FakeIMAP.uids = [1]
            mail.poll_account(acc, state)
            clipboard.assert_not_called()
            self.assertEqual(json.loads(state.read_text())["lastUid"], 1)
            FakeIMAP.uids = [1, 2]
            mail.poll_account(acc, state)
            clipboard.assert_called_once_with("123456")
            self.assertNotIn("123456", state.read_text())
            mail.poll_account(acc, state)
            clipboard.assert_called_once()
            self.assertEqual(json.loads(state.read_text())["lastUid"], 2)


if __name__ == "__main__":
    unittest.main()
