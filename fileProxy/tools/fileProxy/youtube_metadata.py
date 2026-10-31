"""Bounded YouTube oEmbed lookup; cached display data is not ledger evidence."""
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone


HOSTS = {"youtu.be", "www.youtu.be", "youtube.com", "www.youtube.com",
         "m.youtube.com", "music.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"}
TTL = 6 * 60 * 60


def video_id(url):
    parsed = urllib.parse.urlsplit(str(url))
    if parsed.scheme not in ("http", "https") or parsed.hostname not in HOSTS or parsed.username or parsed.password:
        raise ValueError("Use a YouTube video URL without embedded credentials")
    parts = parsed.path.strip("/").split("/")
    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        value = parts[0]
    elif parsed.path == "/watch":
        value = urllib.parse.parse_qs(parsed.query).get("v", [""])[0]
    else:
        value = parts[1] if len(parts) == 2 and parts[0] in ("shorts", "live", "embed", "v") else ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        raise ValueError("YouTube video ID must contain 11 characters")
    return value


def https_url(value, hosts):
    parsed = urllib.parse.urlsplit(str(value or ""))
    return str(value) if parsed.scheme == "https" and parsed.hostname in hosts and not (parsed.username or parsed.password) else ""


def cached_metadata(url, cache_dir):
    try:
        identifier = video_id(url)
        value = json.loads((cache_dir / (identifier + ".json")).read_text(encoding="utf-8"))
        return value["metadata"] if value["metadata"]["videoId"] == identifier else {}
    except (ValueError, KeyError, TypeError, OSError):
        return {}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def lookup(url, cache_dir, atomic_write, refresh=False):
    identifier = video_id(url)
    saved = cached_metadata(url, cache_dir)
    if saved and not refresh:
        try:
            if 0 <= time.time() - datetime.fromisoformat(saved["fetchedAt"]).timestamp() < TTL:
                return {"ok": True, "cached": True, "metadata": saved}
        except (KeyError, TypeError, ValueError):
            pass
    endpoint = "https://www.youtube.com/oembed?" + urllib.parse.urlencode({
        "url": "https://www.youtube.com/watch?v=" + identifier, "format": "json"})
    request = urllib.request.Request(endpoint, headers={"Accept": "application/json", "User-Agent": "Mogwai/0.4"})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=8) as response:
        raw = response.read(256 * 1024 + 1)
    if len(raw) > 256 * 1024:
        raise ValueError("YouTube metadata response is too large")
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("title"), str) or not data["title"].strip():
        raise ValueError("YouTube returned no video title")
    metadata = {
        "videoId": identifier, "title": data["title"][:2000],
        "authorName": str(data.get("author_name") or "")[:500],
        "authorUrl": https_url(data.get("author_url"), HOSTS),
        "thumbnailUrl": https_url(data.get("thumbnail_url"), {"i.ytimg.com", "img.youtube.com"}),
        "provider": "YouTube", "metadataSource": endpoint,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write(cache_dir / (identifier + ".json"), json.dumps({"metadata": metadata}, ensure_ascii=False) + "\n")
    return {"ok": True, "cached": False, "metadata": metadata}
