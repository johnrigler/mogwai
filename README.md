# Mogwai

Mogwai is the tools checkout for preparing, cataloging, browsing and publishing
filesystem records. [FileProxy](fileProxy/) and [SB Shell](sbshell/) now live
here alongside the annual archive starter and other tools.

Daisy is John's working environment and one use of the record format.
Personal annual archives and customer engagements keep their own repositories.
Command names follow working habits: a `d.*` function may call a Mogwai tool
and be saved in a dated Daisy repo.

[Signed editions](docs/SIGNED-EDITIONS.md) records the HTML → PDF → signing →
external commitment workflow and planned automatic signature inspection.
[Local workspace](docs/LOCAL-WORKSPACE.md) records the proposed stable Mogwai
control/status window on port 1132 and movable working root on port 39632.
These are plans; existing runtime entry points below remain unchanged.

## Suggestions

[Browser discussions and Bluesky](docs/BROWSER-AND-BLUESKY-SUGGESTIONS.md)
records two proposals: a subscribed discussion overlay for YouTube, Bluesky
and other sites, plus Bluesky / AT Protocol reading, publishing and portable
discussion records. These are suggestions, not implemented features.

## FileProxy and SB Shell

```bash
git -C "$HOME/mogwai" pull --ff-only
source "$HOME/mogwai/fileProxy/shell/fp.sh"
fp roots
```

Run the optional FileProxy HTTP service with `fp serve --local`.
To browse an existing archive with SB Shell:

```bash
cd "$HOME/daisy_2026"
php -S 127.0.0.1:39692 -t . "$HOME/mogwai/sbshell/cruff/index.php"
```

See [setup, migration and import provenance](docs/CONSOLIDATION.md).
The existing local FileProxy root config is reused. Archive data and SQLite
catalogs stay in their own roots.

## New annual repositories

```bash
source "$HOME/mogwai/templates/daisy-year/m.daisy.new"
m.daisy.new 2027 "$HOME"
```

[The annual starter](templates/daisy-year/) creates a clean local
`daisy_2027` tree with valid ISO `WWD/` directories and tool instructions.
It refuses existing destinations. GitHub repository creation and publication
are explicit subsequent steps. It is an inspectable Bash function with a
content-derived Shoctal snapshot; the created archive remains ordinary files.

## GitHub toward IPFS

Work in the active annual repo, catalog the actual bytes, and publish sources
and SQLite deliberately. SB Shell supplies local assembly and static browser
publication. Later archival editions can retain the selected records and
their required code/assets for pinning and retrieval.
[Automatic IPFS handoff and combined archive lookup remain planned](fileProxy/docs/ANNUAL-IPFS-ARCHIVE.md).

## Shared home configuration

[Signing identities](signatures/) inspects original PDF signatures without
Adobe, records independently checked certificate fingerprints in the home
database, exports public certificate records for GitHub/IPFS, and signs PDF
copies using an existing local signing identity. Open **Signing identities**
from the local directory viewer's hamburger menu after installing its Python
dependencies. Published certificates and locally verified identities are
reported separately.

[People and correspondence](profiles/) adds a local GUI for John and Shannon's
saved identity fields and NCS letter defaults. Open it from the directory
viewer's hamburger menu. It uses `~/catalog.sqlite3`, outside the checkouts.
The JSON example below remains shared project configuration, not a place for
birth dates or SSNs.

Copy [config.example.json](config.example.json) to `~/config.json` for shared
names, repository locations and local FileProxy settings. See
[Home config](HOME-CONFIG.md). FileProxy and SB Shell are components of the
Mogwai checkout, so the example no longer lists them as separate repositories.
Your sourced `d.pull` can update Mogwai and the other configured Git roots.
The [earlier pull snapshot](tools/home-config/) remains available.

## Recast

[Recast](tools/recast/) is a static HTML tool for video layouts, timed panels
and an FFmpeg render package. [Open the hosted copy](https://johnrigler.github.io/chisel/tools/recast/).
Chosen source video stays on the device.

## CTP500 printer

[Receipts and folded letters](tools/ctp500-folded-letter/) builds receipts
or sideways four-page strips. Printer work is currently on hold.
