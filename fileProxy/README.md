# FileProxy

FileProxy is now maintained inside [Mogwai](../README.md), at
`mogwai/fileProxy/`. See [the consolidation guide](../docs/CONSOLIDATION.md)
for switching an existing installation. The original GitHub repository retains
its history and previously published catalog.

A local-first **storage, catalog and API layer** for Daisy, Chisel, CertLedger,
SB Shell, SB Stats and other projects. This is the common *non-crypto*
infrastructure. Original files stay in their own configured directories.
FileProxy does not automatically move them into this Git repository.

**Current status:** command-first Python tools with archive-local SQLite
catalogs and an optional HTTP service. Chisel's original HTTP
implementation is copied unchanged under `tools/fileProxy/`; the new
`fileproxy/` package adds a Bash-friendly CLI and general-purpose `/v1`
filesystem catalog API.

## Persistent notes and publication

Read [AGENTS.md](AGENTS.md) before changing function naming, Shoctal identity,
FileProxy responsibilities, or publication conventions.

**Two FileProxies:** this is the new standalone `johnrigler/fileProxy`
implementation. The old Chisel implementation lives under
`johnrigler/chisel/tools/fileProxy/` (a compatibility copy lives here in
`tools/fileProxy/`). This SQLite catalog change does not replace its legacy
routes.

The user creates/updates a **real SQLite database locally**, commits it to
GitHub, and an authorized assistant retrieves the binary SQLite file at a
specific commit and queries it in Python. No JSON/manifest substitute is
required for that workflow. The full SHA-256 is a 32-byte BLOB in SQLite,
rendered as hex for the current CLI and HTTP interface. To publish:

```bash
# The root must already be registered against its actual local directory:
python3 fp.py scan daisy2026
cd "$HOME/daisy_2026"
git add -f catalog.sqlite3
git add files.txt
git commit -m "Update catalog"
git push
```

By default every registered root owns its own `catalog.sqlite3` and generated
`files.txt`. Thus `daisy2026` writes inside the registered Daisy 2026 directory,
not inside the FileProxy code checkout. `git add -f` handles archives that
ignore SQLite files; review the selected repository before publishing.
**Only the catalog and listing** are committed by these commands, not the
source files they describe. Publish actual sources or stable chain/IPFS
references separately.

An explicit `--index /path/catalog.sqlite3` or `FILEPROXY_INDEX` still selects
the older shared-catalog mode. The already-published database stays in the original FileProxy
repository; it was not copied into Mogwai. To query it, use
`python3 fp.py --index /path/to/that/catalog.sqlite3 find TERM`. A normal scan does not migrate or delete it.
Unset `FILEPROXY_INDEX` when switching from a shared catalog to archive-local
catalogs, and launch the optional service with the same configuration.

## Repository roles

- **Daisy:** filesystem representation of the personal archive, with
  year / ISO-week / ISO-day and ordinal directory conventions. ALP/Fiona
  can create and manipulate this tree from Bash.
- **FileProxy (here):** handles data roots, safe file access, hashing,
  indexing, retrieval and transport. Neither authors nor interprets ledger
  transactions.
- **Mogwai:** contains FileProxy, SB Shell and reusable project tools.
  Source records and catalogs stay in independently registered archive roots.
- **Chisel:** interprets and creates blockchain data. Its existing FileProxy
  cache/API endpoints are preserved.
- **CertLedger, SB Shell, SB Stats:** domain-specific records, publication
  and analytics that read the same catalog without owning transport.

For details see [Architecture](docs/ARCHITECTURE.md).

## Quick start (Termux, Linux or macOS)

From the consolidated Mogwai checkout:

```bash
cd ~/mogwai/fileProxy
python3 fp.py add-root daisy "$HOME/daisy"
python3 fp.py add-root certledger "$HOME/certLedger"
python3 fp.py add-root sbshell "$HOME/mogwai/sbshell"
python3 fp.py add-root sbstats "$HOME/sbstats"
python3 fp.py add-root chisel "$HOME/chisel"
python3 fp.py roots
python3 fp.py scan
python3 fp.py find receipt
python3 fp.py ls daisy --prefix 2026/42/
```

**Only register directories that actually exist.** The names above are
illustrative, not assumptions about your local directory names. Every
`add-root` registers an absolute directory in the machine-local config,
by default `~/.config/fileproxy/config.json`. Each registered directory gets
its own derived `catalog.sqlite3` and `files.txt` when scanned.
The local root configuration stays outside Git. The SQLite
database is meant to be committed to an approved GitHub repository.

