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

Only ordinary, newline-delimited path input is supported. File names
containing embedded newlines require another workflow. The command does not
silently recurse into directories.

## m.pick

Reads candidate lines on stdin, writes a temporary menu, and opens your
`$VISUAL` or `$EDITOR` (default: `vi`).

```bash
printf '%s\n' 'first choice' 'a file with spaces.pdf' 'third choice' | m.pick
```

The editor shows two leading spaces in front of each item:

```text
  first choice
  a file with spaces.pdf
  third choice
```

Go to the chosen line and replace **its very first space** with `x`:

```text
  first choice
x a file with spaces.pdf
  third choice
```

With Vim: `0rx` (move to column 1, replace the space with x), then
`:wq`. Mogwai returns **exactly the selected original line**, preserving
internal and leading spaces. A zero-choice or multiple-choice edit is rejected
rather than guessing. Editor UI goes to the terminal; stdout is reserved for
the result so pipelines still work.

`MOGWAI_PICK_EDITOR` can override the editor, which is also used for
noninteractive regression tests. The pick function returns text only; it does
not treat it as a shell command or evaluate it.

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
