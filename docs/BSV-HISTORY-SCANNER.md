# BSV history scanner

`tools/bsv_indexer.py` measures BSV mainnet transactions and has both bounded
`scan` invocations and a continuous `daemon` command. It uses Python's standard library and needs no BSV, wallet,
FileProxy service, API key, or installed packages. A public-provider plan may
still impose limits. Requests are paced and HTTP 429/temporary failures back
off. Each invocation has a transaction budget and a completed-block budget.

The default selection is transaction size **at least 1,024 bytes** OR pushed
OP_RETURN data **at least 128 bytes**. Coinbase transactions are measured but
excluded from candidates. Size identifies a candidate, not a known file format:
a large transaction can simply have many payment inputs or outputs. B:// file
metadata is now indexed from push boundaries: MIME type, filename, output,
declared byte count and completeness. JPEG/PNG/GIF/WebP signatures identify
images even when truncation hides later MIME metadata. BCAT and 1Sat
reconstruction remain separate reader work.

## Run on rigler.org

Pull Mogwai main, then start a bounded historical scan:

```bash
cd "$HOME/mogwai"
git pull --ff-only
python3 tools/bsv_indexer.py scan --blocks 5 --max-transactions 200
python3 tools/bsv_indexer.py status
```

The first invocation starts six blocks behind the current tip. Later invocations
resume the saved backward cursor. To begin at a particular historical block,
add `--start-height 575045` on the first invocation. A different explicit start
opens a new backward segment in the same database; the report lists only blocks
actually visited, never claims that gaps between segments were checked.
Use `--stop-height` to set the oldest block to visit. The boundary is saved
with the job and reused when later invocations omit it. Pre-fork history is shared with
other Bitcoin chains; these records are sourced from BSV mainnet.

`nextHeight` stays on the same block until all of its transactions are checked.
The default budget is **200 transactions per invocation**, so a block with
50,000 transactions needs 250 default-budget runs. Each run resumes at its
saved zero-based transaction index; it does not start that block again.
`blocksThisRun` shows each block's `startTransactionIndex`,
`nextTransactionIndex`, `transactionsTotal` and `checkedThisRun`. The `jobs`
section in both `scan` and `status` includes a readable `progress` line and
`currentBlock` counts, for example **400/527 transactions checked; next
transaction index 400**. The next invocation starts at index 400. When the
block is complete the job moves to the next height; `currentBlock` is null
until that next block is visited. A job waiting at the confirmed head or its
saved stop boundary also has no current block.

An unchanged height with increasing transaction counts is normal progress.
If the transaction index also stays unchanged, check `checkedThisRun`,
`lastError` and the command's exit status. A failed provider request retains
the last committed batch for retry. Use the same `--db` on every invocation;
the `jobs` section distinguishes independent named cursors. The continuous
`daemon` command below repeats bounded passes automatically.

The working database is `~/.local/state/mogwai/bsv-index.sqlite3`. Every checked
transaction retains its ID, size, data-byte count, block/index and timestamp.
Raw public-provider JSON is retained only for selected candidates. Database
state, lock files and logs remain outside the repository. `--db` selects a
different scan database. Thresholds are saved per database; use a separate
database to scan under different thresholds, so earlier coverage stays accurate.

## Inspect transaction files with Linux commands

Both `scan` and the background daemon now default to `~/chisel_data` as the
canonical data root. Each qualifying transaction is saved as:

```text
~/chisel_data/transactions/bsv/<64-hex-txid>.json
```

The scanner creates that directory and writes original public-provider JSON
after each committed batch, including partial blocks. The filename deduplicates
transactions from both scan directions. Existing files are preserved without
changing their contents or modification times. Files already saved in SQLite
are backfilled on startup and export without querying the chain again.

```bash
cd "$HOME/chisel_data/transactions/bsv"
find . -maxdepth 1 -type f -name '*.json' | wc -l
du -sh .
ls -lt | head
```

The folder contains **all selected candidates**, independently of the portal's
1,000-record display limit. A batch containing no qualifying candidate can
advance the checked transaction index without adding a file. Use the saved
status for the total number of transactions checked. An offline backfill is:

