# Annual Daisy starter

A portable m.daisy.new Bash function creates a clean local daisy_YYYY archive:
all valid ISO WWD/ directories, assistant conventions and a README linking
the tools that may write into it. No existing records or credentials are copied.

~~~bash
cd "$HOME/mogwai"
git pull
source templates/daisy-year/m.daisy.new
m.daisy.new 2027 "$HOME"
~~~

The second argument is an existing parent directory; the default is the
current directory. Existing destinations and symlinks are refused. The
caller's directory is retained. ISO 2026 has 371 coordinates; ISO 2027 has
364. Empty markers keep the generated directories in Git.

`m.daisy.new` is a symlink selecting `m.daisy.new-02255564-7304`.
Older snapshots remain unchanged. The function is a pure declare-f snapshot with its short Shoctal identifier
and byte count in the filename. It works when copied elsewhere and requires
Bash, mkdir, cat and sed. Daisy does not acquire a Mogwai runtime dependency.

The generated README uses Mogwai's `fileProxy/` and `sbshell/` components for
FileProxy registration, PHP browsing and
Git publication steps, with links to Daisy, Mogwai, SB Shell, FileProxy,
SB Stats, Chisel and CertLedger. The exact crypto-python repository was not
resolved; its named writer reference is explicitly pending.

SB Shell maintains each archive beyond its date structure, including
numbered units, selected files, symlinks, navigation and printable pages.
See [the local PHP direction](https://github.com/johnrigler/mogwai/blob/main/sbshell/notes/2026-10-18-public-daisy-and-local-php.md).
The starter prepares a local tree; it does not initialize Git, create a
remote, register a root or publish an IPFS archive automatically.
See [the consolidated setup and IPFS boundaries](../../docs/CONSOLIDATION.md).

## GitHub template scope

This is the Mogwai-maintained source for generating an annual repository.
GitHub's native [Use this template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository)
copies a repository tree. A native button for only the Daisy tree requires a
separate template repository containing that export. Mogwai remains the tools
repository. This function creates local files; remote creation and public
visibility remain explicit publishing steps.

## Independent engagements

Daisy's record format can also describe separate customer or domain
engagements, each with its own annual repositories and Git history.
The current `m.daisy.new` command creates `daisy_YYYY`; it does not yet
accept an engagement name. See [Daisy engagement conventions](https://github.com/johnrigler/daisy/blob/main/docs/ENGAGEMENTS.md).
A possible `certLedger_YYYY` layout is deferred; existing CertLedger records
and repository names remain in place.

## Public release

New annual archives are intended to be public. CertLedger becomes public
after private material is removed. For existing repositories, review the
retained history as well as the current tree; deleting a current file leaves
its prior revisions. See [GitHub's removal guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

## Verify

From the Mogwai root:

~~~bash
python3 -m unittest discover -s tests -p 'test_daisy_year.py' -v
~~~

The checks compare output with the ISO calendar, exercise overwrite refusal
and verify that the function definition survives source/declare-f round trips.
