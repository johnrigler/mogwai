# FileProxy and SB Shell in Mogwai

Mogwai now carries FileProxy and SB Shell in one tools checkout. Annual
archives and customer engagement repositories remain separate working trees.

| Path | Purpose |
| --- | --- |
| `fileProxy/` | Python CLI, optional local HTTP service, SQLite cataloging and browser tools. |
| `sbshell/` | PHP directory/document renderer, Bash helpers and static publication tools. |
| `templates/daisy-year/` | Inspectable starter for a new `daisy_YYYY` tree. |
| An archive such as `~/daisy_2027` | Records, selected saved functions, `catalog.sqlite3` and `files.txt`. |

Command prefixes follow the operator's working habits. A `d.*` function can
use Mogwai tools and be saved in a dated Daisy archive. Prefix, implementation
location and historical storage location do not need to agree.

## Use the consolidated checkout

```bash
git -C "$HOME/mogwai" pull --ff-only
source "$HOME/mogwai/fileProxy/shell/fp.sh"
fp roots
```

The wrapper locates its source checkout when sourced; an explicit
`FILEPROXY_HOME` still selects another installation. The CLI also works
directly from any directory:

```bash
python3 "$HOME/mogwai/fileProxy/fp.py" roots
python3 "$HOME/mogwai/fileProxy/fp.py" serve --local
```

FileProxy's registered roots and service settings are still machine-local.
The default `~/.config/fileproxy/config.json` is reused. Each registered
archive still owns its catalog by default; consolidating code does not move
archive files or databases. Existing Chisel legacy endpoint configuration
and explicit `FILEPROXY_INDEX` overrides still apply.

To run SB Shell against an existing archive:

```bash
bash "$HOME/mogwai/sbshell/setup" check "$HOME/daisy_2026"
cd "$HOME/daisy_2026"
php -S 127.0.0.1:39692 -t . "$HOME/mogwai/sbshell/cruff/index.php"
```

Use your installed PHP 8+ binary, with SQLite3 and GD. `SB_PHP` selects
the setup check's binary; invoke that same binary for the server.
The renderer and FileProxy continue to use the archive's same SQLite file.
Stop the previous listener before starting its replacement on the same port.

Update direct RC references to `~/mogwai/sbshell/lib/...` or
`~/mogwai/fileProxy/shell/fp.sh` where those components are loaded.
Keep existing source references to your own dated `d.pull` snapshot.
If `FILEPROXY_HOME` still points at `~/fileProxy`, unset it before sourcing
the new wrapper, or explicitly set it to `~/mogwai/fileProxy`.

In your real `~/config.json`, keep `projects.mogwai.path` pointing at the
Mogwai Git root. Remove the old FileProxy and SB Shell checkout entries
once you have switched. Their new component directories are not independent
Git checkouts and should not be added to a repo-pull list. The supplied
example already reflects this; it does not overwrite your real config.
Do not remove old local checkouts until any local-only work is accounted for.

## Create the next annual archive

```bash
source "$HOME/mogwai/templates/daisy-year/m.daisy.new"
m.daisy.new 2027 "$HOME"
python3 "$HOME/mogwai/fileProxy/fp.py" add-root daisy2027 "$HOME/daisy_2027"
python3 "$HOME/mogwai/fileProxy/fp.py" scan daisy2027
```

The starter creates the local directory and all 364 valid ISO `WWD/`
coordinates for 2027. It refuses an existing destination. It does not create
a GitHub repository, switch the active intake destination or close 2026.
ISO 2027 begins January 4, 2027; January 1–3 still belong to ISO 2026.
Git initialization, remote creation and publication remain explicit steps
in the generated README. No actual `daisy_2027` remote is created by this
consolidation.

The starter currently names the tree `daisy_YYYY`. Independent engagements
can follow the same format with their own names, histories and visibility.
CertLedger has not moved.

## Progress toward IPFS

The current path is ordinary source files, local Python/PHP tools, actual
SQLite catalogs, and deliberate Git publication. SB Shell's static browser
files can be hosted on IPFS. PHP and Python execute locally; publish rendered
HTML and its required assets for a static archive.

Later, an archival edition can retain selected records and the function
definitions/assets needed to understand them, with a consistent SQLite
snapshot and tested pinned CIDs. Keep the fuller working history separately
where useful. Smaller editions reduce storage and replication work.

Automatic IPFS publishing, consistent snapshot export, pin management,
retrieval verification and combined active/archive search are still planned.
This repository consolidation does not claim to implement them. See
[the annual archive plan](../fileProxy/docs/ANNUAL-IPFS-ARCHIVE.md).

## Import provenance and original repositories

Code was imported from these exact revisions:

| Source | Revision | Destination |
| --- | --- | --- |
| `johnrigler/fileProxy` | `6e09f8873ba430648c59c1dfc132c946327ef7d9` | `fileProxy/` |
| `johnrigler/sbshell` | `6025da18b61767455924e7acfa76133421e25ef3` | `sbshell/` |

The original repositories retain their history and local-data artifacts.
Their READMEs point new development here. They have not been deleted,
rewritten or changed to GitHub's archived/read-only setting. This is a source
snapshot import, not a merge of their complete Git histories.

The import preserves executable modes and relative symlinks. These
non-source or machine-specific files stay only in the original repositories:

- FileProxy: `catalog.sqlite3` and `20261018-W42-7-001019.unixTs`.
- SB Shell: `lib/jira.cookies`, `modules/composer.phar`,
  `modules/go/pkg/linux_amd64/github.com/rthornton128/goncurses.a`,
  `modules/rust/hello.world/hello`, `modules/svg/.svg_lib.php.swp`,
  `modules/zork/DATA/ZORK1.DAT`, and `modules/zork/DATA/ZORK1.sav`.

The source and tests for the current FileProxy and SB Shell entry points
are included. SB Shell's historical modules remain reference material;
the import does not make every old experiment a supported runtime.
