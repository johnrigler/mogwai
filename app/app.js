"use strict";
const $ = id => document.getElementById(id);
const CHISEL = "mogwai.chisel-url.v1";
const LAST = "mogwai.shared-link.v1";
const CONSOLE = "mogwai.share-console.v1";
const CONSOLE_LOG = "mogwai.share-console-log.v1";
const DEFAULT_CHISEL = "https://johnrigler.github.io/chisel/?v=2.8.13";
const METADATA_URL = "https://rigler.org/fileproxy/youtube-metadata";
const SYSTEM_TEST = {title: "Mogwai sharing test", text: "Mogwai system-share test: this is plain text, with no YouTube link."};
let selected = null, installPrompt = null, receiptText = "";
let consoleEnabled = false, consoleEntries = [];
let media = null, metadataRequest = null, metadataSerial = 0;
const userData = MogwaiUserData.create();
let currentCheck = null, checkSerial = 0;

function renderUserData() {
  $("saved-data").textContent = JSON.stringify(userData.exportData(), null, 2);
  const state = userData.state();
  $("remember-data").checked = state.enabled;
  $("saved-count").textContent = String(state.count);
  $("accept-check").hidden = currentCheck?.status !== "changed";
  $("forget-check").hidden = !currentCheck?.savedHash;
  $("check-hashes").textContent = currentCheck?.currentHash ? "Current SHA-256: " + currentCheck.currentHash + "\nSaved SHA-256:   " + (currentCheck.savedHash || "none") : "";
  const labels = {
    saved: "First lookup: saved this SHA-256 as the baseline on this device.",
    match: "Matches this device’s saved SHA-256. The compared data is unchanged.",
    changed: "Changed: the returned data differs from this device’s saved hash. The saved baseline has been kept.",
    off: "Remembering is disabled. This lookup will not save a cookie or baseline.",
    forgotten: "Saved check erased. A later lookup can establish a new baseline."
  };
  $("check-status").textContent = currentCheck?.error || labels[currentCheck?.status] || (media?.state === "ready" ? "Computing SHA-256…" : "A data check becomes available after a successful metadata lookup.");
  $("check-status").className = currentCheck?.status === "changed" || currentCheck?.error ? "hint error" : "hint";
  $("storage-note").textContent = !state.enabled ? "Remembering is off; its saved checks and cookie are erased." : !state.indexSaved && !state.cookieSaved ? "Storage is unavailable. Checks last only in this window." : "At most 100 SHA-256 baselines stay in this browser. One first-party cookie remembers the most recent accepted check for 180 days. Export checks to carry them to another host or device.";
}
async function syncIntegrity() {
  const serial = ++checkSerial;
  currentCheck = null;
  renderPortal();
  if (media?.state !== "ready" || selected?.kind !== "youtube") return;
  const content = selected.content, metadata = media.metadata;
  try {
    let check = await userData.inspect(content, MogwaiShare.integrityData(content, metadata, media.cards));
    if (serial !== checkSerial || media?.content !== content || media?.metadata !== metadata) return;
    if (check.status === "new" || check.status === "match") check = userData.remember(check);
    currentCheck = check;
  } catch (error) {
    if (serial !== checkSerial) return;
    currentCheck = {error: error.message};
  }
  renderPortal();
}
$("remember-data").addEventListener("change", () => {
  userData.setEnabled($("remember-data").checked);
  syncIntegrity();
});
$("accept-check").addEventListener("click", () => {
  if (currentCheck?.status !== "changed") return;
  currentCheck = userData.remember(currentCheck, true);
  renderPortal();
});
$("forget-check").addEventListener("click", () => {
  if (!currentCheck?.subjectHash) return;
  checkSerial++;
  userData.forget(currentCheck.subjectHash);
  currentCheck = {...currentCheck, status: "forgotten", savedHash: null};
  renderPortal();
});
$("erase-data").addEventListener("click", () => {
  checkSerial++;
  userData.clear();
  currentCheck = currentCheck ? {...currentCheck, status: "forgotten", savedHash: null} : null;
  $("data-status").textContent = "Saved data checks and their cookie erased.";
  renderPortal();
});
$("export-data").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(userData.exportData(), null, 2) + "\n"], {type: "application/json"});
  const url = URL.createObjectURL(blob), anchor = document.createElement("a");
  anchor.href = url; anchor.download = "mogwai-data-checks.json";
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
  $("data-status").textContent = "Export contains hashes and saved times, with no video titles, URLs, receipt text, or keys.";
});
$("import-data").addEventListener("change", async event => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    if (file.size > 256000) throw new Error("Data-check export is too large");
    const count = userData.importData(JSON.parse(await file.text()));
    $("data-status").textContent = count + " saved checks available. Imported hashes are user-supplied baselines.";
    await syncIntegrity();
  } catch (error) { $("data-status").textContent = "Could not import checks: " + error.message; }
  finally { event.target.value = ""; }
});

