# FileProxy rabbit-trail preservation model

Recorded 2026-11-16. Schema proposal; not a migration or deployed feature.

Goal: preserve source bytes and reconstruct verifiable artifacts while allowing Chisel to read without depending on a live centralized service.

Proposed logical tables (names provisional): objects (stable source scheme/ID and version/CID), blobs (full SHA-256 BLOB, size, media type, content locator, byte-verified status), observations (capture time, source-supplied time, retrieval method, origin, status), relations (source object, target object, typed edge, provenance), attestations (chain, txid, exact digest+algorithm, proof status), and identities (source DID, native signing address, independently verified association status). Preserve provenance; a source record, normalized API view and derived M64 representation are different objects. Binary files belong in a content-addressed local store or chosen mirror, not inline SQLite by default. Retain original bytes when available; no retained bytes means no guaranteed backup.

Use existing SQLite catalog and static publication design; avoid proposing a second required service. GitHub, rigler.org and IPFS are optional mirrors. Content-derived paths must verify on ingestion and on recovery. Cache metadata alone is not recovery. Document chain timestamp versus locally observed timestamp versus source-reported timestamp. Typed rabbit trails (parent/reply/quote/mirror/cites/attests) may have unknown or missing targets; a traversal must be bounded and explicitly incomplete when necessary.

Acceptance test: ingest two references to the same AT URI+CID without duplicating blobs, preserve a changed CID as a distinct version, verify media bytes after network disconnection, reconstruct an indexed thread with missing-edge markers, and export a self-contained integrity manifest. No on-chain JSON requirement. See Mogwai docs/PEER_TRANSPORT_AND_RABBIT_TRAILS_2026-11-16.md and Chisel docs/CROSS_PLATFORM_IDENTITY_AND_RABBIT_TRAILS_2026-11-16.md.
