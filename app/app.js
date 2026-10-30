"use strict";
const $ = id => document.getElementById(id);
const CHISEL = "mogwai.chisel-url.v1";
const LAST = "mogwai.shared-link.v1";
const DEFAULT_CHISEL = "https://johnrigler.github.io/chisel/";
let selected = null, installPrompt = null;

function status(message = "", error = false) {
  $("status").textContent = message;
  $("status").className = error ? "error" : "";
}
function preview() {
  selected = null; $("open-chisel").disabled = true;
  try {
    selected = MogwaiShare.fromShare({text: $("shared-url").value});
    MogwaiShare.chiselURL($("chisel-url").value, selected.url);
    const bytes = new TextEncoder().encode(selected.url).byteLength;
    $("detected").textContent = (selected.youtube ? "YouTube video" : "Web link") + " · " + bytes + " bytes in OP_RETURN" + (bytes > 80 ? " · check the selected chain’s payload limit in Chisel" : "");
    $("open-chisel").disabled = false;
    try { sessionStorage.setItem(LAST, selected.url); } catch {}
  } catch (error) {
    $("detected").textContent = $("shared-url").value.trim() ? error.message : "YouTube watch, Shorts, live, and short links are supported.";
  }
}
function openChisel(event) {
  if (event) event.preventDefault();
  preview(); if (!selected || $("open-chisel").disabled) return;
  try {
    const target = MogwaiShare.chiselURL($("chisel-url").value, selected.url);
    try { localStorage.setItem(CHISEL, $("chisel-url").value); } catch {}
    status("Opening Chisel with " + selected.url + " in OP_RETURN…");
    location.replace(target);
  } catch (error) { status(error.message, true); }
}
$("share-form").addEventListener("submit", openChisel);
$("shared-url").addEventListener("input", () => { status(); preview(); });
$("chisel-url").addEventListener("input", preview);
$("chisel-url").addEventListener("change", () => {
  try { MogwaiShare.chiselURL($("chisel-url").value, "test"); localStorage.setItem(CHISEL, $("chisel-url").value); } catch {}
});
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
let incoming = null;
try {
  if (fragment.has("share")) incoming = JSON.parse(fragment.get("share"));
  else if (["title", "text", "url"].some(key => query.has(key))) incoming = Object.fromEntries(["title", "text", "url"].map(key => [key, query.get(key) || ""]));
  if (incoming) {
    if (typeof incoming !== "object" || new TextEncoder().encode(JSON.stringify(incoming)).byteLength > 70000) throw new Error("Shared content is too large or invalid.");
    $("shared-url").value = MogwaiShare.fromShare(incoming).url;
  }
  if (fragment.has("share-error")) status(fragment.get("share-error"), true);
} catch (error) { incoming = null; status(error.message, true); }
if (fragment.has("share") || fragment.has("share-error") || ["title", "text", "url"].some(key => query.has(key))) history.replaceState(null, "", location.pathname);
preview();
if (incoming && selected) openChisel();
if ("serviceWorker" in navigator && window.isSecureContext) {
  navigator.serviceWorker.register("sw.js").then(() => navigator.serviceWorker.ready).then(() => { $("offline-status").textContent = "Share receiver ready. Install Mogwai to enable system sharing."; }).catch(() => { $("offline-status").textContent = "Share setup failed. Reload this page online before installing."; });
} else $("offline-status").textContent = "Use HTTPS or localhost to install the share receiver.";
