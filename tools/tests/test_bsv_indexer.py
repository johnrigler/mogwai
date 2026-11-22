import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location("bsv_indexer", Path(__file__).resolve().parents[1] / "bsv_indexer.py")
bsv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bsv)


def h(n):
    return "%064x" % n


def tx(n, size=300, payload=b"", truncated=False, coinbase=False):
    script = "006a4d" + len(payload).to_bytes(2, "little").hex() + payload.hex() if payload else "76a914" + "12" * 20 + "88ac"
    return {"txid": h(n), "size": size, "blockhash": h(100),
            "vin": [{"coinbase": "abc"}] if coinbase else [{}],
            "vout": [{"scriptPubKey": {"hex": script, "isTruncated": truncated}}]}


class Provider:
    def __init__(self):
        self.items = [tx(1, coinbase=True), tx(2, 2000), tx(3, payload=b"hello " * 30), tx(4)]
        self.calls = []
        self.fail = False
        self.block_hash = h(100)

    def tip(self):
        return 1000

    def block(self, height):
        return {"height": height, "hash": self.block_hash, "size": 4000,
                "time": 1700000000, "txcount": len(self.items), "tx": [t["txid"] for t in self.items]}

    def transactions(self, block, start, limit):
        self.calls.append(start)
        if self.fail:
            raise ValueError("rate limited")
        return [dict(t, blockhash=self.block_hash) for t in self.items[start:start + limit]]


def args(**kw):
    return SimpleNamespace(**dict(dict(start_height=100, stop_height=100, blocks=1,
        max_transactions=2, confirmations=6, min_tx_bytes=None, min_data_bytes=None), **kw))