```bash
python3 "$HOME/mogwai/tools/bsv_indexer.py" export
```

`--data-root /actual/chisel_data` or the `CHISEL_DATA_ROOT` environment setting
selects another root. If Apache serves another directory at `/chisel-data/`,
set that actual filesystem path. The scanner does not configure Apache.

## Publish a Chisel feed

The default feed is `~/chisel_data/bsv/`, next to the shared `transactions/`
directory. It is intended for Apache's
`https://rigler.org/chisel-data/bsv/` URL. The general dataset has its own
manifest, which the scanner leaves intact. `scan`, `daemon` and `export`
publish this BSV feed automatically; `--export-dir` can override its location.

```bash
BSV_EXPORT_DIR="$HOME/chisel_data/bsv"
python3 "$HOME/mogwai/tools/bsv_indexer.py" scan --export-dir "$BSV_EXPORT_DIR"
```

The BSV feed contains a ranked index, `scan.json` coverage/notes and a manifest.
Its rows reference `../transactions/bsv/` in the shared archive. The manifest is
replaced atomically after the immutable index snapshot and raw transaction
files are ready. The largest 1,000 candidates appear in the index by default;
`--limit` changes that presentation limit without dropping any candidate files
or scan history from SQLite. Index snapshots remain for
readers holding an earlier manifest; archive/prune old snapshots as needed on
a long-running host. Dataset files are public read-only files (mode 644).

Chisel 2.8.67 loads this manifest in addition to the general dataset. Its BSV
filter shows candidates and byte counts. Expand **BSV scan coverage** for
completed/partial blocks, ranked data-byte totals, next block, timestamps and
errors. Refresh the portal for newly exported results. The bundled sample
remains browsable if rigler.org is unavailable.

For a standalone static/IPFS copy, export to a directory **outside** the
canonical data root. That export includes its indexed raw transactions locally
under `transactions/bsv/`. Use it as `data-bsv/` beside Chisel's `index.html`,
or add its manifest to
`staticDiscoveryManifestPaths` in `chisel.portal.config.json`. Apache must
allow cross-origin GETs from Chisel's origin, as the parent `/chisel-data/`
directory already does. Scanning and static portal reads run independently of
FileProxy. This release also adds BSV to FileProxy's existing record activity
and share-page currency lists; restart that service after pulling Mogwai if
you use shared activity/comments or social previews for BSV records.

## Transaction exploration

Chisel 2.8.71 record pages include a chain-scoped search panel, **Images only**,
and a **This block** pivot. File searches cover loaded catalog entries, not the
entire chain. B:// file inventories show incomplete previews; **Load image**
reads the complete output explicitly from WhatsOnChain and checks it against
the saved prefix before displaying a Blob image. Export recomputes file
metadata from saved transaction JSON, so older databases need only an export
to gain image search tags. No rescanning or database migration is necessary.

Starting the Mogwai/FileProxy daemon does not start this scanner; the BSV
scanner has its own service described below. FileProxy
health and the separately published BSV scanner feed appear independently in
the record panel. A missing `/chisel-data/bsv/scan.json` means Chisel cannot
observe scanner coverage, even when FileProxy is connected.

## Continuous two-cursor daemon

The BSV daemon is separate from FileProxy and can run with no browser open:

```bash
python3 "$HOME/mogwai/tools/bsv_indexer.py" daemon
```

The default feed is `~/chisel_data/bsv/`; set `--data-root` if Apache exposes
another filesystem directory at `/chisel-data/`. No host path is inferred from a URL.
A missing feed is not evidence that the process is running or stopped.

One process alternates two independently saved jobs using one rate-limited
provider and one SQLite transaction store:

- `recent`: starts six blocks behind the current tip and walks backward toward
  the historical anchor.
- `early`: starts at [the Alice anchor](BSV-ALICE-ANCHOR.md), block **566492**,
  and walks forward. After reaching the confirmed head it waits and resumes
  when new confirmed blocks become available.

Each job gets its own budget of 200 transactions / 5 completed blocks per pass.
The process waits 60 seconds between passes by default (`--interval`). Existing
complete/partial block rows are shared, so overlap cannot duplicate transaction
rows or reported coverage. When both ranges meet and every block between their
anchors is complete, the daemon joins them and the forward job follows new
blocks. It does not infer complete coverage across a gap.

