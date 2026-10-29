"""Exercise local opt-in and token authentication through the real HTTP API."""
import base64
import hashlib
from http.client import HTTPConnection
from http.server import HTTPServer
import io
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fileproxy import cli, server
from fileproxy.core import load_catalog, write_config


class WriteModeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "archive"
        self.root.mkdir()
        self.config = {"version": 1, "roots": {"daisy": str(self.root)}}
        self.config_path = self.base / "config.json"
        write_config(self.config, self.config_path)
        self.env = patch.dict(os.environ, {"FILEPROXY_WRITE_TOKEN": ""})
        self.env.start()
        self.addCleanup(self.env.stop)

    def start(self, local):
        handler = server.make_handler(self.config_path, None, local=local)
        httpd = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=httpd.serve_forever,
                                  kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 3)
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        self.port = httpd.server_port
        self.origin = "http://127.0.0.1:" + str(self.port)

    def request(self, path, body=None, headers=None):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request("GET" if body is None else "POST", path,
                               body=None if body is None else json.dumps(body),
                               headers={"Content-Type": "application/json", **(headers or {})})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def put(self, path, headers=None, **payload):
        return self.request("/v1/put", {"root": "daisy", "path": path,
                                       "text": "saved locally", **payload}, headers)

    def test_local_inbox_ingest_stores_original_metadata_and_catalog_without_token(self):
        self.start(local=True)
        status, health = self.request("/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["writeMode"], "local")
        self.assertFalse(health["writeTokenRequired"])
        text = "A locally imported note."
        status, result = self.request("/v1/ingest", {"text": text, "destination": "daisy"},
                                      {"Origin": self.origin, "Sec-Fetch-Site": "same-origin"})
        self.assertEqual(status, 200, result)
        self.assertEqual(result["count"], 1)
        item = result["items"][0]
        self.assertEqual((self.root / item["path"]).read_bytes(), text.encode())
        metadata = json.loads((self.root / item["metadataPath"]).read_text())
        self.assertEqual(metadata["sha256"], hashlib.sha256(text.encode()).hexdigest())
        self.assertIn(item["path"], [row["path"] for row in load_catalog(self.config)["entries"]])
        self.assertTrue((self.root / "catalog.sqlite3").is_file())

    def test_local_cli_and_same_origin_browser_puts_work_and_keep_overwrite_rules(self):
        self.start(local=True)
        for host in ("127.0.0.1", "localhost", "[::1]"):
            with self.subTest(host=host):
                headers = {"Host": host + ":" + str(self.port)}
                headers["Origin"] = "http://" + headers["Host"]
                status, result = self.put(host.replace(":", "") + ".txt", headers)
                self.assertEqual(status, 200, result)
        self.assertEqual(self.put("note.txt")[0], 200)
        self.assertEqual(self.put("note.txt")[0], 409)
        binary = b"\x00\xff\x01"
        status, result = self.put("binary.dat", base64=base64.b64encode(binary).decode())
        self.assertEqual(status, 200, result)
        self.assertEqual((self.root / "binary.dat").read_bytes(), binary)

    def test_local_mode_rejects_cross_origin_rebinding_and_forwarded_writes(self):
        self.start(local=True)
        cases = [
            {"Origin": "https://example.com"},
            {"Origin": "null"},
            {"Origin": "http://127.0.0.1:1"},
            {"Origin": self.origin.replace("http:", "https:")},
            {"Host": "rebound.example:" + str(self.port)},
            {"Host": "127.0.0.1:1"},
            {"Sec-Fetch-Site": "cross-site"},
            {"Sec-Fetch-Site": "same-site"},
        ]
        cases.extend({header: "proxy"} for header in
                     ("Forwarded", "X-Forwarded-For", "X-Real-IP", "X-Forwarded-Host", "Via"))
        for headers in cases:
            with self.subTest(headers=headers):
                status, result = self.put("denied.txt", headers)
                self.assertEqual(status, 403, result)
                self.assertFalse((self.root / "denied.txt").exists())
                status, health = self.request("/v1/health", headers=headers)
                self.assertEqual(status, 200)
                self.assertTrue(health["writeTokenRequired"])

    def test_default_mode_requires_configured_matching_token(self):
        self.start(local=False)
        status, health = self.request("/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["writeMode"], "token")
        self.assertTrue(health["writeTokenRequired"])
        self.assertEqual(self.put("denied.txt")[0], 403)
        self.assertEqual(self.put("denied.txt", {"X-FileProxy-Token": "invented"})[0], 403)
        os.environ["FILEPROXY_WRITE_TOKEN"] = "test-write-secret"
        self.assertEqual(self.put("denied.txt")[0], 403)
        self.assertEqual(self.put("denied.txt", {"X-FileProxy-Token": "wrong"})[0], 403)
        self.assertEqual(self.put("header.txt", {"X-FileProxy-Token": "test-write-secret"})[0], 200)
        self.assertEqual(self.put("bearer.txt", {"Authorization": "Bearer test-write-secret"})[0], 200)
        self.assertFalse((self.root / "denied.txt").exists())

    def test_cross_origin_client_can_still_use_explicit_token_in_local_mode(self):
        self.start(local=True)
        os.environ["FILEPROXY_WRITE_TOKEN"] = "test-write-secret"
        status, result = self.put("remote.txt", {"Origin": "https://example.com",
                                                "X-FileProxy-Token": "test-write-secret"})
        self.assertEqual(status, 200, result)

    def test_local_scan_needs_no_token(self):
        self.start(local=True)
        (self.root / "scan.txt").write_text("index me")
        status, result = self.request("/v1/scan", {"roots": ["daisy"]})
        self.assertEqual(status, 200, result)
        self.assertEqual(result["scanned"], 1)

    def test_local_delete_and_undo_use_the_same_authentication_policy(self):
        self.start(local=True)
        self.put("11703")
        digest = hashlib.sha256(b"saved locally").hexdigest()
        status, removed = self.request("/v1/trash", {"root": "daisy", "path": "11703", "sha256": digest})
        self.assertEqual(status, 200, removed)
        self.assertFalse((self.root / "11703").exists())
        status, restored = self.request("/v1/restore", {"root": "daisy", "trashId": removed["trashId"]})
        self.assertEqual(status, 200, restored)
        self.assertEqual((self.root / "11703").read_text(), "saved locally")

    def test_token_mode_guards_management_and_packet_routes(self):
        self.start(local=False)
        for route in ("/v1/trash", "/v1/restore", "/v1/packet", "/v1/mkdir", "/v1/transfer"):
            with self.subTest(route=route):
                self.assertEqual(self.request(route, {})[0], 403)

    def test_local_folder_creation_and_ordered_copy_need_no_token(self):
        self.start(local=True)
        self.put("01.pdf")
        status, result = self.request("/v1/mkdir", {"root": "daisy", "path": "response-1"}, {"Origin": self.origin})
        self.assertEqual(status, 200, result)
        status, folders = self.request("/v1/folders?root=daisy")
        self.assertEqual(status, 200)
        self.assertIn("response-1", folders["directories"])
        status, result = self.request("/v1/transfer", {"root": "daisy", "destination": "response-1",
                                     "numbered": True, "operation": "copy", "files": [{"path": "01.pdf",
                                     "sha256": hashlib.sha256(b"saved locally").hexdigest()}]}, {"Origin": self.origin})
        self.assertEqual(status, 200, result)
        self.assertEqual((self.root / "response-1/001-01.pdf").read_text(), "saved locally")
        self.assertTrue((self.root / "01.pdf").exists())

    def test_saved_html_folder_serves_relative_images_and_allows_printing_without_scripts(self):
        self.start(local=True)
        folder = self.root / "response-1"
        folder.mkdir()
        html = b'<img src="001-scan.png">'
        (folder / "index.html").write_bytes(html)
        (folder / "001-scan.png").write_bytes(b"original image")
        connection = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request("GET", "/v1/fs/daisy/response-1")
            response = connection.getresponse()
            self.assertEqual(response.status, 302)
            self.assertEqual(response.getheader("Location"), "/v1/fs/daisy/response-1/")
            response.read()
            connection.request("GET", "/v1/fs/daisy/response-1/")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            policy = response.getheader("Content-Security-Policy")
            self.assertIn("allow-same-origin allow-modals", policy)
            self.assertIn("img-src 'self'", policy)
            self.assertNotIn("allow-scripts", policy)
            self.assertEqual(response.read(), html)
            connection.request("GET", "/v1/fs/daisy/response-1/001-scan.png")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b"original image")
            connection.request("GET", "/v1/fs/daisy/../config.json")
            response = connection.getresponse()
            self.assertEqual(response.status, 400)
            response.read()
        finally:
            connection.close()

    def test_html_files_are_sandboxed_and_original_downloads_are_attachments(self):
        self.start(local=True)
        source = b"<script>parent.changed=true</script>"
        (self.root / "page.html").write_bytes(source)
        connection = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request("GET", "/v1/file?root=daisy&path=page.html&download=1")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertIn("sandbox", response.getheader("Content-Security-Policy"))
            self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")
            self.assertTrue(response.getheader("Content-Disposition").startswith("attachment;"))
            self.assertEqual(response.read(), source)
        finally:
            connection.close()


class LocalListenerTests(unittest.TestCase):
    def test_both_peer_and_listener_must_be_loopback(self):
        handler_type = server.make_handler(None, None, local=True)
        for peer, bind, allowed in (
            ("127.0.0.1", "127.0.0.1", True),
            ("::1", "::1", True),
            ("::ffff:127.0.0.1", "::1", True),
            ("192.0.2.1", "127.0.0.1", False),
            ("127.0.0.1", "0.0.0.0", False),
            ("::1", "::", False),
        ):
            with self.subTest(peer=peer, bind=bind):
                handler = handler_type.__new__(handler_type)
                handler.client_address = (peer, 1234)
                handler.server = SimpleNamespace(server_address=(bind, 7799))
                handler.connection = object()
                handler.headers = {"Host": "localhost:7799"}
                self.assertEqual(handler.local_write_allowed(), allowed)

    def test_cli_local_mode_forces_loopback_and_explicit_host_is_passed(self):
        base_handler = server.chisel.Handler
        for args, expected_host in ((["serve", "--local", "--host", "0.0.0.0"], "127.0.0.1"),
                                    (["serve", "--host", "0.0.0.0"], "0.0.0.0"),
                                    (["serve"], "127.0.0.1")):
            with self.subTest(args=args), patch.object(server.chisel, "HOST", "0.0.0.0"), \
                 patch.object(server.chisel, "Handler", base_handler), \
                 patch.object(server.chisel, "main") as run, \
                 patch("sys.stdout", new_callable=io.StringIO):
                cli.main(args)
                run.assert_called_once_with(host=expected_host, port=7799)


if __name__ == "__main__":
    unittest.main()
