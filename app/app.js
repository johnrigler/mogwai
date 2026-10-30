"use strict";
const $ = id => document.getElementById(id);
const CHISEL = "mogwai.chisel-url.v1";
const LAST = "mogwai.shared-link.v1";
const CONSOLE = "mogwai.share-console.v1";
const CONSOLE_LOG = "mogwai.share-console-log.v1";
const DEFAULT_CHISEL = "https://johnrigler.github.io/chisel/?v=2.8.11";
const SYSTEM_TEST = {title: "Mogwai sharing test", text: "Mogwai system-share test: this is plain text, with no YouTube link."};
let selected = null, installPrompt = null, receiptText = "";
let consoleEnabled = false, consoleEntries = [];

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
}
function openChisel(event) {
  if (event) event.preventDefault();
  preview(); if (!selected || $("open-chisel").disabled) return;
  try {
    const target = MogwaiShare.chiselURL($("chisel-url").value, selected.content);
    try { localStorage.setItem(CHISEL, $("chisel-url").value); } catch {}
    status("Opening Chisel with the reviewed content in OP_RETURN…");
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
  $("chisel-url").value = !savedChisel || ["https://johnrigler.github.io/chisel/", "https://johnrigler.github.io/chisel/?v=2.8.10"].includes(savedChisel) ? DEFAULT_CHISEL : savedChisel;
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
      status(received.reason || (received.kind === "youtube" && !consoleEnabled && !fragment.has("review") ? "YouTube link received. Opening Chisel…" : received.label + " received. Review it, then choose Open in Chisel."), received.kind === "unknown");
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
  if (received?.kind === "youtube" && selected && !fragment.has("review") && !consoleEnabled) openChisel();
}
receiveFromLocation();
window.addEventListener("hashchange", receiveFromLocation);
if ("serviceWorker" in navigator && window.isSecureContext) {
  navigator.serviceWorker.register("sw.js").then(() => navigator.serviceWorker.ready).then(() => { $("offline-status").textContent = "Share receiver ready · 0.3.0. Installed Mogwai can receive shared text and links."; }).catch(() => { $("offline-status").textContent = "Share setup failed. Reload this page online."; });
} else $("offline-status").textContent = "Use HTTPS or localhost to install the share receiver.";
