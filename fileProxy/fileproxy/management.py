"""Hash-checked file arrangement and reversible removal in registered roots."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
from uuid import uuid4

from .core import atomic_bytes, catalog_paths, generated_file, resolve_file, roots_from, scan, sha256_file
from .names import canonical_filename, require_no_space_path


def directory_path(config, root, relative=""):
    roots = roots_from(config)
    if root not in roots:
        raise ValueError("Unknown root: " + str(root))
    target = managed_path(config, root, relative) if relative else roots[root]
    if not target.is_dir():
        raise FileNotFoundError("Folder does not exist: " + relative)
    return target


def list_folders(config, root):
    base = directory_path(config, root)
    directories = [""]
    for folder, dirs, _ in os.walk(base, followlinks=False):
        dirs[:] = sorted(name for name in dirs if not name.startswith(".")
                         and not (os.path.islink(os.path.join(folder, name))))
        directories.extend((Path(folder) / name).relative_to(base).as_posix() for name in dirs)
        if len(directories) > 5000:
            raise ValueError("Folder list exceeds 5,000 directories")
    return {"ok": True, "root": root, "directories": directories}


def make_directory(config, root, relative, index_path=None):
    require_no_space_path(relative)
    target = managed_path(config, root, relative)
    directory_path(config, root, str(PurePosixPath(relative).parent) if "/" in relative else "")
    target.mkdir()
    try:
        scan(config, [root], index_path)
    except Exception:
        target.rmdir()
        raise
    return {"ok": True, "root": root, "path": relative}


def transfer_files(config, root, destination, files, operation="copy", numbered=False, index_path=None):
    if operation not in ("copy", "move") or not isinstance(numbered, bool):
        raise ValueError("Choose Copy or Move")
    if numbered and operation != "copy":
        raise ValueError("Numbered ordering creates copies")
    if not isinstance(files, list) or not files or len(files) > 200:
        raise ValueError("Select 1 to 200 files")
    folder = directory_path(config, root, destination)
    base = roots_from(config)[root]
    next_number = 1
    if numbered:
        used = [int(match.group(1)) for path in folder.iterdir()
                if (match := re.match(r"^(\d{3,})-", path.name))]
        next_number = max(used, default=0) + 1
    planned, sources, destinations = [], set(), set()
    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            raise ValueError("Invalid file selection")
        source = checked_file(config, root, entry.get("path", ""), entry.get("sha256"))
        if source in sources:
            raise ValueError("A file was selected twice")
        sources.add(source)
        name = (f"{next_number + index:03}-" if numbered else "") + source.name
        name = canonical_filename(name)
        target = folder / name
        relative = target.relative_to(base).as_posix()
        require_no_space_path(relative)
        managed_path(config, root, relative)
        if target in destinations or target.exists() or target.is_symlink():
            raise FileExistsError("Destination already exists; choose another folder or Copy in order: " + relative)
        destinations.add(target)
        planned.append((source, target, entry["sha256"]))
    completed, backups = [], []
    try:
        for source, target, digest in planned:
            # Exclusive creation refuses an overwrite even if another program
            # creates a target after the complete selection was checked.
            with target.open("xb") as output:
                completed.append((source, target))
                with source.open("rb") as incoming:
                    shutil.copyfileobj(incoming, output, length=1024 * 1024)
            shutil.copystat(source, target)
            if sha256_file(target) != digest:
                raise FileExistsError("Source changed while copying: " + source.relative_to(base).as_posix())
        if operation == "move":
            # Keep originals until every destination is complete and verified.
            # Same-folder hidden backups let a failed scan restore all sources.
            for source, _, digest in planned:
                if sha256_file(source) != digest:
                    raise FileExistsError("Source changed; no files were moved")
            for source, _, digest in planned:
                backup = source.with_name(".fileproxy-moving-" + uuid4().hex)
                source.rename(backup)
                backups.append((source, backup))
                if sha256_file(backup) != digest:
                    raise FileExistsError("Source changed while moving")
        scan(config, [root], index_path)
    except Exception:
        for source, backup in reversed(backups):
            if source.exists() or source.is_symlink():
                raise FileExistsError("A new source appeared; its prior copy is retained at " + str(backup))
            backup.rename(source)
        for _, target in reversed(completed):
            target.unlink()
        raise
    for _, backup in backups:
        backup.unlink()
    return {"ok": True, "root": root, "destination": destination, "operation": operation,
            "files": [{"source": source.relative_to(base).as_posix(),
                       "path": target.relative_to(base).as_posix(), "sha256": digest}
                      for source, target, digest in planned]}


def managed_path(config, root, relative):
    target = resolve_file(config, root, relative)
    parts = PurePosixPath(relative).parts
    if any(part.startswith(".") for part in parts):
        raise ValueError("Hidden and repository files cannot be managed here")
    current = roots_from(config)[root]
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Symlinks cannot be managed here")
    if generated_file(target, catalog_paths(config).values()):
        raise ValueError("Catalogs and generated inventories cannot be removed here")
    return target


def checked_file(config, root, relative, expected_sha256):
    target = managed_path(config, root, relative)
    if not target.is_file():
        raise FileNotFoundError(relative)
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
        raise ValueError("The file's current SHA-256 is required; refresh the catalog first")
    if sha256_file(target) != expected_sha256:
        raise FileExistsError("File changed; refresh and preview it again: " + relative)
    return target


def trash_directory(config, root):
    base = roots_from(config)[root] / ".fileproxy-trash"
    if base.is_symlink() or (base.exists() and not base.is_dir()):
        raise ValueError("Trash must be a real directory inside the data root")
    return base


def trash_file(config, root, relative, expected_sha256, index_path=None):
    source = checked_file(config, root, relative, expected_sha256)
    if generated_file(source, catalog_paths(config, path=index_path).values()):
        raise ValueError("Catalogs cannot be removed here")
    base = trash_directory(config, root)
    base.mkdir(mode=0o700, exist_ok=True)
    if not (base / ".gitignore").exists():
        atomic_bytes(base / ".gitignore", b"*\n")
    trash_id = uuid4().hex
    folder = base / trash_id
    folder.mkdir(mode=0o700)
    record = {"root": root, "path": relative, "sha256": expected_sha256,
              "bytes": source.stat().st_size,
              "deletedAt": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    moved = False
    try:
        atomic_bytes(folder / "record.json", (json.dumps(record, indent=2) + "\n").encode())
        source.rename(folder / "content")
        moved = True
        if sha256_file(folder / "content") != expected_sha256:
            raise FileExistsError("File changed while being removed; it has been restored")
        scan(config, [root], index_path)
    except Exception:
        if moved:
            if source.exists() or source.is_symlink():
                raise FileExistsError("A new file appeared at the original path; the removed copy remains in Trash")
            (folder / "content").rename(source)
        shutil.rmtree(folder)
        raise
    return {"ok": True, **record, "trashId": trash_id}


def restore_file(config, root, trash_id, index_path=None):
    if not isinstance(trash_id, str) or not re.fullmatch(r"[a-f0-9]{32}", trash_id):
        raise ValueError("Invalid Trash item")
    folder = trash_directory(config, root) / trash_id
    content, metadata = folder / "content", folder / "record.json"
    if folder.is_symlink() or content.is_symlink() or metadata.is_symlink():
        raise ValueError("Trash items must not be symlinks")
    record = json.loads(metadata.read_text())
    target = managed_path(config, root, record["path"])
    if target.exists() or target.is_symlink():
        raise FileExistsError("Restore would replace an existing file: " + record["path"])
    if sha256_file(content) != record["sha256"]:
        raise ValueError("Trash content no longer matches its saved SHA-256")
    target.parent.mkdir(parents=True, exist_ok=True)
    content.rename(target)
    try:
        scan(config, [root], index_path)
    except Exception:
        target.rename(content)
        raise
    shutil.rmtree(folder)
    return {"ok": True, "root": root, "path": record["path"], "sha256": record["sha256"]}