function renderPortal() {
  $("tx-preview").hidden = !selected;
  $("portal-data").textContent = selected ? JSON.stringify(MogwaiShare.portalPreview(selected, media?.state === "ready" ? media.cards : []), null, 2) : "";
  $("youtube-preview").hidden = selected?.kind !== "youtube";
  $("metadata-image").hidden = true;
  $("metadata-title").textContent = "";
  $("metadata-author").textContent = "";
  $("metadata-source").textContent = "";
  renderUserData();
  if (!media || selected?.kind !== "youtube") return;
  $("metadata-status").textContent = media.state === "loading" ? "Loading metadata via rigler.org…" : media.state === "ready" ? "Metadata via rigler.org · " + (media.cached ? "cached lookup" : "fresh lookup") : media.error;
  $("metadata-status").className = media.state === "error" ? "hint error" : "hint";
  $("retry-metadata").disabled = media.state === "loading";
  if (media.state !== "ready") return;
  $("metadata-title").textContent = media.metadata.title;
  $("metadata-author").textContent = media.metadata.authorName || "Channel not supplied";
  $("metadata-source").textContent = "YouTube · " + media.metadata.videoId + " · fetched " + media.metadata.fetchedAt;
  try {
    const thumbnail = new URL(media.metadata.thumbnailUrl);
    if (thumbnail.protocol === "https:" && ["i.ytimg.com", "img.youtube.com"].includes(thumbnail.hostname) && !thumbnail.username && !thumbnail.password) {
      $("metadata-image").src = thumbnail.href;
      $("metadata-image").hidden = false;
    }
  } catch {}
}
function syncMetadata(force = false) {
  const content = selected?.kind === "youtube" ? selected.content : "";
  if (!force && content && content === media?.content) { renderPortal(); return; }
  metadataSerial++;
  checkSerial++;
  currentCheck = null;
  metadataRequest?.abort();
  metadataRequest = null;
  media = null;
  if (!content) { renderPortal(); return; }
  const serial = metadataSerial;
  const abort = new AbortController();
  metadataRequest = abort;
  media = {content, state: "loading"};
  renderPortal();
  const timeout = setTimeout(() => abort.abort(), 12000);
  (async () => {
    try {
      const endpoint = new URL(METADATA_URL);
      endpoint.searchParams.set("url", content);
      if (force) endpoint.searchParams.set("refresh", "1");
      const response = await fetch(endpoint.href, {signal: abort.signal, cache: "no-store", credentials: "omit", referrerPolicy: "no-referrer"});
      if (!response.ok) throw new Error("rigler.org returned HTTP " + response.status);
      const data = await response.json();
      if (!data.ok || data.metadata?.videoId !== new URL(content).pathname.slice(1) || typeof data.metadata?.title !== "string" || !Array.isArray(data.mediaCards) || !data.mediaCards.every(card => card && typeof card === "object" && !Array.isArray(card))) throw new Error(data.error || "Invalid metadata response");
      if (serial !== metadataSerial) return;
      media = {content, state: "ready", metadata: data.metadata, cards: data.mediaCards, cached: !!data.cached};
    } catch (error) {
      if (serial !== metadataSerial) return;
      media = {content, state: "error", error: "Metadata unavailable: " + (error.name === "AbortError" ? "request timed out" : error.message) + ". Retry the lookup, or continue with the URL. No metadata has been added to the preview."};
    } finally {
      clearTimeout(timeout);
      if (serial === metadataSerial) {
        metadataRequest = null;
        if (media?.state === "ready") syncIntegrity();
        else renderPortal();
      }
    }
  })();
}
$("retry-metadata").addEventListener("click", () => syncMetadata(true));
$("copy-portal").addEventListener("click", async () => {
  try {
    if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
    await navigator.clipboard.writeText($("portal-data").textContent);
    status("TX portal preview copied.");
  } catch { status("Select and copy the TX portal preview directly.", true); }
});

