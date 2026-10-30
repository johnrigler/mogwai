const assert = require("node:assert/strict");
const {readFileSync, existsSync} = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const base = path.join(__dirname, "../app");
const core = readFileSync(path.join(base, "core.js"), "utf8");
const app = readFileSync(path.join(base, "app.js"), "utf8");
const context = vm.createContext({URL, URLSearchParams});
vm.runInContext(core, context);
const C = context.MogwaiShare;
const id = "jNQXAC9IVRw", short = "https://youtu.be/" + id;

test("Android text and ChromeOS URL shares identify the same YouTube video", () => {
  for (const input of [
    {text: "Me at the zoo " + short + "?si=tracking"},
    {url: "https://www.youtube.com/watch?v=" + id + "&feature=shared"},
    {title: "https://m.youtube.com/shorts/" + id},
    {text: "https://www.youtube.com/live/" + id + "?si=tracking"},
    {url: "https://www.youtube-nocookie.com/embed/" + id}
  ]) {
    const result = C.fromShare(input);
    assert.equal(result.url, short); assert.equal(result.youtube, true);
    assert.ok(Buffer.byteLength(result.url) <= 80);
  }
});
test("valid start times survive short-link conversion", () => {
  for (const [value, expected] of [["1m30s", "90"], ["90", "90"], ["90s", "90"], ["1h2m3s", "3723"]]) {
    assert.equal(C.fromShare({text: short + "?t=" + value + "&si=x"}).url, short + "?t=" + expected);
  }
  assert.equal(C.fromShare({url: "https://youtube.com/watch?v=" + id + "&start=12"}).url, short + "?t=12");
  assert.equal(C.fromShare({url: short + "?t=garbage"}).url, short);
});
test("URL extraction rejects executable schemes and embedded credentials and checks YouTube's exact hostname", () => {
  for (const value of ["javascript:alert(1)", "data:text/html,x", "https://user:password@example.test/"]) assert.throws(() => C.fromShare({text: value}));
  assert.equal(C.fromShare({url: "https://youtube.com.attacker.test/watch?v=" + id}).youtube, false);
  assert.equal(C.fromShare({text: "A video (" + short + ")."}).url, short);
  assert.equal(C.fromShare({text: "https://example.test/ " + short}).url, short);
});
test("the Chisel handoff preserves the selected base and supplies only OP_RETURN plus Send mode", () => {
  const target = new URL(C.chiselURL("https://gateway.example/ipfs/bafyfixture/index.html?coin=ltc#keep=here", short + "?t=90"));
  assert.equal(target.pathname, "/ipfs/bafyfixture/index.html");
  assert.equal(target.searchParams.get("coin"), "ltc"); assert.equal(target.searchParams.get("mode"), "send");
  assert.equal(new URLSearchParams(target.hash.slice(1)).get("opreturn"), short + "?t=90");
  assert.equal(new URLSearchParams(target.hash.slice(1)).get("keep"), "here");
  assert.throws(() => C.chiselURL("javascript:alert(1)", short));
});

