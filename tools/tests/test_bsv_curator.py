import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location("bsv_curator", SOURCE / "bsv_curator.py")
curator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(curator)


def transaction(n, data=None, truncated=False):
    script = "76a914" + "11" * 20 + "88ac"
    if data is not None:
        script = "006a4d" + len(data).to_bytes(2, "little").hex() + data.hex()
    return {"txid": f"{n:064x}", "size": 1500, "blockhash": f"{100:064x}",
            "vin": [{}], "vout": [{"scriptPubKey": {"hex": script, "isTruncated": truncated}}]}


class ClassificationTests(unittest.TestCase):
    def test_large_payment_not_artifact(self):
        row = curator.classify(transaction(1))
        self.assertEqual((row["classification"], row["reason"]),
                         ("discard", "no-observed-op-return-payload"))

    def test_ipfs_pointer_is_metadata(self):
        row = curator.classify(transaction(2, b"ipfs://bafybeigdyrztkinkhotxexample"))
        self.assertEqual(row["classification"], "metadata")
        self.assertTrue(row["hasLink"])

    def test_jpeg_is_artifact(self):
        row = curator.classify(transaction(3, b"\xff\xd8\xff" + b"abc"))
        self.assertEqual(row["classification"], "artifact")
        self.assertIn("image/jpeg", row["mimeTypes"])

    def test_truncated_script_is_not_pruned(self):
        row = curator.classify(transaction(4, b"", truncated=True))
        self.assertEqual(row["classification"], "unknown")

    def test_unknown_binary_retained(self):
        row = curator.classify(transaction(5, b"\x00\x01\x02\x03\x04"))
        self.assertEqual(row["classification"], "unknown")


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.archive = self.root / "transactions/bsv"
        self.archive.mkdir(parents=True)
        self.db = sqlite3.connect(self.root / "scan.db")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE transactions (height INTEGER,tx_index INTEGER,txid TEXT,selected INTEGER,raw TEXT);
            CREATE TABLE blocks (height INTEGER,hash TEXT,time INTEGER);
        """)
        self.db.execute("INSERT INTO blocks VALUES (100,?,100)", (f"{100:064x}",))
        for n, data in [(1, None), (2, b"hello meaningful message"), (3, b"\xff\xd8\xffabc")]:
            raw = transaction(n, data)
            self.db.execute("INSERT INTO transactions VALUES (100,?,?,1,?)", (n, raw["txid"], json.dumps(raw)))
            (self.archive / (raw["txid"] + ".json")).write_text(json.dumps(raw))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_enrich_does_not_prune(self):
        original = curator.export
        curator.export = lambda *args: None
        try:
            report = curator.operate(self.db, self.root, self.root / "bsv", 100, prune=False)
            self.assertEqual(report["mode"], "enrich")
            self.assertEqual(report["prunedRecords"], 0)
            self.assertEqual(self.db.execute("SELECT SUM(selected) FROM transactions").fetchone()[0], 3)
            self.assertEqual(self.db.execute("SELECT COUNT(*) FROM bsv_curation").fetchone()[0], 3)
            self.assertEqual(len(list(self.archive.glob("*.json"))), 3)
        finally:
            curator.export = original

    def test_collect_and_prune_reversible(self):
        report, _ = curator.collect(self.db, self.root)
        self.assertEqual(report["byClass"], {"discard": 1, "metadata": 1, "artifact": 1})
        original = curator.export
        curator.export = lambda *args: None  # Scanner feed publication is independently tested.
        try:
            applied = curator.operate(self.db, self.root, self.root / "bsv", 100)
            self.assertEqual(applied["prunedRecords"], 1)
            self.assertEqual(self.db.execute("SELECT SUM(selected) FROM transactions").fetchone()[0], 2)
            self.assertFalse((self.archive / (f"{1:064x}.json")).exists())
            self.assertTrue((self.archive / (f"{3:064x}.json")).exists())
            self.assertEqual(self.db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 3)
            restored = curator.operate(self.db, self.root, self.root / "bsv", 100, restore=True)
            self.assertEqual(restored["restored"], 1)
            self.assertEqual(self.db.execute("SELECT SUM(selected) FROM transactions").fetchone()[0], 3)
        finally:
            curator.export = original


if __name__ == "__main__":
    unittest.main()