Both cursors survive restarts. A legacy single cursor migrates to a named
`history` job and retains its records; the daemon adds `recent` and `early`.
Provider failures retain the partial transaction offset, report the affected
job, and allow the other job to proceed. SIGTERM/SIGINT stop between batches,
export committed work, and release the process lock. An interrupted HTTP read
may take up to its timeout. A forced kill resumes from the prior committed
batch. Selection thresholds remain fixed per database.

`--once` runs one bounded daemon pass for setup verification. A different
`--anchor-tx TXID` resolves that confirmed transaction's block. Alternatively,
`--anchor-height HEIGHT` sets a block directly. An existing daemon's saved anchor
cannot silently change; use another `--db` for a different historical segment.

### Start and stop in the background with Bash

No service installation is required:

```bash
cd "$HOME/mogwai"
git pull --ff-only
bash tools/bsv-start.sh
bash tools/bsv.sh status
bash tools/bsv-stop.sh
```

Start detaches the two-cursor daemon with `nohup`, so it continues after the
terminal disconnects. Start is idempotent; it refuses a second scanner using
the same database. Stop sends SIGTERM and waits up to 45 seconds for the
current request and final export. It does not force-kill the process. Starting
again resumes saved checkpoints. These scripts manage the process they
started; use `systemctl --user stop mogwai-bsv.service` for a systemd instance.

The PID and appended log are under
`${XDG_STATE_HOME:-$HOME/.local/state}/mogwai/bsv-daemon/`. Follow the output with:

```bash
tail -f "${XDG_STATE_HOME:-$HOME/.local/state}/mogwai/bsv-daemon/daemon.log"
```

The database defaults to the same `~/.local/state/mogwai/bsv-index.sqlite3`
used by manual `scan` commands. The scripts load optional Bash-compatible
settings from `~/.config/mogwai/bsv.env`: `BSV_EXPORT_DIR` selects the directory
for the feed, `CHISEL_DATA_ROOT` selects the shared transaction root, and
`BSV_DB` can select another scan database. Without these settings, transactions
go to `~/chisel_data/transactions/bsv/` and the feed goes to `~/chisel_data/bsv/`.
After pulling this change, stop and start an existing daemon to switch it from
the earlier private-state export default. No database reset is needed.
Extra start arguments are passed to the daemon, for example:

```bash
bash tools/bsv-start.sh --max-transactions 500 --interval 30
```

These scripts survive logout but do not automatically start after reboot.

### Keep it running as a user service

Mogwai includes a user-systemd unit. Set the real public export directory in
`~/.config/mogwai/bsv.env` before enabling it:

```bash
mkdir -p "$HOME/.config/mogwai" "$HOME/.config/systemd/user"
cp "$HOME/mogwai/config-examples/bsv.env.example" "$HOME/.config/mogwai/bsv.env"
# Edit CHISEL_DATA_ROOT and BSV_EXPORT_DIR to match the existing Apache alias.
cp "$HOME/mogwai/config-examples/systemd/mogwai-bsv.service" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now mogwai-bsv.service
```

For boot operation without an interactive login, enable lingering for the user
(`loginctl enable-linger "$USER"`, subject to host policy). This is an
installation step on rigler.org, not something GitHub publication performs.

```bash
systemctl --user status mogwai-bsv.service
journalctl --user -u mogwai-bsv.service -n 30
python3 "$HOME/mogwai/tools/bsv_indexer.py" status
systemctl --user stop mogwai-bsv.service
```

`status` reads a committed SQLite snapshot without taking the daemon's process
lock. The public `scan.json` includes direction, anchor, next block, phase and
error for each cursor, plus the runner's last reported state and heartbeat.
A saved heartbeat is an observation timestamp, not a live process probe.
Chisel displays these fields in **BSV scan coverage**. Feed export and HTTP
serving remain separate from process supervision.

## Bounded scans and cron alternative

