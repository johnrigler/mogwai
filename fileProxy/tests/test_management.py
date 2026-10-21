import hashlib
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from fileproxy.core import load_catalog, scan
from fileproxy.management import list_folders, make_directory, restore_file, transfer_files, trash_file


class ManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {"version": 1, "roots": {"work": str(self.root)}}
        self.path = self.root / "case" / "11703"
        self.path.parent.mkdir()
        self.path.write_text("temporary shell output\n")
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        scan(self.config)

    def test_delete_and_undo_keep_bytes_and_refresh_catalog_and_inventory(self):
        result = trash_file(self.config, "work", "case/11703", self.digest)
        self.assertFalse(self.path.exists())
        self.assertEqual(load_catalog(self.config)["entries"], [])
        self.assertNotIn("11703", (self.root / "files.txt").read_text())
        self.assertNotIn(".fileproxy-trash", (self.root / "files.txt").read_text())
        restored = restore_file(self.config, "work", result["trashId"])
        self.assertEqual(restored["sha256"], self.digest)
        self.assertEqual(self.path.read_text(), "temporary shell output\n")
        self.assertEqual(load_catalog(self.config)["entries"][0]["path"], "case/11703")
        self.assertIn("case/11703", (self.root / "files.txt").read_text())

    def test_changed_or_unverified_files_are_not_removed(self):
        with self.assertRaises(ValueError):
            trash_file(self.config, "work", "case/11703", None)
        self.path.write_text("changed since preview")
        with self.assertRaises(FileExistsError):
            trash_file(self.config, "work", "case/11703", self.digest)
        self.assertEqual(self.path.read_text(), "changed since preview")

    def test_restore_never_overwrites_a_new_file(self):
        result = trash_file(self.config, "work", "case/11703", self.digest)
        self.path.write_text("replacement")
        with self.assertRaises(FileExistsError):
            restore_file(self.config, "work", result["trashId"])
        self.assertEqual(self.path.read_text(), "replacement")
        self.assertTrue((self.root / ".fileproxy-trash" / result["trashId"] / "content").exists())

    def test_scan_failure_rolls_back_file_move(self):
        with patch("fileproxy.management.scan", side_effect=ValueError("catalog unavailable")):
            with self.assertRaisesRegex(ValueError, "catalog unavailable"):
                trash_file(self.config, "work", "case/11703", self.digest)
        self.assertEqual(self.path.read_text(), "temporary shell output\n")

    def test_hidden_generated_symlink_and_escape_targets_are_rejected(self):
        (self.root / ".private").write_text("keep")
        (self.root / "link").symlink_to(self.path)
        for name in (".private", "catalog.sqlite3", "files.txt", "link", "../outside", "/etc/passwd"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                trash_file(self.config, "work", name, self.digest)
        self.assertTrue(self.path.exists())

    def test_redirected_trash_directory_is_rejected(self):
        other = self.root / "other"
        other.mkdir()
        (self.root / ".fileproxy-trash").symlink_to(other, target_is_directory=True)
        with self.assertRaises(ValueError):
            trash_file(self.config, "work", "case/11703", self.digest)
        self.assertTrue(self.path.exists())

    def selection(self, *paths):
        return [{"path": path, "sha256": hashlib.sha256((self.root / path).read_bytes()).hexdigest()}
                for path in paths]

    def test_new_empty_folders_are_browsable_without_indexing_fake_files(self):
        make_directory(self.config, "work", "case/response-1")
        self.assertIn("case/response-1", list_folders(self.config, "work")["directories"])
        self.assertEqual([row["path"] for row in load_catalog(self.config)["entries"]], ["case/11703"])

    def test_ordered_copies_preserve_source_bytes_and_append_after_existing_numbers(self):
        destination = self.root / "response-1"
        destination.mkdir()
        (destination / "003-existing.pdf").write_bytes(b"keep")
        (self.path.parent / "02.pdf").write_bytes(b"second")
        selected = self.selection("case/02.pdf", "case/11703")
        result = transfer_files(self.config, "work", "response-1", selected, numbered=True)
        self.assertEqual([row["path"] for row in result["files"]],
                         ["response-1/004-02.pdf", "response-1/005-11703"])
        self.assertEqual((destination / "004-02.pdf").read_bytes(), b"second")
        self.assertEqual((destination / "005-11703").read_bytes(), self.path.read_bytes())
        self.assertEqual((destination / "003-existing.pdf").read_bytes(), b"keep")
        self.assertTrue((self.path.parent / "02.pdf").exists())
        self.assertIn("response-1/005-11703", (self.root / "files.txt").read_text())

    def test_move_refreshes_catalog_and_removes_only_verified_sources(self):
        (self.root / "response-1").mkdir()
        self.path.chmod(0o755)
        transfer_files(self.config, "work", "response-1", self.selection("case/11703"), operation="move")
        self.assertFalse(self.path.exists())
        self.assertEqual((self.root / "response-1/11703").read_text(), "temporary shell output\n")
        self.assertEqual((self.root / "response-1/11703").stat().st_mode & 0o777, 0o755)
        self.assertEqual([row["path"] for row in load_catalog(self.config)["entries"]], ["response-1/11703"])
        self.assertFalse(list(self.root.rglob(".fileproxy-moving-*")))

    def test_collisions_and_changed_sources_abort_the_complete_selection(self):
        destination = self.root / "response-1"
        destination.mkdir()
        (self.path.parent / "02.pdf").write_bytes(b"second")
        (destination / "02.pdf").write_bytes(b"keep")
        selected = self.selection("case/11703", "case/02.pdf")
        with self.assertRaises(FileExistsError):
            transfer_files(self.config, "work", "response-1", selected, operation="move")
        self.assertTrue(self.path.exists())
        self.assertFalse((destination / "11703").exists())
        self.assertEqual((destination / "02.pdf").read_bytes(), b"keep")
        selected[0]["sha256"] = "0" * 64
        with self.assertRaises(FileExistsError):
            transfer_files(self.config, "work", "response-1", selected[:1])
        self.assertFalse((destination / "11703").exists())

    def test_failed_scan_rolls_back_all_moves_and_copies(self):
        destination = self.root / "response-1"
        destination.mkdir()
        selected = self.selection("case/11703")
        for operation in ("copy", "move"):
            with self.subTest(operation=operation), patch("fileproxy.management.scan", side_effect=ValueError("unavailable")):
                with self.assertRaisesRegex(ValueError, "unavailable"):
                    transfer_files(self.config, "work", "response-1", selected, operation=operation)
            self.assertEqual(self.path.read_text(), "temporary shell output\n")
            self.assertEqual(list(destination.iterdir()), [])
            self.assertFalse(list(self.root.rglob(".fileproxy-moving-*")))

    def test_folder_controls_reject_symlinks_hidden_paths_and_escaping_destinations(self):
        (self.root / "link").symlink_to(self.path.parent, target_is_directory=True)
        (self.root / ".hidden").mkdir()
        folders = list_folders(self.config, "work")["directories"]
        self.assertNotIn("link", folders)
        self.assertNotIn(".hidden", folders)
        for path in ("link/new", "../escape", ".hidden/new", "spaces here"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                make_directory(self.config, "work", path)
        for destination in ("link", "../escape", ".hidden"):
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                transfer_files(self.config, "work", destination, self.selection("case/11703"))


if __name__ == "__main__":
    unittest.main()
