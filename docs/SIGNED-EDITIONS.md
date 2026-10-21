# Signed editions and portable identities — October 20, 2026

This records the discussion and next implementation work. It does not claim
that the proposed viewer integration, key generation, wallet binding or QR
verification interface is implemented. Resume from
[Daisy week 43](https://github.com/johnrigler/daisy_2026/blob/main/43/1_01.html).

## Where the parts belong

- Commons holds reusable public arguments and source references, with no
  paragraph-length editorial limit. Working documents may be HTML and use
  SB Shell's ordered parts. Preserve exact, immutable published versions.
- Daisy holds working sources, drafts, chronological records and the current
  handoff. CertLedger is the finished case work-product repository: completed
  PDFs, either copied byte-for-byte or referenced back to exact Daisy editions.
  Customer/private access boundaries remain separate. No migration is implied.
- SB Shell, maintained here, assembles readable web and US Letter print views.
- Mogwai supplies local inspection, identity records and signing tools.
- Chisel prepares/signs chain transactions that can commit a document hash
  or a reference to an exact published record. This is not Litecoin-specific.

CertLedger's final product combines the selected Commons argument versions
with Daisy case evidence. It assumes artifacts may be on IPFS and retains
their CIDs, byte hashes and exact ledger references. CertLedger is product:
IPFS operations, signing and the operational ledger verifier belong in Mogwai,
not another tool suite copied into CertLedger. Product pages can display
recorded results or link to the tool.

The proposed global timestamp/announcement transaction links elements through
its OP_RETURN payload and labeled unspendable outputs, using Chisel's declared
encoding. Preserve the network, tx ID, output indexes, actual payload and
mapping to the source versions/final artifacts or manifest. Do not fabricate
outputs, claim broadcast or exceed the chosen encoding's payload capacity.
Block inclusion anchors the commitment in public order/time; it is not an
exact document-creation timestamp or proof of the document's assertions.

The later Mogwai verifier should retrieve the actual referenced Litecoin
transaction and compare its decoded commitment with the finished PDF or
committed manifest. Report network, source, block/confirmation state and byte
comparison separately from PDF signatures and identity trust. A stored tx ID
is not an independently checked ledger match. This tool integration is planned,
not supplied by this documentation.

## Author, print, sign, then commit

1. Author the full argument in HTML, with sources, scope and review status.
   Preserve any referenced Commons statements by their exact version/CID.
2. Use Chrome Print to PDF to create a publication edition. This workflow
   still works; PDF signing does not require replacing the HTML authoring path.
3. Sign the resulting PDF using a compatible certificate identity, retaining
   the unsigned source and inspecting every signature and revision afterward.
4. Hash the completed signed PDF. Signing changes bytes, so a pre-signing
   digest is not the identity of the signed edition. A further signature or
   reprint is another version with another full-file digest.
5. Record the exact final digest, source references and actual chain/tx ID
   externally. A transaction signature authenticates that transaction;
   publishing somebody else's PDF hash does not prove that person signed it.

Do not insert a final PDF's own hash, CID or resulting transaction ID into
that same PDF and expect its bytes to stay identical. A QR placed before
signing can use a preassigned reference. Final hashes/CIDs/transaction IDs can
be recorded in a separate signed manifest, registration sheet or receipt.
Never describe an intended transaction or dispatch as completed.

The embedded PDF signature and external wallet/transaction signature cover
different objects. Record the object and the attestation explicitly: authorship,
approval, receipt, retention or publication are different assertions. Neither
signature establishes that the argument is true or legally authoritative.

## A common secret, distinct key formats

A typical raw secp256k1 private scalar is 32 bytes, displayed as 64 hex digits.
WIF is an encoding, not a different secret. Bitcoin, Litecoin, DigiByte and
EVM use relevant secp256k1 signing mechanisms but different address, message
and transaction formats. Do not interchange their signature formats blindly.
An HD seed/master extended key and one raw private scalar are distinct objects.

The discussed goal is one secret source for wallet and PDF credentials. A raw
scalar can be loaded on secp256k1 and wrapped with an X.509 certificate. An
Acrobat-compatible alternative can use a supported curve such as P-256;
reusing the same scalar requires a range check and produces a different public
key on that curve. Deriving purpose-specific keys from the common secret is
another design choice, not a feature already supplied by this workbench.

pyHanko documents support for cryptography's ECDSA curves. This does not prove
Acrobat interoperability for secp256k1; Adobe's documented supported curves
are different. Test creation, import and validation with synthetic keys in
the intended readers before claiming compatibility. The existing local
workbench accepts an existing PKCS#12 identity; it does not generate one.

Reusing the exact spending scalar in a document keystore means that keystore
also contains the spending secret. Keep real keys and passwords out of Git,
catalog exports, public HTML and PDF content. Do not request them in chat.
Preserve the actual certificate: its serial, validity and other fields mean
that regenerating it from the same secret need not reproduce its fingerprint.

## Public identity and the paper view

The visible signature block can contain both the signer's name and a public
wallet address. Include the declaration in the bytes covered by the signature.
Typing an address does not prove control of it. A separately verifiable wallet
message can bind a chain/address to the PDF certificate's fingerprint and a
specific purpose. Different public keys do not reveal a common secret source.
No such binding format or verifier is implemented yet.

The signing page may have clearly labeled QR codes for distinct jobs: locate
the exact signed edition, inspect the public identity/binding, or inspect the
actual ledger commitment. A plain address QR is not automatically a document
verification link. Keep readable identifiers alongside codes.

Paper and rendered page images retain the signature appearance, not the
embedded verification data. A QR can retrieve that data, but does not by
itself authenticate the surrounding paper. Compare the paper with the signed
original. Retrieval should respect the case's access rules; do not publish
private evidence or home profile values merely to make a public QR work.

## PDF viewer acceptance criteria — next tool change

Opening a PDF in the local Mogwai/SB Shell viewer should automatically inspect
the original bytes and reveal the signature information next to the document.
Reuse the existing workbench rather than create another verifier.

Show the signer/certificate subject, issuer, certificate and public-key full
fingerprints, validity dates, signed coverage/revision, integrity/mathematical
result, later modifications and local identity assessment. Keep PKI trust and
revocation-check limitations visible and separate from a local fingerprint pin.
Expose certificate/validation details without requiring a separate upload.

An unsigned PDF, a malformed/encrypted or unsupported PDF, a missing verifier,
and a cryptographically invalid signature need different visible outcomes.
Do not call a failed inspection "unsigned." Check all document signatures.
Inspect on opening/expanding the PDF rather than scanning an entire directory
with Python on every listing. Preserve originals and the existing local-only
access boundary. Saved/static/IPFS pages must not claim fresh local validation.

Current status: `signatures/` provides manual inspection, local fingerprint
records, public certificate export and CLI signing with an existing PKCS#12
identity. Automatic viewer inspection remains planned. This documentation
update does not change those runtime behaviors.

The proposed [two-window local workspace](LOCAL-WORKSPACE.md) keeps Mogwai
controls/status on port 1132 and a movable working root on port 39632.

## References checked during the discussion

- [Current workbench and limitations](../signatures/README.md)
- [pyHanko signing features](https://github.com/MatthiasValvekens/pyHanko#features)
- [Private scalar and curve APIs](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ec/)
- [Acrobat signature algorithms](https://www.adobe.com/devnet-docs/acrobatetk/tools/DigSigDC/standards.html)
- [Commons signed-edition direction](https://github.com/johnrigler/commons/blob/main/docs/SIGNED-EDITIONS.md)
- [Case/evidence interpretation](https://github.com/johnrigler/certLedger/blob/main/README-2026-10-20-commons-and-signed-editions.md)
