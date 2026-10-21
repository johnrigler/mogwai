#!/usr/bin/env python3
"""Local PDF signatures and explicitly checked public signing identities."""
import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import urlparse


def now():
    return datetime.now(timezone.utc).isoformat()


def certificate_info(pem):
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    if not isinstance(pem, str) or len(pem) > 65536 or not re.fullmatch(
        r"\s*-----BEGIN CERTIFICATE-----[A-Za-z0-9+/=\s]+-----END CERTIFICATE-----\s*", pem
    ):
        raise ValueError("Supply one public PEM certificate, without private keys or extra data.")
    cert = x509.load_pem_x509_certificate(pem.encode("ascii"))
    der = cert.public_bytes(serialization.Encoding.DER)
    key = cert.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    self_signed = False
    if cert.subject == cert.issuer:
        try:
            cert.verify_directly_issued_by(cert)
            self_signed = True
        except (ValueError, TypeError):
            pass
        except Exception:
            # Unsupported signature algorithms do not establish self-signing.
            self_signed = None
    return dict(certificate_sha256=hashlib.sha256(der).hexdigest(),
                public_key_sha256=hashlib.sha256(key).hexdigest(),
                subject=cert.subject.rfc4514_string(), issuer=cert.issuer.rfc4514_string(),
                not_before=cert.not_valid_before_utc.isoformat(), not_after=cert.not_valid_after_utc.isoformat(),
                self_signed=self_signed,
                certificate_pem=cert.public_bytes(serialization.Encoding.PEM).decode("ascii"))


def fingerprint(value):
    value = re.sub(r"[\s:]", "", value).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("Use the full SHA-256 certificate fingerprint (64 hexadecimal digits).")
    return value


def database(write=False):
    path = Path(os.environ.get("MOGWAI_HOME_DB") or Path.home() / "catalog.sqlite3").expanduser()
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("Use an absolute home database path, not a symlink.")
    if not write and not path.exists():
        return None
    mask = os.umask(0o077)
    try:
        if write:
            if path.exists():
                path.chmod(0o600)
            db = sqlite3.connect(path, timeout=3)
            path.chmod(0o600)
            db.executescript("""
                CREATE TABLE IF NOT EXISTS mogwai_signing_identities (
                    fingerprint TEXT PRIMARY KEY, certificate TEXT NOT NULL,
                    label TEXT NOT NULL, publication TEXT NOT NULL, status TEXT NOT NULL,
                    evidence TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS mogwai_signing_events (
                    id INTEGER PRIMARY KEY, fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL, evidence TEXT NOT NULL, recorded_at TEXT NOT NULL
                );
            """)
        else:
            db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=3)
        db.row_factory = sqlite3.Row
        return db
    finally:
        os.umask(mask)


def identities():
    db = database()
    if db is None:
        return []
    try:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='mogwai_signing_identities' AND type='table'").fetchone():
            return []
        return [dict(row) for row in db.execute("SELECT * FROM mogwai_signing_identities ORDER BY label,fingerprint")]
    finally:
        db.close()


def remember(data):
    cert = certificate_info(data.get("certificate_pem", ""))
    label = data.get("label", "").strip()
    publication = data.get("publication", "").strip()
    evidence = data.get("evidence", "").strip()
    status = data.get("status", "observed")
    if not label or len(label) > 200 or len(evidence) > 2000 or len(publication) > 2000:
        raise ValueError("Supply a label (up to 200 characters); source and evidence are limited to 2000 characters.")
    if publication and urlparse(publication).scheme not in ("https", "ipfs"):
        raise ValueError("Use an https:// or ipfs:// publication reference.")
    if status not in ("observed", "verified", "revoked"):
        raise ValueError("Choose observed, verified or revoked.")
    if status in ("verified", "revoked") and not evidence:
        raise ValueError("Record how you checked the identity, or why you revoked local trust.")
    if status == "verified" and fingerprint(data.get("confirmed_fingerprint", "")) != cert["certificate_sha256"]:
        raise ValueError("The independently checked fingerprint does not match this certificate.")
    db = database(True)
    try:
        with db:
            db.execute("""INSERT INTO mogwai_signing_identities VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(fingerprint) DO UPDATE SET label=excluded.label,
                publication=excluded.publication,status=excluded.status,
                evidence=excluded.evidence,updated_at=excluded.updated_at""",
                (cert["certificate_sha256"], cert["certificate_pem"], label, publication, status, evidence, now()))
            db.execute("INSERT INTO mogwai_signing_events (fingerprint,status,evidence,recorded_at) VALUES (?,?,?,?)",
                       (cert["certificate_sha256"], status, evidence, now()))
    finally:
        db.close()
    return cert


