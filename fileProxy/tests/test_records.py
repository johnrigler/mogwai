"""Paper IDs resolve real files, with year ordering and private read boundaries."""
import hashlib
from http.client import HTTPConnection
from http.server import HTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.parse import urlencode
from unittest.mock import patch

from fileproxy.core import write_config
from fileproxy.records import lookup_record, record_config, record_id, resolve_record_file
from fileproxy.server import make_handler

ID = "0123456789ABCDEF"


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.roots = {year: self.base / ("daisy_" + str(year)) for year in (2024, 2025, 2026, 2027)}
        for root in self.roots.values():
            root.mkdir()
        self.config = {"version": 1, "roots": {"daisy" + str(y): str(p) for y, p in self.roots.items()}}
        self.home = self.base / "home.json"
        self.home.write_text(json.dumps({"projects": {"daisy_2026": {"path": str(self.roots[2026])},
                                                      "unrelated": {"path": str(self.base)}}}))

    def folder(self, year, path="444/records/" + ID):
        folder = self.roots[year] / path
        folder.mkdir(parents=True)
        (folder / "record-id").write_text(ID.lower() + "\n")
        (folder / "README.md").write_text("Physical collection. Inventory pending.")
        (folder / "scan.txt").write_bytes(b"actual source bytes")
        return folder

    def test_newest_matching_year_wins_and_prior_year_is_fallback(self):
        self.folder(2024)
        old = self.folder(2025)
        self.folder(2027)  # A future archive is not searched.
        result = lookup_record(self.config, ID.lower(), current_year=2026)
        self.assertEqual(result["recordId"], ID)
        self.assertEqual([x["isoYear"] for x in result["searched"]], [2026, 2025])
        self.assertEqual([x["isoYear"] for x in result["records"]], [2025])
        current = self.folder(2026)
        result = lookup_record(self.config, ID, current_year=2026)
        self.assertEqual([x["isoYear"] for x in result["searched"]], [2026])
        self.assertEqual([x["isoYear"] for x in result["records"]], [2026])
        row = next(x for x in result["records"][0]["entries"] if x["path"].endswith("scan.txt"))
        self.assertEqual(row["sha256"], hashlib.sha256((current / "scan.txt").read_bytes()).hexdigest())
        self.assertNotIn(str(self.base), json.dumps(result))
        self.assertFalse((old / "catalog.sqlite3").exists())

    def test_same_year_collisions_are_returned_as_separate_records(self):
        self.folder(2026)
        self.folder(2026, "445/another-folder")
        result = lookup_record(self.config, ID, 2026)
        self.assertEqual(len(result["records"]), 2)
        self.assertNotEqual(result["records"][0]["path"], result["records"][1]["path"])

    def test_new_files_and_changes_are_visible_without_catalog_writes(self):
        folder = self.folder(2026)
        lookup_record(self.config, ID, 2026)
        (folder / "later.txt").write_text("later source")
        (folder / "scan.txt").write_text("new source bytes")
        result = lookup_record(self.config, ID, 2026)
        self.assertEqual(len(result["records"][0]["entries"]), 4)
        self.assertFalse((self.roots[2026] / "catalog.sqlite3").exists())

    def test_shared_mogwai_paths_are_private_to_record_lookup(self):
        self.folder(2026)
        original = {"version": 1, "roots": {}}
        configured = record_config(original, self.home)
        self.assertEqual(list(configured["roots"]), ["daisy_2026"])
        self.assertEqual(original["roots"], {})
        self.assertTrue(lookup_record(configured, ID, 2026)["found"])
        override = {"version": 1, "roots": {"daisy2026": str(self.roots[2025])}}
        self.assertEqual(record_config(override, self.home)["roots"], override["roots"])

    def test_generic_daisy_year_layout_and_missing_year_reporting(self):
        generic = self.base / "daisy"
        folder = generic / "2025" / "442" / ID.lower()
        folder.mkdir(parents=True)
        (folder / "scan.txt").write_text("source")
        config = {"roots": {"daisy": str(generic), "daisy2026": str(self.base / "missing")}}
        result = lookup_record(config, ID, 2026)
        self.assertTrue(result["found"])
        self.assertEqual(result["searched"][0]["status"], "unavailable")
        self.assertEqual(result["records"][0]["isoYear"], 2025)

    def test_files_must_belong_to_exact_record_and_visible_tree(self):
        folder = self.folder(2026)
        prefix = "444/records/" + ID + "/"
        conf = self.config
        self.assertEqual(resolve_record_file(conf, ID, "daisy2026", prefix + "scan.txt"), folder / "scan.txt")
        (folder / ".private").write_text("hidden")
        (folder / "linked.txt").symlink_to(folder / "scan.txt")
        (self.roots[2026] / "unrelated.txt").write_text("unrelated")
        for path in [prefix + ".private", prefix + "linked.txt", "unrelated.txt", "../outside"]:
            with self.subTest(path=path), self.assertRaises((FileNotFoundError, ValueError)):
                resolve_record_file(conf, ID, "daisy2026", path)
        rows = lookup_record(conf, ID, 2026)["records"][0]["entries"]
        self.assertFalse(any("linked.txt" in row["path"] or ".private" in row["path"] for row in rows))

    def test_symlinked_record_and_markers_are_not_followed(self):
        folder = self.folder(2025)
        (self.roots[2026] / ID).symlink_to(folder, target_is_directory=True)
        marker_folder = self.roots[2026] / "unrelated"
        marker_folder.mkdir()
        (marker_folder / "record-id").symlink_to(folder / "record-id")
        result = lookup_record(self.config, ID, 2026)
        self.assertEqual(result["records"][0]["isoYear"], 2025)

    def test_id_is_complete_identifier_not_a_key_or_hash_prefix(self):
        for bad in [None, "", "0x" + ID, ID + "0", ID * 4, "../../" + ID, "G" * 16]:
            with self.subTest(value=bad), self.assertRaises(ValueError):
                record_id(bad)
        self.assertFalse(lookup_record(self.config, ID, 2026)["found"])

    def start_server(self):
        self.folder(2026)
        conf_path = self.base / "fileproxy.json"
        write_config({"version": 1, "roots": {}}, conf_path)
        handler = make_handler(conf_path, None, home_config=self.home, record_token="synthetic-read-token")
        httpd = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 3)
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        self.port = httpd.server_port

    def request(self, path, headers=None):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request("GET", path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_http_guard_same_origin_token_read_and_file_membership(self):
        self.start_server()
        with patch("fileproxy.records.daisy_date", return_value={"year": 2026}):
            route = "/v1/record?id=" + ID
            code, headers, raw = self.request(route)
            self.assertEqual(code, 200)
            self.assertEqual(headers["Cache-Control"], "private, no-store")
            self.assertTrue(json.loads(raw)["found"])
            for extra in [{"Origin": "https://untrusted.example"}, {"Via": "proxy"},
                          {"Sec-Fetch-Site": "cross-site"}, {"Host": "rebound.example"}]:
                with self.subTest(headers=extra):
                    self.assertEqual(self.request(route, extra)[0], 403)
            remote = {"Via": "proxy", "Authorization": "Bearer synthetic-read-token"}
            self.assertEqual(self.request(route, remote)[0], 200)
            remote["Authorization"] = "Bearer wrong"
            self.assertEqual(self.request(route, remote)[0], 403)
            file_route = "/v1/record-file?" + urlencode({"id": ID, "root": "daisy_2026", "path": "444/records/" + ID + "/scan.txt"})
            code, _, data = self.request(file_route)
            self.assertEqual((code, data), (200, b"actual source bytes"))
            self.assertEqual(self.request(file_route, {"Via": "proxy"})[0], 403)
            self.assertEqual(self.request("/v1/file?root=daisy_2026&path=444/records/" + ID + "/scan.txt")[0], 400)
            self.assertIn(b"Physical folder record", self.request("/record?id=" + ID)[2])


if __name__ == "__main__":
    unittest.main()
