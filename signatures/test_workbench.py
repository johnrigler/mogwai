"""Synthetic signing identities only; never reads the operator's home records."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import logging
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from asn1crypto import keys, x509 as asn1x509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from pyhanko.pdf_utils import generic
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils.writer import PageObject, PdfFileWriter
from pyhanko.sign import signers
from pyhanko.sign.fields import MDPPerm
from pyhanko_certvalidator.registry import SimpleCertificateStore

logging.getLogger("pyhanko").setLevel(logging.CRITICAL)

spec = importlib.util.spec_from_file_location("workbench", Path(__file__).with_name("workbench.py"))
workbench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workbench)


class WorkbenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key, cls.cert, cls.pem = cls.make_identity("Synthetic signer")
        cls.other_key, cls.other_cert, cls.other_pem = cls.make_identity("Synthetic signer")

    @staticmethod
    def make_identity(name):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
        start = datetime.now(timezone.utc) - timedelta(days=1)
        cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
                .public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(start).not_valid_after(start + timedelta(days=30))
                .add_extension(x509.KeyUsage(True, True, False, False, False, False, False, False, False), critical=True)
                .sign(key, hashes.SHA256()))
        return key, cert, cert.public_bytes(serialization.Encoding.PEM).decode()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.db = self.root / "home.sqlite3"
        self.env = patch.dict(os.environ, {"MOGWAI_HOME_DB": str(self.db)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def data(self, **values):
        return dict(certificate_pem=self.pem, label="Example signer", **values)

    def signed_pdf(self, original=None, output=None, field="First", certify=False):
        if original is None:
            original = self.root / "original.pdf"
            writer = PdfFileWriter()
            stream = writer.add_object(generic.StreamObject(stream_data=b"% SYNTHETIC-ORIGINAL-CONTENT\n"))
            writer.insert_page(PageObject(stream, (0, 0, 300, 300)))
            with original.open("wb") as destination:
                writer.write(destination)
        output = output or self.root / "signed.pdf"
        private = self.key.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        signer = signers.SimpleSigner(asn1x509.Certificate.load(self.cert.public_bytes(serialization.Encoding.DER)),
                                      keys.PrivateKeyInfo.load(private), SimpleCertificateStore())
        with original.open("rb") as source, output.open("wb") as destination:
            signers.sign_pdf(IncrementalPdfFileWriter(source), signers.PdfSignatureMetadata(
                field_name=field, certify=certify, docmdp_permissions=MDPPerm.NO_CHANGES if certify else MDPPerm.FILL_FORMS),
                             signer=signer, output=destination)
        return output

    def test_read_does_not_create_home_database(self):
        self.assertEqual(workbench.identities(), [])
        self.assertFalse(self.db.exists())

    def test_public_export_excludes_home_fields_and_local_trust(self):
        with sqlite3.connect(self.db) as db:
            db.execute("CREATE TABLE mogwai_people (ssn TEXT)")
            db.execute("INSERT INTO mogwai_people VALUES ('SYNTHETIC-PRIVATE-VALUE')")
        cert = workbench.remember(self.data(evidence="Private discussion", publication="ipfs://example-certificate"))
        public = workbench.export_public(cert["certificate_sha256"])
        self.assertTrue(public["self_signed"])
        self.assertNotIn("Private discussion", json.dumps(public))
        self.assertNotIn("SYNTHETIC-PRIVATE-VALUE", json.dumps(public))
        self.assertNotIn("status", public)
        self.assertEqual(self.db.stat().st_mode & 0o777, 0o600)
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute("SELECT ssn FROM mogwai_people").fetchone()[0], "SYNTHETIC-PRIVATE-VALUE")

    def test_private_key_and_unconfirmed_trust_rejected_before_writes(self):
        private = self.key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
        with self.assertRaises(ValueError):
            workbench.remember(dict(certificate_pem=self.pem + private, label="Bad export"))
        with self.assertRaises(ValueError):
            workbench.remember(self.data(status="verified", evidence="Checked", confirmed_fingerprint="0" * 64))
        with self.assertRaises(ValueError):
            workbench.remember(self.data(status="verified", evidence=""))
        self.assertFalse(self.db.exists())

    def test_identity_pin_is_not_a_name_match_and_revocation_is_retained(self):
        actual = workbench.certificate_info(self.pem)["certificate_sha256"]
        workbench.remember(self.data(status="verified", evidence="Fingerprint compared in person", confirmed_fingerprint=actual))
        workbench.remember(dict(certificate_pem=self.other_pem, label="Example signer"))
        rows = workbench.identities()
        self.assertEqual(len(rows), 2)
        self.assertEqual(next(row for row in rows if row["fingerprint"] == actual)["status"], "verified")
        workbench.remember(self.data(status="revoked", evidence="Synthetic key compromise"))
        with sqlite3.connect(self.db) as db:
            self.assertEqual([row[0] for row in db.execute("SELECT status FROM mogwai_signing_events WHERE fingerprint=? ORDER BY id", (actual,))], ["verified", "revoked"])

    def test_original_signature_tampering_and_second_signature(self):
        signed = self.signed_pdf()
        original_bytes = signed.read_bytes()
        report = workbench.inspect_pdf(signed)
        signature = report["signatures"][0]
        self.assertTrue(signature["intact"])
        self.assertTrue(signature["cryptographically_valid"])
        self.assertEqual(signature["coverage"], "ENTIRE_FILE")
        self.assertTrue(signature["permitted_changes"])
        self.assertFalse(signature["certificate_chain_trusted"])
        self.assertEqual(signature["local_identity"]["status"], "unknown")
        workbench.remember(self.data(status="verified", evidence="Direct comparison", confirmed_fingerprint=signature["certificate_sha256"]))
        self.assertEqual(workbench.inspect_pdf(signed)["signatures"][0]["local_identity"]["status"], "verified")
        tampered = self.root / "tampered.pdf"
        tampered.write_bytes(original_bytes.replace(b"SYNTHETIC-ORIGINAL-CONTENT", b"SYNTHETIC-MODIFIED-CONTENT"))
        self.assertFalse(workbench.inspect_pdf(tampered)["signatures"][0]["intact"])
        double = self.signed_pdf(signed, self.root / "double.pdf", "Second")
        both = workbench.inspect_pdf(double)["signatures"]
        self.assertEqual(len(both), 2)
        self.assertTrue(all(row["intact"] and row["cryptographically_valid"] for row in both))
        self.assertEqual(both[0]["coverage"], "ENTIRE_REVISION")
        self.assertEqual(signed.read_bytes(), original_bytes)

    def test_sign_command_preserves_original_and_refuses_overwrite(self):
        source = self.signed_pdf()
        original = source.read_bytes()
        secret = self.root / "secret.p12"
        secret.write_bytes(pkcs12.serialize_key_and_certificates(b"Synthetic", self.key, self.cert, None,
                                                              serialization.BestAvailableEncryption(b"synthetic-only")))
        destination = self.root / "second.pdf"
        with patch.object(workbench.getpass, "getpass", return_value="synthetic-only"):
            workbench.sign_pdf(source, destination, secret)
            with self.assertRaises(FileExistsError):
                workbench.sign_pdf(source, destination, secret)
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(len(workbench.inspect_pdf(destination)["signatures"]), 2)

    def test_cli_json_and_symlink_database_rejection(self):
        result = subprocess.run([sys.executable, str(Path(workbench.__file__)), "request"],
                                input='{"action":"list"}', capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), [])
        target = self.root / "target.sqlite3"
        target.touch()
        self.db.symlink_to(target)
        with self.assertRaises(ValueError):
            workbench.identities()

    def test_certification_lock_blocks_another_signature(self):
        source = self.signed_pdf(certify=True)
        secret = self.root / "secret.p12"
        secret.write_bytes(pkcs12.serialize_key_and_certificates(b"Synthetic", self.key, self.cert, None,
                                                              serialization.BestAvailableEncryption(b"synthetic-only")))
        destination = self.root / "blocked.pdf"
        with patch.object(workbench.getpass, "getpass", return_value="synthetic-only"):
            with self.assertRaises(Exception):
                workbench.sign_pdf(source, destination, secret)
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
