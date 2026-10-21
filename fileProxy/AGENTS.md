# FileProxy: repository notes for assistants

## Consolidated location
Current source is `johnrigler/mogwai/fileProxy/`. The original
`johnrigler/fileProxy` repo is retained for history and data artifacts.
Read [the migration guide](../docs/CONSOLIDATION.md). Runtime configs and
archive catalogs stay outside the tools tree.

## Which FileProxy?
This repository (`johnrigler/fileProxy`) is the **new standalone Python FileProxy**. The older Chisel implementation is preserved at `johnrigler/chisel/tools/fileProxy/` and copied into this repository under `tools/fileProxy/` for compatibility. Do not confuse them or modify Chisel's legacy API as part of catalog work.

## SQLite -> GitHub -> Python
The user runs FileProxy and SQLite on their own machines (Termux, Linux, macOS).
FileProxy is a set of commands plus an optional HTTP service. By default each
registered filesystem root owns its `catalog.sqlite3` and generated `files.txt`;
an annual root such as Daisy 2026 keeps both files in that archive. An explicit
`--index` path or `FILEPROXY_INDEX` preserves shared-catalog mode. The existing
checkout-root database is retained, not automatically migrated or deleted.
A scan updates catalogs and listings without a daemon; HTTP queries read the
same catalogs on demand. A scan does **not** automatically publish them.

The user commits and pushes the actual **SQLite database file** to a GitHub repository, public or private as appropriate. Assistants should retrieve that **exact binary database at a known commit** through authorized GitHub access, then inspect it with Python `sqlite3`. Do not substitute an imagined catalog, speculative transactions, or JSON for the database. GitHub's web/code search does not query SQLite directly.

```bash
python3 fp.py scan daisy2026
cd "$HOME/daisy_2026"
git add -f catalog.sqlite3
git add files.txt
git commit -m "Update FileProxy catalog"
git push
```

The local root configuration and credentials are machine-specific and **must not** be published. Review a catalog for private paths or sensitive metadata before committing it to a *public* repo. Committing the catalog does not commit source files themselves; GitHub needs those files or usable Web3/IPFS references separately.

The full SHA-256 is stored as a **32-byte SQLite BLOB**. FileProxy renders hex only at its CLI/HTTP boundary. Avoid storing an ASCII-hex SHA as 64 bytes in the database unless an explicit external format requires it.

## Grounding Web3
The goal is for assistants to inspect specific artifacts and events, not discuss hypothetical objects. Keep exact network/chain, transaction ID, output or contract reference where relevant, IPFS CID, repository path and commit, and supporting source bytes when available. Chisel owns chain interpretation; FileProxy catalogs bytes and references. Do not fabricate identifiers or claim an event was independently verified merely because its metadata exists.

## ALP / Daisy conventions
ALP `a.*` and Daisy `d.*` are native Bash functions. `declare -f NAME` serializes the function into source that must restore the **same function name** when sourced and reserialized. Snapshot names are **function-name + short Shoctal/checksum code**, optionally followed by a byte count, rather than generic `.sh` modules. Short Shoctal collisions are an intentional property. Name, Shoctal code and byte count can qualify the identity; full SHA-256 belongs in FileProxy. Never silently overwrite or rename historical snapshots.

Prefer minimal shell functions and direct composition. Do not invent manifests, option matrices, new runtimes, normalization, or abstraction layers without a demonstrated requirement. Read the corresponding Daisy and ALP repositories before modifying their conventions.

`scan` generates the plain root-relative `files.txt` inventory. Preserve ALP's
`.files.txt`: it may define executable loading actions and manual ordering.
Do not rewrite it as an automatically sorted path list. Generated catalogs,
SQLite sidecars and `files.txt` are excluded from the scanned source records.

## Possible later multi-ledger SQLite layout
See [docs/LEDGER-DATABASE-ROADMAP.md](docs/LEDGER-DATABASE-ROADMAP.md). Later, individual chains (Bitcoin, Litecoin, Dogecoin, Solana, etc.) may each have their own Git-published SQLite database, located through one or several small **gatekeeper/registry SQLite databases**. Preserve chain-specific models rather than flattening all networks. **Roadmap only:** don't migrate, split, implement a router, or add flags now.

## Year lifecycle and 2026 milestone
GitHub is the working, AI-readable stand-in for IPFS while an ISO-year archive remains active. The user publishes **actual local SQLite database files** to GitHub. After an ISO year closes, its source records and SQLite catalog are to be pinned to IPFS, with CID(s) recorded so FileProxy can search/query both the current GitHub-backed catalog and older IPFS-retrieved SQLite snapshots. **Target: functional implementation by December 31, 2026**, first handoff after ISO year 2026 actually closes on January 3, 2027 (ISO 2027 begins January 4). Do not seal it on December 31. This is a planned milestone, not implemented behavior. See [docs/ANNUAL-IPFS-ARCHIVE.md](docs/ANNUAL-IPFS-ARCHIVE.md) for the detailed acceptance criteria, pinned availability, and privacy safeguards. No speculative extra framework.