## Work with an annual archive, with or without a server

After sourcing `shell/fp.sh`, these commands run directly against the filesystem:

```bash
fp add-root daisy2026 "$HOME/daisy_2026"
fp scan daisy2026
fp ls daisy2026
fp find receipt --root daisy2026
sqlite3 "$HOME/daisy_2026/catalog.sqlite3" \
  'SELECT path, bytes, hex(sha256) FROM files ORDER BY path;'
```

The SQLite example uses the optional standard `sqlite3` command-line tool;
FileProxy itself needs only Python's built-in SQLite support.
Rerun `fp scan daisy2026` after adding, editing or deleting source files.
It refreshes the database and the plain `files.txt` inventory from the same
scan. The listing contains root-relative file and directory paths, including
empty directories, one per line, in sorted order. A browser can fetch this
listing through ordinary static hosting or IPFS without a FileProxy process.
Metadata and hashes remain in the actual SQLite database; `files.txt` is only
a filesystem projection, not a replacement database.

`scan` owns the generated `files.txt`; it preserves ALP's `.files.txt`, which
may contain manually ordered `source`, `script`, `view` and `directory` entries.
Generated catalogs, SQLite sidecars and `files.txt` listings are excluded from
source hashing and the listing to avoid indexing the index itself.

`fp serve` is optional. Its `/v1/index` reads the same root-local databases on
each request; CLI scans are visible on the next query without a server restart.
The existing `/catalog` page still uses the HTTP service; the plain inventory
can be consumed separately by a static browser. The service does not scan on
startup or watch directories, and it does not synchronize Chisel's separate
transaction index. Existing Chisel-only services need the updated standalone
service to provide these `/v1` reads.

Other CLI actions:

```bash
python3 fp.py cat daisy 2026/42/1/01/receipt.txt
python3 fp.py put daisy /tmp/receipt.pdf 2026/42/1/01/receipt.pdf
python3 fp.py scan daisy
# Paste a URL from the terminal through the same intake pipeline:
python3 fp.py ingest "https://www.lagunapueblo-nsn.gov/wp-content/uploads/2021/02/Form-211-Business-Registration-Application-Rev_2_20_19.pdf"
# Or pipe clipboard/text into the intake pipeline:
# cat paste.txt | python3 fp.py ingest --destination certledger
# Export SB Shell navigation from its myshell subtree to sbshell/files.txt:
python3 fp.py inventory sbshell myshell --output files.txt
python3 -m unittest discover -s tests -v
```

`put` refuses to overwrite an existing file unless `--overwrite` is
explicitly supplied. Binary files are handled as bytes. SHA-256 and size
are recorded when you run `scan`.

To use the minimal Bash wrapper, source `shell/fp.sh` (it defaults
`FILEPROXY_HOME` to the component directory when sourced). The CLI itself is Python
stdlib only and does **not** require Node.js, npm, Bun or Deno.

## The Daisy naming convention

For example:

```text
daisy/
  2026/
    42/
      1/
        01/
          receipt.pdf
      2/
  2027/
```

FileProxy does not force ordinal naming on files. When the relative path
starts `YYYY/WW/D/...`, the catalog additionally records `year`,
`isoWeek` and `isoDay`. Chronological names stay in Daisy; a FileProxy
record ID stays portable, e.g. `daisy:2026/42/1/01/receipt.pdf`.

To index a CertLedger case without copying it to Daisy, register the
CertLedger repository as its own root. To centralize its data later, copy
the source artifact into Daisy deliberately and rebuild the catalog;
don't silently relocate files.

## Run the unified HTTP service

By default the existing Chisel HTTP implementation listens on
`127.0.0.1:7799`:

```bash
export CHISEL_FILE_HOST=127.0.0.1
export CHISEL_FILE_PORT=7799
# If you use an existing Chisel checkout, preserve its current paths:
export CHISEL_FILE_ROOT="$HOME/chisel"
# Optional: point to the actual existing Chisel data directory:
# export CHISEL_DATA_ROOT="$HOME/daisy/2026/chisel-data"
export FILEPROXY_WRITE_TOKEN="choose-a-long-random-local-token"
python3 fp.py serve
```

Check:

