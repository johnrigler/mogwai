import sqlite3
import tempfile
import unittest
from pathlib import Path

from fileproxy.url_catalog import lookup, normalize_youtube_url, resolve


class URLCatalogTests(unittest.TestCase):
    def test_variants_resolve_to_one_key(self):
        video_id = "ABC123xyz00"
        urls = (
            "https://www.youtube.com/watch?v=" + video_id + "&t=9",
            "https://youtu.be/" + video_id,
            "https://youtube.com/shorts/" + video_id,
            "https://m.youtube.com/watch?v=" + video_id,
            "https://www.youtube.com/embed/" + video_id,
            "https://youtube.com/live/" + video_id,
        )
        self.assertEqual({normalize_youtube_url(url)["key"] for url in urls},
                         {"youtube:" + video_id})

    def test_single_record_preserves_first_source_url(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "urls.sqlite3"
            original = "https://youtu.be/ABC123xyz00?t=40"
            first = resolve(db, original)
            second = resolve(db, "https://youtube.com/watch?v=ABC123xyz00")
            self.assertTrue(first["created"])
            self.assertFalse(second["created"])
            self.assertEqual(first["resource"], second["resource"])
            self.assertEqual(second["resource"]["sourceUrl"], original)
            self.assertEqual(lookup(db, original), first["resource"])
            with sqlite3.connect(db) as connection:
                self.assertEqual(connection.execute(
                    "SELECT count(*) FROM url_resources").fetchone()[0], 1)

    def test_lookup_does_not_create_database(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "urls.sqlite3"
            self.assertIsNone(lookup(db, "https://youtu.be/ABC123xyz00"))
            self.assertFalse(db.exists())

    def test_reject_untrusted_hosts_and_malformed_ids(self):
        for url in (
            "https://youtube.com.evil.example/watch?v=ABC123xyz00",
            "http://youtu.be/ABC123xyz00",
            "https://youtube.com/watch?v=short",
            "https://youtube.com/watch?v=ABC123xyz00&v=DEF123xyz00",
            "https://youtube.com/playlist?list=ABC123xyz00",
            "https://user:pass@youtube.com/watch?v=ABC123xyz00",
            "https://youtube.com/shorts/ABC123xyz00/extra",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_youtube_url(url)


if __name__ == "__main__":
    unittest.main()
