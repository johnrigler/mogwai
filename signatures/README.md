# Signing identities

Mogwai can inspect embedded PDF signatures without Adobe, record independently
checked certificate fingerprints in the home database, export public signing
identities, and add a PDF signature using an existing PKCS#12 identity.
It uses pyHanko, not an Adobe service. No signing identity is generated for the
operator and no real person's certificate is preinstalled as trusted.

## Setup and local GUI

```bash
python3 -m venv "$HOME/.venvs/mogwai-signatures"
"$HOME/.venvs/mogwai-signatures/bin/python" -m pip install -r "$HOME/mogwai/signatures/requirements.txt"
cd "$HOME/daisy_2026"
php -S 127.0.0.1:39692 -t . "$HOME/mogwai/sbshell/cruff/index.php"
```

Open the hamburger menu → **Signing identities**, or
`http://127.0.0.1:39692/?mogwai-signatures=1`.
PHP needs `proc_open`; set `MOGWAI_SIGNATURE_PYTHON` to an absolute Python
executable if using a different environment. The home DB remains
`~/catalog.sqlite3`, or the existing `MOGWAI_HOME_DB` override. It must be
outside the served archive. The GUI requires a direct loopback connection,
checks CSRF and Origin on POST, uses no-store responses and executes Python
with an argument array, without a shell. PDF uploads exist only for the request;
the original on disk is unchanged. PHP's upload limit may be below the 25 MB
workbench limit; adjust `upload_max_filesize` and `post_max_size` if necessary.

Choose the **original PDF**, not a screenshot or a PDF printed from page
images. Each embedded document signature reports its certificate subject and
issuer, certificate and public-key SHA-256 fingerprints, validity dates,
verified self-signature if present, signed coverage, cryptographic integrity,
and permitted subsequent changes. Timestamp tokens are included in pyHanko's
validation details when applicable; standalone document timestamp signatures
are not listed as identity cards.

Copy the extracted public PEM certificate into the identity form. A record
starts **observed**. To mark it **verified**, supply the full certificate
fingerprint you independently compared and describe how and when you checked
it. A name, email address or publication URL alone is not identity proof.
Use **revoked** to withdraw local trust, with a reason. Assessments are the
operator's records, not an external identity verification service.

`mogwai_signing_identities` and the append-only `mogwai_signing_events` audit
table share the home DB with existing records without replacing other tables.
The DB is owner-only (`0600`), not encrypted. Reads do not create a missing DB.
Private signing keys and passwords are never stored there or accepted by the
certificate form. New certificate fingerprints create separate records;
renewal/rotation never silently inherits a previous certificate's trust.
The public-key fingerprint helps compare keys across renewed certificates,
but does not automatically authorize a new certificate.

## Publication and trust

**Export public certificate record** downloads a JSON record containing only
the public PEM certificate, its DER SHA-256 fingerprint, its SPKI public-key
SHA-256 fingerprint, certificate metadata, identity label and publication
reference. It deliberately excludes local trust assessments/evidence and all
home profile fields. You can publish that record on GitHub, your own site or
IPFS and put its location in the publication field. The tool does not upload
anything, fetch those references or automatically trust imported information.
The JSON label/location are descriptive metadata, not signed identity claims.

This is analogous to publishing a PGP public key: availability lets others
find the key; independently checking the fingerprint binds it to the person.
PDF signing uses X.509 certificates, not OpenPGP keys. Mogwai does not pretend
the two key formats are interchangeable or implement an OpenPGP web of trust.
A self-signed certificate can be useful after its fingerprint is checked.
An **unknown issuer** only means no trusted certificate chain was established;
it does not by itself prove self-signing or fraud.

The inspector intentionally uses **no trusted certificate roots** and disables
network fetching. It reports local fingerprint matches separately from PKI
trust. Thus `certificate_chain_trusted` is not expected to become true merely
because the user pinned an identity. No online OCSP/CRL revocation check is
performed. A local verified pin does not override invalid signature bytes,
expired certificates, prohibited modifications or timestamp problems. Read
all these results separately; this is not a legal conclusion about a document.
The report's `checked_at` is the local computer's time, not a trusted timestamp.

The NCS welcome packet previously passed Poppler's integrity check with an
unknown certificate issuer. Its certificate is not automatically enrolled or
trusted here. The corporate-use signature's position does not establish what
the signer authorized or whether any disputed charge is correct.

## Command line

Use the same Python interpreter from setup:

```bash
"$HOME/.venvs/mogwai-signatures/bin/python" "$HOME/mogwai/signatures/workbench.py" inspect \
  "$HOME/daisy_2026/42/firmus-ncs/Centro/agreement.pdf"

"$HOME/.venvs/mogwai-signatures/bin/python" "$HOME/mogwai/signatures/workbench.py" remember \
  public-cert.pem --label 'Example signer' --publication 'https://example.org/signing.json'

"$HOME/.venvs/mogwai-signatures/bin/python" "$HOME/mogwai/signatures/workbench.py" list
```

`remember` optionally takes `--status verified --confirmed-fingerprint FULL_SHA256
--evidence 'How and when the fingerprint was independently checked'`.
`export FULL_SHA256` writes the public JSON record to stdout. Redirect that
specific export to a publication file; don't publish the home database or
`list` output, which includes your private assessment notes.

To add an **invisible certificate signature** with your existing encrypted
PKCS#12/PFX signing identity:

```bash
"$HOME/.venvs/mogwai-signatures/bin/python" "$HOME/mogwai/signatures/workbench.py" sign \
  original.pdf signed-copy.pdf --p12 "$HOME/signing/identity.p12"

"$HOME/.venvs/mogwai-signatures/bin/python" "$HOME/mogwai/signatures/workbench.py" inspect signed-copy.pdf
```

The password is prompted at the terminal, never supplied in argv or a URL.
The tool writes an incremental PDF revision, refuses to overwrite a file,
retains the original, and respects signing restrictions enforced by pyHanko.
Inspect **every signature and later modification** in the output afterward.
The signature records the existing certificate identity, not a handwritten
mark or an assertion about why you signed. Use a separately worded statement
identifying the original file's hash when you need to attest only to receipt
or retention. PDF certification restrictions can prevent another signature.

There is no key-generation UI, automatic publication, blockchain inscription,
or offline IPFS-browser PDF validation in this first workbench. The tools live
in Mogwai; public exported records are ordinary static JSON/PEM suitable for
IPFS. Private keys remain in their existing local keystore. Certificate
fingerprints are not blockchain addresses.

## Checks and format references

```bash
python -m unittest discover -s signatures -p test_workbench.py -v
MOGWAI_SIGNATURE_PYTHON=python SB_PHP=php node signatures/test-http.mjs
```

Checks generate synthetic identities and PDFs in temporary directories and
use isolated home databases. They cover altered bytes, multiple signatures,
certificate pinning, key rotation/name collisions, revocation history,
public-only exports and the local GUI boundary.

- [pyHanko signing](https://docs.pyhanko.eu/en/stable/cli-guide/signing.html)
- [pyHanko validation and trust](https://docs.pyhanko.eu/en/stable/cli-guide/validation.html)
- [Adobe self-signed digital IDs](https://helpx.adobe.com/acrobat/desktop/protect-documents/manage-digital-ids/create-self-signed-id.html)
- [GnuPG fingerprints](https://wiki.gnupg.org/Fingerprint)
