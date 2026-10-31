"""Real HTTP lookup, cache, and transaction-summary integration with synthetic oEmbed."""
import io
import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode, urlsplit, parse_qs

from fileproxy import server
import youtube_metadata as youtube

VIDEO = "jNQXAC9IVRw"
URL = "https://youtu.be/" + VIDEO + "?t=90"
OEMBED = {"title": "Synthetic video title", "author_name": "Synthetic channel",
          "author_url": "https://www.youtube.com/@synthetic",
          "thumbnail_url": "https://i.ytimg.com/vi/" + VIDEO + "/hqdefault.jpg",
          "html": "<iframe>never rendered</iframe>"}


class YoutubeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        paths = patch.object(server.chisel, "data_path", side_effect=lambda *parts: self.base.joinpath(*parts))
        paths.start()
        self.addCleanup(paths.stop)
        handler = server.make_handler(self.base / "config.json", None)
        self.httpd = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 3)
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def request(self, url, refresh=False):
        connection = HTTPConnection("127.0.0.1", self.httpd.server_port, timeout=5)
        try:
            connection.request("GET", "/youtube-metadata?" + urlencode({"url": url, **({"refresh": "1"} if refresh else {})}), headers={"Origin": "https://johnrigler.github.io"})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), json.loads(response.read())
        finally:
            connection.close()

    def upstream(self, data=OEMBED):
        opener = MagicMock()
        opener.open.return_value = io.BytesIO(json.dumps(data).encode())
        return opener

    def test_lookup_caches_metadata_and_new_transaction_summaries_use_the_same_card(self):
        opener = self.upstream()
        with patch.object(youtube.urllib.request, "build_opener", return_value=opener):
            status, headers, result = self.request(URL)
            self.assertEqual(status, 200, result)
            self.assertEqual(headers["Access-Control-Allow-Origin"], "*")
            self.assertFalse(result["cached"])
            self.assertEqual(result["metadata"]["authorName"], "Synthetic channel")
            self.assertNotIn("html", result["metadata"])
            upstream = opener.open.call_args.args[0]
            self.assertEqual(urlsplit(upstream.full_url).hostname, "www.youtube.com")
            self.assertEqual(parse_qs(urlsplit(upstream.full_url).query)["url"], ["https://www.youtube.com/watch?v=" + VIDEO])
            self.assertEqual(opener.open.call_args.kwargs["timeout"], 8)
            self.assertTrue(self.request(URL)[2]["cached"])
            self.assertEqual(opener.open.call_count, 1)
        # This is an explicitly synthetic transaction fixture, never a ledger claim.
        tx = {"txid": "a" * 64, "vout": [{"scriptpubkey_asm": "OP_RETURN OP_PUSHBYTES_" + str(len(URL)) + " " + URL.encode().hex()}]}
        summary = server.chisel.summarize_tx_json(tx, coin="litecoin")["summary"]
        self.assertEqual(summary["opReturnText"], URL)
        self.assertEqual(summary["mediaCards"], result["mediaCards"])
        self.assertEqual(summary["mediaCards"][0]["title"], "Synthetic video title")
        self.assertIn("fetchedAt", summary["mediaCards"][0])
        self.assertFalse((self.base / "transactions").exists())

    def test_rejects_untrusted_urls_before_network_access(self):
        with patch.object(youtube.urllib.request, "build_opener") as network:
            for url in ("http://127.0.0.1/private", "https://youtube.com.attacker.test/watch?v=" + VIDEO,
                        "https://user:password@youtube.com/watch?v=" + VIDEO, "https://youtu.be/../../private", "https://youtube.com/watch?v=short"):
                self.assertEqual(self.request(url)[0], 400, url)
            network.assert_not_called()

    def test_explicit_refresh_fetches_new_metadata_instead_of_reusing_the_cache(self):
        with patch.object(youtube.urllib.request, "build_opener", return_value=self.upstream()):
            self.assertEqual(self.request(URL)[0], 200)
        with patch.object(youtube.urllib.request, "build_opener", return_value=self.upstream({**OEMBED, "title": "Changed title"})) as upstream:
            self.assertEqual(self.request(URL)[2]["metadata"]["title"], OEMBED["title"])
            upstream.assert_not_called()
            result = self.request(URL, refresh=True)[2]
            self.assertEqual(result["metadata"]["title"], "Changed title")
            self.assertFalse(result["cached"])
            self.assertEqual(result["mediaCards"][0]["title"], "Changed title")

    def test_unavailable_upstream_has_no_fake_metadata_and_retry_can_succeed(self):
        with patch.object(youtube.urllib.request, "build_opener", side_effect=OSError("synthetic offline")):
            status, _, result = self.request(URL)
        self.assertEqual(status, 502)
        self.assertFalse(result["ok"])
        self.assertNotIn("metadata", result)
        with patch.object(youtube.urllib.request, "build_opener", return_value=self.upstream()):
            self.assertEqual(self.request(URL)[0], 200)

    def test_oversized_oembed_and_non_https_media_urls_are_not_used(self):
        opener = self.upstream()
        opener.open.return_value = io.BytesIO(b"x" * (256 * 1024 + 1))
        with patch.object(youtube.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.request(URL)[0], 502)
        unsafe = {**OEMBED, "thumbnail_url": "javascript:alert(1)", "author_url": "https://attacker.test/"}
        with patch.object(youtube.urllib.request, "build_opener", return_value=self.upstream(unsafe)):
            metadata = self.request(URL)[2]["metadata"]
        self.assertEqual(metadata["thumbnailUrl"], "")
        self.assertEqual(metadata["authorUrl"], "")


if __name__ == "__main__":
    unittest.main()