function renderConsole() {
  $("console-enabled").checked = consoleEnabled;
  $("share-console").hidden = !consoleEnabled;
  $("console-data").textContent = consoleEntries.map(entry => JSON.stringify(entry, null, 2)).join("\n\n");
  $("console-count").textContent = String(consoleEntries.length);
  $("console-data").scrollTop = $("console-data").scrollHeight;
}
function clearConsole() {
  consoleEntries = [];
  try { sessionStorage.removeItem(CONSOLE_LOG); } catch {}
  renderConsole();
}
function recordConsole(fields, error = "") {
  if (!consoleEnabled) return;
  consoleEntries.push({received_at: new Date().toISOString(), ...(error ? {error} : {}), fields});
  while (consoleEntries.length > 20 || (consoleEntries.length > 1 && new TextEncoder().encode(JSON.stringify(consoleEntries)).byteLength > 200000)) consoleEntries.shift();
  try { sessionStorage.setItem(CONSOLE_LOG, JSON.stringify(consoleEntries)); } catch {}
  renderConsole();
}
try {
  consoleEnabled = localStorage.getItem(CONSOLE) === "1";
  if (!consoleEnabled) sessionStorage.removeItem(CONSOLE_LOG);
  const saved = consoleEnabled ? sessionStorage.getItem(CONSOLE_LOG) : null;
  if (saved && new TextEncoder().encode(saved).byteLength <= 200000) {
    const parsed = JSON.parse(saved);
    if (Array.isArray(parsed)) consoleEntries = parsed.slice(-20);
  }
} catch {}
renderConsole();
$("console-enabled").addEventListener("change", () => {
  consoleEnabled = $("console-enabled").checked;
  try { localStorage.setItem(CONSOLE, consoleEnabled ? "1" : "0"); } catch {}
  if (!consoleEnabled) clearConsole();
  else if (receiptText && !consoleEntries.length) recordConsole(JSON.parse(receiptText));
  renderConsole();
  status(consoleEnabled ? "Share console enabled. Incoming shares stay here for inspection." : "Share console disabled and its log cleared.");
});
$("clear-console").addEventListener("click", clearConsole);
$("copy-console").addEventListener("click", async () => {
  try {
    if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
    await navigator.clipboard.writeText($("console-data").textContent);
    status("Console copied.");
  } catch { status("Select and copy the console text directly.", true); }
});

