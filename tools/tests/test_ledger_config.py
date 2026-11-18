"""Tests for host-local secrets configuration (no network requests)."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from tools.ledger_config import check, endpoint_key, load_ledger_config


class LedgerConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "ledgers.json"
        self.valid = {
            "version": 1,
            "ledgers": {
                "polygon": {
                    "family": "evm",
                    "chainId": 137,
                    "read": {"url": "https://rpc.example", "apiKey": "very-private-test-token"},
                },
            },
        }

    def write(self, data=None, mode=0o600):
        self.path.write_text(json.dumps(data if data is not None else self.valid))
        self.path.chmod(mode)

    def test_valid_and_redacted(self):
        self.write()
        self.assertEqual(load_ledger_config(self.path)["ledgers"]["polygon"]["chainId"], 137)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            check(self.path)
        self.assertIn("chainId=137", output.getvalue())
        self.assertIn("key set", output.getvalue())
        self.assertNotIn("very-private-test-token", output.getvalue())
        self.assertIn("broadcast not configured", output.getvalue())

    def test_insecure_permissions_rejected(self):
        self.write(mode=0o644)
        if os.name == "posix":
            with self.assertRaisesRegex(ValueError, "chmod 600"):
                load_ledger_config(self.path)

    def test_symlink_rejected(self):
        self.write()
        target = Path(self.temp.name) / "link.json"
        target.symlink_to(self.path)
        with self.assertRaisesRegex(ValueError, "symlink"):
            load_ledger_config(target)

    def test_evm_id_required(self):
        data = json.loads(json.dumps(self.valid))
        del data["ledgers"]["polygon"]["chainId"]
        self.write(data)
        with self.assertRaisesRegex(ValueError, "chainId"):
            load_ledger_config(self.path)

    def test_insecure_remote_http_rejected(self):
        data = json.loads(json.dumps(self.valid))
        data["ledgers"]["polygon"]["read"]["url"] = "http://remote.example"
        self.write(data)
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            load_ledger_config(self.path)

    def test_env_key(self):
        endpoint = {"url": "https://rpc.example", "apiKeyEnv": "TEST_MOGWAI_API_KEY"}
        original = os.environ.get("TEST_MOGWAI_API_KEY")
        try:
            os.environ["TEST_MOGWAI_API_KEY"] = "from-environment"
            self.assertEqual(endpoint_key(endpoint), "from-environment")
        finally:
            if original is None:
                os.environ.pop("TEST_MOGWAI_API_KEY", None)
            else:
                os.environ["TEST_MOGWAI_API_KEY"] = original


if __name__ == "__main__":
    unittest.main()