def export_public(value):
    value = fingerprint(value)
    row = next((row for row in identities() if row["fingerprint"] == value), None)
    if row is None:
        raise ValueError("That certificate is not in the local registry.")
    # An allowlist: no home profiles, local evidence, trust claims or database path.
    return dict(format="mogwai-public-certificate-v1", label=row["label"],
                publication=row["publication"], **certificate_info(row["certificate"]))


def inspect_pdf(path):
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko_certvalidator import ValidationContext
    path = Path(path)
    known = {row["fingerprint"]: row for row in identities()}
    report = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), checked_at=now(),
                  validation_policy="Offline, no trusted roots supplied; local identity pins are reported separately.",
                  revocation="No online revocation check; local revoked status is a separate record.", signatures=[])
    with path.open("rb") as stream:
        reader = PdfFileReader(stream)
        for signature in reader.embedded_regular_signatures:
            cert = x509.load_der_x509_certificate(signature.signer_cert.dump())
            item = dict(field=signature.field_name, **certificate_info(
                cert.public_bytes(serialization.Encoding.PEM).decode("ascii")))
            row = known.get(item["certificate_sha256"])
            item["local_identity"] = ({key: row[key] for key in ("label", "publication", "status", "evidence", "updated_at")}
                                      if row else {"status": "unknown"})
            try:
                context = ValidationContext(trust_roots=[], allow_fetching=False)
                status = validate_pdf_signature(signature, signer_validation_context=context,
                                                ts_validation_context=context)
                item.update(intact=bool(status.intact), cryptographically_valid=bool(status.valid),
                            coverage=status.coverage.name if status.coverage else "UNKNOWN",
                            modification_level=status.modification_level.name if status.modification_level else "UNKNOWN",
                            permitted_changes=bool(status.docmdp_ok), certificate_chain_trusted=bool(status.trusted),
                            validation_details=status.pretty_print_details())
            except Exception as error:
                item.update(intact=None, cryptographically_valid=None, coverage="UNKNOWN",
                            permitted_changes=None, error=str(error))
            report["signatures"].append(item)
    return report


def sign_pdf(source, destination, p12):
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers
    if Path(source).resolve() == Path(destination).resolve():
        raise ValueError("Keep the original; choose a separate output PDF.")
    signer = signers.SimpleSigner.load_pkcs12(p12, passphrase=getpass.getpass("Signing identity password: ").encode())
    if signer is None:
        raise ValueError("Could not unlock the signing identity.")
    # x mode refuses existing files. The original and earlier signed revisions stay intact.
    created = False
    try:
        with open(source, "rb") as original, open(destination, "xb") as output:
            created = True
            writer = IncrementalPdfFileWriter(original)
            metadata = signers.PdfSignatureMetadata(field_name="Mogwai-" + os.urandom(8).hex())
            signers.sign_pdf(writer, metadata, signer=signer, output=output)
    except Exception:
        if created:
            Path(destination).unlink(missing_ok=True)
        raise
    return dict(output=str(destination), note="Signature added. Inspect the output to check all signatures and permitted changes.")


def request(data):
    action = data.get("action")
    if action == "list":
        return identities()
    if action == "inspect":
        return inspect_pdf(data["path"])
    if action == "remember":
        return remember(data)
    if action == "export":
        return export_public(data["fingerprint"])
    raise ValueError("Unknown workbench action.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("request", help="JSON on stdin for the local PHP workbench")
    sub.add_parser("list", help="List locally recorded signing identities")
    sub.add_parser("inspect", help="Verify an original PDF and compare identity pins").add_argument("pdf")
    export = sub.add_parser("export", help="Export a public certificate record, without local trust notes")
    export.add_argument("fingerprint")
    save = sub.add_parser("remember", help="Record a public PEM certificate")
    save.add_argument("certificate")
    save.add_argument("--label", required=True)
    save.add_argument("--publication", default="")
    save.add_argument("--status", choices=["observed", "verified", "revoked"], default="observed")
    save.add_argument("--evidence", default="")
    save.add_argument("--confirmed-fingerprint", default="")
    sign = sub.add_parser("sign", help="Add a certificate signature using an existing password-protected PKCS#12 identity")
    sign.add_argument("source")
    sign.add_argument("destination")
    sign.add_argument("--p12", required=True)
    args = parser.parse_args()
    try:
        if args.command == "request":
            result = request(json.load(sys.stdin))
        elif args.command == "inspect":
            result = inspect_pdf(args.pdf)
        elif args.command == "list":
            result = identities()
        elif args.command == "export":
            result = export_public(args.fingerprint)
        elif args.command == "remember":
            data = vars(args).copy()
            data["certificate_pem"] = Path(args.certificate).read_text()
            result = remember(data)
        else:
            result = sign_pdf(args.source, args.destination, args.p12)
        print(json.dumps(result, indent=2))
    except Exception as error:
        print(json.dumps({"error": str(error)}))
        return 1
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.CRITICAL)
    sys.exit(main())
