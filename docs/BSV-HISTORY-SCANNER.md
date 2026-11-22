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

The working database is `~/.local/state/mogwai/bsv-index.sqlite3`. Every checked
transaction retains its ID, size, data-byte count, block/index and timestamp.
Raw public-provider JSON is retained only for selected candidates. Database
state, lock files and logs remain outside the repository. `--db` selects a
different scan database. Thresholds are saved per database; use a separate
database to scan under different thresholds, so earlier coverage stays accurate.

## Publish a Chisel feed

Choose the filesystem directory that Apache exposes as
`https://rigler.org/chisel-data/bsv/`. Adjust the example path below to the
existing Apache `/chisel-data/` alias. Use a separate BSV subdirectory; the
general dataset has its own manifest.

```bash
BSV_EXPORT_DIR=/path/to/chisel-data/bsv
python3 "$HOME/mogwai/tools/bsv_indexer.py" scan --export-dir "$BSV_EXPORT_DIR"
```

`--export-dir` writes public candidate transactions, a ranked index, and
`scan.json` coverage/notes. The manifest is replaced atomically after the
immutable index snapshot and raw transaction files are ready. The largest
1,000 candidates are exported by default; `--limit` changes that presentation
limit without dropping scan history from SQLite. Index snapshots remain for
readers holding an earlier manifest; archive/prune old snapshots as needed on
a long-running host. Dataset files are public read-only files (mode 644).

Chisel 2.8.67 loads this manifest in addition to the general dataset. Its BSV
filter shows candidates and byte counts. Expand **BSV scan coverage** for
completed/partial blocks, ranked data-byte totals, next block, timestamps and
errors. Refresh the portal for newly exported results. The bundled sample
remains browsable if rigler.org is unavailable.

For a standalone static/IPFS copy, use the exported directory as `data-bsv/`
beside Chisel's `index.html`, or add its manifest to
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
python3 "$HOME/mogwai/tools/bsv_indexer.py" daemon --export-dir /path/to/chisel-data/bsv
```

Replace the example with the filesystem directory Apache already exposes at
`https://rigler.org/chisel-data/bsv/`. No host path is inferred from a URL.
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

### Keep it running as a user service

Mogwai includes a user-systemd unit. Set the real public export directory in
`~/.config/mogwai/bsv.env` before enabling it:

```bash
mkdir -p "$HOME/.config/mogwai" "$HOME/.config/systemd/user"
cp "$HOME/mogwai/config-examples/bsv.env.example" "$HOME/.config/mogwai/bsv.env"
# Edit BSV_EXPORT_DIR in that file to match the existing Apache alias.
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
