# Mogwai public-document watch (2026-10-12)

The initial watch adapter is `scripts/m.watch.py` (Python 3 standard library).
It performs bounded HTTP GET polling, conditional ETag/Last-Modified requests,
SHA-256 of retrieved bytes, optional immutable local snapshots, and JSONL
change/error events. It requires **no daemon, NodeJS or wallet** and runs on
Termux, macOS and Linux. The watcher does not use GPU/CPU instrumentation.

**Separation of responsibilities:** Mogwai discovers/observes. Daisy owns
the chronological subject record. FileProxy is the canonical local content
store/indexer, including full-byte hashes. CertLedger qualifies source
claims and procedural facts. SB Shell publishes an editorial view. Chisel
optionally anchors reviewed manifests. No arbitrary change is automatically
considered a case filing or anchored transaction.

Example with a local checkout of `johnrigler/daisy_2026`:

```bash
cd ~/mogwai
python3 scripts/m.watch.py \
  --config "$HOME/daisy_2026/421/04-project-jupiter-watch-sources.json" \
  --archive
python3 -m unittest discover -s tests -p 'test_m_watch.py' -v
```

By default, state, snapshots and JSONL logs are kept outside source repos in
`~/.local/state/mogwai/watch/`. `--archive` preserves the exact response bytes
in `blobs/<source-id>/<sha256>.pdf|.bin`. Without `--archive`, a hash is only
an observation; it is not a retained primary artifact. Neither mode creates
a GitHub commit or IPFS pin. Back up / ingest valuable snapshots explicitly.

Outputs:

- `state-<subject-id>.json`: last known source state and digest
- `events.jsonl`: baseline or byte-change events, **unreviewed**
- `errors.jsonl`: fetch errors, including unavailable/authenticated sites
- `blobs/`: optional locally archived exact bytes

A HTML byte change can be just a cookie banner, timestamp, or site redesign.
A court listing may require registered access to see the underlying documents.
A private force-majeure notice is **not** a court filing merely because news
reports mention it. No claim is made that this adapter automatically extracts
or validates individual court docket events.

For scheduled checks, run the same CLI via Termux/cron where supported, or
use an external scheduled watcher. Do not run frequently or bypass logins
and rate limits. The separate ChatGPT daily Project Jupiter check is an
external notification workflow, *not* a Mogwai daemon and does not push data
to Daisy. A watch should notify only after a reviewed **material** change;
byte diff alone is not sufficient.

## Operational measurements

Even at a live data center, `vmstat` samples one host's CPU/run queue/memory
activity, **not aggregate center-wide compute**. Accelerator instrumentation
might use NVIDIA DCGM, `nvidia-smi`, ROCm SMI or vendor telemetry APIs, with
operator permission, calibrated sampling, documented scope and counter units.
Before commissioning, `operationalStatus=not_operational` and measured
telemetry values must be `null`, not zero. A public MW capacity figure,
design TDP or emissions estimate is a different measurement class.

Never poll private production hardware, credentials, or management interfaces
without authorization. Public power readings and official environmental
monitoring can later be linked as separate sources with their own timestamps.
