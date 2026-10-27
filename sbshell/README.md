# SB Shell

SB Shell is now maintained inside [Mogwai](../README.md), at
`mogwai/sbshell/`. See [the consolidation guide](../docs/CONSOLIDATION.md).
The original repository remains available for history.

Filesystem-first publishing with a local PHP assembler and a static browser
path. Files, names, directories and symlinks supply the document structure.
Bash and vi remain first-class authoring tools; Python and FileProxy are optional.

## Working standards

[STANDARDS.md](STANDARDS.md) records John's direct PHP/shell style and the
mechanisms visible in the current source. [AGENTS.md](AGENTS.md) applies those
standards to assistant changes. The PHP work is in [cruff/index.php](cruff/index.php)
with nested index.php symlinks reusing the same renderer. John reports this
PHP path running locally; commit 5344787 records the October 18 revival.

The PHP assembler reads its directory. The static inventory conventions below
describe the separate static browser path.

## Directory navigation in PHP

### PHP setup

Run SB Shell's plain Bash/PHP setup check in Penguin's terminal. It uses
`php8.2` when available, then `php`; select another binary with `SB_PHP`:

```bash
bash ~/mogwai/sbshell/setup check ~/daisy_2026
```

To install the PHP components on **Penguin / Debian / Ubuntu** and run the
check again:

```bash
bash ~/mogwai/sbshell/setup install ~/daisy_2026
```

The installer matches the selected PHP version, installing its CLI, common
modules, **SQLite3** and **GD** packages. It enables SQLite3, GD and Fileinfo
for that version's CLI, including the built-in server. If PHP is absent, it
installs the distribution's default PHP instead. It uses the normal apt/sudo
prompts and does not add repositories or change archive permissions. Other
systems can run the check after installing PHP with their own package manager.

The check tests an in-memory SQLite database and PNG encoding, checks PHP 8+,
JSON, SHA-256 and archive/catalog permissions, and reports optional GD JPEG,
FreeType and Fileinfo capabilities. It does not modify archive files. An
incomplete base setup exits with status 1; a ready setup exits with status 0.
If no archive argument is supplied, it checks the current directory.

Every directory page has a right-hand hamburger menu in its header containing
**PHP setup** (also available with `?sb-check=1`) and the **Auto-refresh** toggle.
PHP setup checks the PHP process
actually serving the page, showing
its version, binary, configuration and archive root. A terminal and web server
can use different PHP versions or configurations; the page gives the matching
installer command. Restart the PHP server after installing or enabling modules,
then check again. GD is included for graphics work; ordinary image and PDF
previews still use the browser. No Composer packages or PHP frameworks are
needed.

For example, to select PHP 8.2 explicitly:

```bash
SB_PHP=php8.2 bash ~/mogwai/sbshell/setup install ~/daisy_2026
```

Check the setup reports with `php8.2 tests/php-setup.php` and
`php8.2 -n tests/php-setup.php` (extensions disabled). Test installer commands
without installing packages with `SB_PHP=php8.2 node tests/setup.mjs`.

### Start the viewer

Start PHP in the directory you want to browse, with the assembler as its router:

```bash
cd /home/john/daisy_2026
php8.2 -S 127.0.0.1:39692 -t . /home/john/mogwai/sbshell/cruff/index.php
```

Open `http://127.0.0.1:39692/`. A directory without `1_*.*` parts shows
a table of its directories and files. Click down through `42/` to
`firmus-ncs/`, for example. Each assembled page has breadcrumbs back to the
directory where you started PHP. Directories with numbered parts assemble
them as before, with their directory list available under **Files and directories**.
The list starts open when there are no numbered parts, and closed when there are.

Files and directories appear in a table with alternating white and light-gray
rows, a selection checkbox on the left, and a **Tags** column on the right
reserved for future tag associations. The header stays visible while scrolling
and contains **Select all**, **Unselect all**, **Expand all**, **Collapse all**,
**Expand selected**, **Copy selected**, the selected-entry count, breadcrumbs
and the hamburger menu. **Expand selected** opens checked previewable files without collapsing
other open previews; the button is disabled when none of the checked rows has
a preview. Selection covers
the current directory's rows, independently of preview expansion, and is
remembered for this tab and directory across refreshes. Selection alone does
not modify any files or catalog records.

