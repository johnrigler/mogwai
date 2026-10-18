import datetime
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "templates/daisy-year/m.daisy.new-02244558-6686"


class DaisyYearTest(unittest.TestCase):
    def run_function(self, arguments, parent, source=SNAPSHOT, command=None):
        return subprocess.run(
            ["bash", "--noprofile", "--norc", "-c",
             command or 'source "$1"; shift; m.daisy.new "$@"',
             "bash", str(source), *arguments],
            cwd=parent,
            env={"PATH": os.environ["PATH"], "HOME": str(parent)},
            text=True, capture_output=True, timeout=15,
        )

    def test_coordinates_match_iso_calendar(self):
        for year in (2000, 2004, 2026, 2027, 2200):
            with self.subTest(year=year), tempfile.TemporaryDirectory() as temporary:
                parent = Path(temporary)
                result = self.run_function([str(year), str(parent)], parent)
                self.assertEqual(result.returncode, 0, result.stderr)
                archive = parent / f"daisy_{year}"
                expected = set()
                current = datetime.date(year - 1, 12, 20)
                stop = datetime.date(year + 1, 1, 10)
                while current < stop:
                    iso_year, week, day = current.isocalendar()
                    if iso_year == year:
                        expected.add(f"{week:02d}{day}")
                    current += datetime.timedelta(days=1)
                actual = {p.name for p in archive.iterdir() if p.is_dir()}
                self.assertEqual(actual, expected)
                for coordinate in expected:
                    self.assertEqual(
                        list((archive / coordinate).iterdir()),
                        [archive / coordinate / ".gitkeep"],
                    )
                readme = (archive / "README.md").read_text()
                self.assertIn(f"ISO week-year **{year}**", readme)
                self.assertNotIn("@DAISY_YEAR@", readme)
                self.assertIn("crypto-python", readme)
                self.assertIn("https://github.com/johnrigler/sbstats", readme)
                self.assertIn("https://github.com/johnrigler/fileProxy", readme)
                self.assertFalse((archive / str(year)).exists())

    def test_existing_destination_refused_even_in_conditional(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            archive = parent / "daisy_2027"
            archive.mkdir()
            note = archive / "keep"
            note.write_bytes(b"existing bytes")
            result = self.run_function(
                ["2027", str(parent)], parent,
                command='source "$1"; shift; if m.daisy.new "$@"; then exit 99; fi',
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(archive.iterdir()), [note])
            self.assertEqual(note.read_bytes(), b"existing bytes")

    def test_existing_file_and_dangling_symlink_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            target = parent / "daisy_2027"
            target.write_bytes(b"retain")
            result = self.run_function(["2027", str(parent)], parent)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(target.read_bytes(), b"retain")
            target.unlink()
            missing = parent / "missing"
            target.symlink_to(missing, target_is_directory=True)
            result = self.run_function(["2027", str(parent)], parent)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(target.is_symlink())
            self.assertFalse(missing.exists())

    def test_invalid_arguments_write_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for args in ([], ["0000"], ["20x7"], ["2027/011"],
                         ["2027", str(parent), "extra"]):
                with self.subTest(args=args):
                    result = self.run_function(args, parent)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual(list(parent.iterdir()), [])

    def test_portable_snapshot_round_trip_and_caller_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            copied = parent / "copied-function"
            shutil.copyfile(SNAPSHOT, copied)
            original = copied.read_bytes()
            result = self.run_function(
                [], parent, source=copied,
                command='source "$1"; declare -f m.daisy.new',
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.encode(), original)
            prefix = int(hashlib.sha256(original).hexdigest()[:4], 16)
            shoctal = "02" + "".join(str(int(digit) + 2)
                                     for digit in format(prefix, "06o"))
            self.assertEqual(SNAPSHOT.name,
                             f"m.daisy.new-{shoctal}-{len(original)}")
            result = self.run_function(
                ["2027"], parent, source=copied,
                command='source "$1"; shift; before=$PWD; m.daisy.new "$@" && test "$PWD" = "$before"',
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((parent / "daisy_2027/011").is_dir())


if __name__ == "__main__":
    unittest.main()
