// Development-only Node harness. Product UI is ordinary local PHP/HTML.
import assert from 'node:assert/strict';
import {spawn, spawnSync} from 'node:child_process';
import {mkdtemp, mkdir, readFile, rm, stat} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import http from 'node:http';
import net from 'node:net';

const root = fileURLToPath(new URL('../', import.meta.url));
const temporary = await mkdtemp(join(tmpdir(), 'mogwai-signatures-'));
const archive = join(temporary, 'archive');
const pdf = join(temporary, 'synthetic.pdf');
const database = join(temporary, 'home.sqlite3');
const python = process.env.MOGWAI_SIGNATURE_PYTHON || 'python3';
await mkdir(archive);
const fixture = spawnSync(python, ['-c', `
import json, sys
from pathlib import Path
from signatures.test_workbench import WorkbenchTests, workbench
WorkbenchTests.setUpClass()
test = WorkbenchTests()
test.setUp()
try:
    test.signed_pdf(output=Path(sys.argv[1]))
    print(json.dumps(workbench.certificate_info(test.pem)))
finally:
    test.doCleanups()
`, pdf], {cwd:root, env:process.env, encoding:'utf8'});
assert.equal(fixture.status, 0, fixture.stderr);
const cert = JSON.parse(fixture.stdout);
const socket = net.createServer();
await new Promise(resolve => socket.listen(0, '127.0.0.1', resolve));
const port = socket.address().port;
await new Promise(resolve => socket.close(resolve));
const origin = 'http://127.0.0.1:' + port;
const url = origin + '/?mogwai-signatures=1';
const server = spawn(process.env.SB_PHP || 'php', ['-S', '127.0.0.1:' + port, '-t', archive, join(root, 'sbshell/cruff/index.php')], {
  cwd:archive, env:{...process.env, MOGWAI_HOME_DB:database, MOGWAI_SIGNATURE_PYTHON:python}, stdio:['ignore', 'ignore', 'pipe']
});
let log = '';
server.stderr.on('data', chunk => { log += chunk; });
const closed = new Promise(resolve => server.on('close', resolve));
try {
  for(let attempt = 0; attempt < 60; attempt++) {
    if(server.exitCode !== null) throw new Error('PHP listener failed: ' + log);
    try { await fetch(origin + '/?sb-check=1'); break; }
    catch { await new Promise(resolve => setTimeout(resolve, 50)); }
  }
  const response = await fetch(url);
  assert.equal(response.status, 200, await response.clone().text());
  assert.match(response.headers.get('cache-control'), /no-store/);
  const cookie = response.headers.get('set-cookie').split(';')[0];
  const form = await response.text();
  const csrf = form.match(/name="csrf" value="([0-9a-f]+)"/)[1];
  assert.match(form, /Signing identities/);
  await assert.rejects(stat(database), {code:'ENOENT'});
  const headers = {Cookie:cookie, Origin:origin};
  const values = {
    csrf, action:'remember', certificate_pem:cert.certificate_pem,
    label:'Synthetic <signer>', publication:'https://example.invalid/signing.json',
    status:'observed', evidence:'LOCAL-ONLY-NOTE', confirmed_fingerprint:''
  };
  let result = await fetch(url, {method:'POST', headers, body:new URLSearchParams({...values, csrf:'wrong'})});
  assert.equal(result.status, 403);
  result = await fetch(url, {method:'POST', headers:{...headers, Origin:'https://other.invalid'}, body:new URLSearchParams(values)});
  assert.equal(result.status, 403);
  await assert.rejects(stat(database), {code:'ENOENT'});
  result = await fetch(url, {method:'POST', headers, body:new URLSearchParams({...values, status:'verified', confirmed_fingerprint:'0'.repeat(64)})});
  assert.equal(result.status, 400);
  await assert.rejects(stat(database), {code:'ENOENT'});
  result = await fetch(url, {method:'POST', headers, body:new URLSearchParams(values)});
  assert.equal(result.status, 200);
  assert.match(await result.text(), /Synthetic &lt;signer&gt;/);
  assert.equal((await stat(database)).mode & 0o777, 0o600);
  const upload = new FormData();
  upload.set('csrf', csrf);
  upload.set('action', 'inspect');
  upload.set('pdf', new Blob([await readFile(pdf)], {type:'application/pdf'}), 'synthetic.pdf');
  result = await fetch(url, {method:'POST', headers, body:upload});
  assert.equal(result.status, 200);
  const inspection = await result.text();
  assert.match(inspection, /ENTIRE_FILE/);
  assert.match(inspection, /Signature mathematics<\/dt><dd>Valid/);
  assert.match(inspection, /observed — Synthetic &lt;signer&gt;/);
  result = await fetch(url, {method:'POST', headers, body:new URLSearchParams({csrf, action:'export', fingerprint:cert.certificate_sha256})});
  assert.equal(result.status, 200);
  assert.match(result.headers.get('content-disposition'), /attachment/);
  const publicData = await result.text();
  assert.doesNotMatch(publicData, /LOCAL-ONLY-NOTE|evidence|updated_at|status/);
  assert.equal(JSON.parse(publicData).certificate_sha256, cert.certificate_sha256);
  const wrongHost = await new Promise((resolve, reject) => {
    http.get(url, {headers:{Host:'example.invalid:' + port}}, response => {
      response.resume();
      response.on('end', () => resolve(response.statusCode));
    }).on('error', reject);
  });
  assert.equal(wrongHost, 403);
  console.log('Signing GUI: PDF verification, escaped identities, explicit pinning, public export, local access and CSRF checks passed.');
} finally {
  server.kill();
  await closed;
  await rm(temporary, {recursive:true, force:true});
}