After verifying one export, use a cron invocation every minute. Substitute the
actual export directory. The first run creates the state/log directory.
Overlapping runs skip under a nonblocking file lock. A stopped/failed run
resumes from its last committed batch. A large block can take many runs; the
scanner does not skip its remaining transactions when its budget runs out.

```cron
* * * * * /usr/bin/python3 "$HOME/mogwai/tools/bsv_indexer.py" scan --max-transactions 200 --export-dir /path/to/chisel-data/bsv >> "$HOME/.local/state/mogwai/bsv-indexer.log" 2>&1
```

This single-job cron alternative scans backward from its initial anchor; it
does not also monitor new tip blocks. Use it instead of the daemon, not alongside
a second process contending for the same database lock. Remove the cron entry to pause it. The script does not install a
cron job or perform blockchain writes.

A manual forward cursor can also be advanced with repeated bounded scans:

```bash
python3 "$HOME/mogwai/tools/bsv_indexer.py" scan --direction forward --job early --start-height 566492
python3 "$HOME/mogwai/tools/bsv_indexer.py" scan --direction forward --job early
```

## Inspect or annotate coverage

```bash
python3 "$HOME/mogwai/tools/bsv_indexer.py" status
python3 "$HOME/mogwai/tools/bsv_indexer.py" note --height 575045 --text 'Reviewed data outputs; file reconstruction pending.'
python3 "$HOME/mogwai/tools/bsv_indexer.py" export --export-dir /path/to/chisel-data/bsv
```

Notes added with `note` are public when exported. Chisel's per-transaction
annotation editor remains separate. For exact local audit:

```sql
SELECT height, checked, tx_count, status, error, note FROM blocks ORDER BY height DESC;
SELECT height, tx_index, txid, bytes, data_bytes, data_complete, selected
FROM transactions ORDER BY bytes DESC;
```

## Completeness and provider boundaries

- Each batch and its cursor commit together. Missing, duplicate, or wrong-block
  transactions do not advance that cursor. Complete means the declared number
  of transactions has been checked.
- WoC's initial 100 IDs precede its remaining-ID pages. Bulk lookup uses at
  most 20 transactions and restores block order if the provider reorders them.
- A changed hash at a revisited block discards that block and saved descendants.
  The six-block lag reduces reorg exposure. Changed revisited blocks discard
  saved descendants and rewind affected cursors; this explorer-backed scan
  does not continuously revalidate all old forks.
- WoC truncates large output scripts. `dataComplete: false` and lower-bound
  data-byte counts are preserved. Chisel labels truncated previews. The scanner
  does not silently download large files or claim full reconstruction.
- These are saved provider observations, not independently verified inclusion
  proofs. Imported scan rows do not get Chisel's ledger-verified display status.
  The scanner never executes payload bytes.

Primary API references:

