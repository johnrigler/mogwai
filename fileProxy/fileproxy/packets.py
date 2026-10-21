"""Arrange original files and a printable HTML response, using stdlib only.

The browser prints the response to PDF. Existing PDF enclosures are rendered
for that HTML view with the user's shell pdftoppm command when needed.
"""
from functools import lru_cache
from html import escape
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import quote

from .core import roots_from, scan, sha256_file
from .management import checked_file, directory_path
from .names import canonical_filename, require_no_space_path


CSS = """
*{box-sizing:border-box}body{margin:0;background:#ddd;color:#111;font:10.5pt/1.28 Georgia,serif}
.page{position:relative;width:8.5in;min-height:11in;margin:18px auto;background:white;padding:.6in .65in;break-after:page}
.page:last-child{break-after:auto}p{white-space:pre-line;margin:0 0 8pt}h1{font-size:17pt;margin:0 0 12pt}h2{font-size:13pt;margin:10pt 0 7pt}
table{border-collapse:collapse;width:100%;font-size:9pt;margin:10pt 0}td,th{border:1px solid #aaa;padding:6pt;vertical-align:top;white-space:pre-line;text-align:left}
th{background:#eee}.label-zone{float:right;width:1in;height:1in;border:1px dashed #777;white-space:pre-line;text-align:center;font:7pt/1.4 system-ui;padding:8pt;margin:0 0 10pt 12pt}
.signature{display:inline-block;width:47%;padding-top:28pt;margin-right:2%;vertical-align:top;break-inside:avoid}.signature p{border-top:1px solid #222;padding-top:6pt}
.scan-page{padding:.25in;display:flex;align-items:center;justify-content:center;height:11in}.scan-page img{display:block;max-width:100%;max-height:10.5in;object-fit:contain;image-orientation:from-image}
.scan-page.captioned{padding-top:.6in}.scan-page.captioned img{max-height:10.1in}.scan-caption{position:absolute;top:.2in;left:.3in;right:.3in;font:9pt/1.3 system-ui}
.enclosure{margin:12pt 0;break-inside:avoid}.meta{font:8pt/1.4 system-ui;overflow-wrap:anywhere}.draft{font:9pt system-ui;color:#555;margin-bottom:12pt}
@page{size:Letter;margin:0}@media print{body{background:white}.page{margin:0;box-shadow:none}.no-print{display:none}}
"""


def validate_blocks(blocks):
    if not isinstance(blocks, list) or not blocks or len(blocks) > 300:
        raise ValueError("The response needs 1 to 300 text blocks")
    if len(json.dumps(blocks).encode()) > 100000:
        raise ValueError("Response letter is too long")
    for block in blocks:
        if not isinstance(block, dict) or block.get("kind") not in (
                "paragraph", "address", "heading", "table", "signature", "pagebreak", "label"):
            raise ValueError("Unsupported response text block")
        if block["kind"] == "table":
            rows = block.get("rows")
            if (not isinstance(rows, list) or not rows or len(rows) > 60
                    or any(not isinstance(row, list) or not row or len(row) > 8
                           or any(not isinstance(cell, str) for cell in row) for row in rows)
                    or len({len(row) for row in rows}) != 1):
                raise ValueError("Invalid response table")
        elif block["kind"] != "pagebreak" and not isinstance(block.get("text"), str):
            raise ValueError("Response text must be a string")


def letter_sections(blocks, draft, insertions=None):
    sections, page = [], []

    def finish_page():
        if page:
            sections.append('<section class="page response-letter">'
                            + ('<div class="draft">DRAFT - complete the letter fields</div>' if draft else "")
                            + "".join(page) + "</section>")
            page.clear()

    for number, block in enumerate(blocks):
        kind = block["kind"]
        if kind == "pagebreak":
            finish_page()
        elif kind == "table":
            rows = ["<tr>" + "".join("<td>" + escape(cell) + "</td>" for cell in row) + "</tr>"
                    for row in block["rows"]]
            page.append("<table>" + "".join(rows) + "</table>")
        else:
            text = escape(block["text"])
            if kind == "label":
                value = '<div class="label-zone">' + text + "</div>"
            elif kind == "heading":
                value = "<h2>" + text + "</h2>"
            elif kind == "signature":
                value = '<div class="signature"><p contenteditable="true">' + text + "</p></div>"
            else:
                value = '<p' + (' class="addr"' if kind == "address" else '') + ' contenteditable="true">' + text + "</p>"
            page.append(value)
        if insertions and number in insertions:
            finish_page()
            sections.extend(insertions[number])
    finish_page()
    return "".join(sections)


