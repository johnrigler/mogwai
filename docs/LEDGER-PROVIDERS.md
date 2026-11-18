# Mogwai host-local ledger providers

Mogwai code is updated through Git. Provider endpoints and API keys are
machine-local; never store them in a repository, a browser application, or a
FileProxy-served data root. The host-side Polygon adapter now provides
**read-only** EVM JSON-RPC status and transaction queries. There is no new
transaction signing, broadcasting, or public API service.

## Install on rigler.org or another machine

The maintained, copyable examples for all host-local settings are in
[config-examples](../config-examples/README.md), including a safe installer
for `ledgers.json`, `pinata.json` and FileProxy's local configuration.
The older `tools/ledger-config.example.json` remains available for
compatibility but has fewer network examples.

```bash
git -C "$HOME/mogwai" pull --ff-only
install -d -m 700 "$HOME/.config/mogwai"
if [ ! -e "$HOME/.config/mogwai/ledgers.json" ]; then
    install -m 600 "$HOME/mogwai/tools/ledger-config.example.json" \
        "$HOME/.config/mogwai/ledgers.json"
fi
${EDITOR:-vi} "$HOME/.config/mogwai/ledgers.json"
chmod 600 "$HOME/.config/mogwai/ledgers.json"
python3 "$HOME/mogwai/tools/ledger_config.py" check
```

The example only demonstrates the structure. Replace example endpoint URLs
with working provider URLs. The Digibyte URL is a placeholder, not a working
service. Polygon is EVM chain 137. Each network can specify a read endpoint
and an optional broadcast endpoint; provider APIs have different request
formats, and this config does not make them interchangeable.

The checked-in sample config uses `https://polygon.drpc.org`, listed in
Polygon's current public RPC documentation, without a key. Polygon announced
that its previous `https://polygon-rpc.com` endpoint would be deprecated
on July 31, 2026. Existing private configs are not overwritten by Git pulls;
if you copied an older example, manually replace that old URL with
`https://polygon.drpc.org` or a provider you trust. API key handling varies by provider; header-based providers can use:

```json
{
  "family": "evm",
  "chainId": 137,
  "network": "mainnet",
  "read": {
    "url": "https://provider.example/rpc",
    "apiKeyEnv": "POLYGON_RPC_API_KEY",
    "apiKeyHeader": "X-API-Key"
  }
}
```

For a provider using bearer authentication, use
`"apiKeyHeader": "Authorization"` and `"apiKeyPrefix": "Bearer "`.
Keep the key outside Git; never add API credentials to a public web UI.
A provider requiring a key embedded in a URL needs a provider-specific
adapter rather than interpolating secrets into a public endpoint.

Use either `apiKey` (stored in the 0600 file) or `apiKeyEnv` (read from
the process environment), not both for the same endpoint. Set
`MOGWAI_LEDGER_CONFIG` to override the default path. Trusted local Python
adapters can import `load_ledger_config` and `endpoint_key` from
`tools.ledger_config` after adding the Mogwai checkout to Python's path.

`check` validates the JSON and prints ledger names, family, chain/network
identity, and whether read/broadcast endpoints and credentials are present.
It never prints URLs or API key values. It does not make network calls, query
balances, sign transactions, or broadcast anything. Running Git pull alone
does not populate the private file or restart FileProxy.

## Trust boundary

- **Reads:** A later provider adapter may use its configured read URL/key to
  query the relevant chain and validate returned chain identity, data and
  transaction IDs. Untrusted remote responses must not be taken as proof.
- **Writes:** A broadcast URL only names a possible relay for an already
  signed raw transaction. It does **not** authorize the web UI to send funds,
  sign, or post a transaction. Chisel owns validation, explicit confirmation,
  signing and broadcast status. Private keys/WIF, seed phrases, and wallet
  mnemonics do not belong in this file.
- **Hosting:** No route exposes this configuration through FileProxy, PHP or
  the Mogwai Android sharing page. Do not register `~/.config/mogwai` or its
  parent directory as a publicly readable FileProxy root. GitHub Pages and
  IPFS cannot privately read a server's home directory. A future host-side
  adapter must expose only deliberately selected operations, with
  authentication/authorization and rate limiting as needed.
- **Permissions:** The loader rejects symlinks and secrets files with group
  or world permissions on POSIX systems, or files inside the Mogwai checkout.
  Keep the parent directory mode 0700 and the config mode 0600.

## Preferred host-side Polygon reads: Etherscan API V2

