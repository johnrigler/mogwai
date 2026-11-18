"""Offline dRPC tests: no network access, no real keys, no broadcast."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.parse import urlsplit

from tools.drpc_status import _safe_endpoint, check, main, status


class FakeRPC:
    def __init__(self, chain="0x89", block="0xa5"):
        self.chain = chain
        self.block = block
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request)
        assert request.get_method() == "POST"
        data = json.loads(request.data)
        if data["method"] == "eth_chainId":
            answer = self.chain
        elif data["method"] == "eth_blockNumber":
            answer = self.block
        else:
            raise AssertionError("Unexpected RPC method")
        return io.BytesIO(json.dumps({"jsonrpc": "2.0", "id": 1, "result": answer}).encode())


class DRPCStatusTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "drpc.json"
        self.url_token = "fake-url-token-123"
        self.api_token = "fake-header-token-456"

    def write(self, value, mode=0o600):
        self.path.write_text(json.dumps(value), encoding="utf-8")
        self.path.chmod(mode)

    def test_dashboard_url_keeps_key_out_of_stdout_and_header(self):
        url = "https://lb.drpc.live/polygon/" + self.url_token
        self.write({"polygon": url, "api": self.api_token})
        result = check(self.path)
        self.assertEqual(result["authentication"], "url")
        self.assertNotIn(self.url_token, str(result))
        self.assertNotIn(self.api_token, str(result))
        remote = FakeRPC()
        output = status(self.path, opener=remote)
        self.assertEqual(output["chainId"], 137)
        self.assertEqual(output["latestBlock"], 165)
        self.assertEqual(output["authentication"], "url")
        self.assertEqual(len(remote.requests), 2)
        self.assertEqual(remote.requests[0].full_url, url)
        self.assertNotIn("Drpc-key", dict(remote.requests[0].header_items()))

    def test_key_header_when_endpoint_has_no_key_in_url(self):
        self.write({"polygon": "https://lb.drpc.live/polygon", "api": self.api_token})
        remote = FakeRPC()
        output = status(self.path, opener=remote)
        self.assertEqual(output["authentication"], "header")
        headers = dict(remote.requests[0].header_items())
        self.assertEqual(headers["Drpc-key"], self.api_token)
        self.assertNotIn(self.api_token, remote.requests[0].full_url)

    def test_public_url_without_key_has_no_auth(self):
        self.write({"polygon": "https://polygon.drpc.org", "api": ""})
        result = status(self.path, opener=FakeRPC())
        self.assertEqual(result["authentication"], "none")

    def test_reject_wallet_url_before_network(self):
        self.write({"polygon": "https://lb.drpc.live/polygon/test-token/lambda", "api": self.api_token})
        with self.assertRaisesRegex(ValueError, "Data & Wallet"):
            status(self.path, opener=FakeRPC())

    def test_reject_other_chain_before_network(self):
        self.write({"polygon": "https://lb.drpc.live/ethereum/fake-token", "api": self.api_token})
        with self.assertRaisesRegex(ValueError, "Polygon network"):
            status(self.path, opener=FakeRPC())

    def test_reject_other_hosts_even_if_https(self):
        self.write({"polygon": "https://example.com/polygon/fake-token", "api": self.api_token})
        with self.assertRaisesRegex(ValueError, "HTTPS dRPC"):
            status(self.path, opener=FakeRPC())

    def test_reject_non_https(self):
        self.write({"polygon": "http://lb.drpc.live/polygon/fake-token", "api": self.api_token})
        with self.assertRaisesRegex(ValueError, "HTTPS dRPC"):
            status(self.path, opener=FakeRPC())

    def test_chain_mismatch_rejected(self):
        self.write({"polygon": "https://lb.drpc.live/polygon/fake-token", "api": ""})
        with self.assertRaisesRegex(ValueError, "chain mismatch"):
            status(self.path, opener=FakeRPC(chain="0x1"))

    def test_permission_rejected(self):
        self.write({"polygon": "https://lb.drpc.live/polygon/fake-token", "api": ""}, mode=0o644)
        if os.name == "posix":
            with self.assertRaisesRegex(ValueError, "chmod 600"):
                check(self.path)

    def test_symlink_rejected(self):
        self.write({"polygon": "https://lb.drpc.live/polygon/fake-token", "api": ""})
        link = self.path.parent / "alias.json"
        link.symlink_to(self.path)
        with self.assertRaisesRegex(ValueError, "symlink"):
            check(link)

    def test_extra_fields_are_not_exposed(self):
        self.write({"polygon": "https://lb.drpc.live/polygon/fake-token",
                    "api": "", "dataWallet": "https://lb.drpc.live/lambda/fake"})
        result = check(self.path)
        self.assertNotIn("lambda", str(result))

    def test_cli_errors_do_not_print_url_or_key(self):
        self.write({"polygon": "https://example.com/polygon/" + self.url_token,
                    "api": self.api_token})
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(main(["status", "--config", str(self.path)]), 1)
        self.assertNotIn(self.api_token, err.getvalue())
        self.assertNotIn(self.url_token, err.getvalue())

    def test_http_403_is_sanitized_by_rpc_reader(self):
        class RejectRPC:
            def open(self, request, timeout):
                raise HTTPError(request.full_url, 403, "Forbidden", {}, None)
        self.write({"polygon": "https://lb.drpc.live/polygon/" + self.url_token, "api": ""})
        err = io.StringIO()
        # Ensure even direct error details do not include the URL credential.
        with self.assertRaises(ValueError) as got:
            status(self.path, opener=RejectRPC())
        self.assertIn("403", str(got.exception))
        self.assertNotIn(self.url_token, str(got.exception))


if __name__ == "__main__":
    unittest.main()
