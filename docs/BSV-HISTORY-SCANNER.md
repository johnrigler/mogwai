# BSV history scanner

`tools/bsv_indexer.py` walks backward through BSV mainnet blocks and measures
each transaction. It uses Python's standard library and needs no BSV, wallet,
FileProxy service, API key, or installed packages. A public-provider plan may
still impose limits. Requests are paced and HTTP 429/temporary failures back
off. Each invocation has a transaction budget and a completed-block budget.

The default selection is transaction size **at least 1,024 bytes** OR pushed
OP_RETURN data **at least 128 bytes**. Coinbase transactions are measured but
excluded from candidates. Size identifies a candidate, not a known file format:
a large transaction can simply have many payment inputs or outputs. B://,
BCAT, and 1Sat reconstruction remain separate reader work.

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
Use `--stop-height` to set the oldest block to visit. Supply it on each
invocation that should honor that boundary. Pre-fork history is shared with
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

## Background operation

After verifying one export, use a cron invocation every minute. Substitute the
actual export directory. The first run creates the state/log directory.
Overlapping runs skip under a nonblocking file lock. A stopped/failed run
resumes from its last committed batch. A large block can take many runs; the
scanner does not skip its remaining transactions when its budget runs out.

```cron
* * * * * /usr/bin/python3 "$HOME/mogwai/tools/bsv_indexer.py" scan --max-transactions 200 --export-dir /path/to/chisel-data/bsv >> "$HOME/.local/state/mogwai/bsv-indexer.log" 2>&1
```

The job scans backward from its initial anchor; it does not also monitor new
tip blocks. Remove the cron entry to pause it. The script does not install a
cron job or perform blockchain writes.

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
  The six-block lag reduces reorg exposure; this explorer-backed historical scan
  does not continuously revalidate old forks.
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
