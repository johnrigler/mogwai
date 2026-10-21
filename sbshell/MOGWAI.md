# SB Shell → Mogwai

Current implementation: FileProxy and SB Shell are components of Mogwai.
See [the consolidation guide](../docs/CONSOLIDATION.md). Older repository-role
descriptions below record the earlier layout; archive data stays separate.

SB Shell is a local-first publishing/workbench layer for Mogwai.

Current work follows [STANDARDS.md](STANDARDS.md) and [AGENTS.md](AGENTS.md).
The PHP assembler uses its directory directly. The static browser path uses
root files.txt as documented in README.md; the per-directory index.js layout
below is an earlier static design.

The core rule is Unix-simple:

- Bash and vi are first-class authoring tools.
- The filesystem is the document model.
- File and directory names carry order and structure.
- The repository currently contains the working filesystem.
- A directory should remain readable after an edit even when Python, FileProxy, or another helper is no longer running.
- IPFS publication is a later projection of that filesystem, not the editing environment.

## Earlier static directory layout

A browsable directory carries its own checked-in `index.js` manifest.

```
directory/
    index.html   -> shared child renderer
    index.js     # frozen description of this directory
    files...
```

The shared root `index.html` is the renderer. `child.html` points to it, and nested directories may symlink their local `index.html` back to `child.html`.

Because the browser URL remains the nested directory URL, the renderer loads that directory's own:

```html
<script src="./index.js"></script>
```

This removes directory-listing APIs from the document format.

Python, FileProxy, Termux, scanner/fax ingestion, or another tool may regenerate `index.js` after a change. Once that write is complete, the directory is again in a solid state and can be served by an ordinary static HTTP server.

## Ordinal filenames

Content files can use underscore-delimited ordinal fields followed by an optional label:

```
1_01_intro.md
1_02_argument.md
1_02_01_example.md
1_03_graph.md
```

Zero padding is deliberate. Ordinary lexical sorting then agrees with numeric page order without requiring parsing just to sort.

Interpretation:

```
1_02_01_example.md
│ │  │  └─ label
│ │  └──── nested ordinal
│ └─────── position
└───────── page
```

The number of ordinal fields is open-ended. Mogwai consumes leading numeric underscore-separated fields as coordinates. Remaining text is metadata/label.

## Scan ingestion

Scanner output may arrive as:

```
scan_261005-191332_1.png
```

This means source type `scan`, capture time `2026-10-05 19:13:32`, page `1`.

Files sharing the timestamp are treated as one scan event unless later evidence says otherwise. Preserve the original scanner filename as provenance. Mogwai may add packet ordering separately without destroying that identity.

See `mogwai/SCAN-INGEST.md`.

## Optional local service

The existing Python server remains useful as a convenience tool and for future editing APIs:

```bash
python3 /path/to/sbshell/mogwai/server.py .
```

But the static SB Shell representation does not require its `/api/list` or `/api/load` endpoints.

The filesystem remains authoritative. Databases, services, blockchain indexes, and IPFS are projections or transport layers, not the source of truth.
