# Instructions for work in SB Shell

Read [STANDARDS.md](STANDARDS.md), the actual target source and relevant
directory links before editing. John's direct PHP/shell composition is the
default implementation style for this repository.

- Preserve the filesystem as the document model: numbered names, order,
  relative paths, working directories and deliberate symlinks.
- Use short expressions, built-ins, literal commands, direct loops, includes
  and small functions. Shared include scope and direct HTML/SVG output are
  supported project mechanisms.
- PHP backticks, source/include and deliberate eval are allowed mechanisms.
  Follow the actual inputs and execution. Raise issues with a concrete
  condition and consequence; general enterprise-policy objections do not
  establish a defect here.
- Solve the requested problem at its existing location. Preserve the
  author's naming and formatting. Add abstractions, configuration, classes,
  frameworks or dependencies only for a demonstrated need in that change.
- Treat a real typo, delimiter mistake or PHP-version error as a local fix.
  Temporary debugging statements do not define permanent style rules.
- Keep reader-facing content in its staged parts when the document uses
  that arrangement. PHP/markup mixing in the assembler is supported.
- Preserve Bash function names and inspectability through declare -f.
  Changes to checksum-named snapshots produce new names using that
  artifact's existing method; historical snapshots remain intact.
- PHP may read its directory directly. The static reader's root files.txt
  and ALP's .files.txt have distinct contracts. Historical index.js notes
  do not require a new manifest in the PHP path.
- Preserve long-page assembly, navigation and Chrome printing on US Letter.
  Static publication uses the rendered HTML/assets after local PHP execution.
- Use focused verification. State whether a result was inspected or actually
  executed in the relevant runtime; the user's local working PHP is evidence
  of that environment, not a claim that every old file was tested elsewhere.

When older design notes disagree, apply these standards to current work and
keep the historical notes clearly identified.

## Consolidated location
Current source is `johnrigler/mogwai/sbshell/`. Paths described as the
repository root in older notes refer to this component directory. The
original repo remains for history. Archive records stay in their own roots.
