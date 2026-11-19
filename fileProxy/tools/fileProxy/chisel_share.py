"""Render crawler-readable, record-specific Chisel share pages."""
import html
import re
import urllib.parse


TXID_RE = re.compile(r"^[0-9a-fA-F]{64}$")
COINS = {"bitcoin", "digibyte", "dogecoin", "ecash", "evm", "litecoin", "litecoinTestnet", "ravencoin"}
CHISEL_BASE = "https://johnrigler.github.io/chisel/"
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

    target = urllib.parse.urlencode({"mode": "portal", "coin": coin, "txid": txid})
    target_url = CHISEL_BASE + "?" + target
    title_html, description_html = html.escape(title, quote=True), html.escape(description, quote=True)
    image_html, target_html = html.escape(image, quote=True), html.escape(target_url, quote=True)
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
<meta property="og:url" content="https://rigler.org/fileproxy/chisel-share?coin={coin}&amp;txid={txid}">
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
           coin=urllib.parse.quote(coin, safe=""), txid=txid, target=target_html)
