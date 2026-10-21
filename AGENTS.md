# Mogwai: implementation notes for assistants

Keep the existing user's architecture; don't replace it with generic software scaffolding.

- `a.*` is ALP, `d.*` is Daisy, `m.*` is Mogwai. Bash functions are native inspectable/persistable artifacts. `declare -f` is the canonical serialized function definition, retaining the original function name.
- Save function snapshots with ALP/Daisy **content-derived Shoctal/checksum names**, optionally suffixed by source byte count. Short hashes are intentionally collision-capable; do not lengthen them merely to eliminate collisions. Full SHA-256 belongs in FileProxy's catalog, not every filename.
- Daisy is standalone; a saved `daisy()` can load a particular hard-coded set of `d.*` functions. Mogwai supplies tools/UI but must not become a mandatory Daisy dependency.
- Favor the **smallest functional Bash code**, pipes, built-ins, composition, few dependencies, no speculative flags or extra frameworks. Do not normalize filenames into generic `alp.sh`, `daisy.sh`, etc.
- Two FileProxy implementations exist: `johnrigler/fileProxy` is the newer standalone Python catalog/API, while `johnrigler/chisel/tools/fileProxy/` is the legacy Chisel service. Do not confuse them.
- The local standalone FileProxy catalog is **SQLite**, with full SHA-256 stored as 32-byte BLOB. User machines write it, then push the actual database to GitHub. An assistant retrieves the exact GitHub revision and opens it with Python `sqlite3`. GitHub is shared persistent visibility for concrete Web3 artifacts, not an SQL server.
- Anchor references in actual GitHub files/commits, IPFS CIDs, and chain transaction IDs. Never fabricate source records or declare verification without inspecting the cited object.

Read `johnrigler/fileProxy/AGENTS.md`, `johnrigler/daisy`, and `johnrigler/alp` before redesigning these interfaces.

## Future per-ledger catalog idea (not implemented)
The FileProxy [ledger database roadmap](https://github.com/johnrigler/fileProxy/blob/main/docs/LEDGER-DATABASE-ROADMAP.md) proposes one Git-published SQLite database per blockchain (Bitcoin, Litecoin, Dogecoin, Solana, etc.), located via one or more gatekeeper SQLite registry databases. Mogwai can consume those references later. Do not infer this has been implemented or introduce routing/sync features until actually required.

## Annual archive and Daisy naming
GitHub is the working stand-in for IPFS for active Daisy ISO-years. An implementation milestone is **December 31, 2026** for actual SQLite -> IPFS archival and combined GitHub/IPFS lookup. ISO 2026 does not close until January 3, 2027, and the 2027 ISO year begins January 4. This is a future feature, not implemented behavior. Read [FileProxy annual archive plan](https://github.com/johnrigler/fileProxy/blob/main/docs/ANNUAL-IPFS-ARCHIVE.md).

Daisy is intentionally named for the Bell Labs *Daisy Bell* computer-singing demonstration, HAL singing it in *2001: A Space Odyssey*, and Daisy as the conceptual **child of ALP** (Anna Livia Plurabelle) from *Finnegans Wake*. The user's goal is for Daisy to communicate with an AI by exposing specific inspectable artifacts. Read [Why Daisy](https://github.com/johnrigler/daisy/blob/main/docs/WHY-DAISY.md) instead of collapsing it into a conventional module.

## Public annual archives and SB Shell (2026-10-18)

Annual `daisy_YYYY` repositories are intended to be public. The reusable
[year starter](templates/daisy-year/) belongs in Mogwai and generates an
empty dated archive with tool references. SB Shell maintains organization,
numbered units, navigation and print views beyond the ISO WWD coordinate.
PHP is available on the user's laptop for the SB Shell revival. The legacy
PHP assembler has not yet been modernized or tested here. Keep private
source material outside public archives and their retained Git history.

## Tool ownership and engagement scope

Mogwai supplies build/setup/orchestration tools. The working repository
update command belongs in Daisy as `d.pull`; retain existing `m.pull`
snapshots as history rather than making Mogwai a runtime requirement.
Daisy's format can support personal or customer engagement repositories,
each with independent history and access settings. The current annual
starter still creates only `daisy_YYYY`. A future `certLedger_YYYY`
layout is deferred; do not migrate CertLedger as part of this clarification.
See [Daisy engagement conventions](https://github.com/johnrigler/daisy/blob/main/docs/ENGAGEMENTS.md).
