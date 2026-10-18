# Mogwai

Mogwai supplies small, inspectable tools. Daisy keeps the source records and saved projects; it does not depend on Mogwai to exist.

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