def document(title, contents):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            + "<title>" + escape(title) + "</title><style>" + CSS
            + "</style></head><body>" + contents + "</body></html>\n")


def pdf_pages(source, prefix):
    renderer = shutil.which("pdftoppm")
    if not renderer:
        raise ValueError("This PDF needs your shell's pdftoppm command for browser printing. Copy and Move work without PDF tools.")
    result = subprocess.run([renderer, "-png", "-r", "150", "-scale-to", "2200", str(source), str(prefix)],
                            capture_output=True, timeout=120)
    if result.returncode:
        raise ValueError("pdftoppm could not render " + source.name + ": " + result.stderr.decode(errors="replace")[:300])
    pages = sorted(prefix.parent.glob(prefix.name + "-*.png"),
                   key=lambda path: int(path.stem.rsplit("-", 1)[-1]))
    if not pages or len(pages) > 200:
        raise ValueError("PDF must contain 1 to 200 printable pages")
    return pages


@lru_cache(maxsize=128)
def pdf_thumbnail(source, modified_ns, size):
    """Small first-page preview; cache changes with the source's stat values."""
    renderer = shutil.which("pdftoppm")
    if not renderer:
        raise ValueError("PDF thumbnails need the shell's pdftoppm command")
    with tempfile.TemporaryDirectory(prefix="fileproxy-thumbnail-") as directory:
        prefix = Path(directory) / "preview"
        result = subprocess.run([renderer, "-f", "1", "-l", "1", "-singlefile", "-png",
                                 "-r", "72", "-scale-to", "240", str(source), str(prefix)],
                                capture_output=True, timeout=30)
        image = prefix.with_suffix(".png")
        if result.returncode or not image.is_file():
            raise ValueError("PDF preview unavailable")
        return image.read_bytes()