class ScanTests(unittest.TestCase):
    def test_b_file_metadata_survives_truncated_script(self):
        marker = b"19HxigV4QyBv3tHpQVcUEQyq1pzZVdoAut"
        raw = tx(22)
        raw["vout"][0]["scriptPubKey"] = {"hex": "006a" + bytes([len(marker)]).hex() + marker.hex() + "4d1000ffd8ff[truncated]", "isTruncated": True}
        info = bsv.inspect_transaction(raw, 1024, 128)
        file = info["files"][0]
        self.assertEqual((file["mime"], file["mimeSource"], file["bytes"], file["availableBytes"], file["complete"]), ("image/jpeg", "signature", 16, 3, False))
        self.assertEqual(bsv.inspect_files(tx(23, payload=b"https://example.org/image.jpg")), [])

    def test_export_classifies_previously_saved_raw_without_changing_coverage(self):
        provider = Provider()
        bsv.scan(self.db, provider, args(max_transactions=4))
        marker, data = b"19HxigV4QyBv3tHpQVcUEQyq1pzZVdoAut", b"\xff\xd8\xffabc"
        raw = provider.items[1]
        parts = [marker, data, b"image/jpeg", b"binary", b"photo.jpg"]
        raw["vout"][0]["scriptPubKey"]["hex"] = "006a" + b"".join(bytes([len(p)]) + p for p in parts).hex()
        self.db.execute("UPDATE transactions SET raw=? WHERE txid=?", (json.dumps(raw), raw["txid"]))
        checked = bsv.status(self.db)["transactionsChecked"]
        out = Path(self.temp.name) / "reclassified"
        bsv.export(self.db, out, 100)
        manifest = json.loads((out / "manifest.json").read_text())
        index = json.loads((out / manifest["defaultIndex"]).read_text())
        file = index["transactions"][0]["summary"]["files"][0]
        self.assertEqual((file["name"], file["mimeSource"], file["complete"]), ("photo.jpg", "declared", True))
        self.assertEqual(index["scan"]["transactionsChecked"], checked)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = bsv.connect(Path(self.temp.name) / "index.sqlite3")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_partial_resume_sizes_candidates_and_export(self):
        provider = Provider()
        bsv.scan(self.db, provider, args())
        report = bsv.status(self.db)
        self.assertEqual((report["transactionsChecked"], report["blocksComplete"], report["nextHeight"]), (2, 0, 100))
        bsv.scan(self.db, provider, args(start_height=None))
        report = bsv.status(self.db)
        self.assertEqual((report["transactionsChecked"], report["blocksComplete"], report["nextHeight"]), (4, 1, 99))
        self.assertEqual(provider.calls, [0, 2])
        self.assertEqual(report["candidates"], 2)
        self.assertEqual(self.db.execute("SELECT bytes FROM transactions ORDER BY tx_index").fetchall()[0][0], 300)
        out = Path(self.temp.name) / "public"
        bsv.export(self.db, out, 100)
        manifest = json.loads((out / "manifest.json").read_text())
        index = json.loads((out / manifest["defaultIndex"]).read_text())
        self.assertEqual([r["txid"] for r in index["transactions"]], [h(2), h(3)])
        self.assertEqual(index["scan"]["blocksComplete"], 1)
        for record in index["transactions"]:
            self.assertEqual(json.loads((out / record["rawPath"]).read_text())["txid"], record["txid"])

    def test_provider_failure_keeps_partial_cursor(self):
        provider = Provider()
        bsv.scan(self.db, provider, args())
        provider.fail = True
        with self.assertRaisesRegex(ValueError, "rate limited"):
            bsv.scan(self.db, provider, args(start_height=None))
        self.assertEqual(bsv.status(self.db)["transactionsChecked"], 2)
        provider.fail = False
        bsv.scan(self.db, provider, args(start_height=None))
        self.assertEqual(provider.calls, [0, 2, 2])

    def test_mismatched_block_rolls_back_whole_batch(self):
        provider = Provider()
        original = provider.transactions
        def bad(*values):
            batch = original(*values)
            batch[-1]["blockhash"] = h(999)
            return batch
        provider.transactions = bad
        with self.assertRaisesRegex(ValueError, "block hash"):
            bsv.scan(self.db, provider, args())
        self.assertEqual(bsv.status(self.db)["transactionsChecked"], 0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM transactions").fetchone()[0], 0)

    def test_changed_hash_restarts_partial_block(self):
        provider = Provider()
        bsv.scan(self.db, provider, args())
        provider.block_hash = h(101)
        bsv.scan(self.db, provider, args(start_height=None))
        self.assertEqual(provider.calls, [0, 0])
        self.assertEqual(bsv.status(self.db)["transactionsChecked"], 2)

    def test_threshold_changes_do_not_misrepresent_earlier_coverage(self):
        bsv.scan(self.db, Provider(), args())
        with self.assertRaisesRegex(ValueError, "thresholds changed"):
            bsv.scan(self.db, Provider(), args(min_tx_bytes=4000))

    def test_truncated_push_is_lower_bound_and_coinbase_is_not_candidate(self):
        raw = tx(1, 100000, b"data " * 40, truncated=True)
        info = bsv.inspect_transaction(raw, 1024, 128)
        self.assertFalse(info["dataComplete"])
        self.assertEqual(info["dataBytes"], 200)
        raw["vin"] = [{"coinbase": "abc"}]
        self.assertEqual(bsv.inspect_transaction(raw, 1024, 128)["selectionReasons"], [])

    def test_large_block_pages_follow_initial_ids_and_resume_at_page_boundaries(self):
        provider = bsv.WhatsOnChain()
        calls = []
        block = {"height": 100, "hash": h(100), "txcount": 7, "tx": [h(1), h(2)], "pages": {"size": 3}}
        def request(path, payload=None):
            calls.append(path)
            if path.endswith("/page/1"):
                return [h(3), h(4), h(5)]
            if path.endswith("/page/2"):
                return [h(6), h(7)]
            return [tx(int(txid, 16)) for txid in reversed(payload["txids"])]
        provider.request = request
        got = []
        cursor = 0
        while cursor < 7:
            batch = provider.transactions(block, cursor, 20)
            got.extend(t["txid"] for t in batch)
            cursor += len(batch)
        self.assertEqual(got, [h(i) for i in range(1, 8)])
        self.assertEqual(calls.count("/block/hash/" + h(100) + "/page/1"), 1)
        self.assertEqual(provider.transactions(block, 4, 20)[0]["txid"], h(5))

    def test_missing_bulk_transaction_never_advances(self):
        provider = bsv.WhatsOnChain()
        provider.request = lambda *a: [tx(1)]
        with self.assertRaisesRegex(ValueError, "omitted transactions"):
            provider.transactions({"txcount": 2, "tx": [h(1), h(2)]}, 0, 2)


if __name__ == "__main__":
    unittest.main()
