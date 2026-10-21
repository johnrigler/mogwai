"""Filename policy for generated filesystem artifacts.

Canonical paths use POSIX components, no whitespace, and ASCII-safe names.
Keep display titles and original source names in metadata instead of relying
on filenames for human-readable descriptions.
"""
from __future__ import annotations

from pathlib import PurePosixPath
import re
import unicodedata

WHITESPACE = re.compile(r"\s")
DISALLOWED = re.compile(r"[^A-Za-z0-9._-]+")
REPEAT_DASH = re.compile(r"-{2,}")
MAX_COMPONENT = 120


def canonical_filename(value, default="document", max_length=MAX_COMPONENT):
    """Convert a proposed *single filename*, never a full path, to a safe name.

    Examples: "Business Registration Form 211.pdf" ->
    "Business-Registration-Form-211.pdf". Does not modify file content.
    """
    if not isinstance(value, str) or not value or "/" in value or "\\" in value:
        raise ValueError("Expected a single filename, not a path")
    if not isinstance(max_length, int) or max_length < 12:
        raise ValueError("Invalid max_length")
    normalized = unicodedata.normalize("NFKD", value)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_name = DISALLOWED.sub("-", ascii_name)
    ascii_name = REPEAT_DASH.sub("-", ascii_name).strip("._-")
    if not ascii_name:
        ascii_name = default
    stem, dot, ext = ascii_name.rpartition(".")
    # Preserve a reasonable extension after truncation.
    if dot and stem and 1 <= len(ext) <= 12:
        suffix = "." + ext
        kept = stem[:max_length - len(suffix)].rstrip("._-") or default
        result = kept + suffix
    else:
        result = ascii_name[:max_length].rstrip("._-") or default
    if result in (".", "..") or WHITESPACE.search(result):
        raise ValueError("Invalid canonical filename")
    return result


def require_no_space_path(path):
    """Reject whitespace in new artifact paths; reads of legacy names may continue."""
    if not isinstance(path, str) or not path or WHITESPACE.search(path):
        raise ValueError("New FileProxy paths cannot contain whitespace: " + repr(path))
    parts = PurePosixPath(path).parts
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("New FileProxy paths cannot contain empty/dot segments")
    return path
