# Annual archive: GitHub -> IPFS

Current implementation: FileProxy and SB Shell are components of Mogwai.
See [the consolidation guide](../../docs/CONSOLIDATION.md). Older repository-role
descriptions below record the earlier layout; archive data stays separate.

**Status:** planned. **Implementation milestone: working by December 31, 2026**, ready for the first ISO-year handoff. Do not claim an archive or cross-backend lookup is already working.

## Principle

GitHub is the *active-year working stand-in for IPFS*: the user's machines create/update the actual SQLite FileProxy catalog and source files and push them to GitHub so the assistant can inspect real artifacts. Completed yearly archives move to IPFS. During subsequent years, FileProxy searches **both active GitHub-backed and archived IPFS-backed data** through one interface. GitHub is not the permanent authority for old material.

The archive boundaries follow **Daisy ISO week-years** (`%G/%V%u`), not calendar years. The `daisy_2026` repository's relative `421/` means ISO `2026/421`. No renaming or new hierarchy is required.

For 2026 specifically:
- **December 31, 2026**: implementation must be usable and tested, including a trial archive and retrieval.
- **January 1-3, 2027**: these dates *still belong to ISO year 2026*, specifically week 53. Keep accepting records into the 2026 archive; do **not** seal it on December 31.
- **January 4, 2027**: ISO year 2027 begins (`2027/011`); this is the first natural point to finalize the complete 2026 snapshot and publish its IPFS CIDs.

## Minimal lifecycle

```text
Active ISO year 2026                   Closed ISO year 2026
local files + FileProxy SQLite           IPFS-pinned files + SQLite snapshot
          |                                          |
   push actual bytes to GitHub                  recorded CID(s)
          |                                          |
          +---------------- FileProxy ----------------+
                        unified lookup
```

1. Work locally. FileProxy maintains its actual SQLite file with full SHA-256 as a 32-byte BLOB. GitHub receives the actual committed database file, not a substitute JSON catalog. Publish sources if they must also be retrievable.
2. At the ISO-year boundary, take a consistent SQLite snapshot (not an uncheckpointed live WAL file), and archive the year-scoped source tree plus its FileProxy database snapshot to IPFS. Record the resulting CID(s) and verify fetchability and full byte digests.
3. Retain a small, discoverable locator for each year's archived SQLite CID and source root CID (e.g. in the active FileProxy catalog / registry). Do not require a new router, separate ledger databases, or an elaborate manifest to do this first handoff.
4. FileProxy finds records by year/root and queries a retrieved/cached archived SQLite database using ordinary SQLite, as well as the active GitHub-backed/local one. GitHub and IPFS host **bytes**, neither provides SQL execution. Preserve explicit chain/network, txid/output/signature, IPFS CID, and original source references where known.
5. IPFS CIDs give content addressing but **not guaranteed availability**; pin archives with reliable persistence and test retrieval. Do not republish private year archives to public IPFS by default. Private material requires deliberate separation or encryption before IPFS publication; a private GitHub repository does not imply private IPFS hosting.

## December 2026 acceptance criteria

- [ ] FileProxy can publish a test year-scoped SQLite snapshot and associated source files to IPFS, with recorded/pinned CIDs.
- [ ] The snapshot's contents and digest round-trip after IPFS retrieval; Python `sqlite3` can query the retrieved binary SQLite file.
- [ ] One FileProxy search can return both an active-year GitHub/local record and an archived-IPFS record, with its precise backend and locator.
- [ ] The read path can resolve a concrete Web3 artifact reference and retain its chain, txid/output or account/signature, and source/provenance.
- [ ] The ISO year rollover is tested, especially that January 1-3, 2027 remain in `daisy_2026`, and January 4 opens `daisy_2027`.
- [ ] Privacy review and pin/retrieval verification happen before treating any annual archive as complete.

No automatic deletion of GitHub history or local copies is required for the initial milestone. The user's broader aspiration is eventual IPFS archival; making archival safe and reliably findable matters more than prematurely removing older GitHub records.

## Adjacent later roadmap

Separate SQLite databases per Bitcoin, Litecoin, Dogecoin, Solana, etc., potentially located by one or more gatekeeper databases, remain an **independent later idea**. The first annual migration should work with today's single SQLite FileProxy catalog. See [LEDGER-DATABASE-ROADMAP.md](LEDGER-DATABASE-ROADMAP.md).

## Names and responsibilities

- **New FileProxy:** `johnrigler/fileProxy`, standalone Python SQLite catalog / lookup layer.
- **Old Chisel FileProxy:** `johnrigler/chisel/tools/fileProxy/`, not this migration target.
- **Daisy:** year-structured source artifacts, original function/snapshot names and paths.
- **Chisel:** interpretation of specific on-chain records.
- **Mogwai:** user-facing exploration and hydration of retrieved records.

The success condition is that an assistant can retrieve the **specific committed or pinned artifact** and inspect its actual bytes, rather than treating Web3 references as hypotheticals.
