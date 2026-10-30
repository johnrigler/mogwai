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
  const storage = new Map(), session = new Map(), navigations = [], events = {};
  const makeStorage = map => ({getItem(key) {if (options.noStorage) throw Error("blocked"); return map.get(key) || null;}, setItem(key, value) {if (options.noStorage) throw Error("blocked"); map.set(key, value);}});
  const location = {pathname: "/mogwai/app/", search: "", hash: share ? "#share=" + encodeURIComponent(JSON.stringify(share)) : "", replace(target) {navigations.push(target);}};
  const ctx = vm.createContext({document: {getElementById(id) {assert.ok(nodes.has(id), id); return nodes.get(id);}}, URL, URLSearchParams, TextEncoder, location, navigator: {}, history: {replaceState() {}},
    localStorage: makeStorage(storage), sessionStorage: makeStorage(session), addEventListener(type, handler) {events[type] = handler;}});
  ctx.window = ctx;
  vm.runInContext(core + "\n" + app, ctx);
  return {nodes, navigations, storage, session};
}
test("a received share immediately opens Chisel with the extracted URL", () => {
  const ui = controller({text: "Watch this " + short + "?si=tracking"});
  assert.equal(ui.navigations.length, 1);
  const url = new URL(ui.navigations[0]);
  assert.equal(url.origin, "https://johnrigler.github.io"); assert.equal(url.pathname, "/chisel/");
  assert.equal(new URLSearchParams(url.hash.slice(1)).get("opreturn"), short);
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
test("malformed shares stay in the widget and report an actionable error", () => {
  const ui = controller({text: "No URL here"});
  assert.equal(ui.navigations.length, 0);
  assert.match(ui.nodes.get("status").textContent, /No web link/);
});

function worker() {
  const listeners = {}, calls = [], scope = "https://example.test/mogwai/app/";
  const self = {registration: {scope}, addEventListener(name, handler) {listeners[name] = handler;}, skipWaiting() {}, clients: {claim() {}}};
  const caches = {open: async () => ({addAll: async paths => calls.push(...paths), match: async () => new Response("offline shell"), put: async () => {}}), keys: async () => []};
  vm.runInNewContext(readFileSync(path.join(base, "sw.js"), "utf8"), {self, caches, URL, Response, TextEncoder, fetch: async () => {throw Error("offline");}});
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
test("the worker caches the installable shell and leaves unrelated pages untouched", async () => {
  const w = worker(); let installed;
  w.listeners.install({waitUntil(value) {installed = value;}}); await installed;
  for (const name of w.calls) assert.ok(existsSync(path.join(base, name)), name);
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
