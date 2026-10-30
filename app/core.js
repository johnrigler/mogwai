(function (root) {
  "use strict";
  function seconds(value) {
    if (/^\d+s?$/.test(value)) return String(Number(value.replace(/s$/, "")));
    const match = /^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$/.exec(value);
    return match && value ? String(Number(match[1] || 0) * 3600 + Number(match[2] || 0) * 60 + Number(match[3] || 0)) : "";
  }
  function link(value) {
    const url = new URL(value);
    if (!["https:", "http:"].includes(url.protocol) || url.username || url.password) throw new Error("Use an HTTP or HTTPS link without embedded credentials.");
    const host = url.hostname.toLowerCase(), parts = url.pathname.split("/").filter(Boolean);
    let id = "";
    if (host === "youtu.be" || host === "www.youtu.be") id = parts[0] || "";
    else if (["youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "www.youtube-nocookie.com", "youtube-nocookie.com"].includes(host)) {
      if (url.pathname === "/watch") id = url.searchParams.get("v") || "";
      else if (["shorts", "live", "embed", "v"].includes(parts[0])) id = parts[1] || "";
    }
    const youtube = /^[A-Za-z0-9_-]{11}$/.test(id);
    if (!youtube) return {url: url.href, youtube: false};
    const short = new URL("https://youtu.be/" + id);
    const time = seconds(url.searchParams.get("t") || url.searchParams.get("start") || "");
    if (time && Number.isSafeInteger(Number(time)) && Number(time) > 0) short.searchParams.set("t", time);
    return {url: short.href, youtube: true};
  }
  function fromShare(share) {
    const candidates = [];
    for (const key of ["url", "text", "title"]) {
      if (typeof share[key] !== "string") continue;
      for (const match of share[key].matchAll(/https?:\/\/[^\s<>"'`]+/gi)) {
        try { candidates.push(link(match[0].replace(/[.,;!?)\]}]+$/, ""))); } catch {}
      }
    }
    const chosen = candidates.find(item => item.youtube) || candidates[0];
    if (!chosen) throw new Error("No supported web link found.");
    return chosen;
  }
  function describe(share) {
    const unknown = reason => ({kind: "unknown", content: "", label: "Not recognized", reason});
    if (!share || typeof share !== "object" || Array.isArray(share)) return unknown("Mogwai expected shared text or a web link. The received data is shown below.");
    try {
      const chosen = fromShare(share);
      return {kind: chosen.youtube ? "youtube" : "link", content: chosen.url, label: chosen.youtube ? "YouTube video" : "Web link", reason: ""};
    } catch {}
    if (typeof share.url === "string" && share.url.trim()) return unknown("The shared URL is not a supported HTTP or HTTPS link. The original fields are shown below.");
    for (const key of ["text", "title"]) {
      if (typeof share[key] === "string" && share[key].trim()) return {kind: "text", content: share[key], label: "Plain text", reason: ""};
    }
    return unknown("Mogwai does not know what to open from these fields. Here is what it received.");
  }
  function chiselURL(endpoint, value) {
    const url = new URL(endpoint);
    if (!["https:", "http:"].includes(url.protocol) || url.username || url.password) throw new Error("Use an HTTP or HTTPS Chisel address without embedded credentials.");
    const fragment = new URLSearchParams(url.hash.slice(1));
    fragment.set("opreturn", value);
    url.hash = fragment.toString();
    url.searchParams.set("mode", "send");
    return url.href;
  }
  root.MogwaiShare = Object.freeze({fromShare, describe, link, chiselURL});
})(typeof window === "object" ? window : globalThis);
