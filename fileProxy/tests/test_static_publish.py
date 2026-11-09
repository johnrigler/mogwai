"""Static artifacts remain readable when the HTTP FileProxy process is stopped."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from fileproxy.static_publish import publish, verify, main


class StaticPublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "webroot"
        self.source = Path(self.temp.name) / "home.svg"
        self.raw = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>'
        self.source.write_bytes(self.raw)

    def test_publish_produces_independent_static_files_and_valid_hashes(self):
        entry = publish(self.root, "polygon/137/icon/home", self.source, "image/svg+xml")
        self.assertEqual(entry["sha256"], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(entry["provenance"], "unverified")
        self.assertEqual((self.root / entry["path"]).read_bytes(), self.raw)
        doc = json.loads((self.root / "manifest.json").read_text())
        self.assertEqual(doc["format"], "chisel-static-artifacts-v1")
        self.assertEqual(doc["artifacts"]["polygon/137/icon/home"], entry)
        self.assertEqual(verify(self.root), 1)
        self.assertEqual(publish(self.root, "polygon/137/icon/home", self.source, "image/svg+xml"), entry)

    def test_no_implicit_replacement_or_traversal(self):
        publish(self.root, "polygon/137/icon/home", self.source, "image/svg+xml")
        self.source.write_text("<svg/>")
        with self.assertRaises(FileExistsError):
            publish(self.root, "polygon/137/icon/home", self.source, "image/svg+xml")
        old = json.loads((self.root / "manifest.json").read_text())
        self.assertEqual(len(old["artifacts"]), 1)
        with self.assertRaises(ValueError):
            publish(self.root, "../secrets", self.source, "image/svg+xml")
        with self.assertRaises(ValueError):
            publish(self.root, "polygon/137/icon/wallet", self.source, "text/html")
        updated = publish(self.root, "polygon/137/icon/home", self.source, "image/svg+xml", replace=True)
        self.assertEqual(verify(self.root), 1)
        self.assertNotEqual(updated["sha256"], old["artifacts"]["polygon/137/icon/home"]["sha256"])

    def test_tampering_and_noncanonical_paths_rejected(self):
        entry = publish(self.root, "polygon/137/icon/home", self.source, "image/svg+xml")
        (self.root / entry["path"]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "do not match"):
            verify(self.root)
        (self.root / entry["path"]).write_bytes(self.raw)
        manifest = json.loads((self.root / "manifest.json").read_text())
        manifest["artifacts"]["polygon/137/icon/home"]["path"] = "../outside"
        (self.root / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "Non-canonical"):
            verify(self.root)

    def test_publication_is_not_claimed_as_polygon_verification(self):
        entry = publish(self.root, "polygon/137/icon/home", self.source, "image/svg+xml",
                        hint="Polygon contract 0xabc, supplied by operator")
        self.assertEqual(entry["provenance"], "unverified")
        self.assertIn("sourceHint", entry)


if __name__ == "__main__":
    unittest.main()
