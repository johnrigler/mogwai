# Whitespace-free filename contract

Applies to generated HTML, PDF, JSON, scan, and catalog artifacts in FileProxy
and to new files in the project's filesystem-based publishers.

## Filename and path rules

- No spaces, tabs, newlines, or other whitespace in **generated** file or
  directory names. Preferred ASCII characters are `A-Z a-z 0-9 . _ -`.
- Use `-` to separate words, `_` for deliberate ordinal subdivisions, and
  keep conventional extensions: `.html`, `.pdf`, `.json`, `.png`.
- Paths use `/`, and ordinal fields should be zero-padded when their lexical
  ordering matters: `01`, `02`, `10`.
- Human-readable document titles, notes, signatures, and addresses **may**
  contain spaces. The restriction is for filesystem and URL path components,
  not the contents of a document.
- A root-qualified FileProxy path is `<root>:<relative-path>`. For example:
  `certledger:inbox/2026/42/1/01-Business-Registration.pdf`.
- Automatically ingested filenames are normalized, not merely URL-encoded.
  `Legal%20Filing%20Final.pdf` becomes `Legal-Filing-Final.pdf` in the store.
  The original URL and source basename, including spaces, remain in sidecar
  metadata. File content is preserved unchanged.
- Explicit FileProxy `put` operations reject whitespace in the requested
  destination instead of silently changing a caller-supplied path.
- **Do not bulk-rename historical files.** Existing files with spaces can
  still be discovered, hashed, or read. A deliberate migration must update
  referring manifests and URLs and preserve old identity information.
- A path being space-free does not make it trustworthy or cryptographically
  authenticated.

## Directory views are documents too

`/catalog` renders the registered FileProxy roots as a hierarchical
filesystem projection. Directories may be followed recursively, and the
display is formatted for US Letter PDF printing. The HTML view is generated
from the derived catalog and can be rebuilt from source files.

Use **Print / Save PDF** from the catalog. The page suggests a title such as
`fileproxy-catalog-certledger-inbox-2026-42-1.pdf`. A browser's print
dialog may still allow a human to override that name. The output is a
**catalog report**, not the canonical underlying source PDF. The recursive
view currently reads up to 1,000 catalog entries; when it reaches the limit,
it displays a truncation warning and must not be treated as exhaustive.

A directory view is a representation of a tree, not a recursive inclusion
of every binary file. The report should describe its contents with links,
names, and hashes. It does not embed every source PDF in one PDF.

## Canonical PDF to ledger

For CertLedger, use this ordering:

1. Render and finalize the original document.
2. Export to `<case>-<ordinal>-canonical.pdf` (no spaces).
3. Freeze the **byte-exact PDF** and compute SHA-256 on those bytes.
4. Keep the hash and source/provenance metadata in FileProxy.
5. Use Chisel to commit that SHA-256 digest to the selected ledger when
   the record is ready; FileProxy by itself performs no blockchain write.
6. Preserve any later scanned, signed, printed or labeled version as a
   **different artifact**, with its own filename and SHA-256 hash.

A filename is a filesystem convention, not part of the PDF content. Merely
renaming a PDF does not change the SHA-256 of its bytes, whereas printing or
exporting HTML to PDF creates new bytes and therefore a different hash.
Never put the final digest inside its own byte-identical canonical PDF:
that creates the circular hash problem already documented in CertLedger.
