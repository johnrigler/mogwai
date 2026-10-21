# SB Shell standards

SB Shell is John's filesystem program for assembling and publishing documents.
The working style is small, direct PHP and shell expressions whose inputs,
execution and output can be followed in the source. These standards preserve
that style. John reported the PHP path working locally on October 18, 2026;
the source inspected here includes commit 5344787.

## Composition

- **The filesystem supplies structure.** Directories group material; filenames
  carry placement and order. Preserve numbered parts, deliberate ordering,
  working-directory behavior and relative paths.
- **Use the existing language directly.** PHP statements, built-in functions,
  shell commands, loops and arrays are normal building blocks. Prefer the
  shortest clear composition that does the requested work.
- **Shell execution is supported.** PHP backticks and literal operator-written
  commands are part of the local workbench. Preserve them when they express
  the operation clearly. Check the actual output and delimiter when parsing
  text. Changes that introduce outside input must account for that input at
  the specific command or include where it is used.
- **Includes compose a document.** A selected PHP file can execute in the
  assembler's scope and emit its portion of the page. Shared variables and
  direct output are intentional mechanisms; preserve their meaning.
- **Symlinks reuse implementations.** Keep one renderer body where the
  directory layout already points to it. Preserve the links and their
  relative targets.
- **Small functions are inspectable artifacts.** A function can directly
  generate markup or install another function. Preserve its name and calling
  convention. Save changed ALP/Daisy functions under a new name using the
  artifact's existing checksum method; keep historical snapshots.
- **Use ordinary values until interchange needs a format.** A string, PHP
  array, filename or stdout stream can be sufficient. JSON belongs at an
  actual interchange boundary.
- **Keep the execution visible.** Add an abstraction or dependency when a
  concrete operation benefits from it. Frameworks, classes, service layers,
  generic adapters and schema machinery need a demonstrated job in the
  requested change.
- **Make local corrections.** Fix a variable mismatch, delimiter error or
  PHP-version incompatibility at the relevant expression. Preserve the
  surrounding composition and the author's naming and formatting.

## What the repository demonstrates

| Source | Mechanism to preserve |
| --- | --- |
| [cruff/index.php](cruff/index.php) | Directory inspection, a shell-output/string expression, sorting, page grouping, includes and emitted markup. |
| [cruff/sb_shell.php](cruff/sb_shell.php) | Ordered parts assembled into a selected page with previous/next navigation. |
| cruff/test/index.php and cruff/test/test/index.php | Both are symlinks to ../index.php, reusing the renderer through the directory tree. |
| [cruff/sb2.bash](cruff/sb2.bash) | inspectable Bash definitions, declare -f, generated functions and explicit evaluation. |
| [modules/svg/svg_lib.php](modules/svg/svg_lib.php) | Small functions such as line, cup and surface directly emit SVG. |

The Lisp-like relationship is in the inspectable forms and composition:
ordinary source artifacts can be read, named, reordered and executed by a
small visible interpreter. Auditability comes from following those concrete
files, commands, variables and outputs.

These are structural conventions, not a rule to copy every historical token
or temporary debug probe. Read the particular implementation before changing
it. Report a concrete failure separately from a preference about style.

## Publication and checks

The PHP assembler can inspect its working directory directly. The static
browser path has its own root files.txt inventory; that inventory is not a
new prerequisite for PHP. Preserve ALP's separate .files.txt meaning.
Earlier per-directory index.js notes describe an older static layout.

Daisy keeps the annual records. SB Shell maintains their editorial sequence
beyond the date coordinate. Mogwai supplies reusable tools; FileProxy remains
an optional writer/index. Local PHP produces HTML and assets for static
hosting or IPFS. Chrome handles US Letter portrait/landscape printing.

Review a change through its actual entry point, inputs, working directory,
ordered files and resulting page. Use a small relevant check. A generic
warning about shell execution, includes, shared scope or symlinks is not
evidence of a defect in this workflow. State the concrete condition and
observable consequence when raising an issue. Distinguish source inspection
from a runtime check and state which one was performed.
