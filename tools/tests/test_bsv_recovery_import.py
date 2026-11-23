import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bsv_recovery_import", TOOLS / "bsv_recovery_import.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
from fileproxy.core import scan


class RecoveryImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.source = self.base / "source"
        self.target = self.base / "archive"
        self.source.mkdir()
        self.target.mkdir()
        self.txid = "1" * 64
        self.txpath = "transactions/bsv/" + self.txid + ".json"
        self.asset = "artifacts/bsv/" + self.txid + "/1.txt"
        self.write(self.txpath, json.dumps({"txid": self.txid, "vout": [], "size": 123}).encode())
        self.write(self.asset, b"exact recovered bytes")
        self.catalog()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, relative, data):
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def catalog(self):
        scan({"roots": {"recovery": str(self.source)}})

    def test_import_is_idempotent_and_preserves_scanner_state(self):
        state = self.target / "bsv-index.sqlite3"
        state.write_bytes(b"unmodified scanner checkpoint")
        first = module.install(self.source, self.target, reindex=False)
        second = module.install(self.source, self.target, reindex=False)
        self.assertEqual((first["copied"], second["copied"], second["unchanged"]), (2, 0, 2))
        self.assertEqual((self.target / self.asset).read_bytes(), b"exact recovered bytes")
        self.assertEqual(state.read_bytes(), b"unmodified scanner checkpoint")

    def test_hash_mismatch_fails_before_any_write(self):
        (self.source / self.asset).write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            module.install(self.source, self.target, reindex=False)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_catalog_uses_binary_sha_and_rejects_hex_text(self):
        with sqlite3.connect(self.source / "catalog.sqlite3") as db:
            self.assertEqual(db.execute("SELECT DISTINCT typeof(sha256), length(sha256) FROM files").fetchall(), [("blob", 32)])
            db.execute("PRAGMA ignore_check_constraints=ON")
            db.execute("UPDATE files SET sha256=?", ("0" * 64,))
        with self.assertRaisesRegex(ValueError, "32-byte BLOB"):
            module.entries(self.source)

    def test_existing_different_artifact_is_preserved(self):
        target = self.target / self.asset
        target.parent.mkdir(parents=True)
        target.write_bytes(b"existing artifact")
        with self.assertRaises(FileExistsError):
            module.install(self.source, self.target, reindex=False)
        self.assertEqual(target.read_bytes(), b"existing artifact")
        self.assertFalse((self.target / self.txpath).exists())

    def test_existing_transaction_extension_fields_are_preserved(self):
        target = self.target / self.txpath
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps({"txid": self.txid, "localNote": "keep", "size": 100}))
        module.install(self.source, self.target, reindex=False)
        self.assertEqual(json.loads(target.read_text())["localNote"], "keep")
        self.assertEqual(module.install(self.source, self.target, reindex=False)["copied"], 0)

    def test_symlink_destination_cannot_escape(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.target / "artifacts").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "escapes"):
            module.install(self.source, self.target, reindex=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_parent_path_in_catalog_is_rejected(self):
        with sqlite3.connect(self.source / "catalog.sqlite3") as db:
            db.execute("UPDATE files SET path='../outside' WHERE path=?", (self.asset,))
        with self.assertRaises(ValueError):
            module.entries(self.source)

    def test_streams_merge_additively_with_existing_label(self):
        address = "1AxSECRETxBEACHxSoLUTioNSzzzRf6MZh"
        self.write("bsv/discoveries/example.json", json.dumps({"streams": [{"coin": "bsv", "address": address, "label": "new", "transactions": [{"txid": self.txid}]}]}).encode())
        self.catalog()
        sys.path.insert(0, str(TOOLS.parent / "fileProxy/tools/fileProxy"))
        import proxy
        proxy.configure_data_root(self.target)
        proxy.write_main_stream({"coin": "bsv", "address": address, "label": "existing", "transactions": [{"txid": "2" * 64}]})
        module.install(self.source, self.target, reindex=False)
        module.install(self.source, self.target, reindex=False)
        stream = proxy.read_json_object(proxy.stream_manifest_path("bsv", address))
        self.assertEqual(stream["label"], "existing")
        self.assertEqual({r["txid"] for r in stream["transactions"]}, {self.txid, "2" * 64})
        self.assertEqual(len(stream["transactions"]), 2)


if __name__ == "__main__":
    unittest.main()
