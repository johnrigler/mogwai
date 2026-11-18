# CID-addressed static HTTP mirror (first implementation)

Status: operator-side code is in Mogwai main. No rigler.org Apache path
was changed and no CID has been published by this change.

## Purpose

Pinata is the intended primary IPFS pinning/distribution provider.
Kubo is installed on rigler.org and can be used on the laptop for
constructing/inspecting the original IPFS DAG. It is a separate role
from serving a CID-labeled copy of the files under ordinary HTTP.

`fileproxy.cid_mirror` exports a known CID from a **locally running
Kubo API**. It stores both the original CAR and a readable UnixFS
file/directory export. Kubo is only required during the export,
not for verification or serving the resulting files.

This is a separate format from `fileproxy.static_publish`'s existing
SHA-256 object store. It does not replace that implementation.

## Operator commands

Run from the Mogwai checkout on rigler.org, or another machine that
has access to Kubo and can write the intended static directory:

```bash
cd ~/mogwai/fileProxy
python3 -m fileproxy.cid_mirror publish \
  --root /srv/www/chisel-boot \
  --cid CID_FROM_YOUR_IPFS_NODE \
  --ipfs ipfs \
  --api /ip4/127.0.0.1/tcp/5001
```

Use a real CID in place of the uppercase placeholder. The Kubo
admin API must be local loopback, NOT a publicly exposed endpoint.
Use `--timeout 1800` if a large legitimate DAG takes longer to export.
Every option is an explicit CLI argument, not an environment variable.

The command invokes:

```text
ipfs --api=/ip4/127.0.0.1/tcp/5001 --timeout=600s dag export <CID>
ipfs --api=/ip4/127.0.0.1/tcp/5001 --timeout=600s get --output=<STAGING> <CID>
```

It checks the CARv1 header's root CID and the SHA-256 multihashes of
all blocks present in the archive. The archive must contain its root
block. It refuses symlinks, special files and a publication target
that already exists. The static content is committed after its
accompanying archive and checksum inventory.

Result (for an IPFS **directory** with `index.html`):

```text
/srv/www/chisel-boot/
  <CID>/
    index.html
    app.js
    css/...
    images/...
  _cars/
    <CID>.car
  _meta/
    <CID>.json
```

An IPFS single-file root is exposed as `<CID>/content`. The metadata
sidecar records `entrypoint` and the complete file SHA-256 inventory.

After publication, stop Kubo and FileProxy only when operationally
appropriate and run the independent check:

```bash
cd ~/mogwai/fileProxy
python3 -m fileproxy.cid_mirror verify \
  --root /srv/www/chisel-boot \
  --cid CID_FROM_YOUR_IPFS_NODE
```

`verify` performs all file, CAR and block-hash checks using only
Python's standard library. It does not invoke Kubo or FileProxy.

Run the offline regression suite:

```bash
cd ~/mogwai/fileProxy
python3 -m unittest discover -s tests -p 'test_cid_mirror.py' -v
```

## Apache mapping (illustration; NOT deployed)

Serve these objects from a distinct, static-only hostname, e.g.
`boot.rigler.org`, rather than on the origin that exposes a
FileProxy or wallet-related application. An IPFS site may contain
arbitrary executable JavaScript, so origin isolation matters.

```apache
Alias "/boot/" "/srv/www/chisel-boot/"
<Directory "/srv/www/chisel-boot/">
    Require all granted
    Options -Indexes -FollowSymLinks -ExecCGI
    AllowOverride None
    Header always set X-Content-Type-Options "nosniff"
</Directory>
```

With that mapping, an already exported directory will be visible as
`https://boot.rigler.org/boot/<CID>/index.html` without running an
IPFS daemon. Relative URL references should resolve under the CID
folder. A different Apache configuration may be appropriate on the
actual host; check the existing vhost before applying this example.

Never proxy Kubo's API port, FileProxy's mutation routes or host
filesystem through the public boot vhost. Do not blindly publish
archives containing credentials or private data.

## Verification boundaries

- **Verified by this module:** CARv1 has the requested single root,
  root block exists, every present block matches its own SHA-256 CID
  multihash, and every static exported file still matches its
  recorded SHA-256 and length. The archive is separately hashed.
- **Not yet verified by this module:** entire DAG completeness/link
  traversal; equivalence between exported UnixFS files and original
  CAR contents; independent Kubo CAR reimport on another machine;
  Pinata pin status; signer identity and confirmed Polygon attestation.
- CAR must use one root and SHA-256 CIDs in supported CIDv0 or base32
  CIDv1 syntax. Non-SHA-256 multihashes are intentionally rejected.
- An ordinary file served under a CID-named directory is not itself
  cryptographic proof of that directory CID. The CAR is the
  authoritative IPLD preservation object; independent DAG verification
  remains a release gate.

**Do not print a root CID as an authenticated Chisel boot release
merely because this command succeeded.** A stable boot release needs
separate CAR reimport, complete DAG verification, primary Pinata
availability, independently verified author attestation and
cross-machine recovery testing.

## Planned integration

1. Add strict UnixFS DAG/decoded export equivalence verification,
   including recursive link completeness.
2. Add Pinata CAR upload as a separate authenticated operator command,
   with explicit private credential-file path and returned CID check.
3. Make a read-only browser resolver try Pinata or local/public IPFS
   gateways and the static CID mirror, with independent data verification
   and clear source labels.
4. Add a versioned approved-publisher release attestation on Polygon
   137. Never infer identity from a semantic address alone.
5. Replicate the complete CAR to a separate laptop/node and test boot
   with rigler.org unavailable.

The static publisher does not change runtime FileProxy routes and
does not require a FileProxy service restart.
