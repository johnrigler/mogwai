# Host configuration examples

Mogwai's tracked files here are **examples with no credentials**. The actual
settings live under the Unix user's home directory on `rigler.org`, outside
Git and outside the public web root. This directory is for copying and editing,
not for committing secrets.

## Files and destinations

| Repository example | Private destination | Purpose |
| --- | --- | --- |
| `config-examples/ledgers.json` | `~/.config/mogwai/ledgers.json` | Polygon and UTXO ledger read/broadcast endpoints and provider API keys |
| `config-examples/pinata.json` | `~/.config/mogwai/pinata.json` | Pinata JWT and private gateway token placeholders |
| `config-examples/fileproxy.json` | `~/.config/fileproxy/config.json` | Existing FileProxy registered data roots |
| `config.example.json` (repo root) | `~/config.json` | Existing shared project paths; **not installed by this script** |

**Only `ledgers.json` is consumed by the current Mogwai ledger tools.**
`tools/evm_read.py` supports read-only Polygon JSON-RPC. The other ledger
entries are schemas to populate as adapters are added. The `broadcast` fields
are stored as configuration but **no broadcast implementation uses them**.
The Pinata example is for future IPFS integration: no current Mogwai code
reads it, pins files, or validates the token. FileProxy already reads its
own `~/.config/fileproxy/config.json`; the sample has an empty `roots` object.

## Copy all examples without overwriting existing files

On `rigler.org`:

```bash
git -C "$HOME/mogwai" pull --ff-only
bash "$HOME/mogwai/config-examples/install.sh"
```

The script creates `~/.config/mogwai` and `~/.config/fileproxy` with mode
0700, installs new JSON files with mode 0600, and **preserves** any existing
config file. An existing FileProxy root configuration will not be reset.
If you already copied an older ledger sample, this script will not merge or
change it: edit it manually, comparing it with the new example.

Or copy just the files you want:

```bash
install -d -m 700 "$HOME/.config/mogwai"
install -m 600 "$HOME/mogwai/config-examples/ledgers.json" "$HOME/.config/mogwai/ledgers.json"
install -m 600 "$HOME/mogwai/config-examples/pinata.json" "$HOME/.config/mogwai/pinata.json"
```

**Caution:** Unlike the installer script, the direct `install` commands above
overwrite existing destination files. Back up/edit existing files instead.
Do not directly replace an active FileProxy config with the empty-root example.

## Editing and checking

```bash
nano "$HOME/.config/mogwai/ledgers.json"
nano "$HOME/.config/mogwai/pinata.json"
python3 "$HOME/mogwai/tools/ledger_config.py" check
python3 "$HOME/mogwai/tools/evm_read.py" status polygon
```

## Existing Etherscan key: non-destructive migration

Etherscan V2 is an **indexed API provider for Polygon**, not its own ledger.
The maintained example now includes
`ledgers.polygon.providers.etherscan` inside `ledgers.json`. Keep
`polygon.read.url` as your JSON-RPC provider, such as
`https://polygon.drpc.org`; Etherscan is a separate provider interface.

If you already saved a real key in private
`~/.config/mogwai/etherscan.json`, **do not retype or publish it**.
After pulling Mogwai main, you can check the migration without changing
any files:

```bash
python3 ~/mogwai/tools/migrate_etherscan.py
```

If the dry-run says Etherscan can be added, use:

```bash
python3 ~/mogwai/tools/migrate_etherscan.py --apply
python3 ~/mogwai/tools/ledger_config.py check
```

The helper accepts the prior `{"version":1,"etherscan":{"url":"…",
"chainId":137,"apiKey":"…"}}` structure. It copies the Etherscan
endpoint and key into the private `ledgers.json`, keeps the original
`etherscan.json` untouched, refuses to replace nonempty existing
credentials, and **prints no key values**. An existing Etherscan provider
URL must match the legacy URL. It never makes network requests.

This **does not** test Etherscan API V2. The Etherscan adapter is not
implemented yet. The existing `evm_read.py status polygon` test uses
Polygon JSON-RPC and needs no Etherscan API key. Do not run the
installation script to upgrade a populated private file; the installer
preserves existing files.

The ledger file uses one entry per network. The Polygon read example uses
`https://polygon.drpc.org` and chain ID `137`. The UTXO URLs beginning with
`REPLACE-` are deliberately **nonfunctional placeholders**, not verified
providers. Replace them before using those networks. Depending on the provider,
`apiKeyHeader` and `apiKeyPrefix` might be needed, or a provider-specific
adapter may be required. The Polygon adapter's current API key support is for
HTTP headers, not URL-interpolated secrets.

For Pinata, copy your JWT into the private `pinata.jwt` field and set the
optional gateway access token if your gateway uses one. These names describe
planned configuration only: there is no Pinata adapter yet. No command here
will upload files to IPFS.

Do **not** put wallet seed phrases, WIFs, private signing keys or wallet
passwords in these files. A provider API key grants network-service access,
not transaction-signing authority. Do not serve any of the private paths via
FileProxy, a public Apache alias, GitHub Pages, or IPFS. Never paste real
credentials into an issue, chat, log, or public repository.

The already-existing shared `~/config.json` is documented separately in
[Home config](../HOME-CONFIG.md). The ledger reader is documented in
[Ledger providers](../docs/LEDGER-PROVIDERS.md).
