# Email and mail registration

Open `index.html` on localhost or HTTPS. The page is plain browser HTML and
JavaScript; it can be hosted statically with this directory on IPFS.

1. Export the full email edition to its final PDF. Select that file here to
   compute SHA-256 over its exact bytes.
2. Register that digest through Chisel/CertLedger. Enter the returned
   CertLedger ID, network, transaction ID and transaction URL.
3. Prepare the email body and attach that exact PDF. Send through the chosen
   mail client. This tool neither sends mail nor submits ledger transactions.
4. After sending, enter the actual destination and sent timestamp with a time
   zone. Download `email-dispatch.php` into the case directory.
5. Rebuild the shorter mail edition, which now identifies the email for its
   omitted exhibits. Export its final PDF under a different filename.
6. Select that PDF and enter its separate ledger transaction. Prepare the
   registration sheet and thermal receipt, then print them separately from
   the PDF being fingerprinted.

The sheet is generated last and can be placed first as a preface. It is
outside the registered PDF. A preprinted colored sticker can be chosen and
attached before ledger submission: its identifier does not contain a future
PDF hash or transaction. The receipt's primary QR instead contains the
explicit transaction URL.

Download each edition's `.record.json` and retain it with that case. Browser
storage is a convenience; reselect the PDF after reopening to check its bytes.
A changed email PDF clears its former registration and sent-email fields.
The mail edition requires a different PDF hash and a separate transaction.
Entered transaction references are not independently checked for confirmation.

The printable sheet includes the full digest. The 384-dot receipt also
includes both halves of the full digest, the transaction ID, and a QR drawn
with whole modules and a four-module quiet zone. BLE and Serial printing reuse
Chisel's current CTP500 modules. Partial jobs are not automatically retried.
Physical printer operation requires a device check; this is not a background
print service.

Source reuse: printer modules and QRCode.js were copied from
`johnrigler/chisel` at `af1b735e76dee42e546adf0020a08afa53d7e37a`.
QRCode.js retains its MIT license in `QRCODE-LICENSE.txt`.

Development check: `node tests/packet-registration.mjs` from the SB Shell root.