function status(message = "", error = false) {
  $("status").textContent = message;
  $("status").className = error ? "error" : "";
}
function receipt(value, description, error = "", logReceipt = true) {
  receiptText = JSON.stringify(value, null, 2);
  $("received-share").hidden = false;
  $("received-kind").textContent = error ? "Could not process this share" : description.label;
  $("received-note").textContent = error || description.reason || "These are the original fields Mogwai received. Review the content below before opening Chisel.";
  $("received-data").textContent = receiptText;
  if (logReceipt) recordConsole(value, error);
}
function preview() {
  selected = null; $("open-chisel").disabled = true;
  try {
    const description = MogwaiShare.describe({text: $("shared-url").value});
    if (!description.content) throw new Error("Share or paste text or an HTTP(S) link.");
    const bytes = new TextEncoder().encode(description.content).byteLength;
    if (bytes > 4096) throw new Error("Chisel's share import accepts at most 4,096 bytes. Edit the content before opening; the original receipt is unchanged.");
    MogwaiShare.chiselURL($("chisel-url").value, description.content);
    selected = description;
    $("detected").textContent = selected.label + " · " + bytes + " bytes in OP_RETURN" + (bytes > 80 ? " · check the selected chain’s payload limit in Chisel" : "");
    $("open-chisel").disabled = false;
    try {
      if (selected.kind === "youtube" || selected.kind === "link") sessionStorage.setItem(LAST, selected.content);
      else sessionStorage.removeItem(LAST);
    } catch {}
  } catch (error) {
    $("detected").textContent = $("shared-url").value.trim() ? error.message : "Text and web links are supported. YouTube links are shortened automatically.";
  }
  syncMetadata();
}
function openChisel(event) {
  if (event) event.preventDefault();
  preview(); if (!selected || $("open-chisel").disabled) return;
  try {
    const ready = media?.state === "ready";
    const record = MogwaiShare.sharedRecord(selected, ready ? media.metadata : {}, ready ? media.cards : []);
    const target = MogwaiShare.chiselURL($("chisel-url").value, selected.content, record);
    try { localStorage.setItem(CHISEL, $("chisel-url").value); } catch {}
    status("Opening Chisel with the complete record preview above Send…");
    location.replace(target);
  } catch (error) { status(error.message, true); }
}
$("share-form").addEventListener("submit", openChisel);
$("shared-url").addEventListener("input", () => { status(); preview(); });
$("chisel-url").addEventListener("input", preview);
$("chisel-url").addEventListener("change", () => {
  try { MogwaiShare.chiselURL($("chisel-url").value, "test"); localStorage.setItem(CHISEL, $("chisel-url").value); } catch {}
});
$("copy-received").addEventListener("click", async () => {
  try {
    if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
    await navigator.clipboard.writeText(receiptText);
    status("Received fields copied. Review them before sharing them with someone else.");
  } catch { status("Select and copy the received fields directly below the heading.", true); }
});
$("clear-received").addEventListener("click", () => {
  receiptText = ""; $("received-data").textContent = ""; $("received-share").hidden = true;
  $("shared-url").value = "";
  try { sessionStorage.removeItem(LAST); } catch {}
  clearConsole();
  status(); preview();
});
$("system-share-test").addEventListener("click", async () => {
  if (typeof navigator.share !== "function") return;
  $("system-share-test").disabled = true;
  $("system-share-status").textContent = "Choose Mogwai in the system chooser. The receiver should show Plain text and the test message.";
  try {
    await navigator.share(SYSTEM_TEST);
    $("system-share-status").textContent = "Share request completed. Check the receiving Mogwai window for the test message.";
  } catch (error) {
    $("system-share-status").textContent = error.name === "AbortError" ? "Sharing canceled or no destination selected. You can try again." : "System sharing could not open: " + error.message;
  } finally { $("system-share-test").disabled = false; }
});
if (typeof navigator.share !== "function") {
  $("system-share-test").disabled = true;
  $("system-share-status").textContent = "This browser cannot open system sharing from a page. Mogwai may still receive shares from other apps.";
}
$("update-app").addEventListener("click", async () => {
  $("update-app").disabled = true;
  status("Checking for the latest Mogwai app…");
  try {
    const draft = $("shared-url").value;
    if (new TextEncoder().encode(draft).byteLength > 70000) throw new Error("Copy this large draft before updating; it cannot be restored automatically.");
    const registration = await navigator.serviceWorker?.getRegistration();
    if (registration) await registration.update();
    const target = new URL(location.pathname, location.href);
    target.searchParams.set("update", String(Date.now()));
    const restore = new URLSearchParams({review: "1"});
    if (receiptText) restore.set("share", JSON.stringify(JSON.parse(receiptText)));
    if (draft) restore.set("draft", draft);
    target.hash = restore.toString();
    location.replace(target.href);
  } catch (error) {
    status("Could not update: " + error.message + " Your current content is still here.", true);
    $("update-app").disabled = false;
  }
});
window.addEventListener("beforeinstallprompt", event => { event.preventDefault(); installPrompt = event; });
$("install").addEventListener("click", async () => {
  if (!installPrompt) {
    $("install-help").open = true;
    $("install-status").textContent = "Chrome is not offering an install prompt here. If Mogwai is already installed, use Update app. Otherwise use Chrome’s menu to install this page as an app.";
    return;
  }
  const prompt = installPrompt; installPrompt = null; $("install").disabled = true;
  try { await prompt.prompt(); await prompt.userChoice; }
  finally { $("install").disabled = false; }
});
window.addEventListener("appinstalled", () => { installPrompt = null; $("install-status").textContent = "Mogwai was installed. Use Update app whenever you need a fresh load."; });