If your private key is already in `~/.config/mogwai/etherscan.json`,
keep that file. **You do not need a dRPC key or account.** Pull main
and use the migration utility to merge Etherscan into Polygon's single
`ledgers.json` entry:

```bash
git -C "$HOME/mogwai" pull --ff-only
python3 "$HOME/mogwai/tools/migrate_etherscan.py"
python3 "$HOME/mogwai/tools/migrate_etherscan.py" --apply
python3 "$HOME/mogwai/tools/ledger_config.py" check
python3 "$HOME/mogwai/tools/etherscan_read.py" status polygon
```

The first migration command is a **dry run**; only the `--apply` invocation
writes the private `ledgers.json`. It refuses to overwrite a populated
Etherscan provider; does not print the API key; and retains
`~/.config/mogwai/etherscan.json` as the original. If dry-run fails, stop
rather than running `--apply` and use the error to diagnose the local
configuration. Pinata is unrelated to the Polygon test.

After a successful Etherscan status query, inspect a real Polygon hash:

```bash
python3 "$HOME/mogwai/tools/etherscan_read.py" transaction polygon 0xYOUR64HEXTRANSACTIONHASH
```

Etherscan V2 uses HTTPS GET to `https://api.etherscan.io/v2/api`, with
`chainid=137`, `module=proxy`, an allowed read-only `action`, and
`apikey` as query parameters. Your API key stays on the server and is
never printed by the adapter. An HTTPS provider necessarily receives the
key; don't run the request with shell tracing or copy URLs into logs.
The status output reports `latestBlock`, `chainId: 137`,
`provider: "etherscan"`, and `chainIdSource`, which identifies chain ID
137 as the **configured query parameter**, not an independently verified
RPC `eth_chainId` result. A transaction's own returned `chainId` is
checked when present. Etherscan data is provider-reported data.

The Etherscan reader only permits `eth_blockNumber`,
`eth_getTransactionByHash`, and `eth_getTransactionReceipt`. No API
broadcasting, signing, FileProxy endpoint, or wallet integration is added.
The old standalone Etherscan file is a migration source, not the final
runtime configuration.

Relevant provider references:
[Etherscan block number](https://docs.etherscan.io/api-reference/endpoint/ethblocknumber),
[Etherscan transaction by hash](https://docs.etherscan.io/api-reference/endpoint/ethgettransactionbyhash),
[Etherscan transaction receipt](https://docs.etherscan.io/api-reference/endpoint/ethgettransactionreceipt).

## Optional direct Polygon JSON-RPC test

```bash
git -C "$HOME/mogwai" pull --ff-only
python3 "$HOME/mogwai/tools/ledger_config.py" check
python3 "$HOME/mogwai/tools/evm_read.py" status polygon
```

`status` calls `eth_chainId` and `eth_blockNumber`. It refuses a provider
whose chain ID differs from the configured 137. The public RPC endpoint may
have rate limits or downtime; a provider failure is not a failed transaction.

To inspect a known **actual Polygon transaction hash**, including receipt
status and the SHA-256 of its input bytes, use:

```bash
python3 "$HOME/mogwai/tools/evm_read.py" transaction polygon 0xYOUR64HEXTRANSACTIONHASH
```

Use a real `0x`-prefixed 64-hex-character transaction hash in place of the
placeholder. The command reports whether it was found, block number, value
in wei, payload length and hash, and successful/reverted/pending status
when receipt information supports it. This is a response from one RPC provider,
not independent chain verification or finality attestation.

## Offline tests

```bash
cd "$HOME/mogwai"
python3 -m unittest discover -s tools/tests -p 'test_ledger_config.py'
python3 -m unittest discover -s tools/tests -p 'test_evm_read.py'
python3 -m unittest discover -s tools/tests -p 'test_etherscan_read.py'
python3 -m unittest discover -s tools/tests -p 'test_migrate_etherscan.py'
```

These tests use fake RPC and Etherscan responses and never broadcast. Both
`evm_read.py` and `etherscan_read.py` perform read-only network requests
when invoked normally. `evm_read.py` has a strict allowlist
of four read methods, a 15-second request timeout and a response size limit.
The `broadcast` config field is reserved for future use.

Next steps are Digibyte/Litecoin provider-specific readers and connecting
trusted host-side reads to Chisel with a restricted API. Keep the write path
separate until transaction construction, chain checks, confirmation and
signing boundaries are integrated with Chisel.