```bash
curl http://127.0.0.1:7799/ping
curl http://127.0.0.1:7799/v1/health
curl 'http://127.0.0.1:7799/v1/index?root=daisy&limit=20'
curl 'http://127.0.0.1:7799/v1/file?root=daisy&path=2026%2F42%2F1%2F01%2Freceipt.pdf' -o receipt.pdf
```

Read operations do not require a token on the local HTTP listener. By default,
general-purpose mutation routes require `FILEPROXY_WRITE_TOKEN`:

```bash
curl -X POST http://127.0.0.1:7799/v1/scan \
  -H 'Content-Type: application/json' \
  -H "X-FileProxy-Token: $FILEPROXY_WRITE_TOKEN" \
  -d '{"roots":["daisy","certledger"]}'
```

`POST /v1/put` accepts `{"root":"daisy","path":"...","text":"..."}` or
base64 bytes via `"base64"`; setting `"overwrite":true` is required
to replace an existing file. The catalog is rebuilt separately.

For a local Inbox without tokens, stop the running service and start:

```bash
cd ~/mogwai/fileProxy
python3 fp.py serve --local
```

`--local` forces the listener to `127.0.0.1`, even if `CHISEL_FILE_HOST`
specifies another address. Tokenless `/v1` writes must come directly from
loopback with a localhost Host header and, when present, a matching Origin.
Cross-site browser requests, non-loopback connections, and requests carrying
proxy forwarding headers still require a token. Use this mode directly at
`http://127.0.0.1:7799/`, rather than through a reverse proxy. A page hosted on
GitHub Pages is a different origin and still needs a write token.

`GET /v1/health` reports `writeMode` (`local` or `token`) and
`writeTokenRequired` for the requesting client. The Inbox uses that response
to hide the token field in local mode. Ordinary `fp serve` retains the
existing token requirement; it never enables tokenless writes implicitly.

**Security boundary:** The unmodified Chisel legacy routes `/save`,
`/mkdir`, `/delete`, `/save-tx`, etc. do **not** enforce the new v1
write token. Legacy routes have permissive CORS. Do not bind this server to
a public address or expose these routes through an unauthenticated reverse
proxy. Even `/v1/file` allows any HTTP client that can reach the listener
to read from every configured root. Protect access outside localhost.

### Legacy Chisel routes remain available

The original ~3,000-line `tools/fileProxy/proxy.py`, editor module and
editor HTML were imported verbatim from `johnrigler/chisel` on
October 12, 2026. Examples: `/ping`, `/config`, `/list`, `/load`,
`/raw`, `/save`, `/save-tx`, `/tx`, `/txids`, `/tx-index`,
`/reindex`, `/main-stream`, `/main-streams`, `/save-links`,
`/import-jist-feed`, `/save-evm-tx`, `/save-evm-batch` and
other Chisel endpoints.

To run *only* the original Chisel service from this repository, use
`python3 tools/fileProxy/proxy.py`. To serve Chisel **and** the general
API on one port, use `python3 fp.py serve`. Do not run both simultaneously
on the same port.

