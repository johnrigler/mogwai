import json
import tempfile
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from unittest.mock import patch

from fileproxy.core import write_config
from fileproxy.server import make_handler


class WebsiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.handler = make_handler(str(self.base / "config.json"), str(self.base / "index.json"))
        self.httpd = HTTPServer(("127.0.0.1", 0), self.handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.host = "http://127.0.0.1:" + str(self.httpd.server_port)

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=3)
        self.temp.cleanup()

    def test_page_served_from_unified_service(self):
        with urlopen(self.host + "/") as r:
            html = r.read().decode("utf-8")
        self.assertIn("FileProxy", html)
        self.assertIn('<textarea id="paste"', html)
        self.assertIn('id="import"', html)

    def test_recursive_catalog_print_page(self):
        with urlopen(self.host + "/catalog") as r:
            html = r.read().decode("utf-8")
        self.assertIn("Recursive tree", html)
        self.assertIn("Print listing / Save PDF", html)
        self.assertIn("fileproxy-catalog", html)

    def test_health_and_legacy_ping(self):
        with urlopen(self.host + "/v1/health") as r:
            response = json.load(r)
        self.assertTrue(response["ok"])
        self.assertEqual(response["roots"], [])
        with urlopen(self.host + "/ping") as r:
            legacy = json.load(r)
        self.assertTrue(legacy["ok"])
        self.assertEqual(legacy["service"], "chisel-fileproxy")

    def test_ingest_requires_token(self):
        request = Request(self.host + "/v1/ingest",
                          data=json.dumps({"text": "hello"}).encode("utf-8"),
                          headers={"Content-Type": "application/json"},
                          method="POST")
        with self.assertRaises(HTTPError) as response:
            urlopen(request)
        self.assertEqual(response.exception.code, 403)

    def test_health_reports_registered_annual_daisy_default(self):
        write_config({"version": 1, "roots": {"daisy2026": str(self.base)}},
                     self.base / "config.json")
        with patch("fileproxy.server.daisy_date", return_value={"year": 2026}):
            with urlopen(self.host + "/v1/health") as r:
                response = json.load(r)
        self.assertEqual(response["defaultDaisyRoot"], "daisy2026")


if __name__ == "__main__":
    unittest.main()
