#!/usr/bin/env python3
"""Extract the FileProxy browser's inline vanilla JS for parse-only CI."""
from pathlib import Path
import re
import sys

page = sys.argv[1] if len(sys.argv) > 1 else "index.html"
if page not in ("index.html", "catalog.html", "packet.html", "record.html"):
    raise SystemExit("Unknown website page")
html = (Path(__file__).resolve().parents[1] / "web" / page).read_text(encoding="utf-8")
scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, flags=re.S | re.I)
if len(scripts) != 1:
    raise SystemExit("Expected one inline JavaScript block; got " + str(len(scripts)))
sys.stdout.write(scripts[0])
