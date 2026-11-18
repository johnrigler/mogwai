# Mogwai host-local ledger providers

Mogwai code is updated through Git. Provider endpoints and API keys are
machine-local; never store them in a repository, a browser application, or a
FileProxy-served data root. This is the first configuration patch, not a new
transaction or broadcast service.

## Install on rigler.org or another machine

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

A provider entry looks like:

```json
{
  "family": "evm",
  "chainId": 137,
  "network": "mainnet",
  "read": {
    "url": "https://provider.example/rpc",
    "apiKey": "replace-on-server"
  },
  "broadcast": {
    "url": "https://provider.example/rpc",
    "apiKeyEnv": "POLYGON_RPC_API_KEY"
  }
}
```

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

## Local tests

```bash
cd "$HOME/mogwai"
python3 -m unittest discover -s tools/tests -p 'test_ledger_config.py'
```

Next implementation step is a read-only Polygon adapter against the host
configuration, followed by Digibyte/Litecoin provider-specific readers. Keep
the write path separate until transaction construction, chain checks,
confirmation and signing boundaries are integrated with Chisel.
