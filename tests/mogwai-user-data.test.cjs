const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {webcrypto, createHash} = require("node:crypto");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const source = readFileSync(path.join(__dirname, "../app/user-data.js"), "utf8");
const core = readFileSync(path.join(__dirname, "../app/core.js"), "utf8");
function browser(options = {}) {
  const saved = options.storage || new Map(), jar = options.jar || new Map(), writes = [];
  const document = {get cookie() {return [...jar].map(([key, value]) => key + "=" + value).join("; ");}, set cookie(value) {
    if (options.blockCookies) return;
    writes.push(value);
    const [name, content] = value.split(";")[0].split("=");
    if (/Max-Age=0\b/.test(value)) jar.delete(name); else jar.set(name, content);
  }};
  const localStorage = {
    getItem(key) {if (options.blockStorage) throw Error("blocked"); return saved.get(key) || null;},
    setItem(key, value) {if (options.blockStorage) throw Error("blocked"); saved.set(key, value);},
    removeItem(key) {if (options.blockStorage) throw Error("blocked"); saved.delete(key);}
  };
  const context = vm.createContext({crypto: webcrypto, URL, URLSearchParams, TextEncoder, document, localStorage, location: {protocol: "https:", pathname: "/mogwai/app/"}});
  vm.runInContext(source + "\n" + core, context);
  return {data: context.MogwaiUserData.create(), api: context.MogwaiUserData, share: context.MogwaiShare, saved, jar, writes};
}
const subject = "https://youtu.be/jNQXAC9IVRw?t=90";
const metadata = {videoId: "jNQXAC9IVRw", title: "Synthetic title", authorName: "Synthetic channel", provider: "YouTube", fetchedAt: "2026-10-31T12:00:00Z"};

test("a canonical SHA-256 baseline survives a return visit without saving the source data", async () => {
  const b = browser();
  const snapshot = b.share.integrityData(subject, metadata);
  const check = await b.data.inspect(subject, snapshot);
  assert.equal(check.status, "new");
  assert.equal(check.currentHash, createHash("sha256").update(b.api.canonicalJSON(snapshot)).digest("hex"));
  assert.equal(b.data.remember(check).status, "saved");
  assert.match(b.writes.at(-1), /SameSite=Strict; Secure/);
  assert.match(b.writes.at(-1), /Path=\/mogwai\/app\//);
  assert.match(b.writes.at(-1), /Max-Age=15552000/);
  assert.doesNotMatch([...b.saved.values()].join(""), /youtu|Synthetic|jNQXAC9IVRw/);
  const next = browser({storage: b.saved, jar: b.jar});
  const repeated = next.share.integrityData(subject, {...metadata, fetchedAt: "2026-11-01T12:00:00Z", cached: true});
  assert.equal((await next.data.inspect(subject, repeated)).status, "match");
});
test("a changed title is detected and the expected hash is retained until explicit acceptance", async () => {
  const b = browser();
  const first = await b.data.inspect(subject, b.share.integrityData(subject, metadata));
  b.data.remember(first);
  const changed = await b.data.inspect(subject, b.share.integrityData(subject, {...metadata, title: "A changed title"}));
  assert.equal(changed.status, "changed"); assert.equal(changed.savedHash, first.currentHash);
  assert.equal(b.data.remember(changed).status, "changed");
  assert.match(b.jar.get("mogwai_data_check"), new RegExp(first.currentHash));
  b.data.remember(changed, true);
  assert.equal((await b.data.inspect(subject, b.share.integrityData(subject, {...metadata, title: "A changed title"}))).status, "match");
});
test("turning remembering off erases cookie and checks and the choice survives reload", async () => {
  const b = browser();
  b.data.remember(await b.data.inspect(subject, metadata));
  b.data.setEnabled(false);
  assert.equal(b.jar.has("mogwai_data_check"), false); assert.equal(b.saved.has("mogwai.user-data.v1"), false);
  assert.equal((await browser({storage: b.saved, jar: b.jar}).data.inspect(subject, metadata)).status, "off");
  assert.equal(b.data.exportData().checks.length, 0);
});
test("export/import carries baselines to another host and rejects conflicts without replacing local data", async () => {
  const first = browser(), second = browser();
  first.data.remember(await first.data.inspect(subject, metadata));
  const exported = JSON.parse(JSON.stringify(first.data.exportData()));
  second.data.importData(exported);
  assert.equal((await second.data.inspect(subject, metadata)).status, "match");
  const conflict = {...exported, checks: [{...exported.checks[0], hash: "f".repeat(64)}]};
  assert.throws(() => second.data.importData(conflict), /conflicts/);
  assert.equal((await second.data.inspect(subject, metadata)).status, "match");
  second.data.forget(exported.checks[0].subjectHash);
  assert.equal(second.data.exportData().checks.length, 0);
  assert.equal(second.jar.has("mogwai_data_check"), false);
});
test("cookie-only and memory-only modes keep the app usable when storage is blocked", async () => {
  const cookieOnly = browser({blockStorage: true});
  cookieOnly.data.remember(await cookieOnly.data.inspect(subject, metadata));
  assert.equal((await browser({blockStorage: true, jar: cookieOnly.jar}).data.inspect(subject, metadata)).status, "match");
  cookieOnly.data.setEnabled(false);
  assert.equal((await browser({blockStorage: true, jar: cookieOnly.jar}).data.inspect(subject, metadata)).status, "off");
  const memoryOnly = browser({blockStorage: true, blockCookies: true});
  memoryOnly.data.remember(await memoryOnly.data.inspect(subject, metadata));
  assert.equal((await memoryOnly.data.inspect(subject, metadata)).status, "match");
  assert.equal(memoryOnly.data.state().indexSaved, false);
  assert.equal(memoryOnly.data.state().cookieSaved, false);
});
test("saved history is bounded and an import cannot smuggle arbitrary data into it", async () => {
  const b = browser();
  for (let index = 0; index < 103; index++) b.data.remember(await b.data.inspect("item-" + index, {index}));
  assert.equal(b.data.exportData().checks.length, 100);
  const exported = JSON.parse(JSON.stringify(b.data.exportData()));
  exported.checks[0].secret = "Do not import me";
  const next = browser(); next.data.importData(exported);
  assert.doesNotMatch(JSON.stringify(next.data.exportData()), /secret|Do not import/);
  exported.checks[0].hash = "not a SHA-256";
  assert.throws(() => next.data.importData(exported), /valid SHA-256/);
});
