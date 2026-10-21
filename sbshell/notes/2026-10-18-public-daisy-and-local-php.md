# Public Daisy archives and local PHP (2026-10-18)

Annual daisy_YYYY repositories are intended to be public. CertLedger becomes
public after private material is removed, including review of retained Git
history. Private working documents stay outside public archives.

Mogwai holds the [annual starter](https://github.com/johnrigler/mogwai/tree/main/templates/daisy-year)
and references to SB Stats, FileProxy, crypto-python, Chisel and other writers.
Daisy owns its ISO WWD/ date structure. SB Shell maintains each archive beyond
that coordinate: selected units, numbered fragments, images, symlinks,
navigation and long printable pages. Root files.txt remains the current
root-relative inventory; preserve ALP's separate .files.txt convention.

## PHP running locally

John reports the PHP assembler working locally. Commit 5344787
records renewed PHP work in [cruff/index.php](../cruff/index.php). The
nested cruff/test/index.php and cruff/test/test/index.php entries point to
../index.php, reusing the renderer. The project now records the direct
PHP/shell approach in [STANDARDS.md](../STANDARDS.md) and
[AGENTS.md](../AGENTS.md).

From the intended working content directory:

```bash
php8.2 -S 127.0.0.1:8000 -t "$PWD"
```

Inspect GD and other extensions with php8.2 --ri gd and php8.2 -m.
Working-directory behavior, includes, commands and symlinks are part of
the composition and should be preserved when making a change.

PHP assembles pages locally; rendered HTML and assets can be published
statically or through IPFS. Chrome handles US Letter printing. The static
browser's root files.txt convention continues to describe that reader.
