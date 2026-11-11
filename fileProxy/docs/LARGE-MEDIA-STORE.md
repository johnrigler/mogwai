# Large media in FileProxy: storage, hashing, retrieval and independent copies

*Engineering proposal · 10 November 2026 · scope: `mogwai/fileProxy/` · not deployed*

## Reason for this design

Commons needs to preserve exact original audio, corrected SRT, Recast project files and later rendered video as separate artifacts, and optionally move selected redacted derivatives to public storage. A SHA-256 digest is computed from source bytes and is not inherently limited to 64 MiB. Current size ceilings are implementation decisions, not hash-algorithm restrictions.

The current code paths behave differently:

| Path | Observed code | Consequence |
| --- | --- | --- |
| Commons PDF artifact-intake page | 64 MiB source cap and PDF-specific inspection | Not a general-purpose audio/video ingestion route |
| FileProxy `fileproxy.core.sha256_file` and `scan_root` | Reads files in 1 MiB chunks when hashing | Already suitable for hashing larger files without reading them all into RAM |
| FileProxy `fp put` CLI (this proposed code change) | Streams in 1 MiB chunks to a temporary file while hashing | Removes full-file RAM usage for local CLI copies after installation |
| FileProxy `POST /v1/put` | JSON text/base64, 12 MiB request ceiling, whole-body parse | Not suitable for multi-gigabyte media |
| FileProxy `GET /v1/file` | Calls `target.read_bytes()` | Whole file in memory; no dedicated HTTP range streaming for media |
| `static_publish.py` | Checks `MAX_BYTES` and uses `read_bytes()` | Designed for smaller portable static artifacts, not arbitrary media |
| URL paste intake | Fetches up to 12 MiB | This is a separate document-capture path and should retain its bounded policy |

These limits are not a reason to normalize or recompress evidence. The server must preserve exact original bytes.

## Use existing capabilities immediately (no code changes)

1. Copy the original file into a **private** registered FileProxy root using a direct filesystem copy, SSH/SCP or rsync. With the revised CLI installed, `fp put ROOT /path/to/source relative/name.ogg` also performs a chunked local copy. Use the original bytes without editing or renaming in place; filenames can be catalog aliases.
2. Run `fp scan ROOT`. The catalog's SHA-256 is calculated incrementally and stored as a **32-byte BLOB** in SQLite; file length and path are recorded as well.
3. Verify the digest separately on the source device with `sha256sum /path/to/source`, and on the receiving machine with `sha256sum /path/to/stored-copy`. Match full 64-character lowercase hex digests *and* sizes.
4. Keep original audio, exported SRT, corrected transcript, Recast project JSON and later MP4 as **distinct** records; a project file or MP4 does not replace an original source.
5. Make an independent second copy on another storage system, e.g. a separately operated Nerd Coffee host, with a different failure domain. Verify it with the same SHA-256 before declaring it a replica. A second DNS name on the same disk is not redundancy.
6. Keep private case evidence outside public web roots, public Git repositories and public IPFS. Publish reviewed redacted derivatives separately with their own hash and a private source-to-derivative relation.

Simple Linux example (adapt paths and root names to the actual machines, and only register directories that already exist):

```bash
# On the rigler.org host, if the CLI update has been installed:
cd ~/mogwai/fileProxy
python3 fp.py add-root commons_private /srv/private/commons
python3 fp.py put commons_private /path/to/original.ogg calls/original.ogg
python3 fp.py scan commons_private
sha256sum /srv/private/commons/calls/original.ogg

# On the second independent host, compare after copying there:
sha256sum /srv/private/commons/calls/original.ogg
```

Do not assume the first host has the suggested directory, a network API listener, or a working replication channel until checked. `scan` catalogs already-present files; **it does not upload them to the other host**.

## Proposed FileProxy work (not implemented)

### 1. Authenticated streaming large-object ingest

Add a new opt-in raw-byte endpoint, separate from legacy `/v1/put`. Read input as bounded chunks directly into a temporary file inside the selected registered private root while updating a SHA-256 context and counting received bytes. Never materialize the full body as JSON, Base64 or a Python `bytes` object.

