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

    def test_archive_files_appear_after_each_committed_batch_before_pass_finishes(self):
        root = Path(self.temp.name) / 'chisel_data'
        directory = root / 'transactions/bsv'
        provider = Provider()
        provider.items = [tx(i + 1, size=2000) for i in range(41)]
        original = provider.transactions
        def fail_after_first_batch(block, start, limit):
            if start == 20:
                self.assertEqual(len(list(directory.glob('*.json'))), 20)
                self.assertEqual(self.db.execute('SELECT checked FROM blocks').fetchone()[0], 20)
                raise ValueError('provider paused after first committed batch')
            return original(block, start, limit)
        provider.transactions = fail_after_first_batch
        with self.assertRaisesRegex(ValueError, 'provider paused'):
            bsv.scan(self.db, provider, args(data_root=str(root), max_transactions=41))
        self.assertEqual(len(list(directory.glob('*.json'))), 20)
        self.assertFalse((directory / (h(21) + '.json')).exists())

    def test_archive_backfills_all_candidates_without_touching_existing_files_or_main_feed(self):
        import os
        provider = Provider()
        bsv.scan(self.db, provider, args(max_transactions=4))
        root = Path(self.temp.name) / 'chisel_data'
        root.mkdir()
        (root / 'manifest.json').write_text('main feed stays here')
        other = root / 'transactions/litecoin/other.json'
        other.parent.mkdir(parents=True)
        other.write_text('other chain')
        feed = root / 'bsv'
        bsv.export(self.db, feed, 1, root)
        directory = root / 'transactions/bsv'
        self.assertEqual({p.name for p in directory.glob('*.json')}, {h(2) + '.json', h(3) + '.json'})
        manifest = json.loads((feed / 'manifest.json').read_text())
        index = json.loads((feed / manifest['defaultIndex']).read_text())
        self.assertEqual(len(index['transactions']), 1)
        record = index['transactions'][0]
        self.assertEqual(record['rawPath'], '../transactions/bsv/' + h(2) + '.json')
        self.assertEqual(json.loads((feed / record['rawPath']).read_text())['txid'], record['txid'])
        self.assertFalse((feed / 'transactions').exists())
        existing = directory / (h(2) + '.json')
        saved = existing.read_bytes()
        os.utime(existing, ns=(1000000000, 1000000000))
        missing = directory / (h(3) + '.json')
        missing.unlink()
        bsv.export(self.db, feed, 1, root)
        self.assertEqual(existing.stat().st_mtime_ns, 1000000000)
        self.assertEqual(existing.read_bytes(), saved)
        self.assertTrue(missing.exists())
        self.assertEqual((root / 'manifest.json').read_text(), 'main feed stays here')
        self.assertEqual(other.read_text(), 'other chain')
        self.assertEqual(provider.calls, [0])
        with self.assertRaisesRegex(ValueError, 'general data-root manifest'):
            bsv.export(self.db, root, 1, root)
        self.assertEqual((root / 'manifest.json').read_text(), 'main feed stays here')

    def test_cli_export_backfills_the_canonical_folder_without_network_reads(self):
        import contextlib
        import io
        from unittest.mock import patch
        bsv.scan(self.db, Provider(), args(max_transactions=4))
        root = Path(self.temp.name) / 'chisel_data'
        with patch.object(bsv, 'WhatsOnChain') as provider, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bsv.main(['export', '--db', str(Path(self.temp.name) / 'index.sqlite3'),
                                       '--data-root', str(root), '--limit', '1']), 0)
        provider.return_value.tip.assert_not_called()
        provider.return_value.request.assert_not_called()
        self.assertEqual(len(list((root / 'transactions/bsv').glob('*.json'))), 2)
        self.assertTrue((root / 'bsv/manifest.json').is_file())

    def test_archive_write_failure_keeps_batch_checkpoint_and_backfill_recovers(self):
        from unittest.mock import patch
        root = Path(self.temp.name) / 'chisel_data'
        provider = Provider()
        with patch.object(bsv, 'archive_transaction', side_effect=OSError('disk temporarily unavailable')):
            with self.assertRaisesRegex(OSError, 'disk temporarily'):
                bsv.scan(self.db, provider, args(data_root=str(root)))
        self.assertEqual(self.db.execute('SELECT checked FROM blocks').fetchone()[0], 2)
        bsv.archive_saved(self.db, root)
        self.assertTrue((root / 'transactions/bsv' / (h(2) + '.json')).is_file())
        bsv.scan(self.db, provider, args(start_height=None, data_root=str(root)))
        self.assertEqual(provider.calls, [0, 2])

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

    def test_cli_repeated_large_block_reports_saved_offset_and_never_rechecks(self):
        import contextlib
        import io
        from unittest.mock import patch
        provider = Provider()
        provider.items = [tx(i + 1) for i in range(527)]
        command = ['scan', '--db', str(Path(self.temp.name) / 'index.sqlite3'),
                   '--data-root', str(Path(self.temp.name) / 'chisel_data'),
                   '--start-height', '100', '--stop-height', '100']
        reports = []
        # Each main() call opens and closes the DB, as separate shell runs do.
        for checked in (200, 400, 527):
            output = io.StringIO()
            with patch.object(bsv, 'WhatsOnChain', return_value=provider), contextlib.redirect_stdout(output):
                self.assertEqual(bsv.main(command), 0)
            report = json.loads(output.getvalue())
            reports.append(report)
            block = report['blocksThisRun'][0]
            self.assertEqual(block['startTransactionIndex'], checked - report['checkedThisRun'])
            self.assertEqual((block['nextTransactionIndex'], block['transactionsTotal']), (checked, 527))
            self.assertEqual(report['transactionsChecked'], checked)
            job = report['jobs'][0]
            if checked < 527:
                self.assertEqual(job['nextHeight'], 100)
                self.assertEqual(job['currentBlock']['nextTransactionIndex'], checked)
                self.assertEqual(job['currentBlock']['remainingTransactions'], 527 - checked)
                self.assertIn('%d/527 transactions checked' % checked, job['progress'])
            else:
                self.assertEqual(job['nextHeight'], 99)
                self.assertEqual(job['phase'], 'complete')
                self.assertIsNone(job['currentBlock'])
        self.assertEqual([r['checkedThisRun'] for r in reports], [200, 200, 127])
        self.assertEqual(provider.calls, list(range(0, 527, 20)))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM transactions').fetchone()[0], 527)

    def test_mismatched_block_rolls_back_whole_batch(self):
        provider = Provider()
        original = provider.transactions
        def bad(*values):
            batch = original(*values)
            batch[-1]["blockhash"] = h(999)
            return batch
        provider.transactions = bad
        with self.assertRaisesRegex(ValueError, "block hash"):
            bsv.scan(self.db, provider, args(data_root=self.temp.name))
        self.assertEqual(bsv.status(self.db)["transactionsChecked"], 0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM transactions").fetchone()[0], 0)
        self.assertEqual(list((Path(self.temp.name) / 'transactions/bsv').glob('*.json')), [])

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

class ChainProvider:
    def __init__(self, tip=6):
        self.head = tip
        self.fail_height = None
        self.revision = 0
        self.reads = []

    def tip(self):
        return self.head

    def block(self, height):
        if height == self.fail_height:
            raise ValueError('provider temporarily unavailable')
        return {'height': height, 'hash': h(10000 + height + self.revision * 1000),
                'size': 3000, 'time': 1700000000 + height * 600, 'txcount': 2}

    def transactions(self, block, start, limit):
        self.reads.append((block['height'], start))
        return [dict(tx(block['height'] * 10 + n, size=1500), blockhash=block['hash'])
                for n in range(start, min(2, start + limit))]


def runner_args(root, **overrides):
    return SimpleNamespace(**dict(dict(anchor_height=2, anchor_tx=None, start_height=None,
        stop_height=None, direction='backward', job=None, blocks=1, max_transactions=2,
        confirmations=0, min_tx_bytes=None, min_data_bytes=None, limit=100,
        export_dir=str(Path(root) / 'public'), once=True, interval=60), **overrides))


class DaemonTests(unittest.TestCase):
    def setUp(self):
        import threading
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'index.sqlite3'
        self.db = bsv.connect(self.path)
        self.stop = threading.Event()

    def tearDown(self):
        self.db.close()

    def test_forward_resumes_at_safe_head_and_picks_up_new_blocks(self):
        provider = ChainProvider(3)
        options = runner_args(self.temp.name, direction='forward', start_height=2,
                              blocks=5, max_transactions=20)
        bsv.scan(self.db, provider, options)
        report = bsv.status(self.db)
        self.assertEqual(report['transactionsChecked'], 4)
        self.assertEqual(report['jobs'][0]['nextHeight'], 4)
        self.assertEqual(report['jobs'][0]['phase'], 'waiting-for-blocks')
        provider.head = 4
        options.start_height = None
        bsv.scan(self.db, provider, options)
        self.assertEqual(bsv.status(self.db)['transactionsChecked'], 6)
        self.assertEqual(provider.reads, [(2, 0), (3, 0), (4, 0)])

    def test_daemon_meets_in_middle_without_duplicate_transactions_and_then_tails(self):
        provider = ChainProvider(4)
        options = runner_args(self.temp.name)
        jobs = bsv.daemon_jobs(self.db, provider, options)
        bsv.daemon_pass(self.db, provider, options, jobs, self.stop)
        self.assertEqual({j['name']: j['nextHeight'] for j in bsv.status(self.db)['jobs']}, {'early': 3, 'recent': 3})
        bsv.daemon_pass(self.db, provider, options, jobs, self.stop)
        report = bsv.status(self.db)
        self.assertEqual(report['transactionsChecked'], 6)
        self.assertEqual(provider.reads, [(4, 0), (2, 0), (3, 0)])
        self.assertEqual({j['name']: j['phase'] for j in report['jobs']}, {'early': 'waiting-for-blocks', 'recent': 'complete'})
        self.assertTrue(report['runner']['rangesJoinedAt'])
        provider.head = 5
        bsv.daemon_pass(self.db, provider, options, jobs, self.stop)
        self.assertEqual(bsv.status(self.db)['transactionsChecked'], 8)
        manifest = json.loads((Path(options.export_dir) / 'manifest.json').read_text())
        index = json.loads((Path(options.export_dir) / manifest['defaultIndex']).read_text())
        ids = [row['txid'] for row in index['transactions']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(index['scan']['transactionsChecked'], 8)

    def test_one_job_failure_does_not_stop_the_other_cursor_and_recovers(self):
        provider = ChainProvider(6)
        provider.fail_height = 6
        options = runner_args(self.temp.name)
        jobs = bsv.daemon_jobs(self.db, provider, options)
        result = bsv.daemon_pass(self.db, provider, options, jobs, self.stop)
        self.assertIn('error', result['jobs'][0])
        report = bsv.status(self.db)
        self.assertEqual({j['name']: j['nextHeight'] for j in report['jobs']}, {'early': 3, 'recent': 6})
        self.assertIn('recent:', report['lastError'])
        provider.fail_height = None
        bsv.daemon_pass(self.db, provider, options, jobs, self.stop)
        self.assertEqual(bsv.status(self.db)['transactionsChecked'], 6)
        self.assertEqual(bsv.status(self.db)['lastError'], '')

    def test_partial_blocks_are_shared_and_stop_commits_only_finished_batch(self):
        provider = ChainProvider(6)
        options = runner_args(self.temp.name, direction='forward', start_height=2,
                              max_transactions=1)
        bsv.scan(self.db, provider, options)
        options.start_height = None
        options.max_transactions = 20
        original = provider.transactions
        def read_then_stop(*values):
            batch = original(*values)
            self.stop.set()
            return batch
        provider.transactions = read_then_stop
        bsv.scan(self.db, provider, options, self.stop)
        self.assertEqual(bsv.status(self.db)['transactionsChecked'], 2)
        self.assertEqual(provider.reads, [(2, 0), (2, 1)])
        self.assertEqual(self.db.execute('SELECT next_height FROM scan_jobs').fetchone()[0], 3)

    def test_direction_and_daemon_anchor_changes_do_not_reset_saved_cursors(self):
        options = runner_args(self.temp.name)
        provider = ChainProvider(6)
        jobs = bsv.daemon_jobs(self.db, provider, options)
        bsv.daemon_pass(self.db, provider, options, jobs, self.stop)
        changed = runner_args(self.temp.name, direction='backward', job='early')
        with self.assertRaisesRegex(ValueError, 'cannot change direction'):
            bsv.scan(self.db, provider, changed)
        with self.assertRaisesRegex(ValueError, 'anchor changed'):
            bsv.daemon_jobs(self.db, provider, runner_args(self.temp.name, anchor_height=3))
        self.assertEqual(self.db.execute("SELECT next_height FROM scan_jobs WHERE name='early'").fetchone()[0], 3)

    def test_changed_ancestor_invalidates_descendants_and_rewinds_both_jobs(self):
        provider = ChainProvider(6)
        options = runner_args(self.temp.name)
        jobs = bsv.daemon_jobs(self.db, provider, options)
        jobs[1].max_transactions = 1
        bsv.daemon_pass(self.db, provider, options, jobs, self.stop)
        provider.revision = 1
        bsv.scan(self.db, provider, jobs[1])
        self.assertIsNone(self.db.execute('SELECT 1 FROM blocks WHERE height=6').fetchone())
        self.assertEqual(self.db.execute("SELECT next_height FROM scan_jobs WHERE name='recent'").fetchone()[0], 6)
        self.assertEqual(self.db.execute('SELECT checked FROM blocks WHERE height=2').fetchone()[0], 1)

    def test_old_database_cursor_migrates_without_dropping_records(self):
        provider = Provider()
        bsv.scan(self.db, provider, args())
        self.db.execute('DROP TABLE scan_jobs')
        self.db.commit()
        self.db.close()
        self.db = bsv.connect(self.path)
        self.assertEqual(self.db.execute("SELECT next_height FROM scan_jobs WHERE name='history'").fetchone()[0], 100)
        self.assertEqual(bsv.status(self.db)['transactionsChecked'], 2)
        bsv.scan(self.db, provider, args(start_height=None))
        self.assertEqual(bsv.status(self.db)['transactionsChecked'], 4)

    def test_status_can_read_while_daemon_process_lock_is_held(self):
        import contextlib
        import fcntl
        import io
        bsv.scan(self.db, ChainProvider(), runner_args(self.temp.name, direction='forward', start_height=2, max_transactions=1))
        output = io.StringIO()
        with open(str(self.path) + '.lock', 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with contextlib.redirect_stdout(output):
                self.assertEqual(bsv.main(['status', '--db', str(self.path)]), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report['jobs'][0]['nextHeight'], 2)
        self.assertEqual(report['jobs'][0]['currentBlock']['transactionsChecked'], 1)
        self.assertIn('1/2 transactions checked', report['jobs'][0]['progress'])
        self.assertNotIn('skipped', report)

    def test_default_anchor_resolves_once_and_is_saved_for_restart(self):
        provider = ChainProvider(bsv.ALICE_HEIGHT + 3)
        calls = []
        blockhash = h(50000)
        def request(path):
            calls.append(path)
            if path.startswith('/tx/hash/'):
                return {'txid': bsv.ALICE_TXID, 'blockhash': blockhash}
            return {'hash': blockhash, 'height': bsv.ALICE_HEIGHT, 'txcount': 2, 'tx': [h(1), bsv.ALICE_TXID]}
        provider.request = request
        options = runner_args(self.temp.name, anchor_height=None)
        jobs = bsv.daemon_jobs(self.db, provider, options)
        self.assertEqual(jobs[1].start_height, bsv.ALICE_HEIGHT)
        self.assertEqual(jobs[1].anchor_tx, bsv.ALICE_TXID)
        restarted = bsv.daemon_jobs(self.db, provider, options)
        self.assertEqual(restarted[1].start_height, bsv.ALICE_HEIGHT)
        self.assertEqual(len(calls), 2)

    def test_daemon_once_exports_stopped_state_and_heartbeat(self):
        import contextlib
        import io
        options = runner_args(self.temp.name)
        with contextlib.redirect_stdout(io.StringIO()):
            bsv.daemon(self.db, ChainProvider(6), options, self.stop)
        report = json.loads((Path(options.export_dir) / 'scan.json').read_text())
        self.assertEqual(report['runner']['lastReportedState'], 'stopped')
        self.assertTrue(report['runner']['heartbeatAt'])
        self.assertEqual(len(report['jobs']), 2)
        self.assertEqual(report['transactionsChecked'], 4)


if __name__ == "__main__":
    unittest.main()