$("chisel-url").value = DEFAULT_CHISEL;
try {
  const savedChisel = localStorage.getItem(CHISEL);
  $("chisel-url").value = !savedChisel || ["https://johnrigler.github.io/chisel/", "https://johnrigler.github.io/chisel/?v=2.8.10", "https://johnrigler.github.io/chisel/?v=2.8.11", "https://johnrigler.github.io/chisel/?v=2.8.12"].includes(savedChisel) ? DEFAULT_CHISEL : savedChisel;
  $("shared-url").value = sessionStorage.getItem(LAST) || "";
} catch {}
function receiveFromLocation() {
  const fragment = new URLSearchParams(location.hash.slice(1));
  const query = new URLSearchParams(location.search);
  const hasShare = fragment.has("share") || ["title", "text", "url"].some(key => query.has(key));
  let incoming = null, received = null;
  if (hasShare) {
    // A new receipt must not inherit a previous link from this browser session.
    $("shared-url").value = "";
    try { sessionStorage.removeItem(LAST); } catch {}
    const raw = fragment.has("share") ? fragment.get("share") : JSON.stringify(Object.fromEntries(["title", "text", "url"].filter(key => query.has(key)).map(key => [key, query.get(key)])));
    try {
      if (new TextEncoder().encode(raw).byteLength > 70000) throw new Error("Shared data exceeds the 70,000-byte receiver limit. Only a preview is shown.");
      incoming = JSON.parse(raw);
      received = MogwaiShare.describe(incoming);
      receipt(incoming, received, "", !fragment.has("review"));
      $("shared-url").value = received.content;
      status(received.reason || received.label + " received. Review the metadata and TX portal preview, then choose Open in Chisel.", received.kind === "unknown");
    } catch (error) {
      receipt({unparsed: raw.slice(0, 2500), preview_truncated: raw.length > 2500}, null, error.message, !fragment.has("review"));
      status(error.message, true);
    }
  }
  if (fragment.has("share-error")) {
    $("shared-url").value = "";
    const error = fragment.get("share-error").slice(0, 2500);
    receipt({receiver_error: error}, null, error);
    status(error, true);
  }
  if (fragment.has("draft")) $("shared-url").value = fragment.get("draft");
  if (hasShare || fragment.has("share-error") || fragment.has("draft") || fragment.has("review")) history.replaceState(null, "", location.pathname);
  preview();
}
receiveFromLocation();
window.addEventListener("hashchange", receiveFromLocation);
if ("serviceWorker" in navigator && window.isSecureContext) {
  navigator.serviceWorker.register("sw.js").then(() => navigator.serviceWorker.ready).then(() => { $("offline-status").textContent = "Share receiver ready · 0.4.2. Installed Mogwai can receive shared text and links."; }).catch(() => { $("offline-status").textContent = "Share setup failed. Reload this page online."; });
} else $("offline-status").textContent = "Use HTTPS or localhost to install the share receiver.";
