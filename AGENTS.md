# Mogwai: implementation notes for assistants

Keep the existing user's architecture; don't replace it with generic software scaffolding.

- `a.*` is ALP, `d.*` is Daisy, `m.*` is Mogwai. Bash functions are native inspectable/persistable artifacts. `declare -f` is the canonical serialized function definition, retaining the original function name.
- Save function snapshots with ALP/Daisy **content-derived Shoctal/checksum names**, optionally suffixed by source byte count. Short hashes are intentionally collision-capable; do not lengthen them merely to eliminate collisions. Full SHA-256 belongs in FileProxy's catalog, not every filename.
- Daisy is standalone; a saved `daisy()` can load a particular hard-coded set of `d.*` functions. Mogwai supplies tools/UI but must not become a mandatory Daisy dependency.
- Favor the **smallest functional Bash code**, pipes, built-ins, composition, few dependencies, no speculative flags or extra frameworks. Do not normalize filenames into generic `alp.sh`, `daisy.sh`, etc.
- Two FileProxy implementations exist: `fileProxy/` here is the newer standalone Python catalog/API imported from `johnrigler/fileProxy`, while `johnrigler/chisel/tools/fileProxy/` is the legacy Chisel service. Do not confuse them.
- The local standalone FileProxy catalog is **SQLite**, with full SHA-256 stored as 32-byte BLOB. User machines write it, then push the actual database to GitHub. An assistant retrieves the exact GitHub revision and opens it with Python `sqlite3`. GitHub is shared persistent visibility for concrete Web3 artifacts, not an SQL server.
- Anchor references in actual GitHub files/commits, IPFS CIDs, and chain transaction IDs. Never fabricate source records or declare verification without inspecting the cited object.

Read `fileProxy/AGENTS.md`, `sbshell/AGENTS.md`, `johnrigler/daisy`, and `johnrigler/alp` before redesigning these interfaces.

## Future per-ledger catalog idea (not implemented)
The FileProxy [ledger database roadmap](https://github.com/johnrigler/mogwai/blob/main/fileProxy/docs/LEDGER-DATABASE-ROADMAP.md) proposes one Git-published SQLite database per blockchain (Bitcoin, Litecoin, Dogecoin, Solana, etc.), located via one or more gatekeeper SQLite registry databases. Mogwai can consume those references later. Do not infer this has been implemented or introduce routing/sync features until actually required.

## Annual archive and Daisy naming
GitHub is the working stand-in for IPFS for active Daisy ISO-years. An implementation milestone is **December 31, 2026** for actual SQLite -> IPFS archival and combined GitHub/IPFS lookup. ISO 2026 does not close until January 3, 2027, and the 2027 ISO year begins January 4. This is a future feature, not implemented behavior. Read [FileProxy annual archive plan](https://github.com/johnrigler/mogwai/blob/main/fileProxy/docs/ANNUAL-IPFS-ARCHIVE.md).

Daisy is intentionally named for the Bell Labs *Daisy Bell* computer-singing demonstration, HAL singing it in *2001: A Space Odyssey*, and Daisy as the conceptual **child of ALP** (Anna Livia Plurabelle) from *Finnegans Wake*. The user's goal is for Daisy to communicate with an AI by exposing specific inspectable artifacts. Read [Why Daisy](https://github.com/johnrigler/daisy/blob/main/docs/WHY-DAISY.md) instead of collapsing it into a conventional module.

## Public annual archives and SB Shell (2026-10-18)

Annual `daisy_YYYY` repositories are intended to be public. The reusable
[year starter](templates/daisy-year/) belongs in Mogwai and generates an
empty dated archive with tool references. SB Shell maintains organization,
numbered units, navigation and print views beyond the ISO WWD coordinate.
PHP is available on the user's laptop for the SB Shell revival. The current PHP assembler is maintained in `sbshell/cruff/`; follow its
local standards and tests. Keep private
source material outside public archives and their retained Git history.

## Consolidated tools and flexible naming

FileProxy and SB Shell are maintained here, in `fileProxy/` and `sbshell/`.
Read [docs/CONSOLIDATION.md](docs/CONSOLIDATION.md) for exact source revisions,
exclusions, local migration and IPFS boundaries. The original repositories
retain their histories; do not delete them or move existing archive data.

Command prefixes describe the user's typing habits, not rigid ownership.
A `d.*` function can use Mogwai tooling and live in a dated Daisy archive.
Preserve direct RC source references and immutable function snapshots.
New source requires a new content-derived name. The annual starter creates
local `daisy_YYYY` trees; a future CertLedger annual layout remains deferred.
No automatic IPFS publishing or unified archive lookup is implemented here.

## Private home profiles

Mogwai's `profiles/` GUI and PHP helpers use `~/catalog.sqlite3` for private
people and correspondence records, separate from archive catalogs. Existing
tables are preserved. Read [profiles/README.md](profiles/README.md). Never
copy the home database or real identity fixtures into the source tree, a
public catalog or an IPFS export. Local PHP letter rendering may fill these
values; static template builds keep placeholders. Tests use synthetic data.

## Signing identities

`signatures/` verifies original PDFs with pyHanko and records explicit public
certificate fingerprints/local identity assessments in the same home DB.
Read `signatures/README.md`. Publication is availability, not identity proof;
unknown issuer does not establish self-signing. Keep integrity, PDF revision
coverage, certificate validity, local identity pins and PKI trust separate.
Public export uses an allowlist and never includes home profiles or local
assessment notes. Never commit real signing keys, passwords or identity test
fixtures. Adding a signature must retain the original and check restrictions.
