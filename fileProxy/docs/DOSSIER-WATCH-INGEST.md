# Source-watch intake to FileProxy (2026-10-12)

FileProxy is a local content/metadata catalog, not the claim interpreter.
Mogwai's `m.watch.py` adapter detects public source-byte changes and can
archive local copies. Those observations are *not* a declaration that a court
filing, permit action or contractual default occurred.

## Register the actual Daisy_2026 checkout

```bash
cd ~/fileProxy
python3 fp.py add-root daisy2026 "$HOME/daisy_2026"
python3 fp.py roots
```

The root label `daisy2026` is deliberately distinct from a registered
`daisy` development repository or a historical CertLedger root. The annual
repository stores `421/01-project-jupiter.record.json`. General Daisy
coordinates use `2026/421` relative to a multi-year root.

## Ingest a *specific* original

For a public official URL reviewed by the operator:

```bash
python3 fp.py ingest 'https://nmcourts.gov/wp-content/uploads/2026/09/Orders-in-Project-Jupiter-air-quality-permit-and-water-cases.pdf' --destination daisy2026
python3 fp.py scan daisy2026
```

FileProxy import normally writes under its generated `inbox/...` path and
creates provenance metadata; it does not silently rewrite the dossier JSON.
Explicit `fp put` may place a previously saved exact blob into a chosen,
whitespace-free destination. Do not commit snapshots or private originals to
public GitHub automatically. Confirm the destination and source access rules.

## Contract

- Original source bytes and the source URL/time are separate from transformed
  HTML, OCR, summary, transcript or print PDF derivatives.
- A full SHA-256 plus byte count identifies captured bytes, not document truth
  or legal authenticity. Keep metadata that identifies issuer and court docket.
- A Watcher hash with `snapshot=null` does not establish local possession.
- `304 Not Modified` means the HTTP server did not send a new representation,
  not a proof that no new filing exists in a separate docket system.
- Only reviewed entries link an exact document to a CertLedger claim.
- A private Oracle force majeure notice is *not* necessarily a filing.
  An IPRA request can cover relevant agency-held nonexempt documents but
  cannot compel a private company's copy merely because reporting mentions it.
- Live `vmstat` or GPU monitor streams are not legal documents by default;
  aggregate and sample them with explicit operator authorization, units,
  interval, device scope and time before archival.

Mogwai source observations can be reviewed and passed to FileProxy. Daisy
retains dated subject records. SB Shell produces the narrative/print view.
Chisel optionally anchors a versioned evidence manifest. No transition
happens automatically when this document is committed.

## Explicit `#daisy2026` route and WWD layout

The paste/CLI routing marker `#daisy2026` selects **only** the registered
`daisy2026` root. For example:

```bash
printf '%s\n#daisy2026\n' 'https://nmcourts.gov/wp-content/uploads/2026/09/Orders-in-Project-Jupiter-air-quality-permit-and-water-cases.pdf' | python3 fp.py ingest
```

For a year-scoped root named `daisy2026` or `daisy_2026`, FileProxy
stores generated inbox files under `421/inbox/...` on ISO Monday
2026-10-12, not `inbox/2026/421/...`. A mismatch between the current
ISO year and the explicitly selected annual root is refused rather than
quietly putting 2027 material into the 2026 repository.

The historical automatic legal/regulatory classifier still selects the
registered `certledger` root when no destination is specified. This is
intentional compatibility. **Use `#daisy2026` or
`--destination daisy2026` to direct new legal work into Daisy**.
The marker alone does not register a root or commit the file to Git.
