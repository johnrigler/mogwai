# Shared home configuration example

Copy [config.example.json](config.example.json) to `~/config.json`, outside
the project checkouts. Edit your names, paths, service address and defaults
there. Mogwai keeps the example; your home file is the local working copy.

```bash
git -C "$HOME/mogwai" pull
cp -n "$HOME/mogwai/config.example.json" "$HOME/config.json"
```

`cp -n` leaves an existing home config alone. If it already exists, copy the
fields you want into it rather than replacing it. Checkout paths and their
capitalization in the example are editable examples, not a directory scan.

## Fields

| Field | Purpose |
| --- | --- |
| `person` | Your display name and GitHub username. |
| `assistant.name` | The name you want tools to use for the assistant. |
| `projects.KEY.name` | Human-readable project name. |
| `projects.KEY.path` | Local directory for that project. |
| `services.fileproxy.url` | Address of the local FileProxy service. |
| `services.fileproxy.config` | Location of FileProxy's own root configuration. |
| `defaults.chain` | Optional shared chain preference; here, Litecoin. |

Project keys are lookup identifiers; display names can change independently.
For example, `projects.darkstar.name` is `Beautiful Dark Star`, while its
example checkout is still `~/darkStar`. The Daisy shell and the annual
`daisy_2026` archive have separate entries.

The FileProxy address uses its documented default, `http://127.0.0.1:7799`.
On another machine, `127.0.0.1` refers to that machine; edit the address for
your actual setup. This shared file references FileProxy's existing config;
its registered roots still belong in `~/.config/fileproxy/config.json`.

## Pull the configured repositories

Use Daisy's `d.pull`, loaded by directly sourcing its saved function
definition in your shell RC file. Run the command explicitly when you want
updates. See [Daisy's command ownership and local-install status](https://github.com/johnrigler/daisy/blob/main/docs/ENGAGEMENTS.md).

The earlier [Mogwai implementation](tools/home-config/) reads every
`projects.KEY.path`, follows the current branch's upstream and performs
fast-forward-only updates. It skips local changes and reports results per
checkout. The existing snapshot is retained; no local `d.pull` source path
is assumed here.

Personal archives, separate engagements and tooling repos can each have
their own configured path. The `commons` entry should point to `~/commons`
with a lowercase `c`. CertLedger's existing entry stays in place until its
future annual layout is explicitly adopted.

## Reading it

This is plain JSON, with no comments or shell substitutions. A path starting
with `~/` means the current user's home, independently of the caller's working
directory. A reader must explicitly expand it; JSON does not do that itself.

For example, using Python's standard library:

```bash
python3 - <<'PY'
import json
from pathlib import Path

config = json.loads((Path.home() / "config.json").read_text())
print(config["person"]["name"])
print(Path(config["projects"]["mogwai"]["path"]).expanduser())
PY
```

For tools that adopt this convention, use an explicitly chosen project/tool
setting first, then the shared home value, then the tool's existing default.
The home file and individual fields remain optional. Daisy and the other
projects keep working independently without this file or a Mogwai checkout.

Browser JavaScript cannot directly read `~/config.json`. A browser tool would
need a file picker or an explicitly exposed subset through FileProxy. No
shared-config endpoint or automatic loader is introduced by this example.
The original `m.pull` reads the project paths from this file; the working
command is now owned by Daisy as `d.pull`. Other tools can adopt
the shared values when their integrations are implemented.
