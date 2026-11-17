# Mogwai: peer transport, cross-source ingestion and rabbit trails

Recorded 2026-11-16. Proposed work, not implemented.

## Division of responsibility

Mogwai is the Android share shim/orchestrator and local tooling layer. It detects Bluesky/YouTube/LinkedIn/other URLs, forwards a typed source reference to Chisel, and can relay/preserve artifacts via FileProxy. Chisel owns subject resolution, deduplication, identity verification, portal navigation and optional etching. Don't build a second canonical identity/database protocol in the mobile shim. Read existing docs/BROWSER-AND-BLUESKY-SUGGESTIONS.md before implementing Bluesky support.

## Bluesky first read-only path

Share a post URL -> Chisel resolves handle to DID and AT URI -> reads the post and CID -> FileProxy/index checks for existing URI/version -> Chisel opens existing portal entry or stages a new artifact. Capture individual post first; follow root, reply and quote rabbit trails on demand. Preserve source bytes, attachments, missing blob inventory and capture time if backup is intended. PDS raw record fetches and AppView hydrated feed responses are different evidence types. A deleted post may remain independently recoverable only if the actual bytes/blobs were retained. No login required for suitable public reads; writes require explicit account authority and confirmation. LinkedIn ingestion is a separate capability/restriction investigation, not equivalent to public Bluesky APIs.

## WebRTC future adapter

WebRTC DataChannels can transfer signed Chisel messages, M64 payloads, files and hashes over encrypted peer connections. DTLS transport encryption is NOT portable author authentication: signed canonical payloads must remain independently verifiable after relay and persistence. Sign using an approved Chisel crypto identity, with format version, purpose/domain, algorithm, sender key/address, message ID/nonce, source/target references, hash and explicit signing rules. Prefer replay protection, ordering and duplicate handling; no automatic transaction broadcast. Exchange SDP/ICE signaling via a replaceable service or manual QR; account for STUN, TURN, NAT failures and intermittent offline states. Direct P2P cannot be guaranteed. A relay is a transport dependency, not an authority over message authenticity.

## Other channels

Support DIDs and AT Protocol identities as externally verifiable associations, never as mandatory replacements for Chisel native crypto keys. Thunderwords remain cross-chain discovery subjects; association must be signed to prove key control. M64 is a transport-neutral encoding choice when it saves actual bytes and is independently reversible. Optional BSV support is Chisel chain-adapter work and deferred until collaborators/read-path fixtures exist.

## Suggested staged milestones

1. URL classifier and read-only Bluesky importer, preserving URI/CID and existing-record navigation.
2. FileProxy byte-preserving cache and explicit artifact/edge schema; deterministic offline re-open.
3. Chisel-signed transport-neutral message format, local verify and tamper/replay fixtures.
4. WebRTC data-channel proof of concept between Android/Chromebook with replaceable signaling and fallback paths.
5. Authorized Bluesky posting/custom lexicon records only after read path and consent are stable.

Do not state these milestones are implemented until there are passing tests and inspected transactions/messages.
