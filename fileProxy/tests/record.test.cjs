const test = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {createHash,webcrypto} = require('node:crypto');
const {JSDOM} = require('jsdom');

const html = readFileSync(require('node:path').join(__dirname,'../web/record.html'),'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const id = '0123456789ABCDEF';
const source = 'actual source bytes';
const digest = createHash('sha256').update(source).digest('hex');
const settle = () => new Promise(resolve => setImmediate(resolve));

test('record viewer uses the service prefix, literal descriptions and memory-only authorization', async () => {
  const dom = new JSDOM(html,{url:'https://records.example/fileproxy/record?id='+id,runScripts:'outside-only'});
  const w = dom.window, calls = [];
  let changed = false;
  w.HTMLElement.prototype.scrollIntoView = () => {};
  Object.defineProperty(w.crypto,'subtle',{value:webcrypto.subtle});
  w.URL.createObjectURL = () => 'blob:synthetic-local-file';
  w.URL.revokeObjectURL = () => {};
  w.fetch = async (url,options) => {
    calls.push({url,options});
    if (url.startsWith('/fileproxy/v1/record?')) return new Response(JSON.stringify({
      found:true,searched:[{isoYear:2026,root:'daisy2026',status:'searched'}],
      records:[{isoYear:2026,root:'daisy2026',path:'444/folder',description:'<img src=x onerror=alert(1)>',
        entries:[{root:'daisy2026',path:'444/folder/scan.txt',bytes:source.length,sha256:digest}]}]
    }),{headers:{'Content-Type':'application/json'}});
    return new Response(changed ? 'different bytes' : source,{headers:{'Content-Type':'text/plain'}});
  };
  w.eval(script);
  await settle();
  assert.equal(w.document.querySelectorAll('.record').length,1);
  assert.equal(w.document.querySelector('.record pre').textContent,'<img src=x onerror=alert(1)>');
  assert.equal(w.document.querySelector('.record img'),null);
  w.document.getElementById('token').value='synthetic-secret';
  await w.document.querySelector('.record button').onclick();
  assert.match(w.document.getElementById('status').textContent,/SHA-256 matches/);
  assert.equal(w.document.querySelector('#preview pre').textContent,source);
  assert.equal(calls.at(-1).options.headers.Authorization,'Bearer synthetic-secret');
  assert.ok(!calls.at(-1).url.includes('synthetic-secret'));
  assert.equal(w.localStorage.length,0);
  changed = true;
  await w.document.querySelector('.record button').onclick();
  assert.match(w.document.getElementById('status').textContent,/File changed since lookup/);
  assert.notEqual(w.document.querySelector('#preview pre').textContent,'different bytes');
  dom.window.close();
});
