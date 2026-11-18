# Polygon EVM indexer

This is Mogwai's first scheduled ledger ingester. It carries the existing
Chisel EVM Workbench flow into a host-side job: Etherscan V2 discovers address
transactions, Mogwai packages their original transaction fields, and the
existing FileProxy `/save-evm-batch` route stores them in the shared EVM
catalog. Chisel can then read the cache without each browser querying
Etherscan or a Polygon RPC provider.

The first adapter is Polygon mainnet, chain 137. The roots in
`tools/evm_indexer_roots.json` cover Gomez (Stone Man), Jethro, the M64
symbol dictionary, and the earlier Mogwai contract. Each address has its own
checkpoint and polling interval; the current interval is one minute. The root
list contains public contract addresses, not credentials.

## Incremental scan behavior

- Each run reads the current block, then uses a two-confirmation safe head.
  It requests Etherscan's address-filtered `account/txlist` only for each
  contract address and the unscanned block range. It does not query every block
  or scan transactions for unrelated addresses.
- The first scan bootstraps from FileProxy's saved EVM stream status when that
  address already has indexed transactions. Otherwise it starts at the root's
  configured `startBlock`.
- Each address has an independent block checkpoint and last-transaction
  cursor. Later scans start at the block after that address's last successfully
  saved safe block; pages are deduplicated by transaction hash and written
  through FileProxy's existing EVM packet route. The checkpoint advances only
  after all fetched pages have been saved. Etherscan's list API takes block
  bounds and page/offset rather than a transaction-hash cursor, so the saved
  transaction hash/index is retained for status and audit while the block
  boundary drives the next query.
- The checkpoint and lock live under `~/.local/state/mogwai/`, outside Git and
  the public FileProxy data root. A failed scan retries from the prior
  checkpoint on the next run.
- Etherscan credentials are read from the existing private
  `~/.config/mogwai/etherscan.json` (version 1, chain ID 137). The key is never
  printed. No key needs to be copied into the repository or browser.

Etherscan's account `txlist` endpoint returns normal transactions involving
the queried address, including transaction input. It does not replace an
`eth_getLogs` event scanner or an internal-transaction scanner. If a record is
written to a different contract, that transaction is indexed under that
contract's address root. Add or change roots in the checked-in JSON when the
Chisel contract registry changes.

## Run once

Pull Mogwai main on Rigler, then use:

```bash
python3 "$HOME/mogwai/tools/evm_indexer.py" status
python3 "$HOME/mogwai/tools/evm_indexer.py" scan
```

The scan posts locally to FileProxy at `http://127.0.0.1:7799` by default.
Set `FILEPROXY_URL` if the local service uses a different loopback URL. The
existing FileProxy service must be running. This adds no public query route
and does not require a FileProxy restart because it uses the existing
`/evm-stream-status` and `/save-evm-batch` routes.

## Run every minute

After the one-time scan succeeds, add this line to the Rigler user's crontab:

```cron
* * * * * /usr/bin/python3 "$HOME/mogwai/tools/evm_indexer.py" scan >> "$HOME/.local/state/mogwai/evm-indexer.log" 2>&1
```

The script takes a nonblocking lock so two overlapping cron runs do not scan
the same roots concurrently. Check progress with the `status` command and the log file. Gomez, Jethro,
M64 and the legacy Mogwai root can later be assigned different `pollSeconds`
values without changing the scanner.

## Scope

The indexer keeps discovery provider-specific and FileProxy storage shared.
This change implements only the Polygon/Etherscan adapter; it does not add a
UTXO, Solana, Polkadot, internal-call, or event-log adapter. Those can feed
their own chain-specific discovery results into FileProxy's chain-aware
catalog later.