def build_packet(config, request, index_path=None):
    root, directory = request.get("root", ""), request.get("directory", "")
    parent = directory_path(config, root, directory)
    title, note = request.get("title", "Response"), request.get("note", "")
    if not isinstance(title, str) or not title.strip() or len(title) > 120:
        raise ValueError("Response title must contain 1 to 120 characters")
    if not isinstance(note, str) or len(note) > 4096:
        raise ValueError("Response note is too long")
    letter = request.get("letter", {})
    if not isinstance(letter, dict):
        raise ValueError("Choose a response letter")
    source = checked_file(config, root, letter.get("path", ""), letter.get("sha256"))
    if source.suffix.lower() not in (".html", ".htm", ".txt"):
        raise ValueError("Choose an HTML or text response")
    blocks = letter.get("blocks")
    validate_blocks(blocks)
    selected = request.get("attachments", [])
    if not isinstance(selected, list) or not selected or len(selected) > 200:
        raise ValueError("Add 1 to 200 existing enclosures")
    folder_name = request.get("folderName", "response-1")
    if not isinstance(folder_name, str) or canonical_filename(folder_name) != folder_name:
        raise ValueError("Use a plain response folder name without spaces or slashes")
    target = parent / folder_name
    require_no_space_path(target.relative_to(roots_from(config)[root]).as_posix())
    if target.exists() or target.is_symlink():
        raise FileExistsError("Response folder already exists: " + folder_name)
    items, seen = [], set()
    for number, row in enumerate(selected, 1):
        if not isinstance(row, dict):
            raise ValueError("Invalid enclosure")
        relative = row.get("path", "")
        path = checked_file(config, root, relative, row.get("sha256"))
        if relative in seen:
            raise ValueError("An enclosure was added twice")
        seen.add(relative)
        if path.suffix.lower() not in (".pdf", ".png", ".jpg", ".jpeg", ".webp"):
            raise ValueError("Choose existing PDFs or image scans")
        label = row.get("label", path.name)
        if not isinstance(label, str) or len(label) > 240:
            raise ValueError("Enclosure description is too long")
        after = row.get("afterBlock")
        if after is not None and (type(after) is not int or not 0 <= after < len(blocks)
                                  or blocks[after]["kind"] == "pagebreak"):
            raise ValueError("Choose an existing narrative block for the document placement")
        items.append({"sourcePath": relative, "path": canonical_filename(f"{number:03}-" + path.name),
                      "label": label, "sha256": row["sha256"], "afterBlock": after})
    texts = [block["text"] for block in blocks if "text" in block]
    texts.extend(cell for block in blocks if block["kind"] == "table" for row in block["rows"] for cell in row)
    draft = any(re.search(r"\[[^\]\n]{1,160}\]", text) for text in texts)
    letter_html = letter_sections(blocks, draft)
    stage = Path(tempfile.mkdtemp(prefix=".fileproxy-response-", dir=parent))
    committed = False
    try:
        insertions, index = {}, []
        for number, item in enumerate(items, 1):
            incoming = checked_file(config, root, item["sourcePath"], item["sha256"])
            saved = stage / item["path"]
            shutil.copyfile(incoming, saved)
            if sha256_file(saved) != item["sha256"]:
                raise FileExistsError("Enclosure changed while being copied")
            if saved.suffix.lower() == ".pdf":
                (stage / "pages").mkdir(exist_ok=True)
                images = pdf_pages(saved, stage / "pages" / f"{number:03}-page")
            else:
                images = [saved]
            item["pageCount"] = len(images)
            pages = []
            for page_number, image in enumerate(images, 1):
                name = image.relative_to(stage).as_posix()
                caption = (escape(item["label"]) + " · page " + str(page_number) + " of " + str(len(images))) if item["label"] else ""
                pages.append('<section class="page scan-page' + (' captioned' if caption else '') + '">'
                             + ('<div class="scan-caption">' + caption + '</div>' if caption else '')
                             + '<img alt="' + escape(item["label"] or incoming.name, quote=True)
                             + '" src="' + quote(name, safe="/") + '"></section>')
            insertions.setdefault(item["afterBlock"], []).extend(pages)
        ordered = sorted(enumerate(items, 1), key=lambda pair: (
            len(blocks) if pair[1]["afterBlock"] is None else pair[1]["afterBlock"], pair[0]))
        for number, (_, item) in enumerate(ordered, 1):
            index.append('<div class="enclosure" data-source="' + escape(item["sourcePath"], quote=True)
                         + '"><h2>' + str(number) + ". " + escape(item["label"] or Path(item["sourcePath"]).name)
                         + '</h2><p class="meta">' + str(item["pageCount"]) + ' page(s)</p></div>')
        enclosures = '<section class="page enclosures"><h1>Documents included</h1><p>' + escape(note)
        enclosures += "</p>" + "".join(index) + "</section>"
        assembled = letter_sections(blocks, draft, insertions) + enclosures + "".join(insertions.get(None, []))
        (stage / "letter.html").write_text(document(title, letter_html), encoding="utf-8")
        (stage / "index.html").write_text(document(title, assembled), encoding="utf-8")
        stage.rename(target)
        committed = True
        scan(config, [root], index_path)
    except Exception:
        shutil.rmtree(target if committed else stage)
        raise
    relative = target.relative_to(roots_from(config)[root]).as_posix()
    return {"ok": True, "root": root, "directory": relative, "path": relative + "/index.html",
            "letterPath": relative + "/letter.html", "draft": draft,
            "pages": assembled.count('<section '),
            "attachments": items}
