"""Bounded public Facebook oEmbed lookup; cache display fields, never embed HTML."""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


HOSTS = {
    "facebook.com", "www.facebook.com", "m.facebook.com", "web.facebook.com",
    "fb.watch", "www.fb.watch",
}
TTL = 6 * 60 * 60
MAX_URL = 2048
MAX_RESPONSE = 256 * 1024
API_VERSION = re.compile(r"^v[0-9]{1,3}\.[0-9]+$")


def canonical_url(value):
    raw = str(value or "").strip()
    if not raw or len(raw) > MAX_URL:
        raise ValueError("Facebook URL is missing or too long")
    parsed = urllib.parse.urlsplit(raw)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme.lower() not in ("http", "https") or host not in HOSTS or parsed.username or parsed.password:
        raise ValueError("Use a public Facebook post, video, reel, or fb.watch URL")
    if not parsed.path or parsed.path == "/":
        raise ValueError("Facebook URL must point to a post or video")
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    if any(key.lower() in {"access_token", "token", "code", "client_secret"} for key, _ in query):
        raise ValueError("Credential-bearing Facebook URLs are not accepted")
    query = [(key, item) for key, item in query if key.lower() not in {"fbclid", "mibextid", "__tn__", "ref", "refsrc"}]
    return urllib.parse.urlunsplit(("https", host, parsed.path, urllib.parse.urlencode(query), ""))


def _safe_https_url(value, allowed):
    parsed = urllib.parse.urlsplit(str(value or ""))
    host = (parsed.hostname or "").lower().rstrip(".")
    return str(value)[:2048] if parsed.scheme == "https" and any(host == suffix or host.endswith("." + suffix) for suffix in allowed) and not (parsed.username or parsed.password) else ""


def _cache_path(url, cache_dir):
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cache_dir / (digest + ".json")


def _read_cache(url, cache_dir):
    try:
        saved = json.loads(_cache_path(url, cache_dir).read_text(encoding="utf-8"))
        metadata = saved.get("metadata")
        age = time.time() - datetime.fromisoformat(metadata.get("fetchedAt", "")).timestamp()
        if saved.get("url") == url and isinstance(metadata, dict) and 0 <= age < TTL:
            return metadata
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _request_oembed(url, kind):
    version = os.environ.get("FACEBOOK_GRAPH_API_VERSION", "v27.0").strip()
    if not API_VERSION.fullmatch(version):
        raise ValueError("FACEBOOK_GRAPH_API_VERSION must look like v27.0")
    endpoint = "https://graph.facebook.com/" + version + "/oembed_" + kind + "?" + urllib.parse.urlencode({
        "url": url, "format": "json"
    })
    request = urllib.request.Request(endpoint, headers={
        "Accept": "application/json", "User-Agent": "FileProxy/1.0"
    })
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=8) as response:
        raw = response.read(MAX_RESPONSE + 1)
    if len(raw) > MAX_RESPONSE:
        raise ValueError("Facebook metadata response is too large")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Facebook returned invalid metadata")
    return data, endpoint


def lookup(value, cache_dir, atomic_write, refresh=False):
    url = canonical_url(value)
    if not refresh:
        cached = _read_cache(url, cache_dir)
        if cached:
            return {"ok": True, "cached": True, "metadata": cached}

    last_error = None
    data = None
    endpoint = ""
    # Facebook exposes separate oEmbed endpoints for posts and video-style URLs.
    for kind in ("post", "video"):
        try:
            data, endpoint = _request_oembed(url, kind)
            break
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in (400, 404):
                raise
        except urllib.error.URLError as error:
            last_error = error
            break
    if data is None:
        raise ValueError("Facebook public oEmbed metadata is unavailable") from last_error

    author_url = _safe_https_url(data.get("author_url"), {"facebook.com"})
    thumbnail_url = _safe_https_url(data.get("thumbnail_url"), {"fbcdn.net", "facebook.com", "fbsbx.com"})
    metadata = {
        "url": url,
        "title": str(data.get("title") or "")[:2000],
        "description": str(data.get("description") or "")[:4000],
        "authorName": str(data.get("author_name") or "")[:500],
        "authorUrl": author_url,
        "thumbnailUrl": thumbnail_url,
        "provider": str(data.get("provider_name") or "Facebook")[:100],
        "type": str(data.get("type") or "")[:80],
        "width": int(data["width"]) if str(data.get("width", "")).isdigit() else None,
        "height": int(data["height"]) if str(data.get("height", "")).isdigit() else None,
        "metadataSource": endpoint,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
    }
    cache_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(_cache_path(url, cache_dir), json.dumps(
        {"ok": True, "url": url, "metadata": metadata}, ensure_ascii=False
    ) + "\n")
    return {"ok": True, "cached": False, "metadata": metadata}
