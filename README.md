# Mogwai

Mogwai supplies small, inspectable tools. Daisy keeps the source records and saved projects; it does not depend on Mogwai to exist.

## Shared home configuration

Copy [config.example.json](config.example.json) to `~/config.json` for shared
names, project locations, FileProxy settings and defaults outside the checkouts.
See [Home config](HOME-CONFIG.md) for the copy command and a reading example.
Source `tools/home-config/m.pull`, then run `m.pull` to fast-forward the
configured checkouts. See [Pull configured repositories](tools/home-config/).
Other tools do not load the shared config automatically.

## Annual Daisy archives

[The annual Daisy starter](templates/daisy-year/) creates a clean local
`daisy_YYYY` tree with valid ISO `WWD/` directories and references to
SB Shell, FileProxy, SB Stats, crypto-python, Chisel and CertLedger.
It is an inspectable `m.daisy.new` Bash function with a content-derived
Shoctal filename. SB Shell maintains each archive beyond the date structure.
Annual repositories are intended to be public; existing private material
and retained history need cleanup before public release.

## Recast

[Open the Recast source folder](tools/recast/): a static HTML tool for moving one playing video between layouts, adding timed instruction/image panels, and exporting an FFmpeg render package. Audio remains one original stream.

Open `tools/recast/index.html` locally, or use the [hosted copy](https://johnrigler.github.io/chisel/tools/recast/). Choose your video from the device. It is not uploaded.

See [the tool instructions](tools/recast/README.md) and [assistant architecture notes](AGENTS.md). Historical prototype work remains on `concept-notes-2026-09-11`; it has not been merged into this branch by this change.

## CTP500 printer

[Receipts and folded letters](tools/ctp500-folded-letter/) builds upright,
32-column sample receipts or sideways four-page strips for the Core Innovations
CTP500. It uses full-width BLE/Serial raster output with reliable default pacing,
a short connection test, progress and transfer timing. [Open the hosted tool](https://johnrigler.github.io/chisel/tools/ctp500-folded-letter/).
