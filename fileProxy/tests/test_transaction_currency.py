"""Query currency filters must not turn Litecoin files into BSV records."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fileproxy import server


class TransactionCurrencyTests(unittest.TestCase):
    def test_filesystem_filter_uses_the_file_currency(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i, coin in enumerate(("litecoin", "bsv", "bsvtestnet"), 1):
                path = root / "data" / "transactions" / coin / (f"{i:064x}" + ".json")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"txid": f"{i:064x}"}))
            with patch.object(server.chisel, "ROOT", root), patch.object(server.chisel, "ALLOWED_ROOTS", [root]), patch.object(server.chisel, "EXTRA_DATA_ROOTS", []), patch.object(server.chisel, "load_chisel_indexer", return_value=None):
                all_rows = server.chisel.list_txids()
                self.assertEqual(len(all_rows), 3)
                bsv = server.chisel.list_txids("bsv")
                self.assertEqual([r["txid"] for r in bsv], [f"{2:064x}"])
                self.assertTrue(all("/bsv/" in r["path"] and r["coin"] == "bsv" for r in bsv))
                self.assertEqual([r["txid"] for r in server.chisel.list_txids("litecoin")], [f"{1:064x}"])
                self.assertEqual(len(server.chisel.list_txids("bsvTestnet")), 1)


if __name__ == "__main__":
    unittest.main()