- [Blocks and remaining transaction pages](https://docs.taal.com/core-products/whatsonchain/block)
- [Bulk transaction reads, truncation and full output hex](https://docs.taal.com/core-products/whatsonchain/transaction)

Tests: `python3 -m unittest discover -s tools/tests -p 'test_bsv_indexer.py' -v`.

- [B:// file push layout](https://github.com/unwriter/B)


## Offline artifact classification and cautious pruning

Run the curator against the **same SQLite database and data root** as the
scanner. It performs no network requests, does not advance scan checkpoints,
and defaults to a read-only audit. It examines existing selected JSON in SQLite,
not every Bitcoin SV transaction. The `tools/bsv-curate.sh` wrapper loads
`~/.config/mogwai/bsv.env` just like the scanner launcher. With no config,
the default root is `~/chisel_data`.

```bash
cd "$HOME/mogwai"
bash tools/bsv-curate.sh
```

The JSON report gives candidate counts and on-disk byte totals by category:

- **artifact**: declared B:// MIME type or recognizable JPEG, PNG, GIF, WebP,
  PDF, ZIP, MP4, WebM/Matroska, MP3, WAV, gzip, SVG, or HTML signature.
- **metadata**: B:// or MAP protocol markers, URLs, IPFS references, or
  plausible readable text. Even small pointers are retained.
- **unknown**: truncated scripts or unrecognized nonempty OP_RETURN payloads.
  These are retained, never automatically discarded.
- **discard**: selected transactions without observed OP_RETURN payload data,
  including large ordinary payments selected by transaction size alone.

All matches are heuristic: a MIME signature in a provider preview is not proof
that a complete file has been downloaded. The curator does not reconstruct BCAT
or 1Sat multi-transaction files. No payload bytes are executed.

To publish classification metadata without deleting any transaction files,
stop the scanner, run the enrichment pass, and restart it:

```bash
bash tools/bsv-stop.sh
bash tools/bsv-curate.sh --enrich
bash tools/bsv-start.sh
```

This writes the `bsv_curation` table and adds `summary.curation` to the
published BSV portal records, while preserving all selected archive files.

To apply the classification and safely remove *only* the discard category,
**stop the background scanner first**. The curator takes the scanner's exclusive
database lock and refuses to modify a live scanner database:

```bash
bash tools/bsv-stop.sh
bash tools/bsv-curate.sh --apply
bash tools/bsv-start.sh
```

`--apply` stores metadata in the `bsv_curation` SQLite table, sets
`transactions.selected=0` for discard records, and unlinks matching
`transactions/bsv/<txid>.json` files only if the file itself contains the
matching TXID. It preserves the raw JSON and scan history in SQLite so records
can be restored without another network scan. The scanner's archive backfill
will **not** recreate suppressed files because the selected flag has changed.
It regenerates the BSV portal feed, adding `summary.curation` to retained
records, and writes `bsv/curation.json` with the audit totals.

To restore all curator-pruned records:

```bash
bash tools/bsv-stop.sh
bash tools/bsv-curate.sh --restore
bash tools/bsv-start.sh
```

Restore reselects the retained SQLite rows; the feed export backfills their
JSON files. This is reversible only while the original SQLite database is
preserved. Back up that database before applying pruning. Existing immutable
portal index snapshots may still point to removed archive JSON: clients should
refresh the manifest after a prune. The curator does not delete older snapshots.

Set `--db`, `--data-root`, and `--export-dir` consistently if using
custom paths. The dry run may be used while the scanner is running; application
and restoration require an exclusive lock. If the scanner was started outside
`bsv-start.sh`, stop that actual process before applying changes.

Test classification and reversible archive suppression with:

```bash
python3 -m unittest discover -s tools/tests -p 'test_bsv_curator.py' -v
```

## Import targeted discoveries

Recovered address and Thunderword trails use the existing FileProxy archive,
independently of block-scan coverage. The
[Secret Beach Solutions recovery](https://github.com/johnrigler/fileProxy/tree/main/data/bsv-secret-beach)
contains complete transaction JSON, exact extracted payloads and a real
FileProxy `catalog.sqlite3` with 32-byte SHA-256 BLOBs. Its subject-linked
records include posts from other signing addresses; authorship stays
unconfirmed unless separately established.

After pulling both existing checkouts, import that root:

```bash
bash "$HOME/mogwai/tools/bsv-import.sh" "$HOME/fileProxy/data/bsv-secret-beach"
```

The wrapper reads `~/.config/mogwai/bsv.env` and uses `CHISEL_DATA_ROOT`, just
like the scanner. If the running FileProxy has another canonical data root,
pass its actual path to the Python command:

```bash
python3 "$HOME/mogwai/tools/bsv_recovery_import.py" \
  "$HOME/fileProxy/data/bsv-secret-beach" --data-root /actual/fileproxy/data
```

The importer reads and verifies the published SQLite catalog, copies records
under `transactions/bsv/` and payloads under `artifacts/bsv/<txid>/`, retains
provenance under `bsv/discoveries/`, merges additive main-stream references,
and rebuilds FileProxy's existing transaction index. It preserves local
transaction extension fields and existing stream labels, rejects different
artifact bytes at an occupied path, and can be repeated without duplicate
records. Existing canonical JSON is upgraded with the recovered full output
scripts. Scanner checkpoints and reported block coverage are unchanged.
The block-scan ranked feed remains a projection of scanned blocks; the
imported trails are available through FileProxy's transaction/main-stream
catalogs rather than being presented as scanned coverage.

Tests: `python3 -m unittest discover -s tools/tests -p 'test_bsv_recovery_import.py' -v`.
