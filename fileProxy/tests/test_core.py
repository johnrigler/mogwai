import tempfile
import unittest
import sqlite3
from pathlib import Path

from fileproxy.inventory import export_inventory
from fileproxy.names import canonical_filename, require_no_space_path
from fileproxy.core import (
    dated_parts, load_index, put, query_index, resolve_file, scan, sha256_file
)


class TestFileProxy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.daisy = self.base / "daisy"
        self.daisy.mkdir()
        self.config = {"version": 1, "roots": {"daisy": str(self.daisy)}}
        self.index = self.base / "catalog.sqlite3"

    def tearDown(self):
        self.tmp.cleanup()

    def test_put_and_scan_are_rebuildable(self):
        record = put(self.config, "daisy", "2026/421/1_receipt.txt", b"receipt")
        self.assertEqual(record["size"], 7)
        self.assertEqual(record["sha256"], sha256_file(self.daisy / "2026/421/1_receipt.txt"))
        output = scan(self.config, path=self.index)
        self.assertEqual(output["scanned"], 1)
        rows = load_index(self.index)["entries"]
        with sqlite3.connect(self.index) as db:
            stored = db.execute("SELECT sha256, bytes FROM files WHERE root = ? AND path = ?",
                                ("daisy", "2026/421/1_receipt.txt")).fetchone()
        self.assertIsInstance(stored[0], bytes)
        self.assertEqual(len(stored[0]), 32)
        self.assertEqual(stored[0].hex(), record["sha256"])
        self.assertEqual(stored[1], 7)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "daisy:2026/421/1_receipt.txt")
        self.assertEqual(rows[0]["isoWeek"], 42)
        self.assertEqual(rows[0]["isoYear"], 2026)
        self.assertEqual(rows[0]["isoDay"], 1)
        self.assertEqual(query_index(load_index(self.index), text="RECEIPT")[0]["sha256"], record["sha256"])

    def test_hidden_and_symlink_exclusions(self):
        (self.daisy / ".private").write_text("secret")
        (self.daisy / ".git").mkdir()
        (self.daisy / ".git" / "config").write_text("secret")
        (self.daisy / "public.txt").write_text("visible")
        scan(self.config, path=self.index)
        self.assertEqual([e["path"] for e in load_index(self.index)["entries"]], ["public.txt"])

    def test_escape_and_overwrite_protections(self):
        for value in ("../escape", "/etc/passwd", "foo\\bar"):
            with self.assertRaises(ValueError):
                resolve_file(self.config, "daisy", value)
        put(self.config, "daisy", "note.txt", b"one")
        with self.assertRaises(FileExistsError):
            put(self.config, "daisy", "note.txt", b"two")
        self.assertEqual((self.daisy / "note.txt").read_bytes(), b"one")

    def test_canonical_whitespace_free_filename(self):
        self.assertEqual(canonical_filename("Business Registration Form 211.pdf"),
                         "Business-Registration-Form-211.pdf")
        self.assertEqual(canonical_filename("López Filing 01.PDF"), "Lopez-Filing-01.PDF")
        self.assertEqual(canonical_filename("Packet\tFinal.pdf"), "Packet-Final.pdf")
        self.assertNotIn(" ", canonical_filename("A" * 140 + " Legal.pdf"))
        self.assertTrue(canonical_filename("A" * 140 + " Legal.pdf").endswith(".pdf"))

    def test_writes_reject_whitespace_but_old_files_are_readable(self):
        for name in ("2026/42/1/Receipt Final.pdf", "2026/42/1/line\nbreak.pdf",
                     "2026/42/1/tab\tname.pdf"):
            with self.assertRaises(ValueError):
                put(self.config, "daisy", name, b"PDF")
        legacy = self.daisy / "Old Name.pdf"
        legacy.write_bytes(b"old")
        self.assertEqual(resolve_file(self.config, "daisy", "Old Name.pdf").read_bytes(), b"old")

    def test_sb_shell_inventory_at_parent(self):
        shell = self.daisy / "myshell"
        shell.mkdir()
        (shell / "1_01.html").write_text("one")
        (shell / ".private").write_text("skip")
        result = export_inventory(self.config, "daisy", "myshell", "files.txt")
        self.assertEqual(result["entries"], 1)
        self.assertEqual((self.daisy / "files.txt").read_text(), "myshell/1_01.html\n")

    def test_iso_fields(self):
        self.assertEqual(dated_parts("2026/421/r.pdf"), {"isoYear": 2026, "isoWeek": 42, "isoDay": 1, "dateConvention": "DAISY:%G/%V%u"})
        self.assertEqual(dated_parts("inbox/2026/427/r.pdf")["isoDay"], 7)
        self.assertEqual(dated_parts("inbox/2026/420/r.pdf"), {})
        self.assertEqual(dated_parts("2026/42/1/r.pdf"), {})
        self.assertEqual(dated_parts("certledger/r.pdf"), {})


if __name__ == "__main__":
    unittest.main()
