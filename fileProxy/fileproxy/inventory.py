"""Generate static directory inventories (including SB Shell's qualified paths).

This is a projection of the filesystem, not a substitute for the hash catalog.
"""
from pathlib import Path
import os

from .core import atomic_bytes, generated_file, resolve_file, roots_from


def write_scan_inventory(base, records, directories):
    """Publish the same scan as plain paths; preserve ALP's .files.txt."""
    lines = sorted(set(directories) | {row["path"] for row in records})
    output = base / "files.txt"
    if output.is_symlink():
        raise ValueError("Refusing to replace an inventory symlink: " + str(output))
    atomic_bytes(output, (("\n".join(lines) + "\n") if lines else "").encode("utf-8"))
    return str(output)


def export_inventory(config, root_name, subtree=".", output="files.txt"):
    roots = roots_from(config)
    if root_name not in roots:
        raise ValueError("Unknown root " + str(root_name))
    base = roots[root_name]
    if subtree in ("", "."):
        start = base
    else:
        start = resolve_file(config, root_name, subtree)
    destination = resolve_file(config, root_name, output)
    if not start.is_dir():
        raise FileNotFoundError(str(start))
    lines = []
    for folder, dirs, files in os.walk(start, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".")
                         and not (Path(folder) / d).is_symlink())
        for d in dirs:
            lines.append((Path(folder) / d).relative_to(base).as_posix())
        for file in sorted(files):
            p = Path(folder) / file
            if (file.startswith(".") or p.is_symlink() or p.resolve() == destination
                    or generated_file(p)):
                continue
            lines.append(p.relative_to(base).as_posix())
    lines.sort()
    atomic_bytes(destination, (("\n".join(lines) + "\n") if lines else "").encode("utf-8"))
    return {"root": root_name, "subtree": subtree, "output": output, "entries": len(lines)}
