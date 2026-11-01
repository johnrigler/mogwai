"""Real HTTP append/read/retry tests; public synthetic signing vector only."""
import copy
import hashlib
from http.client import HTTPConnection
from http.server import HTTPServer
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from fileproxy import server
import interactions

VECTOR = json.loads((Path(__file__).parent / "fixtures" / "signed-comment-v1.json").read_text())


def unsigned(number=1, kind="select", txid="ab" * 32):
    payload = copy.deepcopy(VECTOR["payload"])
    payload.update(id=f"{number:032x}", kind=kind, action=kind, author=None,
                   comment="An open comment" if kind == "comment" else "")
    payload["subject"]["txid"] = txid
    if kind == "visit":
        payload["subject"] = None
        payload["title"] = "Chisel"
        payload["synopsis"] = payload["url"] = ""
    return {"format": interactions.SCHEMA, "payload": payload}


class InteractionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        paths = patch.object(server.chisel, "data_path", side_effect=lambda *parts: self.root / "data" / Path(*parts))
        paths.start()
        self.addCleanup(paths.stop)
        root = patch.object(server.chisel, "ROOT", self.root)
        root.start()
        self.addCleanup(root.stop)
        allowed = patch.object(server.chisel, "ALLOWED_ROOTS", [self.root])
        allowed.start()
        self.addCleanup(allowed.stop)
        self.httpd = HTTPServer(("127.0.0.1", 0), server.make_handler(self.root / "config.json", None))
        thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 3)
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    @property
    def database(self):
        return self.root / "data" / interactions.DATABASE

    def request(self, path="/interactions", document=None, method=None):
        conn = HTTPConnection("127.0.0.1", self.httpd.server_port, timeout=5)
        try:
            data = json.dumps(document).encode() if document is not None else None
            conn.request(method or ("POST" if document is not None else "GET"), path, data,
                         {"Origin": "https://johnrigler.github.io", "Content-Type": "application/json"})
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def post(self, document):
        status, _, data = self.request(document=document)
        return status, json.loads(data)

    def test_four_interaction_types_append_and_read_newest_first_without_user_agent_or_ip(self):
        for number, kind in enumerate(["visit", "select", "engage", "comment"], 1):
            status, result = self.post(unsigned(number, kind))
            self.assertEqual(status, 201, result)
            self.assertEqual(result["entry"]["document"]["payload"]["kind"], kind)
            self.assertRegex(result["entry"]["receivedAt"], r"Z$")
        status, headers, body = self.request()
        result = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["Access-Control-Allow-Origin"], "*")
        self.assertEqual([row["document"]["payload"]["kind"] for row in result["entries"]], ["comment", "engage", "select", "visit"])
        self.assertNotIn(b"127.0.0.1", body)
        self.assertNotIn(b"User-Agent", body)

    def test_duplicate_retry_is_idempotent_but_a_changed_document_with_the_same_id_conflicts(self):
        document = unsigned(1, "comment")
        status, first = self.post(document)
        self.assertEqual(status, 201)
        status, again = self.post(document)
        self.assertEqual(status, 200)
        self.assertTrue(again["duplicate"])
        self.assertEqual(first["entry"], again["entry"])
        document["payload"]["comment"] = "Overwrite attempt"
        status, result = self.post(document)
        self.assertEqual(status, 409, result)
        original = json.loads(self.request()[2])["entries"]
        self.assertEqual(len(original), 1)
        self.assertEqual(original[0]["document"]["payload"]["comment"], "An open comment")

    def test_pagination_retains_older_cursor_when_a_new_visitor_arrives(self):
        for number in range(1, 7):
            self.assertEqual(self.post(unsigned(number))[0], 201)
        first = json.loads(self.request("/interactions?limit=2")[2])
        self.assertEqual([row["seq"] for row in first["entries"]], [6, 5])
        self.assertTrue(first["hasMore"])
        self.post(unsigned(7, "visit"))
        older = json.loads(self.request("/interactions?limit=2&before=" + str(first["before"]))[2])
        self.assertEqual([row["seq"] for row in older["entries"]], [4, 3])
        newer = json.loads(self.request("/interactions?after=6")[2])
        self.assertEqual([row["seq"] for row in newer["entries"]], [7])

    def test_comment_filters_use_chain_and_transaction_identity(self):
        self.post(unsigned(1, "select"))
        self.post(unsigned(2, "comment"))
        self.post(unsigned(3, "comment", "cd" * 32))
        rows = json.loads(self.request("/interactions?kind=comment&subject=litecoin:" + "ab" * 32)[2])["entries"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["document"]["payload"]["id"], f"{2:032x}")

    def test_signed_comment_preserves_browser_signature_footer_and_exact_unicode_payload(self):
        status, result = self.post(VECTOR)
        self.assertEqual(status, 201, result)
        self.assertEqual(result["entry"]["document"], VECTOR)
        status, headers, data = self.request("/interactions/event?id=" + VECTOR["payload"]["id"])
        self.assertEqual(status, 200)
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertEqual(json.loads(data), VECTOR)
        self.assertGreater(data.index(b'"proof"'), data.index(b'"payload"'))
        self.assertEqual(hashlib.sha256(data).hexdigest(), result["entry"]["sha256"])
        self.assertEqual(result["entry"]["document"]["payload"]["author"]["coin"], "litecoin")
        # The API stores the proof. It never asserts that it checked secp256k1.
        self.assertNotIn("verified", result["entry"])

    def test_altered_signed_text_date_and_subject_are_rejected_before_storage(self):
        for field, value in [("comment", "tampered"), ("at", "2020-01-01T00:00:00.000Z"), ("title", "Other record")]:
            document = copy.deepcopy(VECTOR)
            document["payload"][field] = value
            status, result = self.post(document)
            self.assertEqual(status, 400, result)
        self.assertEqual(json.loads(self.request()[2])["entries"], [])

    def test_unsigned_authorship_unknown_fields_and_private_source_urls_are_rejected(self):
        for mutate in [lambda d: d["payload"].update(author=VECTOR["payload"]["author"]),
                       lambda d: d["payload"].update(privateKeyHex="must not be accepted"),
                       lambda d: d["payload"]["subject"].update(dataUrl="http://127.0.0.1/private.json"),
                       lambda d: d["payload"]["subject"].update(dataUrl="https://records.example/a.json?token=secret"),
                       lambda d: d["payload"].update(comment="x" * 4001)]:
            document = unsigned(1, "comment")
            mutate(document)
            status, result = self.post(document)
            self.assertEqual(status, 400, result)

    def test_sqlite_and_legacy_write_routes_cannot_update_or_delete_existing_history(self):
        self.post(unsigned(1, "comment"))
        with sqlite3.connect(self.database) as db:
            for statement in ["UPDATE interactions SET document='{}'", "DELETE FROM interactions"]:
                with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                    db.execute(statement)
            self.assertEqual(db.execute("SELECT length(sha256) FROM interactions").fetchone()[0], 32)
        for path, body in [("/save", {"path": str(self.database), "text": "destroy"}),
                           ("/delete", {"path": str(self.database)}),
                           ("/save", {"path": str(self.database) + "-wal", "text": "destroy"})]:
            status, _, response = self.request(path, body)
            self.assertEqual(status, 403, response)
        self.assertEqual(len(json.loads(self.request()[2])["entries"]), 1)

    def test_history_survives_new_connections_and_uses_receipt_order_for_an_incorrect_client_clock(self):
        first, second = unsigned(1), unsigned(2)
        first["payload"]["at"] = "2099-01-01T00:00:00.000Z"
        second["payload"]["at"] = "2000-01-01T00:00:00.000Z"
        self.post(first)
        self.post(second)
        rows = json.loads(self.request()[2])["entries"]
        self.assertEqual([row["document"]["payload"]["id"] for row in rows], [f"{2:032x}", f"{1:032x}"])
        self.assertEqual(len(interactions.read(self.database, {})["entries"]), 2)

    def test_bad_cursors_oversized_requests_and_missing_downloads_fail_without_changing_history(self):
        for path in ["/interactions?before=broken", "/interactions?after=9999999999999999999", "/interactions/event?id=../escape"]:
            self.assertEqual(self.request(path)[0], 400)
        self.assertEqual(self.request("/interactions/event?id=" + "f" * 32)[0], 404)
        oversized = unsigned(1, "comment")
        oversized["payload"]["comment"] = "x" * 40000
        self.assertEqual(self.post(oversized)[0], 413)


if __name__ == "__main__":
    unittest.main()
