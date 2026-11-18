"""Offline tests for safe migration of host-private Etherscan V2 credentials."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from tools.ledger_config import load_ledger_config
from tools.migrate_etherscan import migrate


class MigrateEtherscanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / "etherscan.json"
        self.target = root / "ledgers.json"
        self.legacy = {"version": 1, "etherscan": {
            "url": "https://api.etherscan.io/v2/api",
            "chainId": 137, "apiKey": "fake-private-key-test-only"
        }}
        self.current = {"version": 1, "ledgers": {"polygon": {
            "family": "evm", "chainId": 137,
            "read": {"url": "https://polygon.drpc.org"}
        }}}
        self.write(self.source, self.legacy)
        self.write(self.target, self.current)

    def write(self, path, value):
        path.write_text(json.dumps(value), encoding="utf-8")
        path.chmod(0o600)

    def test_dry_run_does_not_change_files_or_show_key(self):
        before = self.target.read_bytes()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertTrue(migrate(self.source, self.target, apply=False))
        self.assertEqual(self.target.read_bytes(), before)
        self.assertNotIn("fake-private-key-test-only", output.getvalue())

    def test_apply_migrates_and_preserves_source(self):
        source_before = self.source.read_bytes()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertTrue(migrate(self.source, self.target, apply=True))
        config = load_ledger_config(self.target)
        self.assertEqual(config["ledgers"]["polygon"]["providers"]["etherscan"]["apiKey"],
                         "fake-private-key-test-only")
        self.assertEqual(config["ledgers"]["polygon"]["read"]["url"], "https://polygon.drpc.org")
        self.assertEqual(self.source.read_bytes(), source_before)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("fake-private-key-test-only", output.getvalue())

    def test_existing_key_is_not_replaced(self):
        self.current["ledgers"]["polygon"]["providers"] = {"etherscan": {
            "url": "https://api.etherscan.io/v2/api", "apiKey": "already-configured"
        }}
        self.write(self.target, self.current)
        before = self.target.read_bytes()
        with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
            migrate(self.source, self.target, apply=True)
        self.assertEqual(self.target.read_bytes(), before)

    def test_reject_insecure_source(self):
        self.source.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "chmod 600"):
            migrate(self.source, self.target, apply=False)


if __name__ == "__main__":
    unittest.main()
