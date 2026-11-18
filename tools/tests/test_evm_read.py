"""Offline tests for the read-only EVM adapter. No external RPC calls."""
import hashlib
import io
import json
import unittest

from tools.evm_read import rpc_read, status, transaction


class FakeRPC:
    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request)
        body = json.loads(request.data)
        method = body["method"]
        assert method in self.responses, "Unexpected RPC method: " + method
        answer = self.responses[method]
        return io.BytesIO(json.dumps({"jsonrpc": "2.0", "id": 1,
                                       "result": answer}).encode("utf-8"))

    @property
    def methods(self):
        return [json.loads(req.data)["method"] for req in self.requests]


class ReadEVMTests(unittest.TestCase):
    HASH = "0x" + "a" * 64

    def config(self, endpoint=None):
        return {"ledgers": {"polygon": {
            "family": "evm", "chainId": 137,
            "read": endpoint or {"url": "https://rpc.example.test"}
        }}}

    def test_chain_status(self):
        remote = FakeRPC({"eth_chainId": "0x89", "eth_blockNumber": "0x10"})
        output = status(self.config(), "polygon", opener=remote)
        self.assertEqual(output, {"ledger": "polygon", "chainId": 137, "latestBlock": 16})
        self.assertEqual(remote.methods, ["eth_chainId", "eth_blockNumber"])

    def test_refuse_wrong_chain(self):
        remote = FakeRPC({"eth_chainId": "0x1", "eth_blockNumber": "0x10"})
        with self.assertRaisesRegex(ValueError, "chain mismatch"):
            status(self.config(), "polygon", opener=remote)
        self.assertEqual(remote.methods, ["eth_chainId"])

    def test_pending_transaction(self):
        remote = FakeRPC({
            "eth_chainId": "0x89",
            "eth_getTransactionByHash": {
                "hash": self.HASH, "chainId": "0x89", "from": "0xfrom",
                "to": "0xto", "value": "0x0", "blockNumber": None,
                "input": "0x414243",
            },
        })
        result = transaction(self.config(), "polygon", self.HASH, opener=remote)
        self.assertTrue(result["found"])
        self.assertEqual(result["execution"], "pending")
        self.assertEqual(result["inputBytes"], 3)
        self.assertEqual(result["inputSha256"], hashlib.sha256(b"ABC").hexdigest())
        self.assertEqual(remote.methods, ["eth_chainId", "eth_getTransactionByHash"])

    def test_mined_transaction_and_receipt(self):
        remote = FakeRPC({
            "eth_chainId": "0x89",
            "eth_getTransactionByHash": {
                "hash": self.HASH, "from": "0xfrom", "to": "0xto",
                "value": "0x100", "blockNumber": "0x10", "input": "0x"
            },
            "eth_getTransactionReceipt": {
                "transactionHash": self.HASH, "blockNumber": "0x10", "status": "0x1"
            },
        })
        result = transaction(self.config(), "polygon", self.HASH, opener=remote)
        self.assertEqual(result["execution"], "success")
        self.assertEqual(result["blockNumber"], 16)
        self.assertEqual(result["valueWei"], 256)
        self.assertEqual(remote.methods[-1], "eth_getTransactionReceipt")

    def test_missing_transaction(self):
        remote = FakeRPC({"eth_chainId": "0x89", "eth_getTransactionByHash": None})
        result = transaction(self.config(), "polygon", self.HASH, opener=remote)
        self.assertFalse(result["found"])

    def test_bad_transaction_hash_is_rejected_before_request(self):
        remote = FakeRPC({})
        with self.assertRaisesRegex(ValueError, "32-byte transaction hash"):
            transaction(self.config(), "polygon", "0xdeadbeef", opener=remote)
        self.assertEqual(remote.methods, [])

    def test_mismatched_receipt_rejected(self):
        remote = FakeRPC({
            "eth_chainId": "0x89",
            "eth_getTransactionByHash": {
                "hash": self.HASH, "value": "0x0",
                "blockNumber": "0x10", "input": "0x"
            },
            "eth_getTransactionReceipt": {
                "transactionHash": self.HASH, "blockNumber": "0x11", "status": "0x1"
            },
        })
        with self.assertRaisesRegex(ValueError, "receipt blockNumber mismatch"):
            transaction(self.config(), "polygon", self.HASH, opener=remote)

    def test_private_key_header(self):
        endpoint = {"url": "https://rpc.example.test", "apiKey": "test-private",
                    "apiKeyHeader": "X-Api-Key"}
        remote = FakeRPC({"eth_chainId": "0x89", "eth_blockNumber": "0x4"})
        status(self.config(endpoint), "polygon", opener=remote)
        headers = dict(remote.requests[0].header_items())
        self.assertEqual(headers["X-api-key"], "test-private")
        self.assertNotIn("test-private", remote.requests[0].full_url)

    def test_key_without_header_cannot_leak(self):
        endpoint = {"url": "https://rpc.example.test", "apiKey": "test-private"}
        with self.assertRaisesRegex(ValueError, "apiKeyHeader"):
            rpc_read(endpoint, "eth_chainId", opener=FakeRPC({}))

    def test_disallow_signing_and_broadcast(self):
        with self.assertRaisesRegex(ValueError, "Disallowed"):
            rpc_read({"url": "https://rpc.example.test"},
                     "eth_sendRawTransaction", ["0x0"], opener=FakeRPC({}))

    def test_invalid_family(self):
        config = self.config()
        config["ledgers"]["polygon"]["family"] = "utxo"
        with self.assertRaisesRegex(ValueError, "not an EVM"):
            status(config, "polygon", opener=FakeRPC({}))


if __name__ == "__main__":
    unittest.main()