The endpoint should require authenticated, root-scoped write permission; reject path traversal, symlink escapes, unsupported content types and dangerous filenames; impose configurable size, disk-space, concurrency and duration limits; require exact content-length or well-defined resumable upload framing. Clean failed partial uploads; use fsync and atomic rename for completed ones. Prevent replacement of an existing object whose digest differs.

Return only a verified immutable artifact identifier, byte count and SHA-256, never a public URL by default. A client-supplied SHA-256 is an expectation to verify, not a trusted fact. Resist exposing the current generic write token to any public webpage.

### 2. Streaming retrieval with range support

Provide a bounded stream from a registered root. For playable audio/video, support HTTP `Range` (`206 Partial Content`, `Content-Range`, `Accept-Ranges: bytes`) without reading the full source into RAM. Require authorization for private objects. Provide `Content-Length`, `Content-Type`, `ETag` from verified metadata and `X-Content-Type-Options: nosniff`; do not let uploaded HTML execute as an app. Preserve `/v1/file` legacy behavior until migration tests pass.

### 3. Content-addressed storage and catalog

A source hash may form a physical immutable key such as `objects/sha256/<first-two-hex>/<full-hash>`. Alias paths, event labels, origin metadata and permissions live in the FileProxy catalog or a sidecar, not inside the source bytes. Keep the **32-byte binary SHA-256** in SQLite. Reject silent replacement of original source files. Catalogue updates must not be confused with source publication.

### 4. Independent replication

A worker can obtain a manifest of *permitted* digests from rigler.org, check the Nerd Coffee server, transfer missing objects over authenticated transport, then compare the complete received SHA-256 and length. Record a per-copy verification result, last verification time, machine/root, and restricted availability. Periodic re-verification detects bit rot and missing copies. Replication must never automatically make private evidence public.

Two servers should be treated as independently managed storage endpoints, not as two websites for one mount. Prefer an offline or otherwise separately controlled third copy for irreplaceable originals. A remote machine's acknowledgment does not prove long-term survival.

### 5. Optional IPFS and Litecoin publication

SHA-256, IPFS CID, and a Litecoin TXID are different identifiers:
- SHA-256 of the original audio: checks exact original bytes.
- IPFS CID of a publication: depends on exact added bytes and IPFS layout/chunking; do not assume it equals the raw SHA-256 digest.
- Litecoin transaction: may contain a digest commitment in OP_RETURN. It does not store the recording or prove when the recording originally occurred.

The current Chisel hash-only ASCII profile is `sha256:` + 64 lowercase hexadecimal characters = 71 bytes; no JSON wrapper is required on-chain. For a Commons-discoverable Litecoin record, the existing **Commons transport address** is `LMxCoMMoNSzzzzzzzzzzzzzzzzzzZU8MFW` (see `commons/docs/PORTAL.md`). The legacy CertLedger review tool currently hardcodes a different transport tag; do not relabel its output as Commons until a dedicated reviewed handoff exists. Funding, signing and broadcast must be explicit operator actions.

Capture time, archive intake time, replica verification time, later IPFS pin time and chain confirmation time are **distinct observations**.

## Safety and delivery criteria for a future implementation

- Test streaming with files much larger than RAM constraints where feasible and assert no full-body `read_bytes()`.
- Test truncated transfers, bad digests, retries, duplicate content, symlinks, unauthorized uploads, quota limits and failed atomic promotions.
- Test `Range` behavior against browsers seeking within large OGG and MP4 samples.
- Test replica mismatch, partial transfer, disconnection and privacy boundaries.
- Confirm that old `/v1/put`, old Chisel routes, static artifact publishing, and the existing FileProxy catalog continue to work.
- Deploy on one private endpoint first; a GitHub commit does **not** restart the server or publish the stored object.

**Status:** this change set includes a bounded-memory implementation for the **local CLI put command** plus an architecture specification. The new CLI behavior requires installation on the target host and passing tests. No new HTTP upload route, live media storage root, replication service, public media, IPFS pin or Litecoin broadcast is claimed.
