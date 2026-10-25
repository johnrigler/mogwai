import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from fileproxy import server, cli


class CompatibilityTests(unittest.TestCase):
    def test_handler_keeps_legacy_endpoints(self):
        handler = server.make_handler("/tmp/fileproxy-test-unconfigured.json", "/tmp/fileproxy-index-unconfigured.json")
        self.assertTrue(issubclass(handler, server.chisel.Handler))
        self.assertTrue(callable(handler.do_GET))
        self.assertTrue(callable(handler.do_POST))
        self.assertTrue(callable(server.chisel.Handler.do_GET))
        self.assertTrue(callable(server.chisel.Handler.do_POST))


    def test_serve_cli_passes_explicit_arguments(self):
        with patch.object(server, "main", return_value=0) as serve:
            self.assertEqual(cli.main([
                "serve", "--host", "127.0.0.1", "--port", "47799",
                "--activity-log", "~/fileproxy-activity.jsonl"
            ]), 0)
        serve.assert_called_once_with(
            str(cli.DEFAULT_CONFIG), cli.DEFAULT_INDEX,
            local=False, host="127.0.0.1", port=47799,
            activity_log="~/fileproxy-activity.jsonl"
        )

    def test_server_receives_explicit_listener_and_log_settings(self):
        with TemporaryDirectory() as directory:
            logfile = Path(directory) / "nested" / "activity.jsonl"
            original_handler = server.chisel.Handler
            try:
                with patch.object(server.chisel, "main") as run:
                    server.main(
                        "/tmp/fileproxy-test-unconfigured.json",
                        "/tmp/fileproxy-index-unconfigured.json",
                        host="127.0.0.1", port=47799,
                        activity_log=str(logfile)
                    )
                run.assert_called_once_with(host="127.0.0.1", port=47799)
                self.assertEqual(server.chisel.Handler.activity_log_path, str(logfile))
                self.assertTrue(logfile.parent.is_dir())
            finally:
                server.chisel.Handler = original_handler

    def test_invalid_port_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "--port"):
            server.main(host="127.0.0.1", port=65536)


    def test_optional_sqlite_absence_preserves_json_reindex_success(self):
        with patch.object(server.chisel, "read_or_build_tx_index",
                          return_value={"transactions": [{"txid": "a" * 64}], "ok": True}):
            with patch.object(server.chisel, "load_chisel_indexer", return_value=None):
                result = server.chisel.refresh_all_indexes()
        self.assertTrue(result["ok"])
        self.assertTrue(result["partial"])
        self.assertEqual(result["json"]["records"], 1)
        self.assertFalse(result["sqlite"]["available"])

    def test_json_reindex_failure_is_still_reported(self):
        with patch.object(server.chisel, "read_or_build_tx_index",
                          side_effect=OSError("index path unwritable")):
            with patch.object(server.chisel, "load_chisel_indexer", return_value=None):
                result = server.chisel.refresh_all_indexes()
        self.assertFalse(result["ok"])
        self.assertFalse(result.get("partial", False))


if __name__ == "__main__":
    unittest.main()
