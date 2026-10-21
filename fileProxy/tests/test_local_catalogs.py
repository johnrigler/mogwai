"""Archive-local scans work offline and are visible to an already-running API."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import HTTPServer
from urllib.request import urlopen

from fileproxy.core import load_catalog, load_index, scan, write_config
from fileproxy.server import make_handler


class LocalCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.archive = self.base / "Daisy_2026"
        self.archive.mkdir()
        self.other = self.base / "Daisy_2025"
        self.other.mkdir()
        self.config = {"version": 1, "roots": {
            "daisy2026": str(self.archive), "daisy2025": str(self.other)}}
        self.config_path = self.base / "config.json"
        write_config(self.config, self.config_path)
        self.project = Path(__file__).resolve().parents[1]

    def tearDown(self):
        self.temp.cleanup()

    def command(self, *args):
        env = dict(os.environ)
        env.pop("FILEPROXY_INDEX", None)
        return subprocess.run([sys.executable, str(self.project / "fp.py"),
                               "--config", str(self.config_path), *args],
                              cwd=self.base, env=env, check=True,
                              text=True, capture_output=True).stdout

    def test_offline_cli_writes_database_and_matching_inventory_in_each_root(self):
        (self.archive / "426").mkdir()
        (self.archive / "426" / "receipt.txt").write_text("receipt")
        (self.archive / "empty").mkdir()
        (self.other / "old.txt").write_text("old")
        result = json.loads(self.command("scan"))
        self.assertEqual(result["scanned"], 2)
        self.assertFalse((self.base / "catalog.sqlite3").exists())
        with sqlite3.connect(self.archive / "catalog.sqlite3") as db:
            self.assertEqual(db.execute("SELECT path, length(sha256) FROM files").fetchall(),
                             [("426/receipt.txt", 32)])
        self.assertEqual((self.archive / "files.txt").read_text(),
                         "426\n426/receipt.txt\nempty\n")
        self.assertEqual((self.other / "files.txt").read_text(), "old.txt\n")
        self.assertIn("daisy2026:426/receipt.txt", self.command("find", "receipt"))
        self.assertNotIn("old.txt", self.command("ls", "daisy2026"))

    def test_rescan_tracks_edits_deletions_and_keeps_other_archive_unchanged(self):
        note = self.archive / "note.txt"
        note.write_text("one")
        (self.other / "old.txt").write_text("old")
        scan(self.config)
        previous = load_index(self.archive / "catalog.sqlite3")["entries"][0]["sha256"]
        other_bytes = (self.other / "catalog.sqlite3").read_bytes()
        note.write_text("two")
        scan(self.config, ["daisy2026"])
        self.assertNotEqual(previous, load_index(self.archive / "catalog.sqlite3")["entries"][0]["sha256"])
        note.unlink()
        scan(self.config, ["daisy2026"])
        self.assertEqual(load_index(self.archive / "catalog.sqlite3")["entries"], [])
        self.assertEqual((self.archive / "files.txt").read_text(), "")
        self.assertEqual((self.other / "catalog.sqlite3").read_bytes(), other_bytes)

    def test_preserves_alp_loader_and_excludes_generated_outputs_and_git(self):
        manifest = self.archive / ".files.txt"
        manifest.write_text("source\td.task-12345.1\n")
        (self.archive / "d.task-12345.1").write_text("d.task () { :; }\n")
        (self.archive / ".git").mkdir()
        (self.archive / ".git" / "config").write_text("private")
        scan(self.config)
        scan(self.config)
        self.assertEqual(manifest.read_text(), "source\td.task-12345.1\n")
        self.assertEqual((self.archive / "files.txt").read_text(), "d.task-12345.1\n")
        self.assertEqual([r["path"] for r in load_index(self.archive / "catalog.sqlite3")["entries"]],
                         ["d.task-12345.1"])

    def test_explicit_shared_index_is_still_available(self):
        (self.archive / "new.txt").write_text("new")
        (self.other / "old.txt").write_text("old")
        shared = self.base / "shared.sqlite3"
        scan(self.config, path=shared)
        scan(self.config, ["daisy2026"], shared)
        self.assertEqual(len(load_index(shared)["entries"]), 2)
        self.assertFalse((self.archive / "catalog.sqlite3").exists())
        self.assertEqual((self.archive / "files.txt").read_text(), "new.txt\n")

    def test_scanning_one_archive_does_not_open_another_archives_database(self):
        (self.archive / "note.txt").write_text("independent")
        (self.other / "catalog.sqlite3").write_bytes(b"not a usable database")
        result = scan(self.config, ["daisy2026"])
        self.assertEqual(result["total"], 1)
        self.assertEqual(load_catalog(self.config, names=["daisy2026"])["entries"][0]["path"],
                         "note.txt")

    def test_archive_can_be_reopened_with_a_different_local_alias(self):
        (self.archive / "note.txt").write_text("portable")
        scan(self.config, ["daisy2026"])
        moved = {"version": 1, "roots": {"work": str(self.archive)}}
        self.assertEqual(load_catalog(moved)["entries"][0]["id"], "work:note.txt")
        scan(moved)
        self.assertEqual(len(load_index(self.archive / "catalog.sqlite3")["entries"]), 1)

    def test_output_symlinks_are_rejected_before_catalog_changes(self):
        outside = self.base / "outside.txt"
        outside.write_text("keep")
        (self.archive / "files.txt").symlink_to(outside)
        with self.assertRaises(ValueError):
            scan(self.config, ["daisy2026"])
        self.assertEqual(outside.read_text(), "keep")
        self.assertFalse((self.archive / "catalog.sqlite3").exists())
        (self.archive / "files.txt").unlink()
        (self.archive / "catalog.sqlite3").symlink_to(outside)
        with self.assertRaises(ValueError):
            scan(self.config, ["daisy2026"])
        self.assertEqual(outside.read_text(), "keep")

    def test_running_http_service_sees_cli_scan_without_restart(self):
        handler = make_handler(self.config_path, None)
        server = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host = "http://127.0.0.1:" + str(server.server_port)
        def query():
            with urlopen(host + "/v1/index?root=daisy2026") as response:
                return json.load(response)["entries"]
        try:
            self.assertEqual(query(), [])
            (self.archive / "note.txt").write_text("one")
            self.command("scan", "daisy2026")
            first = query()
            self.assertEqual(first[0]["path"], "note.txt")
            (self.archive / "note.txt").write_text("two")
            self.command("scan", "daisy2026")
            self.assertNotEqual(first[0]["sha256"], query()[0]["sha256"])
            with urlopen(host + "/v1/file?root=daisy2026&path=files.txt") as response:
                self.assertEqual(response.read(), b"note.txt\n")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
