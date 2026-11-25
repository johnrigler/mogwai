import os
import pathlib
import subprocess
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "publish-files.sh"


class PublishFilesTests(unittest.TestCase):
    def test_one_failed_currency_does_not_block_others(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            home = root / "home"
            home.mkdir()
            tx = root / "archive" / "transactions"
            for name in ("digibyte", "bsv", "ravencoin"):
                (tx / name).mkdir(parents=True)
            previous = "a" * 64 + ".json\n"
            (tx / "digibyte" / ".files").write_text(previous)
            filename = "b" * 64 + ".json"
            (tx / "bsv" / filename).write_text("{}")
            (tx / "ravencoin" / filename).write_text("{}")
            # Inject mktemp failure even when tests run with root privileges.
            bin_dir = root / "bin"
            bin_dir.mkdir()
            stub = bin_dir / "mktemp"
            stub.write_text('#!/bin/bash\nfor a in "$@"; do\n'
                            '  case "$a" in digibyte/*|ravencoin/*) echo "mock write failure" >&2; exit 1;; esac\n'
                            'done\nexec /usr/bin/mktemp "$@"\n')
            stub.chmod(0o755)
            env = dict(os.environ, HOME=str(home), XDG_STATE_HOME=str(root / "state"),
                       PATH=str(bin_dir) + ":" + os.environ["PATH"])
            result = subprocess.run(["bash", str(SCRIPT), str(root / "archive")],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual((tx / "digibyte" / ".files").read_text(), previous)
            self.assertEqual((tx / "bsv" / ".files").read_text(), filename + "\n")
            self.assertFalse((tx / "ravencoin" / ".files").exists())
            self.assertEqual((tx / ".files").read_text(), "bsv\ndigibyte\nravencoin\n")
            self.assertIn("keeping previous", result.stderr)
            self.assertIn("no readable .files", result.stderr)
            self.assertIn("Published inventories for 1 of 3", result.stdout)
            # A subsequent healthy run refreshes all directories.
            env["PATH"] = os.environ["PATH"]
            healthy = subprocess.run(["bash", str(SCRIPT), str(root / "archive")],
                                     env=env, capture_output=True, text=True)
            self.assertEqual(healthy.returncode, 0, healthy.stderr)
            self.assertEqual((tx / "ravencoin" / ".files").read_text(), filename + "\n")


if __name__ == "__main__":
    unittest.main()
