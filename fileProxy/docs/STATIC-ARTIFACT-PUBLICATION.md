# Static artifact publication: FileProxy is a publisher, not a required reader

First pass: 2026-11-09. This document applies to Mogwai/FileProxy and Chisel.

## Invariant

FileProxy discovers, reconstructs and indexes public artifacts. It publishes
ordinary files and small indexes under a static HTTP directory. An Apache or
nginx server serves those files directly without delegating requests to the
FileProxy process. A second independent host or IPFS node can replicate the
same directory. If FileProxy stops, previously published material remains
readable. If rigler.org stops, a *separate* mirror is still required.

Polygon 137, UTXO transactions and other carriers are sources of publication
evidence. A static mirror is not a replacement for fresh blockchain state.
Retain original encoded M64 bytes and the full pinned dictionary snapshot as
well as reconstructed SVG bytes when these become available.

## Implemented in first pass

The standalone Python module fileproxy.static_publish publishes an operator-
selected local file and writes:

    manifest.json
    objects/sha256/ab/<digest>.svg
    objects/sha256/01/<digest>.bin

Manifest fields: format (chisel-static-artifacts-v1), artifacts keyed by stable
public ID, relative path, sha256, bytes, mediaType, provenance (unverified),
optional sourceHint. The JSON manifest is off-ledger metadata; nothing here
alters the binary M64 protocol or embeds JSON in EVM calldata.

Existing object names are derived from SHA-256. Artifact bytes are written
first; a temporary manifest is then atomically renamed over manifest.json.
The CLI will not redirect an existing ID to different bytes unless --replace
is explicit. The first-pass 'verify' operation re-hashes every referenced file.
The module does not run a network service, take credentials, or query Polygon.

Example from the Mogwai checkout:

    cd ~/mogwai/fileProxy
    python3 -m fileproxy.static_publish \
      --root /srv/www/chisel-artifacts \
      publish --id polygon/137/icon/home \
      --file /tmp/home.svg --media-type image/svg+xml
    python3 -m fileproxy.static_publish \
      --root /srv/www/chisel-artifacts verify

This publishes *local input bytes*, not an independently verified Polygon
entry. The provenance field is deliberately 'unverified'. A manifest hash
without an independently trusted digest only verifies self-consistency.

## Static serving (configuration example, NOT deployed)

    Alias "/chisel-artifacts/" "/srv/www/chisel-artifacts/"
    <Directory "/srv/www/chisel-artifacts">
      Require all granted
      Options -Indexes -ExecCGI
      AllowOverride None
      Header set Access-Control-Allow-Origin "*"
      Header set X-Content-Type-Options "nosniff"
    </Directory>

Apache must be able to read the directory; the publisher alone may write it.
No /fileproxy/ reverse proxy is used for GET /chisel-artifacts/... . For
untrusted SVG, configure restrictive CSP/attachment handling to prevent
standalone SVG documents from executing active content. Keep credentials,
private indexes, local paths, Etherscan keys and wallet secrets out of the
public tree. The existing FileProxy public write/delete security boundary
must be tightened separately; this feature adds no public write endpoint.

## Read model

For already-known hashes:
browser cache -> static rigler.org -> secondary static/IPFS mirrors ->
optional FileProxy cache -> direct Polygon RPC.

Actual implementation can choose concurrently and accept the first valid
content digest. Verify every retrieved object against an independently
anchored digest when possible. A pin to the M64 dictionary digest, count,
contract and chain ID is necessary to claim a Polygon reconstruction.

Clues are replaceable static indexes, not authorities. The same object may
appear under multiple mirrors, and older manifests must remain reproducible.

## Next work

- Chisel browser reader for static manifest and SHA-256 verified objects.
- Export packed M64 secondary entries and pinned dictionary snapshots from
  verified Polygon reads, then publish reconstructed SVG plus source bytes.
- Portable snapshot export/import and replication to another real machine.
- Optional private Etherscan V2 key held in server environment with validated
  read-only routes, caching and rate limits. Direct Polygon JSON-RPC remains.
