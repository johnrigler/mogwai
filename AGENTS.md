# Mogwai: implementation notes for assistants

Keep the existing user's architecture; don't replace it with generic software scaffolding.

- `a.*` is ALP, `d.*` is Daisy, `m.*` is Mogwai. Bash functions are native inspectable/persistable artifacts. `declare -f` is the canonical serialized function definition, retaining the original function name.
- Save function snapshots with ALP/Daisy **content-derived Shoctal/checksum names**, optionally suffixed by source byte count. Short hashes are intentionally collision-capable; do not lengthen them merely to eliminate collisions. Full SHA-256 belongs in FileProxy's catalog, not every filename.
- Daisy is standalone; a saved `daisy()` can load a particular hard-coded set of `d.*` functions. Mogwai supplies tools/UI but must not become a mandatory Daisy dependency.
- Favor the **smallest functional Bash code**, pipes, built-ins, composition, few dependencies, no speculative flags or extra frameworks. Do not normalize filenames into generic `alp.sh`, `daisy.sh`, etc.
- Two FileProxy implementations exist: `johnrigler/fileProxy` is the newer standalone Python catalog/API, while `johnrigler/chisel/tools/fileProxy/` is the legacy Chisel service. Do not confuse them.
- The local standalone FileProxy catalog is **SQLite**, with full SHA-256 stored as 32-byte BLOB. User machines write it, then push the actual database to GitHub. An assistant retrieves the exact GitHub revision and opens it with Python `sqlite3`. GitHub is shared persistent visibility for concrete Web3 artifacts, not an SQL server.
- Anchor references in actual GitHub files/commits, IPFS CIDs, and chain transaction IDs. Never fabricate source records or declare verification without inspecting the cited object.

Read `johnrigler/fileProxy/AGENTS.md`, `johnrigler/daisy`, and `johnrigler/alp` before redesigning these interfaces.