For the preexisting Chisel integration and deployment configuration, see
[Chisel's fileProxy README](https://github.com/johnrigler/chisel/blob/main/tools/fileProxy/README.md).
A cutover of an existing server should be tested on a separate local port
before changing Apache proxy routing.


## Filename and recursive web-page policy

All **new generated** FileProxy artifact paths are whitespace-free. Auto-import
converts names such as `Legal%20Filing%20Final.pdf` to
`Legal-Filing-Final.pdf` without modifying PDF bytes. The original filename
and source URL remain in the provenance sidecar. Explicit `fp put` or
`POST /v1/put` writes now reject whitespace-containing destination paths.
Existing/historical files are not bulk-renamed and remain readable.

The server also serves **http://127.0.0.1:7799/catalog**, a recursively
browsable directory index generated from FileProxy's existing catalog.
It includes a **Print listing / Save PDF** action and whitespace-free suggested
filename. Printed catalog PDFs are separate derivative artifacts; only hash
the PDF that was actually produced. Listings are presently limited to the
first 1,000 matching catalog records.

See [Naming and PDF convention](docs/NAMING.md).

## Arrange files and print a response

Open `/catalog`, choose the data root, and browse to a case folder. Clicking a
file name or **Preview** shows text (including extensionless shell scratch
files), a scan, a PDF, or a sandboxed HTML preview. **Download copy** retrieves
the original bytes. HTML previews do not run document scripts or load remote
resources. Raw HTML/SVG responses are sandboxed too.

**Delete** confirms the exact root/path and moves that one file into the
root's hidden `.fileproxy-trash` directory. **Undo delete** restores it.
Deletion verifies the catalog SHA-256 and refreshes the SQLite catalog and
`files.txt`; changed files must be rescanned and previewed again. Restore
refuses to replace a newly created file. Hidden files, symlinks, directories,
catalogs and generated inventories cannot be deleted through these controls.
**Rescan folder root** refreshes the root after changes made outside the GUI.
Writes follow the same local-mode or write-token policy as the Inbox.
Stop the old server and start the updated checkout:

```bash
cd ~/mogwai/fileProxy
python3 fp.py serve --local
```

No `pip install` step or `fp` alias is needed. The server and saved HTML use
Python's standard library. If you want the optional Bash wrapper, source
`shell/fp.sh` in your shell.

For ordinary directory work, select file checkboxes or **Select PDFs / images**.
Selections remain while you browse folders within the same data root. Use
**Up / Down** to set their order, choose a destination, and tap **Copy**, **Move**,
or **Copy in order**. **New folder** offers a `response-1` style name so this can
be done without typing. Copy in order writes `001-`, `002-`, etc. filenames,
continuing after any existing numbered files. Existing destination files are
never overwritten. Source hashes are checked before copying or moving, and
the catalog and `files.txt` are refreshed. `.files.txt` is left alone.

To combine a letter with existing enclosures:

1. In the case folder, tap **Arrange response** and select the existing
   response HTML/text. Edit the letter fields in the preview.
2. Tap **Add all from folder** for the NCS subdirectory, or **Add enclosure**
   for individual PDFs or scans. The folder button uses natural numeric order.
   Thumbnails appear beside image files and on the first page of PDFs; tap
   one to inspect the source. Adjust with **Up / Down** and enter an optional
   caption. Clear the caption to leave the scan uncaptioned. No Exhibit A/B
   scheme is imposed. Saved response folders are hidden by default to avoid
   adding their copied sources and rendered pages again. Enable **Show saved
   response folders** to include those files deliberately.
3. For each added document, choose **Place this document**: after a paragraph,
   heading or table, or **At end of document**. Inline markers show its place
   in the narrative. Documents at the same position follow the added-list
   order. Changing the response source resets placements for the new text.
   Only added files appear in the document index; old enclosure, scan and
   source-index pages are omitted when importing a previous packet.
4. Tap **Save response folder**. It saves `index.html` (the printable view),
   `letter.html` (the edited letter), and numbered copies of the actual files
   in a new folder. Originals stay in place. The document index lists the
   documents and page counts, plus your assembly note. Source hashes remain
   in the catalog and are checked during copying; they are not printed in
   the recipient's document. Document placement does not establish that an
   old draft was sent; use the actual mailing and delivery records for that.
5. Review the saved view, then tap **Print / Save PDF** to use your browser's
   print dialog. The catalog's **Print listing** button prints the directory
   listing; the response has its own print button.

The saved view uses relative file links and inline styles. FileProxy serves
it at `/v1/fs/ROOT/path/index.html`; the folder can also be served by an ordinary
web server. Open the saved folder and use `letter.html` as the source for the
next response, so the next version can build on the previous one.

Image enclosures print directly. For PDF enclosures, FileProxy calls the
existing shell command `pdftoppm` to make page images under `pages/` for the
browser's printable view. It retains the original PDF bytes alongside them.
There are no Python PDF/image packages. PDF page images are rendered at
150 dpi with a 2,200-pixel size limit; browser printing produces a new PDF.
Copy/Move work even without PDF tools. If `pdftoppm` is missing or fails, saving
the printable response stops with an explanation and keeps the source files.
PDF thumbnails use the same command to render only the first page at 240
pixels and are cached in memory. If unavailable, the thumbnail offers an
ordinary PDF link; image thumbnails and file selection still work.

A file must still match its selected SHA-256 before it is included. A failed
save leaves no partial response folder. Unfilled `[FIELD]` markers leave the
letter labeled **DRAFT**. Review page breaks and the actual saved printout.

## Web inbox: paste-to-CertLedger intake

Start FileProxy as a local HTTP service, then open **http://127.0.0.1:7799/**.
The home page is a mobile-friendly paste box that previews classification and
lets you explicitly import URLs or pasted plain text.

On the machine serving FileProxy, first register the data repositories that
actually exist locally:

```bash
cd ~/mogwai/fileProxy
python3 fp.py add-root certledger "$HOME/certLedger"
python3 fp.py add-root daisy "$HOME/daisy"
export CHISEL_FILE_HOST=127.0.0.1
export CHISEL_FILE_PORT=7799
python3 fp.py serve --local
```

In local mode the Inbox imports without a token. If you instead start with
`fp serve`, set `FILEPROXY_WRITE_TOKEN` in that server's environment and enter
the same value in the page's **Local write token** field. The page keeps it
only in memory while open; it is not stored in browser local storage.
The web page is served directly by the unified Python service, **not** by
GitHub Pages. A private repository does not create a public hosted site.
If port 7799 is in use by your running Chisel FileProxy, test on 7800 via
`CHISEL_FILE_PORT=7800` instead, with the matching browser URL.

Paste this real-world fixture to preview the automatic CertLedger route:

```text
https://www.lagunapueblo-nsn.gov/wp-content/uploads/2021/02/Form-211-Business-Registration-Application-Rev_2_20_19.pdf
```

FileProxy classifies the URL as
`certledger / regulatory/business-registration` and, **only when you press
Process and import**, downloads the HTTPS original into a configured
`certledger` root at:

```text
inbox/<ISO-year>/<ISO-week>/<ISO-day>/<sha256-prefix>-<original-filename>.pdf
```

A sibling `.record.json` stores source/resolved URLs, retrieval timestamp,
full SHA-256, MIME type, size, classification, any user note, and the
`unreviewed` status. Any extracted PDF page count is optional and requires
`pypdf`; the original bytes do not depend on PDF parsing.
The SQLite catalog is rebuilt after import. Re-importing identical bytes avoids
replacing existing content. All inputs remain unreviewed; URL classification
does **not** amount to verification of the legal authority or current validity
of a form.

The intake supports up to five HTTPS links per paste, or an ordinary text
note without a link. Auto-routing defaults to Daisy for material without
legal/regulatory markers, or you can select a registered destination manually.
If the intended root is not registered, FileProxy refuses to import instead
of silently writing somewhere else.

For an annual archive registered as `daisy2026`, automatic Daisy imports use
that current ISO-year root when `daisy` is not registered. The alias
`daisy_2026` is also supported. The Inbox preview uses the server's resolved
destination and archive year. Earlier years and unrelated roots such as
`work` are never guessed as a fallback. Explicit destinations and hashtags
keep their exact names: remove an old `#daisy` tag or replace it with
`#daisy2026` when using the annual root.

**Network security:** remote import is intentionally limited to HTTPS,
standard port 443, and public DNS-resolved hosts (the connection is pinned to
the verified address). Redirects are rechecked, documents are capped at
12 MiB, and requests have a timeout. These limits do not turn arbitrary
documents into trusted sources. Both the web inbox and legacy Chisel endpoints
remain appropriate for a loopback server, **not** an unprotected public site.

The example source is a Pueblo of Laguna Tax Administration Division business
registration form with reverse-side instructions. It is an *unfilled form*,
not an issued approval or evidence that a particular business has registered.

## Current boundaries / not yet implemented

There is no automatic GitHub push, IPFS or blockchain publication; no live
file watching; no moving of CertLedger originals; and no Mogwai rendering
UI in this release. The catalog is a derived **SQLite** index, updated by
`scan` and publishable as an actual database file inside its archive.
An index entry's SHA-256 is content identity, not evidence of author or
receipt by another party.

The `fileProxy-node` repository is an older separate implementation;
this project uses the Chisel Python service for compatibility.

## Public document watch ingestion

Mogwai's read-only watcher can detect changes to public sources, but **byte
changes are not legal events**. FileProxy should separately ingest and hash
reviewed official documents into a registered, correctly scoped Daisy root.
See [Dossier/watch ingestion](docs/DOSSIER-WATCH-INGEST.md), including
`daisy_2026` setup and the distinction between observed hashes and preserved
original evidence bytes.

## Future: per-chain databases

A possible later design would keep **separate SQLite catalogs for Bitcoin,
Litecoin, Dogecoin, Solana, etc.** and one or more **gatekeeper SQLite
registries** pointing to them. This is a recorded idea, not the current
implementation. See [per-ledger SQLite roadmap](docs/LEDGER-DATABASE-ROADMAP.md).