In a week directory, click a file's disclosure arrow or filename to expand its
preview in place. PNG and other images display at the available width, PDFs
embed the original document; Markdown renders styled headings, paragraphs,
lists, links, quotes, strikethrough, pipe tables and syntax-colored fenced code.
Source files such as `.sh`, `.py`, `.js`, `.php`, `.json`, `.yaml`, `.sql`
and Godot `.gd` display in a dark, Vim-style highlighted source panel.
Other small readable files get literal text previews. Executable files with
a shebang are recognized even without an extension. Inline source previews
are limited to 512 KiB, and their contents are escaped, never executed.
Existing `.unixTs`, `.ts`, and `.script` terminal recordings continue to
use the ANSI transcript viewer; `.tsx` is treated as source code. Highlighting
is performed by local PHP without a CDN or added package. **Expand all** and **Collapse all** control these file previews;
subdirectories remain ordinary navigation links. **Open file** keeps the
original URL available, including the PDF naming page. If a phone's browser
does not embed PDFs, use **Open original PDF / print**.

Expanded files are remembered for this browser tab and directory across
refreshes. JavaScript checks a file-date/size and directory-entry fingerprint
every ten seconds and reloads only when it changes. Polling does not rewrite
SQLite; catalog journals and other generated files cannot cause a refresh loop.
The same check notices changes to saved document names and atomic file
replacements. Images and PDFs load on expansion, and terminal display starts on
expansion. A week listing prints its expanded previews; an assembled page's
auxiliary listing stays hidden in print. Print a PDF through its own original
PDF link for all pages.

Breadcrumbs, file controls and the refresh checkbox are automatically
hidden when printing. Dotfiles, catalog files and the shared index itself are omitted from
the list. CSS, JavaScript and images use PHP's normal serving behavior. PDFs
open in the document view described below. Directory URLs get a trailing slash
so those relative links keep working.

