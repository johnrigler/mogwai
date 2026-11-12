# FileProxy Litecoin identity namespaces (experimental)

Branch: `feature/fileproxy-litecoin-identity-namespaces`. Not enabled unless `FILEPROXY_IDENTITY_ROOT` is set. No Python crypto dependency is required. Install Node.js and set `CHISEL_ELLIPTIC_PATH` to an absolute path to the existing Chisel `chisel.js` (which embeds elliptic 6.6.1). The server returns 503 if this path is unset. Do not expose publicly before testing with real Litecoin wallet signatures.

## Policy

- Any valid Litecoin **legacy P2PKH (L...)** compact signed-message identity can append records to its own namespace.
- No allowlist. The optional `<FILEPROXY_IDENTITY_ROOT>/blacklist.json` has the form `{"addresses":["L..."]}`.
- Identity is derived from the recovered public key. Client-supplied paths are not accepted.
- A SQLite database under `litecoin/<address>/records.sqlite3` stores append-only JSON records, unique by nonce.
- Other existing FileProxy write endpoints still use their existing shared-token/local authorization. **They are not identity-isolated yet.**
- Anonymous catalog reads remain available.

## Request

`POST /v1/identity/records`, `Content-Type: application/json`, max 64 KiB.

```json
{
  "address": "L...",
  "timestamp": 1700000000,
  "nonce": "0123456789abcdef",
  "body": {"text": "example"},
  "signature": "<base64 65-byte Litecoin compact signed-message signature>"
}
```

Sign the UTF-8 message:

```text
FileProxy Litecoin Identity v1
POST
/v1/identity/records
<unix timestamp>
<nonce>
<lowercase hex SHA-256 of canonical body JSON>
```

Canonical body JSON: sorted object keys, compact separators, JSON ASCII escaping (`ensure_ascii=True`), UTF-8 encoding. For cross-language signing, avoid floating-point values until canonicalization is standardized further. The signature uses Litecoin's signed-message prefix, double SHA-256, and compact recoverable secp256k1 format. Requests expire after 5 minutes; nonce reuse is rejected within each identity.

## Tests

From `fileProxy/`:

```sh
python3 -m unittest discover -s tests -p 'test_identity.py' -v
```

The Python unit tests mock public-key recovery. A Node.js signing/recovery roundtrip is provided by `node tools/test_litecoin_verifier.js`. **A real Litecoin-wallet interoperability test is still required.**

## Limitations before production

- Current implementation only supports legacy P2PKH addresses and append-only JSON records, not arbitrary directory write operations.\n- Each signed request invokes Node.js as a subprocess. Add bounded concurrency/rate limits before exposing this endpoint to the internet.
- The process owner must protect the identity storage root and blacklist against local modification. This is application-level isolation, not an OS process jail.
- Storage quotas, rate limiting, revocation beyond the blacklist, and concurrency-hardening of blacklist updates remain to be implemented.
- The existing shared URL catalog is global. Per-identity references to shared URLs are a follow-on change.

## Local Node.js verifier check

From `fileProxy/`, with Chisel checked out locally:

```sh
export CHISEL_ELLIPTIC_PATH="$HOME/chisel/chisel.js"
node tools/test_litecoin_verifier.js
python3 -m unittest discover -s tests -p 'test_identity.py' -v
```

Node.js uses the exact `chisel.js` elliptic bundle, without a Noble dependency. Do not point `CHISEL_ELLIPTIC_PATH` at an untrusted or user-writable JavaScript file. Keep the verifier local and under operator control.
