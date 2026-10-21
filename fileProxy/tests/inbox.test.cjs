// jsdom is a test-only dependency; the Inbox itself is vanilla JavaScript.
const { readFileSync } = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const test = require("node:test");
const { JSDOM } = require("jsdom");

const html = readFileSync(path.join(__dirname, "../web/index.html"), "utf8");
const tick = () => new Promise(resolve => setImmediate(resolve));
const localHealth = { ok: true, roots: ["daisy2026", "certledger"],
  defaultDaisyRoot: "daisy2026", writeTokenRequired: false };

async function openInbox(t, health = localHealth, options = {}) {
  const calls = [];
  let resolveHealth;
  const pending = new Promise(resolve => { resolveHealth = resolve; });
  const dom = new JSDOM(html, {
    url: "http://127.0.0.1:7799/",
    runScripts: "dangerously",
    beforeParse(window) {
      window.TextEncoder = TextEncoder;
      window.fetch = async (url, init = {}) => {
        calls.push({ url, ...init });
        if (url === "v1/health") {
          if (options.pending) await pending;
          if (options.error) throw new Error("Connection refused");
          return { ok: true, json: async () => health };
        }
        assert.equal(url, "v1/ingest");
        return { ok: true, json: async () => ({ ok: true, count: 1, items: [{
          root: "daisy2026", path: "426/inbox/note.txt", title: "note.txt",
          sha256: "a".repeat(64), bytes: 12, mime: "text/plain"
        }] }) };
      };
    }
  });
  t.after(() => dom.window.close());
  await tick();
  return {
    window: dom.window, calls, resolveHealth,
    $: id => dom.window.document.getElementById(id),
    async importNote(token = "") {
      dom.window.document.getElementById("paste").value = "Archive note";
      dom.window.document.getElementById("destination").value = "daisy2026";
      dom.window.document.getElementById("token").value = token;
      dom.window.document.getElementById("import").click();
      await tick();
    }
  };
}

test("local Inbox hides token input and imports through the API without a token", async t => {
  const ui = await openInbox(t);
  assert.equal(ui.$("tokenField").hidden, true);
  assert.equal(ui.$("import").disabled, false);
  await ui.importNote();
  const post = ui.calls.find(call => call.method === "POST");
  assert.ok(post);
  assert.equal(post.headers["X-FileProxy-Token"], undefined);
  assert.equal(JSON.parse(post.body).destination, "daisy2026");
  assert.match(ui.$("status").textContent, /1 record\(s\) processed/);
  assert.equal(ui.$("output").querySelector("a").getAttribute("href"),
    "v1/file?root=daisy2026&path=426%2Finbox%2Fnote.txt");
});

test("token mode asks for a token and sends it only when entered", async t => {
  const ui = await openInbox(t, { ...localHealth, writeTokenRequired: true });
  assert.equal(ui.$("tokenField").hidden, false);
  await ui.importNote();
  assert.equal(ui.calls.length, 1);
  assert.match(ui.$("status").textContent, /Enter FILEPROXY_WRITE_TOKEN/);
  await ui.importNote("test-write-secret");
  assert.equal(ui.calls[1].headers["X-FileProxy-Token"], "test-write-secret");
  assert.equal(ui.window.localStorage.length, 0);
});

test("older servers without an authentication field retain token mode", async t => {
  const ui = await openInbox(t, { ok: true, roots: ["daisy2026"] });
  assert.equal(ui.$("tokenField").hidden, false);
  await ui.importNote();
  assert.equal(ui.calls.length, 1);
});

test("imports wait for the health result", async t => {
  const ui = await openInbox(t, localHealth, { pending: true });
  assert.equal(ui.$("import").disabled, true);
  await ui.importNote();
  assert.equal(ui.calls.length, 1);
  ui.resolveHealth();
  await tick();
  assert.equal(ui.$("import").disabled, false);
  assert.equal(ui.$("tokenField").hidden, true);
});

test("an unavailable API leaves import disabled", async t => {
  const ui = await openInbox(t, localHealth, { error: true });
  assert.equal(ui.$("import").disabled, true);
  assert.match(ui.$("health").textContent, /unavailable/);
});

test("preview honors the selected registered root and annual routing tag", async t => {
  const ui = await openInbox(t);
  ui.$("paste").value = "Archive note #daisy2026";
  ui.$("paste").dispatchEvent(new ui.window.Event("input"));
  assert.equal(ui.$("preview").querySelector("strong").textContent, "DAISY2026");
  assert.doesNotMatch(ui.$("preview").textContent, /Register root/);
  ui.$("paste").value = "Archive note";
  ui.$("destination").value = "daisy2026";
  ui.$("destination").dispatchEvent(new ui.window.Event("change"));
  assert.equal(ui.$("preview").querySelector("strong").textContent, "DAISY2026");
  assert.doesNotMatch(ui.$("preview").textContent, /Register root/);
});

test("automatic classification previews the server's registered annual Daisy root", async t => {
  const ui = await openInbox(t);
  ui.$("paste").value = "An ordinary archive note";
  ui.$("paste").dispatchEvent(new ui.window.Event("input"));
  assert.equal(ui.$("destination").value, "auto");
  assert.equal(ui.$("preview").querySelector("strong").textContent, "DAISY2026");
  assert.doesNotMatch(ui.$("preview").textContent, /Register root/);
  ui.$("import").click();
  await tick();
  assert.equal(JSON.parse(ui.calls[1].body).destination, "auto");
  assert.match(ui.$("status").textContent, /1 record\(s\) processed/);
});

test("the sample respects a selected annual archive instead of forcing #daisy", async t => {
  const ui = await openInbox(t);
  ui.$("destination").value = "daisy2026";
  ui.$("sample").click();
  assert.match(ui.$("paste").value, /^https:/);
  assert.doesNotMatch(ui.$("paste").value, /#daisy/);
  assert.equal(ui.$("preview").querySelector("strong").textContent, "DAISY2026");
  assert.doesNotMatch(ui.$("preview").textContent, /conflicts/);
});
