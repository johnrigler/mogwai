"""Whitespace-delimited FileProxy destination markers for pasted input.

Do not treat URL fragments as markers. Unrecognized hashtags stay as content.
"""
import re

MAX_PASTE = 65536
ROUTING_TAGS = frozenset(("daisy", "daisy2026", "certledger", "chisel", "sbshell", "sbstats"))
MARKER = re.compile(r"(?<!\S)#([A-Za-z][A-Za-z0-9_-]*)(?=\s|$)", re.I)


def daisy_destination(roots, iso_year):
    """Use a registered annual archive when no multi-year Daisy root exists."""
    for name in ("daisy", "daisy" + str(iso_year), "daisy_" + str(iso_year)):
        if name in roots:
            return name
    return "daisy"


def split_paste(text):
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_PASTE:
        raise ValueError("Paste must contain at most 65536 UTF-8 bytes")
    found = []

    def remove(match):
        name = match.group(1).lower()
        if name in ROUTING_TAGS:
            found.append(name)
            return ""
        return match.group(0)

    content = MARKER.sub(remove, text).strip()
    if len(set(found)) > 1:
        raise ValueError("Conflicting routing directives: " + ", ".join(sorted(set(found))))
    if not content:
        raise ValueError("Paste a URL or text together with the routing directive")
    return content, (found[0] if found else "")
