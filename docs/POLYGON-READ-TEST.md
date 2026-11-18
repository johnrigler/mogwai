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

## Option B: Test your existing private dRPC file directly

This is the simplest option if you already created
`~/.config/mogwai/drpc.json` with two lowercase fields:

```json
{
  "polygon": "https://lb.drpc.live/polygon/EXAMPLE_KEY_NOT_REAL",
  "api": "EXAMPLE_KEY_NOT_REAL"
}
```

The values above are deliberately fake. Keep your actual `polygon`
URL and `api` key in your existing private file. You do **not** need
to copy them into `ledgers.json` or tell ChatGPT what they are.

After pulling main, use the new read-only test:

```bash
python3 "$HOME/mogwai/tools/drpc_status.py" check
python3 "$HOME/mogwai/tools/drpc_status.py" status
```

`check` reads the private JSON, validates its permissions and URL,
and reports only the authentication mode. It makes no network call.
`status` makes two safe Polygon JSON-RPC calls:
`eth_chainId` followed by `eth_blockNumber`. It refuses a
chain other than 137. The result reports the numeric `chainId`,
`latestBlock` and authentication mode, without showing the URL/key.

### Verified connection and transaction inspection

On November 17, 2026, the rigler.org smoke test reported a successful
read-only connection after the local `drpc.json` file permissions were
restricted to 0600:

- `check`: `authentication: "url"`, `configured: true`, expected chain ID 137
- `status`: observed chain ID 137, latest block 97,508,094, `provider: "drpc"`

That block height is a *historical observed result*, not an expected fixed
value. Later successful requests should return a newer block height.
Offline unit tests run independently of the host and are not evidence of
a live transaction read.

To inspect a known Polygon transaction and receipt using the **same private
`drpc.json` file**, run:

```bash
python3 "$HOME/mogwai/tools/drpc_status.py" transaction 0xYOUR64HEXTRANSACTIONHASH
```

Use a real `0x`-prefixed, 64-digit hex transaction hash. The script
verifies the RPC chain ID (137), then calls read-only
`eth_getTransactionByHash` and `eth_getTransactionReceipt` as needed.
It reports whether the transaction was found, its block, reported execution
status, input byte length and SHA-256 digest. It **does not return the
raw input bytes**, decode ABI arguments or reconstruct a Chisel artifact yet.
Nothing is signed or broadcast; transaction output is provider-reported.

The dRPC dashboard commonly embeds the key in the complete Polygon
endpoint URL. If so, the script uses that URL and does **not** also
send the `api` field as a header. If the URL contains no embedded key,
it sends your private `api` value as the documented `Drpc-Key`
HTTP header. The script only connects to documented dRPC HTTPS hosts;
it does not accept a Data & Wallet API URL. Any extra fields in the
private JSON are ignored.

The tracked dummy example is at
[config-examples/drpc.json](../config-examples/drpc.json). Its values
are not working credentials. No credentials, wallet keys, signing,
broadcasting, or FileProxy endpoints are involved.

If the private file is group/world accessible, correct permissions
locally (`chmod 600 ~/.config/mogwai/drpc.json`). The directory
should be mode 0700. A prior 403 from the public
`https://polygon.drpc.org` endpoint does not imply a problem with
your new account-specific endpoint.

## Option C: Configure the shared `ledgers.json` RPC entry

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

## Read contract methods and indexed events with dRPC

The existing private `drpc.json` Polygon RPC endpoint supports read-only
contract calls and bounded event-log queries through `drpc_status.py`. `eth_call` executes a view or
simulation without creating a transaction. `eth_getLogs` filters logs by
contract address, block range, and optional indexed topics. The Mogwai RPC
adapter does not expose signing or broadcast methods.

For M64, use the deployed contract address with ABI-encoded calldata for
`termCount()`, `lookupTerm(id)`, or another view function:

```bash
python3 "$HOME/mogwai/tools/drpc_status.py" call 0xYOUR_M64_CONTRACT 0xABI_ENCODED_CALLDATA --block latest
```

To read M64 `TermAdded` and `Packet` events from a block range, query by
contract address. Those are the M64 contract's emitted event types:

```bash
python3 "$HOME/mogwai/tools/drpc_status.py" logs 0xYOUR_M64_CONTRACT 97514024 97515000
```

Optional `--topic` arguments filter topics by position; pass `--topic '*'`
for a wildcard position. The command requires a bounded range of at most
100,000 blocks and checks that every returned log belongs to the requested
contract and range. For a recurring indexer, persist a separate M64 block
checkpoint and query through a confirmed safe head. Keep Etherscan's
address-transaction scan for complete transaction input; the RPC event query
indexes the M64 contract's emitted logs.

## Offline tests (no provider credentials needed)

```bash
cd "$HOME/mogwai"
python3 -m unittest discover -s tools/tests -p 'test_ledger_config.py'
python3 -m unittest discover -s tools/tests -p 'test_evm_read.py'
python3 -m unittest discover -s tools/tests -p 'test_etherscan_read.py'
python3 -m unittest discover -s tools/tests -p 'test_migrate_etherscan.py'
python3 -m unittest discover -s tools/tests -p 'test_drpc_status.py'
```

The scripts above do not sign or broadcast transactions. The live status
commands are read-only. Do not share the actual API keys, dRPC URLs, Pinata
JWTs, or credential-filled JSON files in tickets, chats, browser logs, or Git.

Provider documentation:
- [dRPC Polygon JSON-RPC](https://drpc.org/docs/polygon-api)
- [dRPC authentication](https://drpc.org/docs/gettingstarted/firstrequest)
- [dRPC Data & Wallet API](https://drpc.org/docs/quickstart-data-api)
- [Etherscan API V2 documentation](https://docs.etherscan.io/)
