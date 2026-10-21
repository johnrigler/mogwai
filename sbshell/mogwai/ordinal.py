"""Ordinal filename helpers for the SB Shell / Mogwai filesystem model."""

from pathlib import Path
import re

ORDINAL = re.compile(r"^\d+$")


def parse_name(name: str) -> dict:
    """Parse leading underscore-separated numeric fields as ordinal coordinates."""
    path = Path(name)
    stem = path.stem
    parts = stem.split("_")

    ordinals = []
    rest = []

    consuming_ordinals = True
    for part in parts:
        if consuming_ordinals and ORDINAL.match(part):
            ordinals.append(part)
        else:
            consuming_ordinals = False
            rest.append(part)

    return {
        "name": name,
        "ordinals": ordinals,
        "coordinate": ".".join(ordinals),
        "label": "_".join(rest),
        "suffix": path.suffix,
    }


def lexical_key(name: str) -> str:
    """SB Shell ordering is intentionally plain lexical ordering."""
    return name
