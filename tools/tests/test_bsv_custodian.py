import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bsv_custodian


class CustodianTest(unittest.TestCase):
    def test_chronology_and_missing_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = root / "transactions/bsv"
            raw.mkdir(parents=True)
            db = sqlite3.connect(":memory:")
            db.executescript("""
                CREATE TABLE blocks(height INTEGER PRIMARY KEY,time INTEGER);
                CREATE TABLE transactions(height INTEGER,tx_index INTEGER,txid TEXT,
                bytes INTEGER,data_bytes INTEGER,data_complete INTEGER,selected INTEGER,
                summary TEXT,raw TEXT);
                INSERT INTO blocks VALUES(100,1234567890),(200,0);
            """)
            for height, pos, char in [(100,0,"a"),(200,0,"b"),(200,1,"c")]:
                txid = char * 64
                db.execute("INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?,?)",
                           (height,pos,txid,100,50,1,1,"{}","{}"))
                if char != "c":
                    (raw / (txid + ".json")).write_text(json.dumps({"txid":txid}))
            db.commit()
            report, rows = bsv_custodian.audit(db,root,root/"bsv/custodian",10,10)
            self.assertEqual([r["txid"] for r in rows], ["b"*64,"a"*64])
            self.assertEqual(report["undated"],2)
            self.assertEqual(report["archive_files_missing_in_examined_rows"],1)
            self.assertEqual(report["selected"],3)
            self.assertEqual(rows[0]["summary"]["blockTime"],0)


if __name__ == "__main__":
    unittest.main()