function controller(share, options = {}) {
  const nodes = new Map();
  const ids = [...readFileSync(path.join(base, "index.html"), "utf8").matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  for (const name of ids) nodes.set(name, {value: "", textContent: "", disabled: false, hidden: false, listeners: {}, addEventListener(type, handler) {this.listeners[type] = handler;}});
  const storage = new Map(options.storage || []), session = new Map(options.session || []), navigations = [], events = {}, history = [];
  const makeStorage = map => ({getItem(key) {if (options.noStorage) throw Error("blocked"); return map.get(key) || null;}, setItem(key, value) {if (options.noStorage) throw Error("blocked"); map.set(key, value);}, removeItem(key) {if (options.noStorage) throw Error("blocked"); map.delete(key);}});
  const location = {pathname: "/mogwai/app/", search: options.search || "", hash: options.hash ?? (share !== null && share !== undefined ? "#share=" + encodeURIComponent(JSON.stringify(share)) : ""), replace(target) {navigations.push(target);}};
  location.href = "https://example.test" + location.pathname + location.search + location.hash;
  const ctx = vm.createContext({document: {getElementById(id) {assert.ok(nodes.has(id), id); return nodes.get(id);}}, URL, URLSearchParams, TextEncoder, location, navigator: options.navigator || {}, history: {replaceState(...args) {history.push(args); location.href = new URL(args[2], location.href).href;}},
    localStorage: makeStorage(storage), sessionStorage: makeStorage(session), addEventListener(type, handler) {events[type] = handler;}});
  ctx.window = ctx;
  vm.runInContext(core + "\n" + app, ctx);
  return {nodes, navigations, storage, session, history, events, location};
}
test("a received share immediately opens Chisel with the extracted URL", () => {
  const ui = controller({text: "Watch this " + short + "?si=tracking"});
  assert.equal(ui.navigations.length, 1);
  const url = new URL(ui.navigations[0]);
  assert.equal(url.origin, "https://johnrigler.github.io"); assert.equal(url.pathname, "/chisel/");
  assert.equal(new URLSearchParams(url.hash.slice(1)).get("opreturn"), short);
});
test("the share console dumps a YouTube receipt and waits for an explicit Chisel handoff", () => {
  const shared = {text: "Watch " + short, custom: "<script>synthetic</script>"};
  const ui = controller(shared, {storage: [["mogwai.share-console.v1", "1"]]});
  assert.equal(ui.nodes.get("share-console").hidden, false);
  assert.equal(ui.navigations.length, 0);
  const entries = JSON.parse(ui.session.get("mogwai.share-console-log.v1"));
  assert.deepEqual(entries[0].fields, shared);
  assert.match(ui.nodes.get("console-data").textContent, /synthetic/);
  assert.doesNotMatch(ui.nodes.get("status").textContent, /Opening Chisel/);
  ui.nodes.get("share-form").listeners.submit({preventDefault() {}});
  assert.equal(ui.navigations.length, 1);
});
test("Tools enables the console, remembers the setting, and receives further shares in the same window", () => {
  const ui = controller({text: "First note"});
  const toggle = ui.nodes.get("console-enabled");
  toggle.checked = true; toggle.listeners.change();
  assert.equal(ui.storage.get("mogwai.share-console.v1"), "1");
  assert.equal(ui.nodes.get("console-count").textContent, "1");
  const second = {title: "Second note", text: "Another share", additional_fields: [{name: "custom", value: "Kept"}]};
  ui.location.hash = "#share=" + encodeURIComponent(JSON.stringify(second));
  ui.events.hashchange();
  const entries = JSON.parse(ui.session.get("mogwai.share-console-log.v1"));
  assert.equal(entries.length, 2);assert.deepEqual(entries[1].fields, second);
  assert.equal(ui.nodes.get("shared-url").value, "Another share");
  const restored = controller(null, {storage: [...ui.storage], session: [...ui.session]});
  assert.equal(restored.nodes.get("console-count").textContent, "2");
  toggle.checked = false;toggle.listeners.change();
  assert.equal(ui.nodes.get("share-console").hidden, true);
  assert.equal(ui.session.has("mogwai.share-console-log.v1"), false);
});
test("console history is bounded, includes receiver errors, and clears independently of the current receipt", () => {
  const ui = controller(null, {storage: [["mogwai.share-console.v1", "1"]]});
  for (let i = 0; i < 25; i++) {
    ui.location.hash = "#share=" + encodeURIComponent(JSON.stringify({text: "Note " + i}));
    ui.events.hashchange();
  }
  assert.equal(JSON.parse(ui.session.get("mogwai.share-console-log.v1")).length, 20);
  ui.location.hash = "#share-error=Could+not+decode";ui.events.hashchange();
  const entries = JSON.parse(ui.session.get("mogwai.share-console-log.v1"));
  assert.equal(entries.at(-1).error, "Could not decode");
  ui.nodes.get("clear-console").listeners.click();
  assert.equal(ui.nodes.get("console-data").textContent, "");
  assert.equal(ui.nodes.get("received-share").hidden, false);
  assert.equal(ui.session.has("mogwai.share-console-log.v1"), false);
});
test("large receipts respect the console byte limit, updates do not duplicate logs, and clearing removes them", async () => {
  const shared = {text: "é".repeat(30000)};
  const ui = controller(shared, {storage: [["mogwai.share-console.v1", "1"]]});
  for (let i = 0; i < 5; i++) {
    ui.location.hash = "#share=" + encodeURIComponent(JSON.stringify(shared));ui.events.hashchange();
  }
  assert.ok(Buffer.byteLength(ui.session.get("mogwai.share-console-log.v1")) <= 200000);
  await ui.nodes.get("update-app").listeners.click();
  const updated = controller(null, {storage: [...ui.storage], session: [...ui.session], hash: new URL(ui.navigations[0]).hash});
  assert.equal(updated.nodes.get("console-count").textContent, ui.nodes.get("console-count").textContent);
  updated.nodes.get("clear-received").listeners.click();
  assert.equal(updated.session.has("mogwai.share-console-log.v1"), false);
  assert.equal(updated.nodes.get("console-data").textContent, "");
});
test("manual paste uses the same handoff and still works with browser storage blocked", () => {
  const ui = controller(null, {noStorage: true});
  assert.equal(ui.navigations.length, 0);
  ui.nodes.get("shared-url").value = "https://youtube.com/watch?v=" + id;
  ui.nodes.get("shared-url").listeners.input();
  assert.equal(ui.nodes.get("open-chisel").disabled, false);
  ui.nodes.get("share-form").listeners.submit({preventDefault() {}});
  assert.equal(ui.navigations.length, 1);
});
test("plain text stays for review and reaches Chisel byte-for-byte without a YouTube URL", () => {
  const text = "A note about a conversation.\nKeep café, spaces, and the final newline.\n";
  const shared = {title: "A note", text};
  const ui = controller(shared);
  assert.equal(ui.navigations.length, 0);
  assert.equal(ui.nodes.get("received-kind").textContent, "Plain text");
  assert.equal(ui.nodes.get("shared-url").value, text);
  assert.deepEqual(JSON.parse(ui.nodes.get("received-data").textContent), shared);
  ui.nodes.get("share-form").listeners.submit({preventDefault() {}});
  assert.equal(new URLSearchParams(new URL(ui.navigations[0]).hash.slice(1)).get("opreturn"), text);
  assert.equal(ui.session.has("mogwai.shared-link.v1"), false);
});
test("non-YouTube links preserve their original received fields and wait for a deliberate handoff", () => {
  const shared = {title: "A shared conversation", text: "An explanation", url: "https://chatgpt.com/share/synthetic-test"};
  const ui = controller(shared);
  assert.equal(ui.navigations.length, 0);
  assert.equal(ui.nodes.get("received-kind").textContent, "Web link");
  assert.deepEqual(JSON.parse(ui.nodes.get("received-data").textContent), shared);
  ui.nodes.get("share-form").listeners.submit({preventDefault() {}});
  assert.equal(new URLSearchParams(new URL(ui.navigations[0]).hash.slice(1)).get("opreturn"), shared.url);
});
test("unrecognized fields remain visible and cannot send a stale previous link", () => {
  const shared = {unexpected: {message: "<img src=x onerror=alert(1)>"}, additional_fields: [{name: "attachment", file: {name: "note.txt", type: "text/plain", size: 12}}]};
  const ui = controller(shared, {session: [["mogwai.shared-link.v1", short]]});
  assert.equal(ui.navigations.length, 0);
  assert.equal(ui.nodes.get("received-kind").textContent, "Not recognized");
  assert.equal(ui.nodes.get("open-chisel").disabled, true);
  assert.equal(ui.nodes.get("shared-url").value, "");
  assert.equal(ui.session.has("mogwai.shared-link.v1"), false);
  assert.deepEqual(JSON.parse(ui.nodes.get("received-data").textContent), shared);
  assert.match(ui.nodes.get("status").textContent, /does not know/);
  assert.deepEqual(ui.history[0], [null, "", "/mogwai/app/"]);
});
test("invalid and oversized share envelopes produce an explicit bounded preview", () => {
  const broken = controller(null, {hash: "#share=" + encodeURIComponent("{broken")});
  assert.equal(broken.nodes.get("received-kind").textContent, "Could not process this share");
  assert.equal(JSON.parse(broken.nodes.get("received-data").textContent).unparsed, "{broken");
  const large = controller({text: "x".repeat(70001)});
  const shown = JSON.parse(large.nodes.get("received-data").textContent);
  assert.equal(shown.unparsed.length, 2500);
  assert.equal(shown.preview_truncated, true);
  assert.equal(large.navigations.length, 0);
  assert.match(large.nodes.get("status").textContent, /70,000-byte/);
});
test("query shares and title-only shares are inspectable even with blocked browser storage", () => {
  const ui = controller(null, {noStorage: true, search: "?title=An+observation&text=Plain+words"});
  assert.equal(ui.nodes.get("received-kind").textContent, "Plain text");
  assert.deepEqual(JSON.parse(ui.nodes.get("received-data").textContent), {title: "An observation", text: "Plain words"});
  assert.equal(controller({title: "Title only"}).nodes.get("shared-url").value, "Title only");
});
test("Chisel's import byte limit disables handoff without truncating the received text", () => {
  assert.equal(controller({text: "é".repeat(2048)}).nodes.get("open-chisel").disabled, false);
  const shared = {text: "é".repeat(2049)};
  const ui = controller(shared);
  assert.equal(ui.nodes.get("open-chisel").disabled, true);
  assert.deepEqual(JSON.parse(ui.nodes.get("received-data").textContent), shared);
  assert.match(ui.nodes.get("detected").textContent, /4,096 bytes/);
  assert.equal(ui.navigations.length, 0);
});
test("system share testing uses a plain-text payload and reports cancellation without claiming receipt", async () => {
  const shared = [];
  const ui = controller(null, {navigator: {async share(value) {shared.push(JSON.parse(JSON.stringify(value))); const error = new Error("Canceled"); error.name = "AbortError"; throw error;}}});
  await ui.nodes.get("system-share-test").listeners.click();
  assert.equal(shared.length, 1);
  assert.equal(shared[0].title, "Mogwai sharing test");
  assert.match(shared[0].text, /plain text/);
  assert.equal(Object.hasOwn(shared[0], "url"), false);
  assert.match(ui.nodes.get("system-share-status").textContent, /canceled/);
  assert.equal(ui.nodes.get("system-share-test").disabled, false);
  const unavailable = controller(null);
  assert.equal(unavailable.nodes.get("system-share-test").disabled, true);
  assert.match(unavailable.nodes.get("system-share-status").textContent, /may still receive/);
});
test("a received record can be copied unchanged and cleared without persisting its raw fields", async () => {
  let copied;
  const shared = {text: "Synthetic diagnostic note", extra: "unhandled"};
  const ui = controller(shared, {navigator: {clipboard: {async writeText(value) {copied = value;}}}});
  await ui.nodes.get("copy-received").listeners.click();
  assert.deepEqual(JSON.parse(copied), shared);
  assert.equal(ui.storage.size, 0);
  ui.nodes.get("clear-received").listeners.click();
  assert.equal(ui.nodes.get("received-share").hidden, true);
  assert.equal(ui.nodes.get("received-data").textContent, "");
  assert.equal(ui.nodes.get("open-chisel").disabled, true);
});
test("updating uses a fresh page request and restores the receipt and edited draft without an automatic handoff", async () => {
  let updates = 0;
  const shared = {text: "Original shared note", custom: "Keep this field"};
  const ui = controller(shared, {navigator: {serviceWorker: {async getRegistration() {return {async update() {updates++;}};}}}});
  const edited = "An edited note\nwith another line.";
  ui.nodes.get("shared-url").value = edited;
  await ui.nodes.get("update-app").listeners.click();
  assert.equal(updates, 1);
  const next = new URL(ui.navigations[0]);
  assert.ok(next.searchParams.get("update"));
  assert.equal(next.pathname, "/mogwai/app/");
  const restored = controller(null, {hash: next.hash});
  assert.deepEqual(JSON.parse(restored.nodes.get("received-data").textContent), shared);
  assert.equal(restored.nodes.get("shared-url").value, edited);
  assert.equal(restored.navigations.length, 0);
  assert.equal(controller(null, {hash: "#review=1&share=" + encodeURIComponent(JSON.stringify({url: short}))}).navigations.length, 0);
});
test("an update failure leaves content in place and allows retry", async () => {
  const ui = controller({text: "Keep my note"}, {navigator: {serviceWorker: {async getRegistration() {throw Error("Offline");}}}});
  await ui.nodes.get("update-app").listeners.click();
  assert.equal(ui.navigations.length, 0);
  assert.equal(ui.nodes.get("shared-url").value, "Keep my note");
  assert.equal(ui.nodes.get("update-app").disabled, false);
  assert.match(ui.nodes.get("status").textContent, /current content is still here/);
});
test("existing default Chisel settings receive the fresh compatible page without replacing custom hosts", () => {
  const old = controller(null, {storage: [["mogwai.chisel-url.v1", "https://johnrigler.github.io/chisel/"]]});
  assert.equal(old.nodes.get("chisel-url").value, "https://johnrigler.github.io/chisel/?v=2.8.11");
  const custom = "https://local.example/chisel/?coin=ltc";
  assert.equal(controller(null, {storage: [["mogwai.chisel-url.v1", custom]]}).nodes.get("chisel-url").value, custom);
});
test("install stays available for a browser prompt or installation instructions", async () => {
  const ui = controller(null);
  await ui.nodes.get("install").listeners.click();
  assert.equal(ui.nodes.get("install-help").open, true);
  assert.match(ui.nodes.get("install-status").textContent, /Update app/);
  let prompted = 0;
  ui.events.beforeinstallprompt({preventDefault() {}, async prompt() {prompted++;}, userChoice: Promise.resolve({outcome: "accepted"})});
  await ui.nodes.get("install").listeners.click();
  assert.equal(prompted, 1);
  ui.events.appinstalled();
  assert.equal(ui.nodes.get("install").hidden, false);
  assert.equal(ui.nodes.get("install").disabled, false);
});

function worker() {
  const listeners = {}, calls = [], scope = "https://example.test/mogwai/app/";
  const self = {registration: {scope}, addEventListener(name, handler) {listeners[name] = handler;}, skipWaiting() {}, clients: {claim() {}}};
  const caches = {open: async () => ({addAll: async paths => calls.push(...paths), match: async () => new Response("offline shell"), put: async () => {}}), keys: async () => []};
  vm.runInNewContext(readFileSync(path.join(base, "sw.js"), "utf8"), {self, caches, URL, Request, Response, TextEncoder, fetch: async () => {throw Error("offline");}});
  return {listeners, calls, scope};
}
test("the installed POST share receiver redirects locally without forwarding shared content to a server", async () => {
  const w = worker(); let response;
  const request = new Request(w.scope + "share", {method: "POST", body: new URLSearchParams({text: short, title: "A video"})});
  w.listeners.fetch({request, respondWith(value) {response = value;}});
  const result = await response;
  assert.equal(result.status, 303);
  const url = new URL(result.headers.get("location"));
  assert.equal(url.origin + url.pathname, w.scope);
  assert.equal(url.search, "");
  const share = JSON.parse(new URLSearchParams(url.hash.slice(1)).get("share"));
  assert.equal(share.text, short); assert.equal(share.title, "A video");
});
test("POST shares retain duplicate and unknown fields plus unexpected file metadata for inspection", async () => {
  const w = worker(); let response;
  const body = new FormData();
  body.append("text", "First note"); body.append("text", "Second note"); body.append("custom", "An extra field");
  body.append("attachment", new Blob(["SYNTHETIC FILE BYTES"], {type: "text/plain"}), "example.txt");
  w.listeners.fetch({request: new Request(w.scope + "share", {method: "POST", body}), respondWith(value) {response = value;}});
  const redirect = new URL((await response).headers.get("location"));
  const share = JSON.parse(new URLSearchParams(redirect.hash.slice(1)).get("share"));
  assert.equal(share.text, "First note");
  assert.deepEqual(share.additional_fields, [{name: "text", value: "Second note"}, {name: "custom", value: "An extra field"}, {name: "attachment", file: {name: "example.txt", type: "text/plain", size: 20}}]);
  assert.equal(redirect.href.includes("SYNTHETIC FILE BYTES"), false);
  assert.equal(redirect.search, "");
});
test("the worker caches the installable shell and leaves unrelated pages untouched", async () => {
  const w = worker(); let installed;
  w.listeners.install({waitUntil(value) {installed = value;}}); await installed;
  for (const request of w.calls) {
    assert.equal(request.cache, "reload");
    const name = new URL(request.url).pathname.slice(new URL(w.scope).pathname.length);
    assert.ok(existsSync(path.join(base, name)), name);
  }
  let response;
  w.listeners.fetch({request: new Request(w.scope), respondWith(value) {response = value;}});
  assert.equal(await (await response).text(), "offline shell");
  w.listeners.fetch({request: new Request("https://example.test/chisel/"), respondWith() {assert.fail("Worker intercepted Chisel");}});
  const manifest = JSON.parse(readFileSync(path.join(base, "manifest.webmanifest"), "utf8"));
  assert.equal(manifest.share_target.method, "POST"); assert.equal(manifest.scope, "./");
  for (const size of [192, 512]) {
    const png = readFileSync(path.join(base, "icon-" + size + ".png"));
    assert.equal(png.readUInt32BE(16), size); assert.equal(png.readUInt32BE(20), size);
  }
});
