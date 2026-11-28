# BSV Custodian (phase 1)

Independent read-only scanner inventory audit and newest-first static publisher.
Uses the existing SQLite blocks/transactions tables. No PHP, provider requests,
scanner restarts, database modifications or raw file deletion.

On rigler.org:

    cd ~/mogwai
    git pull --ff-only
    bash tools/bsv-custodian.sh audit
    bash tools/bsv-custodian.sh publish
    bash tools/bsv-custodian.sh status

The wrapper reads ~/.config/mogwai/bsv.env like bsv.sh. Default: 5,000 newest
selected transactions sorted by block height and transaction index; up to 200
raw JSON identities checked per audit. SQL counts cover the whole scanner DB,
but archive checks cover only examined catalog candidates. Classification count
means existing curator entries, not new classifications. Counts do not imply
entire-chain coverage or cryptographic verification. Set --limit or --verify
to change scope. A nonempty selection with no usable records is rejected.

Endpoints on the default data host:

    /chisel_data/bsv/custodian/manifest.json
    /chisel_data/bsv/custodian/status.json

After a successful manual publish, optional user cron:

    */15 * * * * cd "$HOME/mogwai" && bash tools/bsv-custodian.sh publish >> "$HOME/.local/state/mogwai/bsv-custodian.log" 2>&1

A nonblocking lock prevents overlapping publishers. SQLite is opened read-only
with a five-second lock timeout; a busy database fails safely. Content-addressed
snapshots preserve previous manifest readers; retention is manual for now.
Phase 1 does not repair rows, recover payloads, or classify new protocols.
