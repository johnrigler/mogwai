"use strict";
const $ = id => document.getElementById(id);
const CHISEL = "mogwai.chisel-url.v1";
const LAST = "mogwai.shared-link.v1";
const DEFAULT_CHISEL = "https://johnrigler.github.io/chisel/";
const SYSTEM_TEST = {title: "Mogwai sharing test", text: "Mogwai system-share test: this is plain text, with no YouTube link."};
let selected = null, installPrompt = null, receiptText = "";

function status(message = "", error = false) {
  $("status").textContent = message;
  $("status").className = error ? "error" : "";
}
function receipt(value, description, error = "") {
  receiptText = JSON.stringify(value, null, 2);
  $("received-share").hidden = false;
  $("received-kind").textContent = error ? "Could not process this share" : description.label;
  $("received-note").textContent = error || description.reason || "These are the original fields Mogwai received. Review the content below before opening Chisel.";
  $("received-data").textContent = receiptText;
}
function preview() {
  selected = null; $("open-chisel").disabled = true;
  try {
    const description = MogwaiShare.describe({text: $("shared-url").value});
    if (!description.content) throw new Error("Share or paste text or an HTTP(S) link.");
    MogwaiShare.chiselURL($("chisel-url").value, description.content);
    selected = description;
    const bytes = new TextEncoder().encode(selected.content).byteLength;
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
window.addEventListener("beforeinstallprompt", event => { event.preventDefault(); installPrompt = event; $("install").hidden = false; });
$("install").addEventListener("click", async () => {
  if (!installPrompt) return;
  const prompt = installPrompt; installPrompt = null; $("install").hidden = true;
  await prompt.prompt(); await prompt.userChoice;
});
window.addEventListener("appinstalled", () => { $("install").hidden = true; });

$("chisel-url").value = DEFAULT_CHISEL;
try { $("chisel-url").value = localStorage.getItem(CHISEL) || DEFAULT_CHISEL; $("shared-url").value = sessionStorage.getItem(LAST) || ""; } catch {}
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
    receipt(incoming, received);
    $("shared-url").value = received.content;
    status(received.reason || (received.kind === "youtube" ? "YouTube link received. Opening Chisel…" : received.label + " received. Review it, then choose Open in Chisel."), received.kind === "unknown");
  } catch (error) {
    receipt({unparsed: raw.slice(0, 2500), preview_truncated: raw.length > 2500}, null, error.message);
    status(error.message, true);
  }
}
if (fragment.has("share-error")) {
  $("shared-url").value = "";
  receipt({receiver_error: fragment.get("share-error")}, null, fragment.get("share-error"));
  status(fragment.get("share-error"), true);
}
if (hasShare || fragment.has("share-error")) history.replaceState(null, "", location.pathname);
preview();
if (received?.kind === "youtube" && selected) openChisel();
if ("serviceWorker" in navigator && window.isSecureContext) {
  navigator.serviceWorker.register("sw.js").then(() => navigator.serviceWorker.ready).then(() => { $("offline-status").textContent = "Share receiver ready · 0.2.0. Installed Mogwai can receive shared text and links."; }).catch(() => { $("offline-status").textContent = "Share setup failed. Reload this page online."; });
} else $("offline-status").textContent = "Use HTTPS or localhost to install the share receiver.";
