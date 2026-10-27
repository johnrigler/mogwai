"""Offline, local HTTP regression tests for m.watch.py."""
import http.server
import json
import pathlib
import subprocess
import sys
import tempfile
import threading
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "m.watch.py"


class Handler(http.server.BaseHTTPRequestHandler):
    body = b"first"
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(type(self).body)
    def log_message(self, *_):
        return


class WatchTests(unittest.TestCase):
    def test_baseline_unchanged_change(self):
        with tempfile.TemporaryDirectory() as base:
            base = pathlib.Path(base)
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/fixture"
                config = base / "config.json"
                config.write_text(json.dumps({"subjectId": "test", "sources": [
                    {"id": "fixture", "url": url}
                ]}))
                def run():
                    return subprocess.run([sys.executable, str(SCRIPT),
                        "--config", str(config), "--state-dir", str(base / "state"), "--archive"],
                        text=True, capture_output=True, check=True).stdout
                Handler.body = b"first"
                self.assertIn("baseline", run())
                self.assertIn("unchanged", run())
                Handler.body = b"second"
                self.assertIn("changed", run())
                events = [json.loads(x) for x in (base / "state/events.jsonl").read_text().splitlines()]
                self.assertEqual([e["type"] for e in events],
                                 ["source-baseline", "source-byte-change"])
                state = json.loads((base / "state/state-test.json").read_text())
                self.assertEqual(state["sources"]["fixture"]["byteLength"], 6)
                self.assertEqual(len(list((base / "state/blobs/fixture").iterdir())), 2)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
