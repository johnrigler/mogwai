#!/usr/bin/env python3
"""Increment the Mogwai share-receiver patch version everywhere it is used."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
files = [root / "app" / path for path in ("index.html", "app.js", "sw.js")]
sources = {path: path.read_text(encoding="utf-8") for path in files}
match = re.search(r"Share receiver · (\d+)\.(\d+)\.(\d+)", sources[files[0]])
if not match:
    raise SystemExit("Mogwai share-receiver version not found")
old = match.group(0).removeprefix("Share receiver · ")
major, minor, patch = map(int, match.groups())
new = f"{major}.{minor}.{patch + 1}"
for path, content in sources.items():
    if old not in content:
        raise SystemExit(f"Missing version {old} in {path}")
    path.write_text(content.replace(old, new), encoding="utf-8")
    print(f"{path.relative_to(root)}: {old} -> {new}")
# The public homepage is a generated display of the share receiver's version.
# Never increment or maintain a separate homepage version.
homepage = root / "site" / "index.html"
html = homepage.read_text(encoding="utf-8")
updated, count = re.subn(
    r'(<span id="mogwai-home-version"[^>]*>Mogwai v)\d+\.\d+\.\d+(</span>)',
    lambda match: match.group(1) + new + match.group(2),
    html,
)
if count != 1:
    raise SystemExit("Expected exactly one Mogwai homepage version label")
homepage.write_text(updated, encoding="utf-8")
print(f"{homepage.relative_to(root)}: -> {new}")
