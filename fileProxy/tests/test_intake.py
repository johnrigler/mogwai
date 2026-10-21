import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from fileproxy.core import load_index
from fileproxy.intake import (
    classify, extract_urls, intake, proposed_records, url_details, canonical_filename,
)


LAGUNA = (
    "https://www.lagunapueblo-nsn.gov/wp-content/uploads/2021/02/"
    "Form-211-Business-Registration-Application-Rev_2_20_19.pdf"
)


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cert = self.root / "cert"
        self.daisy = self.root / "daisy"
        self.cert.mkdir()
        self.daisy.mkdir()
        self.config = {"version": 1, "roots": {"certledger": str(self.cert), "daisy": str(self.daisy)}}
        self.index = self.root / "index.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def fake_get(self, url):
        self.assertEqual(url, LAGUNA)
        return b"%PDF-1.4\nfixture\n", url, "application/pdf"

    def test_laguna_business_form_routes_to_certledger(self):
        p = proposed_records("Look at this form: " + LAGUNA)
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["root"], "certledger")
        self.assertEqual(p[0]["category"], "regulatory/business-registration")

    def test_import_preserves_bytes_and_provenance(self):
        result = intake(self.config, LAGUNA, note="Example of regulatory filing",
                        index_path=self.index, downloader=self.fake_get)
        record = result["items"][0]
        self.assertEqual(record["root"], "certledger")
        self.assertEqual((self.cert / record["path"]).read_bytes(), b"%PDF-1.4\nfixture\n")
        metadata = json.loads((self.cert / record["metadataPath"]).read_text())
        self.assertEqual(metadata["sourceUrl"], LAGUNA)
        self.assertEqual(metadata["reviewStatus"], "unreviewed")
        self.assertEqual(metadata["category"], "regulatory/business-registration")
        self.assertEqual(metadata["sha256"], record["sha256"])
        self.assertEqual(len(load_index(self.index)["entries"]), 2)

    def test_duplicate_does_not_overwrite(self):
        first = intake(self.config, LAGUNA, index_path=self.index, downloader=self.fake_get)
        second = intake(self.config, LAGUNA, index_path=self.index, downloader=self.fake_get)
        self.assertFalse(first["items"][0]["duplicate"])
        self.assertTrue(second["items"][0]["duplicate"])

    def test_html_error_page_is_not_saved_as_pdf(self):
        with self.assertRaises(ValueError):
            intake(self.config, LAGUNA, index_path=self.index,
                   downloader=lambda url: (b"<html>blocked</html>", url, "text/html"))
        self.assertFalse(list(self.cert.rglob("*.pdf")))

    def test_explicit_annual_daisy_root_uses_yearless_wwd_coordinate(self):
        from unittest.mock import patch
        annual_root = self.root / "daisy_2026"
        annual_root.mkdir()
        conf = {"version": 1, "roots": {"daisy2026": str(annual_root)}}
        fixed_date = {"year": 2026, "week": 42, "weekday": 1,
                      "wwd": "421", "path": "2026/421",
                      "localDate": "2026-10-12", "timezone": "America/Denver",
                      "convention": "DAISY:%G/%V/%u"}
        with patch("fileproxy.intake.daisy_date", return_value=fixed_date):
            result = intake(conf, LAGUNA, root_override="daisy2026",
                            index_path=self.index, downloader=self.fake_get)
        row = result["items"][0]
        self.assertEqual(row["root"], "daisy2026")
        self.assertTrue(row["path"].startswith("421/inbox/"))
        self.assertEqual((annual_root / row["path"]).read_bytes(), b"%PDF-1.4\nfixture\n")

    def test_plain_text_to_daisy(self):
        result = intake(self.config, "a note without a URL", index_path=self.index)
        self.assertEqual(result["items"][0]["root"], "daisy")
        self.assertEqual(result["items"][0]["mime"], "text/plain")

    def test_automatic_daisy_import_uses_registered_annual_archive(self):
        conf = {"version": 1, "roots": {"daisy2026": str(self.daisy)}}
        fixed = {"year": 2026, "week": 42, "weekday": 6, "wwd": "426",
                 "path": "2026/426", "localDate": "2026-10-17", "timezone": "America/Denver",
                 "convention": "DAISY:%G/%V/%u"}
        with patch("fileproxy.intake.daisy_date", return_value=fixed):
            result = intake(conf, "An ordinary archive note", index_path=self.index)
        row = result["items"][0]
        self.assertEqual(row["root"], "daisy2026")
        self.assertTrue(row["path"].startswith("426/inbox/"))
        self.assertEqual((self.daisy / row["path"]).read_text(), "An ordinary archive note")
        with self.assertRaisesRegex(ValueError, "not registered: daisy"):
            intake(conf, "An explicitly routed note", root_override="daisy", index_path=self.index)

    def test_missing_root_refuses_to_route_elsewhere(self):
        with self.assertRaises(ValueError):
            intake({"version": 1, "roots": {"daisy": str(self.daisy)}},
                   LAGUNA, index_path=self.index, downloader=self.fake_get)

    def test_imported_source_name_canonicalization(self):
        url = "https://example.org/Legal%20Filing%20Final.pdf"
        result = intake(self.config, url, root_override="certledger", index_path=self.index,
                        downloader=lambda source: (b"%PDF-1.4\\nfixture", source, "application/pdf"))
        item = result["items"][0]
        self.assertTrue(item["path"].endswith("-Legal-Filing-Final.pdf"))
        self.assertNotIn(" ", item["path"])
        metadata = json.loads((self.cert / item["metadataPath"]).read_text())
        self.assertEqual(metadata["sourceFilename"], "Legal Filing Final.pdf")
        self.assertEqual(metadata["sourceUrl"], url)

    def test_host_validation(self):
        for url in ["http://example.org/test.pdf", "https://localhost/x",
                    "https://127.0.0.1/a", "https://example.org:444/a",
                    "https://user:pass@example.org/a"]:
            with self.assertRaises(ValueError):
                url_details(url)

    def test_many_urls_limit(self):
        urls = "\n".join("https://example.org/x" + str(i) + ".pdf" for i in range(6))
        with self.assertRaises(ValueError):
            proposed_records(urls)


if __name__ == "__main__":
    unittest.main()
