# Roadmap: per-ledger SQLite catalogs

**Status: idea only. Not an implemented schema or an instruction to migrate current data.**

## Current arrangement
- The newer standalone `johnrigler/fileProxy` has one local, Git-publishable `catalog.sqlite3` with source root/path, byte size, timestamp, and full SHA-256 stored as a 32-byte BLOB.
- The user runs the database locally and commits/pushes **the actual SQLite file** to an authorized GitHub repository. An assistant downloads the binary file from that exact repository revision and queries it with Python `sqlite3`.
- `johnrigler/chisel/tools/fileProxy/` is the older Chisel service; do not conflate it with this catalog.
- FileProxy currently catalogs files, not an all-chain transaction model. Chisel interprets and indexes ledger data.

## Possible later structure

```text
registry.sqlite3                  # Gatekeeper / database locator
  |
  +-- Bitcoin  -> bitcoin.sqlite3
  +-- Litecoin -> litecoin.sqlite3
  +-- Dogecoin -> dogecoin.sqlite3
  +-- Solana   -> solana.sqlite3
  +-- ...      -> other catalogs
```

Each chain could own a separate SQLite database. Keep chain-specific data models: Bitcoin, Litecoin, and Dogecoin have UTXO outputs; Solana has different transaction/account conventions. Do not force a generic transaction schema onto all four.

One or several **gatekeeper SQLite databases** may index the catalogs without copying their full records. A registry entry might carry:
- stable chain/network key and catalog identifier;
- GitHub repository, database path, and exact commit (or another immutable reference);
- database SHA-256 (binary when stored in SQLite), schema version;
- visibility/access policy and optional locally resolved path.

An authorized consumer resolves a gatekeeper record, retrieves **the actual binary SQLite database** at its pinned GitHub revision, optionally verifies its full digest, and queries it using Python `sqlite3`. Locally available catalogs can be queried directly; remote catalogs must be fetched first. GitHub itself does not provide SQL queries.

A separate gatekeeper for personal identity, an SB Shell publication, CertLedger, or another view could reference the same chain databases; it need not duplicate data.

## Web3 grounding
- Preserve the precise blockchain/network and concrete txid, output index, contract reference, or Solana signature/account/slot when relevant, as well as IPFS CIDs, repository paths and commits, rather than fictional or illustrative identities presented as real.
- Distinguish *recorded reference* from *independently checked on-chain fact*.
- Keep source bytes (if required) separately accessible; a catalog or registry pointer cannot reconstruct bytes absent from GitHub, IPFS or the ledger.
- Respect GitHub private repository permissions; never assume private information is publishable just because the SQLite file is small.

**Implementation gate:** no database splitting, router, automatic migration, synchronization daemon, universal schema, or extra flags until a concrete multi-chain requirement warrants one. Keep the existing single SQLite catalog operational.
