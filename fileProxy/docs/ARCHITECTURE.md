# One filesystem, several projections

Current implementation: FileProxy and SB Shell are components of Mogwai.
See [the consolidation guide](../../docs/CONSOLIDATION.md). Older repository-role
descriptions below record the earlier layout; archive data stays separate.

FileProxy is the non-cryptographic infrastructure layer shared by the projects.
It transports bytes, catalogs paths, computes hashes and exposes a CLI/HTTP API.

## Responsibilities

| Component | Owns | Does not own |
| --- | --- | --- |
| Daisy | Original personal/project artifacts, dates and ordinal hierarchy | HTTP API or cryptocurrency |
| FileProxy | Data-root registry, safe IO, content hashes, derived indexes, CLI, API | Original artifacts or wallet signing |
| Mogwai | Document/identity-oriented renderers and hydration of indexed objects | Primary file persistence |
| Chisel | Ledger transactions, signatures, streams, blockchain interpretation | General document storage |
| CertLedger | Legal matter schemas, receipts, chronology, evidentiary claims | Filesystem transport |
| SB Shell | Directory-based publication/navigation | Canonical cross-project catalog |
| SB Stats | Metrics and reporting on existing data | Primary store |

Nothing prevents any vertical project from having its own repository for code,
views, tests and domain-specific schemas. Its *data* can live in Daisy or in
another configured data root. A FileProxy catalog can always be rebuilt.

## Commands first, service optional

Each registered filesystem root owns a `catalog.sqlite3` and generated plain
`files.txt` at its top level. For example, registering the actual local
`daisy_2026` directory as `daisy2026` makes `fp scan daisy2026` refresh those two
files inside that directory. Commands use Python/SQLite directly and work
without any daemon. An explicit `--index` path or `FILEPROXY_INDEX` retains
the shared-catalog mode for existing workflows; older databases are retained.

The optional HTTP service reads these same files on each request. It holds no
second general catalog in memory, requires no restart after a CLI scan, and
does not perform automatic scans. A local root alias can differ between
machines: API reads rebind an archive-local catalog's records to the current
alias without rewriting the original artifact paths.

The plain inventory records the files and directories observed by the scan,
including empty directories, in sorted root-relative order. A static browser
can fetch it over HTTP or IPFS independently of FileProxy. SQLite remains
available for direct SQL and byte-identity metadata; the listing does not
substitute for it. Generated catalogs, SQLite sidecars and listings are skipped
as source records. ALP's `.files.txt` loading actions and ordering are preserved.
The existing `/catalog` browser page itself continues to require the HTTP API.

## Canonical path identity

A record is named `<root>:<relative-path>`, e.g.:

```text
daisy:2026/42/1/01/receipt.pdf
certledger:records/jgg-trump-contempt-2025-2026.json
sbshell:myshell/1_01-gemini-balloon.html
```

The name of the root is an alias from local config, **not** a hard-coded path.
Do not put absolute local paths into data record IDs. An index row includes
SHA-256, size, MIME type and nanosecond filesystem modification timestamp.
For year/week/day paths, ISO year, week and day are extracted as metadata.

The catalog is a **SQLite** projection, not a store of original artifact bytes.
Full SHA-256 values are stored as 32-byte BLOBs and rendered to hex only on
API/CLI output. SHA-256 establishes byte identity but, alone, proves neither
authorship nor when someone received a document.

The user builds the catalog locally, commits the actual `catalog.sqlite3`
file to an authorized GitHub repository, and assistants retrieve a specific
committed SQLite file and inspect it using Python `sqlite3`. Public/private
visibility follows the chosen repository. GitHub does not execute SQL on
the database. The local roots configuration and credentials are not published.
For Web3, preserve concrete chain, txid, output/contract and CID references
from real source records; do not infer them from a catalog path.

## Chisel compatibility

`tools/fileProxy/proxy.py` and the editor assets are copied verbatim from
`johnrigler/chisel`. The `fileproxy/server.py` handler subclasses the Chisel
handler and adds `/v1` routes. The legacy namespace remains completely
unchanged (`/ping`, `/save-tx`, `/tx`, `/txids`, `/main-stream`,
`/save-links`, `/list`, `/load`, `/save`, `/import-jist-feed`,
`/reindex`, etc.).

When running the unified service for an existing Chisel installation, set:

```bash
export CHISEL_FILE_ROOT="$HOME/chisel"
export CHISEL_DATA_ROOT="$HOME/daisy/2026/chisel-data"
python3 fp.py serve
```

`CHISEL_DATA_ROOT` is only an **example**; use the real existing data path.
Legacy Chisel's file layout remains `data/transactions/<coin>/...` (or the
configured external data root). The general catalog has separate root mappings.

## Interoperability and limitations

- General `/v1` routes are independent of Chisel's transaction parsing.
- `/v1/index` reads already-built catalogs from the registered roots (or the
  explicitly selected shared catalog). CLI `scan` or authenticated
  `POST /v1/scan` refreshes catalogs and plain inventories.
- The scanner skips dotfiles, dot-directories and symlinks to avoid importing
  internal Git state or accidentally traversing other roots.
- Files may have non-ASCII names; ordinal names are a convention, not required.
- Unmodified Chisel legacy endpoints include unauthenticated writes and broad
  CORS. Bind the service to loopback and do **not** expose legacy routes on
  an untrusted public endpoint without external authentication/ACLs.
- `/v1/put` and `/v1/scan` require `FILEPROXY_WRITE_TOKEN`. It does not
  protect the legacy endpoints.
- `/v1/file` exposes configured data roots to anyone who can reach the HTTP
  listener. Only register roots appropriate for that listener.
- Scanning updates local SQLite but does not automatically create a Git commit
  or push it. Publication uses explicit Git add/commit/push. No blockchain
  writes or IPFS publication occur when scanning or saving.
