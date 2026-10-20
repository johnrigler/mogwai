# Pull configured repositories

`m.pull` reads `projects` from `~/config.json` and updates each existing Git
checkout at its configured `path`. Requires Bash, Python 3 and Git; no packages
or FileProxy server are needed.

```bash
git -C "$HOME/mogwai" pull --ff-only
source "$HOME/mogwai/tools/home-config/m.pull"
m.pull
```

To keep the function available, put the `source` line in your `.bashrc`.
You can inspect it with `declare -f m.pull`. The `m.pull` file is a symlink
to the current content-derived Shoctal/byte-count snapshot. The function is
self-contained and can also be sourced from a copied snapshot elsewhere.

An optional argument selects another config file:

```bash
m.pull /path/to/config.json
```

## What happens

- All project paths are validated before any fetch starts. `~/` expands to
  your home; relative project paths are also relative to home, not the current
  directory. Names and paths containing spaces remain literal data.
- Each path must identify a checkout root. Missing folders, non-repositories,
  nested subdirectories, detached HEADs, branches without an upstream,
  unfinished Git operations and checkouts with tracked changes or untracked
  files are reported and skipped. Missing repos are not cloned automatically.
- Each eligible checkout fetches from the current branch's configured remote
  and fast-forwards to its configured upstream. There is no assumption about
  `main`, `master` or `origin`, and the checked-out branch is not switched.
- Updates use `git fetch`, followed by `git merge --ff-only --no-autostash
  --no-overwrite-ignore @{upstream}`. The final option also protects ignored
  local data, such as a catalog, from being overwritten by incoming tracked
  files. Diverged branches are reported for manual resolution. No reset,
  stash, rebase, new merge commit, push or automatic conflict resolution runs.
- A failed repo does not stop the remaining ones. Aliases resolving to the
  same directory are handled once. The caller's directory stays unchanged.

The summary counts updated, unchanged, skipped and failed checkouts. Return
status is `0` when all unique configured checkouts succeed, `1` when any are
skipped or fail, and `2` for an invalid config, arguments or missing Git.
Normal Git authentication and SSH/credential-helper settings still apply.

This updates checked-out files. It does not restart services or reload shell
functions already in memory. Source an updated function again when needed.

If your real home config still says `~/Commons`, change that entry to
`~/commons` to match the lowercase checkout. Pulls do not rename directories.
The example's display name is also now `commons`.

## Verification

```bash
python3 -m unittest discover -s tests -p 'test_home_pull.py' -v
```

Tests use local temporary bare remotes and check fast-forwards, custom branch
names, dirty/untracked work, divergence, ignored-data collisions, missing and
invalid paths, in-progress operations, failed fetches, aliases, config validation,
literal paths, caller-directory preservation and snapshot identity. No real
project checkout is pulled by the tests.
