"""Offline tests for private Etherscan V2 Polygon reader. Never calls the network."""
import io
import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
import unittest

from tools.etherscan_read import proxy_read, status, transaction


class FakeHTTP:
    def __init__(self, results=None, error=None):
        self.results = results or {}
        self.error = error
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        query = parse_qs(urlsplit(request.full_url).query)
        action = query["action"][0]
        if action not in self.results:
            raise AssertionError("Unexpected action")
        value = self.results[action]
        return io.BytesIO(json.dumps({
            "jsonrpc": "2.0", "id": 83, "result": value
        }).encode("utf-8"))


class EtherscanReadTests(unittest.TestCase):
    TXID = "0x" + "a" * 64

    def config(self):
        return {"ledgers": {"polygon": {
            "family": "evm", "chainId": 137,
            "read": {"url": "https://polygon.drpc.org"},
            "providers": {"etherscan": {
                "url": "https://api.etherscan.io/v2/api", "apiKey": "fake-private-test-key"
            }}
        }}}

    def test_status_uses_etherscan_not_rpc(self):
        remote = FakeHTTP({"eth_blockNumber": "0x100"})
        result = status(self.config(), opener=remote)
        self.assertEqual(result["latestBlock"], 256)
        self.assertEqual(result["provider"], "etherscan")
        self.assertEqual(result["chainId"], 137)
        self.assertEqual(result["chainIdSource"], "configured request parameter")
        self.assertEqual(len(remote.requests), 1)
        request = remote.requests[0]
        self.assertEqual(request.get_method(), "GET")
        parsed = urlsplit(request.full_url)
        self.assertEqual(parsed.hostname, "api.etherscan.io")
        q = parse_qs(parsed.query)
        self.assertEqual(q["module"], ["proxy"])
        self.assertEqual(q["chainid"], ["137"])
        self.assertEqual(q["apikey"], ["fake-private-test-key"])
        self.assertEqual(q["action"], ["eth_blockNumber"])

    def test_transaction_and_receipt(self):
        remote = FakeHTTP({
            "eth_getTransactionByHash": {
                "hash": self.TXID, "chainId": "0x89", "value": "0x0",
                "input": "0x414243", "blockNumber": "0x20", "from": "0xfrom",
                "to": "0xto"
            },
            "eth_getTransactionReceipt": {
                "transactionHash": self.TXID, "blockNumber": "0x20", "status": "0x1"
            }
        })
        result = transaction(self.config(), "polygon", self.TXID, opener=remote)
        self.assertTrue(result["found"])
        self.assertEqual(result["inputBytes"], 3)
        self.assertEqual(result["execution"], "success")
        self.assertEqual(len(remote.requests), 2)

    def test_missing_transaction(self):
        remote = FakeHTTP({"eth_getTransactionByHash": None})
        self.assertFalse(transaction(self.config(), "polygon", self.TXID, opener=remote)["found"])

    def test_wrong_transaction_chain_rejected(self):
        remote = FakeHTTP({"eth_getTransactionByHash": {
            "hash": self.TXID, "chainId": "0x1", "value": "0x0",
            "input": "0x", "blockNumber": None}})
        with self.assertRaisesRegex(ValueError, "chainId mismatch"):
            transaction(self.config(), "polygon", self.TXID, opener=remote)

    def test_missing_key_rejected_before_request(self):
        cfg = self.config()
        cfg["ledgers"]["polygon"]["providers"]["etherscan"]["apiKey"] = ""
        remote = FakeHTTP({})
        with self.assertRaisesRegex(ValueError, "API key not configured"):
            status(cfg, opener=remote)
        self.assertEqual(remote.requests, [])

    def test_wrong_tx_hash_rejected_before_request(self):
        remote = FakeHTTP({})
        with self.assertRaisesRegex(ValueError, "32-byte"):
            transaction(self.config(), "polygon", "0xdeadbeef", opener=remote)
        self.assertEqual(remote.requests, [])

    def test_write_methods_rejected(self):
        remote = FakeHTTP({})
        with self.assertRaisesRegex(ValueError, "Disallowed"):
            proxy_read(self.config()["ledgers"]["polygon"]["providers"]["etherscan"],
                       137, "eth_sendRawTransaction", opener=remote)
        self.assertEqual(remote.requests, [])

    def test_http_403_does_not_leak_key(self):
        remote = FakeHTTP(error=HTTPError("https://example.test/?apikey=fake-private-test-key",
                                          403, "Forbidden", {}, None))
        with self.assertRaises(ValueError) as issue:
            status(self.config(), opener=remote)
        self.assertIn("403", str(issue.exception))
        self.assertNotIn("fake-private-test-key", str(issue.exception))

    def test_api_error_does_not_echo_remote_message(self):
        class ErrorHTTP(FakeHTTP):
            def open(self, request, timeout):
                self.requests.append(request)
                return io.BytesIO(json.dumps({
                    "status": "0", "message": "NOTOK",
                    "result": "Secret: fake-private-test-key"
                }).encode("utf-8"))
        with self.assertRaises(ValueError) as issue:
            status(self.config(), opener=ErrorHTTP())
        self.assertNotIn("fake-private-test-key", str(issue.exception))

    def test_receipt_block_mismatch_rejected(self):
        remote = FakeHTTP({
            "eth_getTransactionByHash": {
                "hash": self.TXID, "value": "0x0", "input": "0x",
                "blockNumber": "0x20"
            },
            "eth_getTransactionReceipt": {
                "transactionHash": self.TXID, "blockNumber": "0x21", "status": "0x1"
            }
        })
        with self.assertRaisesRegex(ValueError, "receipt block mismatch"):
            transaction(self.config(), "polygon", self.TXID, opener=remote)


if __name__ == "__main__":
    unittest.main()
