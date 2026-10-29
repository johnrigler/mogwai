# Paper label lookup

Chisel's RECORD scanner uses one complete 16-hex identifier for a physical
folder or collection. FileProxy resolves it in Daisy, current ISO year first,
then earlier configured years. All matches in the newest matching year are
returned. Future years are skipped; unavailable roots are reported.

Configure `projects.daisy_2026.path`, `projects.daisy_2025.path`, etc. in
`~/config.json`. FileProxy also accepts explicit `daisy2026`/`daisy_2026`
roots or a generic `daisy` root with `YYYY/` children. Explicit year mappings
win over shared paths. Daisy itself needs no Mogwai initialization.

An existing folder needs a plain ASCII `record-id` file containing its complete
identifier. Add a description in `README.md` and actual scans beside it or in
subdirectories. A directory named exactly for the ID also works. A present
marker takes precedence. Existing files need not move; no source is executed.

```bash
python3 ~/mogwai/fileProxy/fp.py record 0123456789ABCDEF
python3 ~/mogwai/fileProxy/fp.py serve --host 127.0.0.1 --port 47799
```

Open `http://127.0.0.1:47799/record?id=0123456789ABCDEF`, or Chisel's
**SCAN RECORD**. The viewer lists actual source bytes with full SHA-256,
previews images/PDFs/text and offers original downloads. New source files
appear on the next lookup. Reads do not write catalogs, commit, anchor or
publish anything. The existing SQLite `scan` workflow is unchanged.

`--home-config FILE` selects another shared config; place it before the
subcommand. Shared home paths are private to the new record reads and do not
become roots in `/v1/roots`, `/v1/index` or `/v1/file`.

## Private reads

`/v1/record` and `/v1/record-file` accept same-origin loopback requests.
Forwarded, cross-origin or remote requests require a dedicated Bearer token.
Set `serve --record-token-file FILE` to read it from a local file outside Git.
The viewer retains the password field only in page memory. Use HTTPS remotely.
Existing explicitly registered roots retain their general API behavior;
this guard does not turn legacy endpoints into protected storage.

Reads stay within the matched folder, exclude hidden/generated files and
skip symlinks. Same-year collisions remain separate results. This short label
is a locator. The viewer's SHA-256 comparison checks its current listing,
not a historical on-chain commitment. GitHub/IPFS retrieval and automatic
wallet matching remain separate work.

See Chisel's [physical-record workflow](https://github.com/johnrigler/chisel/blob/main/docs/physical-records.md),
including the proposed wallet-only Litecoin/satoshi-code reference path.
