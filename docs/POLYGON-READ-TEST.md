# Polygon read test on rigler.org

This is the canonical host-side Polygon setup and smoke test.
The credential-bearing files are private and **outside Git**. Pull the
instructions instead of copying commands from a phone conversation.

## Which service?

- **dRPC Polygon JSON-RPC**: normal chain calls such as `eth_chainId`,
  `eth_blockNumber`, transaction lookup and receipts. The current
  `tools/evm_read.py` adapter uses `ledgers.polygon.read`.
- **Etherscan API V2**: indexed/proxy chain queries under
  `ledgers.polygon.providers.etherscan`, consumed by
  `tools/etherscan_read.py`.
- **dRPC Data & Wallet API**: a **different** service for wallet balances,
  token holdings, portfolio/PnL and indexed history. Its dashboard URL may
  contain `/lambda` and a private API token. Do not put that URL into
  `ledgers.polygon.read.url`; the current Mogwai tools do not call it.
  dRPC's documentation says it is enabled by default for paid users.

The dRPC and Etherscan services are complementary, not interchangeable.
The standard JSON-RPC adapter sends HTTP POST requests with JSON-RPC method
names, while Etherscan's V2 proxy API uses GET with chainid=137.

## Pull Mogwai

```bash
git -C "$HOME/mogwai" pull --ff-only
```

## Option A: Use your existing Etherscan key

If your key was originally saved in `~/.config/mogwai/etherscan.json`,
import it without retyping the credential:

```bash
python3 "$HOME/mogwai/tools/migrate_etherscan.py"
python3 "$HOME/mogwai/tools/migrate_etherscan.py" --apply
python3 "$HOME/mogwai/tools/etherscan_read.py" status polygon
```

The first migration command is a dry run. Only proceed to `--apply` if it
reports that the import is safe. The original file is kept; no key is
printed or copied into Git. If Etherscan has already been imported, skip
the migration. The status command reports the block height and requested
chain ID 137; this is **not** an independent RPC chain-identity check.

## Option B: Use your new private dRPC Polygon URL

The dashboard provides a full HTTPS Polygon RPC endpoint, often like
`https://lb.drpc.live/polygon/YOUR_KEY`. The full endpoint itself carries
your credential; you do **not** need to duplicate the API key in
`read.apiKey`. Put the actual dashboard-provided URL, not the placeholder,
into the existing private file:

```bash
nano "$HOME/.config/mogwai/ledgers.json"
```

The relevant **illustrative** portion of the JSON looks like:

```json
{
  "polygon": {
    "family": "evm",
    "chainId": 137,
    "network": "mainnet",
    "read": {
      "url": "https://lb.drpc.live/polygon/YOUR_KEY"
    },
    "providers": {
      "etherscan": {
        "url": "https://api.etherscan.io/v2/api",
        "apiKey": "YOUR_ETHERSCAN_KEY"
      }
    }
  }
}
```

The actual file also has outer `version` and `ledgers` keys, and may
contain other ledgers. **Edit only** `ledgers.polygon.read.url`, preserving
the other entries. The display above is not a full replacement file.
Keep the separate Etherscan key in its provider field.

Validate configuration, then check the chain identity and block height:

```bash
chmod 600 "$HOME/.config/mogwai/ledgers.json"
python3 "$HOME/mogwai/tools/ledger_config.py" check
python3 "$HOME/mogwai/tools/evm_read.py" status polygon
```

Expected values include `chainId: 137` and a numeric `latestBlock`. A
`403` means the service rejected the request. It does not by itself prove
a ledger outage or identify the cause. Confirm that the URL is the HTTPS
Polygon *RPC* endpoint from your account, not the Data & Wallet URL.
Provider policy, account permissions, and rate limits may affect access.

dRPC also documents authentication by an HTTP `Drpc-Key` header, and the
Mogwai RPC adapter supports `apiKeyHeader`; use a verified endpoint/header
combination if you choose that approach. The dashboard's complete URL is
simpler to configure, but it must remain secret.

## Offline tests (no provider credentials needed)

```bash
cd "$HOME/mogwai"
python3 -m unittest discover -s tools/tests -p 'test_ledger_config.py'
python3 -m unittest discover -s tools/tests -p 'test_evm_read.py'
python3 -m unittest discover -s tools/tests -p 'test_etherscan_read.py'
python3 -m unittest discover -s tools/tests -p 'test_migrate_etherscan.py'
```

The scripts above do not sign or broadcast transactions. The live status
commands are read-only. Do not share the actual API keys, dRPC URLs, Pinata
JWTs, or credential-filled JSON files in tickets, chats, browser logs, or Git.

Provider documentation:
- [dRPC Polygon JSON-RPC](https://drpc.org/docs/polygon-api)
- [dRPC authentication](https://drpc.org/docs/gettingstarted/firstrequest)
- [dRPC Data & Wallet API](https://drpc.org/docs/quickstart-data-api)
- [Etherscan API V2 documentation](https://docs.etherscan.io/)
