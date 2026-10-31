(function (root) {
  "use strict";
  const INDEX = "mogwai.user-data.v1", ENABLED = "mogwai.user-data.enabled.v1", COOKIE = "mogwai_data_check", PREFERENCE = "mogwai_data_preference";
  const LIMIT = 100, HEX = /^[a-f0-9]{64}$/;
  function canonicalJSON(value) {
    if (Array.isArray(value)) return "[" + value.map(canonicalJSON).join(",") + "]";
    if (value && typeof value === "object") return "{" + Object.keys(value).sort().map(key => JSON.stringify(key) + ":" + canonicalJSON(value[key])).join(",") + "}";
    return JSON.stringify(value);
  }
  async function digest(value) {
    if (!root.crypto?.subtle) throw new Error("SHA-256 requires HTTPS and Web Crypto support");
    const bytes = new TextEncoder().encode(canonicalJSON(value));
    const result = await root.crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(result), byte => byte.toString(16).padStart(2, "0")).join("");
  }
  function validEntry(entry) {
    return entry && HEX.test(entry.subjectHash) && HEX.test(entry.hash) && Number.isSafeInteger(entry.savedAt) && entry.savedAt > 0;
  }
  function create() {
    let entries = [], enabled = true, indexSaved = false, cookieSaved = false;
    const path = root.location.pathname.replace(/[^/]*$/, "") || "/";
    const suffix = "; Path=" + path + "; SameSite=Strict" + (root.location.protocol === "https:" ? "; Secure" : "");
    function cookieValue(name) {
      try { return root.document.cookie.split(";").map(item => item.trim()).find(item => item.startsWith(name + "="))?.split("=")[1] || ""; }
      catch { return ""; }
    }
    function cookie() {
      try {
        const value = cookieValue(COOKIE);
        const match = /^v1\.([a-f0-9]{64})\.([a-f0-9]{64})\.(\d{13})$/.exec(value);
        return match ? {subjectHash: match[1], hash: match[2], savedAt: Number(match[3])} : null;
      } catch { return null; }
    }
    function reload() {
      const preference = cookieValue(PREFERENCE);
      if (preference === "off" || preference === "on") enabled = preference === "on";
      try {
        const savedPreference = root.localStorage.getItem(ENABLED);
        if (savedPreference !== null) enabled = savedPreference !== "0";
        const raw = root.localStorage.getItem(INDEX);
        const data = raw && raw.length < 100000 ? JSON.parse(raw) : [];
        if (Array.isArray(data)) entries = data.filter(validEntry).slice(-LIMIT);
        indexSaved = true;
      } catch { indexSaved = false; }
      const last = cookie();
      if (enabled && last && !entries.some(entry => entry.subjectHash === last.subjectHash)) entries.push(last);
      entries = entries.slice(-LIMIT);
      if (!enabled) entries = [];
    }
    function writeCookie(entry) {
      try {
        root.document.cookie = COOKIE + "=" + (entry ? "v1." + entry.subjectHash + "." + entry.hash + "." + entry.savedAt : "") + "; Max-Age=" + (entry ? 15552000 : 0) + suffix;
        cookieSaved = entry ? cookie()?.hash === entry.hash : !cookie();
      } catch { cookieSaved = false; }
    }
    function persist(entry) {
      try {
        root.localStorage.setItem(INDEX, JSON.stringify(entries));
        indexSaved = true;
      } catch { indexSaved = false; }
      writeCookie(entry);
    }
    function result(subjectHash, hash) {
      const saved = entries.find(entry => entry.subjectHash === subjectHash);
      return {subjectHash, currentHash: hash, savedHash: saved?.hash || null,
        status: !enabled ? "off" : !saved ? "new" : saved.hash === hash ? "match" : "changed",
        savedAt: saved?.savedAt || null};
    }
    async function inspect(subject, value) {
      const [subjectHash, hash] = await Promise.all([digest(subject), digest(value)]);
      reload();
      return result(subjectHash, hash);
    }
    function remember(check, replace = false) {
      reload();
      if (!enabled || !HEX.test(check.subjectHash) || !HEX.test(check.currentHash)) return check;
      const previous = entries.find(entry => entry.subjectHash === check.subjectHash);
      if (previous && previous.hash !== check.currentHash && !replace) return result(check.subjectHash, check.currentHash);
      const entry = {subjectHash: check.subjectHash, hash: check.currentHash,
        savedAt: previous?.hash === check.currentHash ? previous.savedAt : Date.now()};
      entries = entries.filter(item => item.subjectHash !== entry.subjectHash).concat(entry).slice(-LIMIT);
      persist(entry);
      return {...result(entry.subjectHash, entry.hash), status: previous ? "match" : "saved"};
    }
    function clear() {
      entries = [];
      try { root.localStorage.removeItem(INDEX); indexSaved = true; } catch { indexSaved = false; }
      writeCookie(null);
    }
    function forget(subjectHash) {
      reload();
      entries = entries.filter(entry => entry.subjectHash !== subjectHash);
      persist(entries.at(-1) || null);
    }
    function setEnabled(value) {
      enabled = !!value;
      try { root.localStorage.setItem(ENABLED, enabled ? "1" : "0"); } catch {}
      try { root.document.cookie = PREFERENCE + "=" + (enabled ? "on" : "off") + "; Max-Age=15552000" + suffix; } catch {}
      if (!enabled) clear();
    }
    function exportData() {
      reload();
      return {format: "mogwai-user-data", version: 1, enabled, checks: entries.map(entry => ({...entry}))};
    }
    function importData(data) {
      if (!data || data.format !== "mogwai-user-data" || data.version !== 1 || !Array.isArray(data.checks) || data.checks.length > LIMIT || !data.checks.every(validEntry)) throw new Error("Choose a Mogwai data-check export with at most 100 valid SHA-256 checks");
      reload();
      const imported = new Map(entries.map(entry => [entry.subjectHash, entry]));
      for (const entry of data.checks) {
        if (imported.has(entry.subjectHash) && imported.get(entry.subjectHash).hash !== entry.hash) throw new Error("An imported check conflicts with a saved hash. Existing checks were kept.");
        imported.set(entry.subjectHash, {subjectHash: entry.subjectHash, hash: entry.hash, savedAt: entry.savedAt});
      }
      setEnabled(true);
      entries = [...imported.values()].slice(-LIMIT);
      persist(entries.at(-1) || null);
      return entries.length;
    }
    reload();
    return Object.freeze({inspect, remember, forget, clear, setEnabled, exportData, importData,
      state() {return {enabled, count: entries.length, indexSaved, cookieSaved};}});
  }
  root.MogwaiUserData = Object.freeze({create, canonicalJSON, digest});
})(typeof window === "object" ? window : globalThis);
