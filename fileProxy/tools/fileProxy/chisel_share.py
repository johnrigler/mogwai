"""Render crawler-readable, record-specific Chisel share pages."""
import html
import os
import re
import urllib.parse


TXID_RE = re.compile(r"^[0-9a-fA-F]{64}$")
COINS = {"bitcoin", "bsv", "bsvTestnet", "digibyte", "dogecoin", "ecash", "evm", "litecoin", "litecoinTestnet", "ravencoin"}
CHISEL_BASE = "https://johnrigler.github.io/chisel/"
PUBLIC_FILEPROXY_BASE = os.environ.get("CHISEL_PUBLIC_FILEPROXY_URL", "https://rigler.org/fileproxy").rstrip("/")
if not PUBLIC_FILEPROXY_BASE.startswith("https://") or "?" in PUBLIC_FILEPROXY_BASE or "#" in PUBLIC_FILEPROXY_BASE:
    PUBLIC_FILEPROXY_BASE = "https://rigler.org/fileproxy"
DEFAULT_IMAGE = "https://johnrigler.github.io/chisel/docs/chisel-social.png"


def _text(value, limit):
    value = str(value or "")
    value = "".join(ch for ch in value if ch >= " " and ch != "\x7f")
    return value.strip()[:limit]


def _https_image(value):
    parsed = urllib.parse.urlsplit(str(value or "").strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return DEFAULT_IMAGE
    if len(str(value)) > 2048:
        return DEFAULT_IMAGE
    return str(value)


def render(query):
    coin = str((query.get("coin") or [""])[0])
    txid = str((query.get("txid") or [""])[0]).lower()
    if coin not in COINS or not TXID_RE.fullmatch(txid):
        raise ValueError("A supported coin and 64-hex transaction ID are required")

    title = _text((query.get("title") or [""])[0], 200)
    description = _text((query.get("description") or [""])[0], 1000)
    image = _https_image((query.get("image") or [""])[0])
    if not title:
        title = coin.upper() + " record " + txid[:12]
    if not description:
        description = "Public ledger record " + txid + " on " + coin + "."

    target_params = {"mode": "portal", "coin": coin, "txid": txid}
    chain = str((query.get("chain") or [""])[0])
    source = str((query.get("source") or [""])[0])
    if coin == "evm" and re.fullmatch(r"[0-9]{1,15}", chain):
        target_params["chain"] = chain
    if coin == "evm" and source in {"evmGomez", "evmJethro", "evmPolygonThunderword", "other"}:
        target_params["source"] = source
    target_url = CHISEL_BASE + "?" + urllib.parse.urlencode(target_params)
    share_params = {"coin": coin, "txid": txid}
    if (query.get("title") or [""])[0]:
        share_params["title"] = title
    if (query.get("description") or [""])[0]:
        share_params["description"] = description
    if (query.get("image") or [""])[0]:
        share_params["image"] = image
    if coin == "evm" and re.fullmatch(r"[0-9]{1,15}", chain):
        share_params["chain"] = chain
    if coin == "evm" and source in {"evmGomez", "evmJethro", "evmPolygonThunderword", "other"}:
        share_params["source"] = source
    share_url = PUBLIC_FILEPROXY_BASE + "/chisel-share?" + urllib.parse.urlencode(share_params)
    title_html, description_html = html.escape(title, quote=True), html.escape(description, quote=True)
    image_html, target_html = html.escape(image, quote=True), html.escape(target_url, quote=True)
    share_url_html = html.escape(share_url, quote=True)
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<meta name="robots" content="noindex">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Chisel">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{share_url}">
<meta property="og:image" content="{image}">
<meta property="og:image:secure_url" content="{image}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{image}">
</head>
<body>
<main>
<h1>{title}</h1>
<p>{description}</p>
<p><a href="{target}">Open this record in Chisel</a></p>
<img src="{image}" alt="" style="max-width:100%;height:auto">
</main>
</body>
</html>
""".format(title=title_html, description=description_html, image=image_html,
           coin=urllib.parse.quote(coin, safe=""), txid=txid, target=target_html, share_url=share_url_html)
