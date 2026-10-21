"""Exercise the imported components against one new annual archive."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FP = ROOT / "fileProxy/fp.py"
PHP = os.environ.get("SB_PHP", "php")


class ConsolidationTests(unittest.TestCase):
    def test_sourced_wrapper_locates_checkout_and_respects_override(self):
        with tempfile.TemporaryDirectory(prefix="mogwai tools ") as directory:
            temporary = Path(directory)
            # Copy the whole small CLI, so the test uses a non-default location.
            component = temporary / "other checkout" / "fileProxy"
            shutil.copytree(ROOT / "fileProxy", component,
                            ignore=shutil.ignore_patterns("__pycache__"))
            config = temporary / "roots.json"
            config.write_text(json.dumps({"roots": {"example": directory}}))
            env = dict(os.environ)
            env.pop("FILEPROXY_HOME", None)
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-c",
                 'source "$1"; fp --config "$2" roots',
                 "bash", str(component / "shell/fp.sh"), str(config)],
                cwd=temporary, env=env, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("example\t" + directory, result.stdout)
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-c",
                 'source "$1"; fp --config "$2" roots',
                 "bash", str(ROOT / "fileProxy/shell/fp.sh"), str(config)],
                cwd=temporary, env={**env, "FILEPROXY_HOME": str(component)},
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("example\t" + directory, result.stdout)

    def test_new_2027_archive_is_indexed_without_writing_tools_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            self.make_archive(temporary)
            archive = temporary / "daisy_2027"
            self.assertTrue((archive / "011").is_dir())
            self.assertFalse((archive / "531").exists())
            record = archive / "011/record.txt"
            record.write_text("Synthetic integration fixture.\n")
            config = temporary / "roots.json"
            self.fp(config, "add-root", "personal2027", str(archive))
            self.fp(config, "scan", "personal2027")
            with sqlite3.connect(archive / "catalog.sqlite3") as database:
                row = database.execute(
                    "SELECT root, sha256 FROM files WHERE path='011/record.txt'"
                ).fetchone()
            self.assertEqual(row, ("personal2027", hashlib.sha256(record.read_bytes()).digest()))
            self.assertIn("011/record.txt", (archive / "files.txt").read_text())
            self.assertFalse((ROOT / "fileProxy/catalog.sqlite3").exists())

    @unittest.skipUnless(shutil.which(PHP), "PHP is needed for the cross-language catalog check")
    def test_php_and_fileproxy_share_the_same_archive_database(self):
        capability = subprocess.run(
            [PHP, "-r", 'exit(class_exists("SQLite3") ? 0 : 1);'],
            capture_output=True, timeout=10,
        )
        if capability.returncode:
            self.skipTest("PHP SQLite3 is not installed")
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            self.make_archive(temporary)
            archive = temporary / "daisy_2027"
            record = archive / "011/record.txt"
            record.write_text("Synthetic initial record.\n")
            config = temporary / "roots.json"
            self.fp(config, "add-root", "personal2027", str(archive))
            self.fp(config, "scan", "personal2027")
            record.write_text("Synthetic PHP-side edit.\n")
            source = '''$GLOBALS["sb_root"] = $argv[1];
require $argv[2];
sb_catalog_scan($argv[1] . "/011");
sb_save_document("011/record.txt", "Integration record", hash_file("sha256", $argv[1] . "/011/record.txt", true));
'''
            result = subprocess.run(
                [PHP, "-r", source, str(archive), str(ROOT / "sbshell/cruff/catalog.php")],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            found = self.fp(config, "find", "record.txt", "--root", "personal2027")
            self.assertIn(hashlib.sha256(record.read_bytes()).hexdigest(), found.stdout)
            self.fp(config, "scan", "personal2027")
            with sqlite3.connect(archive / "catalog.sqlite3") as database:
                self.assertEqual(database.execute("SELECT name FROM sb_documents").fetchone(),
                                 ("Integration record",))
                self.assertEqual(database.execute(
                    "SELECT root FROM files WHERE path='011/record.txt'"
                ).fetchone(), ("personal2027",))

    def make_archive(self, parent):
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-c",
             'source "$1"; m.daisy.new 2027 "$2"', "bash",
             str(ROOT / "templates/daisy-year/m.daisy.new"), str(parent)],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def fp(self, config, *arguments):
        result = subprocess.run(
            [sys.executable, str(FP), "--config", str(config), *arguments],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result