Using the [PHP built-in server's router](https://www.php.net/commandline.webserver)
means child directories need no index.php copies or inventory file. Existing
index.php symlinks also keep using the requested directory, rather than the
directory holding the shared renderer source.

### Browser selection to shell clipboard

Check rows and click **Copy selected** to write **`.clip` in the directory
being viewed**. It is a plain text list of the selected absolute file or
directory paths, one per line, in table order. Each directory keeps its own
list, and copying again replaces that directory's `.clip`. Checkbox selection
or expansion alone does not save the list.

Load the inspectable shell function using its full path:

```bash
source ~/mogwai/sbshell/lib/sb/clip.bash
cd ~/daisy_2026/42
sb.clip | more
```

The shell function is simply:

```bash
sb.clip() {
    cat -- .clip
}
```

It reads `.clip` in the shell's current directory. You can also read the file
directly with `cat /path/to/week/.clip`. Saving the list uses PHP's file
operations; reading it uses ordinary shell tools. The complete list replaces
the old file atomically. `.clip` and its temporary files are hidden from the
directory table, catalog scans and change checks. For example, preserve
spaces while consuming the list:

```bash
sb.clip | while IFS= read -r file; do
    printf '%s\n' "$file"
done
```

Check persistence with `php8.2 tests/clipboard.php` and browser-request-to-shell
interoperation with `SB_PHP=php8.2 node tests/clipboard-cli.mjs`.

### Automatic SQLite catalog maintenance

Opening a directory creates **catalog.sqlite3 at the PHP document root** if
needed and refreshes its file records for that directory and its descendants.
Opening the archive root indexes the whole archive. Change-triggered refresh
maintains the browsed subtree as files are added, changed, renamed or
removed. Records outside that subtree, saved document names and FileProxy's
metadata remain intact. Existing single-root FileProxy catalogs keep their
root alias; a new catalog uses the document-root directory's name.

The shared `files` table stores root-relative paths, sizes, modification times,
MIME types and full SHA-256 as 32-byte BLOBs. Page loads verify file hashes;
the periodic change check reads only file metadata and saved document names.
Dotfiles, symlinks, `files.txt`, the catalog and its journal/sidecar files are
excluded from the scan. Symlinks remain usable in the directory viewer.
Scans use one transaction and record their time in `metadata.sbScannedAt`.
There is no second database or background service. Enable PHP's **SQLite3**
extension and make the archive directory writable; a failed catalog update
shows a message while file browsing remains available.

Check source highlighting and Markdown with `php8.2 tests/source-preview.php`,
scanning and previews with `php8.2 tests/week-directory.php`, the browser
polling decisions with `node tests/directory-refresh.mjs`, and naming
compatibility with `php8.2 tests/document-names.php`.

## Name a document while viewing it

With the router above, open any PDF from the directory list or its original
URL. The page shows the PDF below a **Document name** field. Enter a name such
as `Centro welcome letter` and click **Save name**. Directory listings then
show that name beside the original filename. The viewer's **Reference by name**
link opens the saved document through `/?document=Centro%20welcome%20letter`.
Saving a different name updates that file's entry; names must be unique within
the catalog, ignoring ASCII letter case.

PHP writes the name, root-relative source path, 32-byte SHA-256 and save time
to the `sb_documents` table in **catalog.sqlite3 at the PHP document root**.
Start PHP at the Daisy archive root to share FileProxy's archive catalog.
Existing catalog rows are preserved. The directory browser also maintains
FileProxy-compatible `files` and `metadata` tables as described above.
FileProxy scans replace the file index while preserving `sb_documents`.
The catalog and its directory must be writable by the account running PHP.

PHP needs its **SQLite3** extension; check with `php8.2 --ri sqlite3`. The PDF
still displays if that extension is missing, with a message beside the naming
form. **Open original PDF / print** opens the original PDF in Chrome; use its
PDF print controls. Adding `?raw=1` to a PDF URL also serves the original bytes.
The viewer's name field and breadcrumbs are hidden in print styles.

Numbered PHP parts can reference a saved name directly:

```php
<a href="<?= htmlspecialchars(sb_document_url('Centro welcome letter')) ?>">Welcome letter</a>
```

`sb_document_path($name)` returns the verified local path. `sb_document_url($name)`
resolves it while PHP renders and emits a relative file URL, so saved HTML can
travel with its source assets. These functions are loaded by `cruff/index.php`.
A separate CLI builder can require `cruff/catalog.php` and set `$sb_root` to
the archive directory and `$sb_url` to the output directory's root-relative URL
(for example, `/42/firmus-ncs/`) before rendering its parts.

A missing source or changed fingerprint stops lookup by name with a visible
message. Open the file and save its name again to accept its current contents.
No PDF bytes or source filename are changed by naming a document.

Check naming and catalog preservation with `php8.2 tests/document-names.php`.

## Script logs in PHP

The current `cruff/index.php` loop assembles `1_*.*` in directory order.
PHP parts still use `include`; `.ts`, `.unixTs` and `.script` recordings use
[cruff/script.php](cruff/script.php). Here `.ts` means a Unix `script` log.
Prefer **`.unixTs`** for new recordings, matching Daisy's `d.script` filenames;
existing `.ts` files, including `cruff/1_05.ts`, keep working without renaming.

The viewer comes from `daisy_2026/42/sbshell-script-viewer.html`. Terminal mode
preserves ANSI colors and basic cursor editing. Sections mode groups `-->>`
commands and turns `-->> #` comments into annotations. Previous, Next and
Show all step through blocks. Complete alternate-screen sessions, such as Vim,
become boundary markers; their original recording stays intact.

The PHP include embeds the recording and viewer in the assembled HTML, so a
saved page needs no transcript fetch or external library. Transcript text is
displayed literally, including any captured HTML or PHP source. Each recording
has its own controls. The HTML viewer uses a larger 16px monospace font in
an 80-column panel; narrow screens scroll horizontally. Chrome printing uses
9pt type and compact padding to fit an 80-column listing on US Letter with
one-inch margins. Longer metadata or older, wider output can still wrap.
Use **Auto-refresh when files change** at the top of the PHP page to
pause or resume checks. Refresh starts on and remembers your choice for that
page in this browser.

Capture new recordings at 80 columns:

```bash
source ./lib/d.script.bash
d.script
```

`d.script` sets the terminal width before starting `script`, so both the
recording header and commands such as `ls` use 80 columns. Leaving the recording
restores the previous terminal width. The timestamped `.unixTs` naming stays
the same; use the usual numbered part name to place a recording in the page.
Already recorded output, including `1_05.ts`, keeps its original layout.

From the SB Shell component directory (`~/mogwai/sbshell`):

```bash
php8.2 -S localhost:8000 -t .
```

Open `http://localhost:8000/cruff/` to read the sample. The nested index.php
symlinks use the same include while continuing to read their own directories.

## Public annual Daisy archives and local PHP

SB Shell will maintain each public `daisy_YYYY` archive beyond its ISO week/day
structure. Mogwai owns the reusable year starter and tool references. The user reports the local PHP assembler running. See
[the October 18 direction and PHP sources](notes/2026-10-18-public-daisy-and-local-php.md).

## Static navigation convention (October 12, 2026)

**The inventory is at the repository root: `files.txt`.** The entries are qualified paths relative to that root, for example:

```text
myshell/1_01-gemini-balloon.html
myshell/1_02.html
myshell/live.png
```

Do **not** put this same inventory inside `myshell/files.txt`. The renderer searches from its current directory upward for an inventory and interprets listed paths relative to the location where it found the inventory. A `myshell/files.txt` containing `myshell/...` makes an extra nested `myshell` appear.

`child.html` and `myshell/index.html` contain the renderer code. It builds its listing from the inventory, not from the older `index.js` manifests. `index.js` is legacy metadata, not the current navigation source. The files `index.html`, `index.js`, and `files.txt` are treated as infrastructure.

The root `files.txt` covers the `myshell` tree. To include other trees, add their qualified relative paths too. Empty directories may not appear in navigation if nothing inside them is indexed.

## Rebuild from Bash

From the **SB Shell component directory** (the directory containing `myshell/`):

```bash
find myshell -mindepth 1 \
    -name '.*' -prune -o \
    -name 'files.txt' -prune -o \
    -name '.files.txt' -prune -o \
    -print | LC_ALL=C sort > files.txt
```

This includes normal files and subdirectories below `myshell/` but skips hidden files and directories. The committed `sb.find-43742.1` Bash function performs this operation (its optional argument is a repository-root path, not the `myshell` directory). If your interactive shell already has an older `sb.find` definition loaded, source the updated function again.

```bash
source ./sb.find-43742.1
sb.find
git diff -- files.txt
git add files.txt
git commit -m "Refresh SB Shell inventory"
git push
```

Note that a Bash function loaded into your terminal does not automatically change when its file changes in Git; you must source it again. Do not run the function from inside `myshell` unless you supply the correct repository root.

## Serving and checking

From the SB Shell component directory (`~/mogwai/sbshell`):

```bash
python3 -m http.server 8000
```

Visit `http://localhost:8000/myshell/`. You should see `1_01-gemini-balloon.html`, `1_02.html` and the other children directly, **not** another `myshell` entry. If an extra `myshell` appears, check for a leftover `myshell/files.txt` or another nearer inventory. If the page reports no inventory, ensure the root `files.txt` is being served successfully.

## Hidden inventory filename

A `.files.txt` variant is **not the canonical repository layout yet**. One copy of the shared renderer has been changed to probe `.files.txt` first, then fall back to `files.txt`, but `myshell/index.html` still follows the existing `files.txt` behavior. The current working convention remains root `files.txt`. A future migration must update both renderer copies and the Bash generator together. A dotfile is not private and can still be served publicly.

See [MOGWAI.md](MOGWAI.md) for architecture and [mogwai/SCAN-INGEST.md](mogwai/SCAN-INGEST.md) for scan naming.

## Project Jupiter: first CertLedger-style publication page

[`myshell/1_03-project-jupiter.html`](myshell/1_03-project-jupiter.html) is a
static, self-contained, US Letter-printable dated dossier with YouTube video,
evidence links, two New Mexico Supreme Court docket IDs, a timeline, and
explicit missing-document/telemetry statuses. It is listed in the **root**
`files.txt`, respecting the working navigation convention. It is a public
editorial derivative of the annual
[`daisy_2026/421`](https://github.com/johnrigler/daisy_2026/tree/main/421)
record, not a live private-repo synchronization. Material changes need a
reviewed new publication snapshot.

## Email and mail registration

[Packet registration](tools/packet-registration/index.html) fingerprints the
separate final email and mail PDFs, prepares the email body and actual dispatch
reference, and prints a separate registration sheet and transaction receipt.
It reuses Chisel's CTP500 printer modules and runs as static browser files.
See [the sequence and hash boundaries](tools/packet-registration/README.md).
