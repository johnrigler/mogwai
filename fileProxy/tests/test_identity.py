import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fileproxy.identity import authenticate, canonical_message, identity_root, is_blocked, write_record

ADDRESS = "L" + "a" * 33

class IdentityTests(unittest.TestCase):
    def test_signed_request_binds_payload_and_path(self):
        envelope = {"address": ADDRESS, "timestamp": 1700000000,
                    "nonce": "0123456789abcdef", "body": {"url": "https://example.org"},
                    "signature": "signature"}
        with patch("fileproxy.identity.recover_address", return_value=ADDRESS) as verifier:
            self.assertEqual(authenticate(envelope, "POST", "/v1/identity/records", now=1700000000), ADDRESS)
            self.assertTrue(verifier.called)
        with self.assertRaises(ValueError):
            authenticate(envelope, "POST", "/v1/other", now=1700000000)
        with self.assertRaises(ValueError):
            authenticate(envelope, "POST", "/v1/identity/records", now=1700000400)

    def test_identity_mismatch_rejected(self):
        envelope = {"address": ADDRESS, "timestamp": 1700000000,
                    "nonce": "0123456789abcdef", "body": {}, "signature": "signature"}
        with patch("fileproxy.identity.recover_address", return_value="L" + "b" * 33):
            with self.assertRaises(ValueError):
                authenticate(envelope, "POST", "/v1/identity/records", now=1700000000)

    def test_namespaces_and_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            first = write_record(temp, ADDRESS, "0123456789abcdef", {"text": "hello"}, 1700000000)
            self.assertEqual(first["identity"], "litecoin:" + ADDRESS)
            self.assertTrue((identity_root(temp, ADDRESS) / "records.sqlite3").is_file())
            with self.assertRaises(FileExistsError):
                write_record(temp, ADDRESS, "0123456789abcdef", {"text": "different"}, 1700000000)
            other = "L" + "b" * 33
            write_record(temp, other, "0123456789abcdef", {"text": "independent"}, 1700000000)
            self.assertNotEqual(identity_root(temp, ADDRESS), identity_root(temp, other))

    def test_blacklist(self):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, "blacklist.json").write_text(json.dumps({"addresses": [ADDRESS]}))
            self.assertTrue(is_blocked(temp, ADDRESS))
            with self.assertRaises(PermissionError):
                write_record(temp, ADDRESS, "0123456789abcdef", {}, 1700000000)

    def test_no_client_path(self):
        with self.assertRaises(ValueError):
            identity_root("/tmp/identities", "../../etc")

if __name__ == "__main__":
    unittest.main()
