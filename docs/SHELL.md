# Mogwai Bash tools

Mogwai's current shell helpers implement the two commands described in the
2026-10-12 Unix `script` transcript. They are ordinary Bash functions and
do **not** depend on loading ALP or Daisy.

```bash
cd ~/mogwai/mogwai  # or your own checkout path
git pull
source scripts/mogwai.bash
declare -f m.file.fix
declare -f m.pick
```

A periodic `git pull` updates files on disk; it **does not reload functions
already defined in your current shell**. Source `scripts/mogwai.bash` again
after pulling new code.

## m.file.fix

Receives existing paths either as arguments or one path per standard-input
line. It normalizes each basename into a shell-friendly name without spaces:
leading hyphens and problematic punctuation are removed, and word separators
become hyphens. Text files with recognized extensions have CRLF line endings
converted to LF. PDF, image and other binary file **contents remain unchanged**.

```bash
m.file.fix --dry-run -- './-My Report (Final).TXT'
m.file.fix -- './-My Report (Final).TXT'

printf '%s\n' './Another Report.txt' './-Form (final).pdf' | m.file.fix
```

The command refuses to overwrite an existing destination or follow symbolic
links. If the parent directory includes whitespace, rename that directory
separately first. Use `--dry-run` when you need to inspect changes.

**Integrity warning:** rewriting CRLF in a text file changes its hash.
Do not run the converter on a finalized, signed, or ledger-hashed source
document without intending to create a new canonical artifact. The command
also changes paths, so update any references that previously used old names.
PDF bytes are not rewritten.

Use `m.file.fix -0` with `find -print0` to support even paths containing
embedded newlines. Generated names normalize newline, carriage return,
and tab to hyphens. The command does not
silently recurse into directories.

## m.pick

The picker now uses numbered rows. It stores each original stdin record
separately, so the editor's indentation and the `x` marker are **never**
included in the output filename. If a path exists, the menu also displays
its filesystem device and inode for context. The row number, rather than
inode alone, identifies the selected item within the menu.

The original failing pipeline now works for ordinary one-line filenames:

```bash
ls -1 | m.pick | m.file.fix
```

For arbitrary Unix filenames, including embedded newlines, use a NUL-delimited
pipeline:

```bash
find . -maxdepth 1 -type f -print0 | m.pick -0 | m.file.fix -0
```

Each menu row begins with two spaces and a fixed row number:

```text
  [000001] ./first.txt [dev:ino 2049:12345]
  [000002] ./Screen Shot 2024.png [dev:ino 2049:12346]
```

Use Vim `0rx`, or insert `x` at column one, on **one** row. Then save and
quit with `:wq`. The selected original input record is returned verbatim.
Changing the filename in the editor is not a rename operation.

To run a chosen file through another tool, pipe the selection into that tool.
For example, a deliberately destructive command is:

```bash
find . -maxdepth 1 -type f -print0 | m.pick -0 | xargs -0 -r rm -v --
```

Only run that command when you actually intend to delete the selected file.
A safer preview is to replace `rm -v` with `ls -li`.
No delete, rename, or command execution happens inside `m.pick`.

File names containing arbitrary bytes should be obtained through `find
-print0` rather than parsing human-oriented `ls -l` or `ls -i`
output. Inode numbers are useful diagnostic identifiers, not permanent
file names or sufficient protection against races.

The editor uses `$VISUAL`, `$EDITOR`, or `MOGWAI_PICK_EDITOR`.
Noninteractive tests supply a temporary editor script. `m.pick` writes
status to stderr so stdout remains pipeline-safe.

## Daisy interoperability

The same functions are maintained as plain Bash source in
`johnrigler/daisy/2026/mogwai.bash`. After loading Daisy as desired,
they may be saved using its content-derived naming:

```bash
source ~/daisy/scripts/daisy.bash
source scripts/mogwai.bash
d.fs m.pick
d.fs m.file.fix
```

Note: `m.file.fix` relies on the private `_m.file.name` and
`_m.file.one` helper functions. If you plan to load individual function
snapshots rather than the complete `mogwai.bash` file, snapshot or
include those dependencies too.

Regression tests:

```bash
bash tests/test-mogwai.bash
```
