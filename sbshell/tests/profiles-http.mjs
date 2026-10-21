// Development check: synthetic records, a temporary DB and a loopback PHP server.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, mkdir, writeFile, readFile, stat, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import net from 'node:net';

const temporary = await mkdtemp(join(tmpdir(), 'mogwai-profile-http-'));
const archive = join(temporary, 'archive');
const database = join(temporary, 'home.sqlite3');
const router = fileURLToPath(new URL('../cruff/index.php', import.meta.url));
const php = process.env.SB_PHP || 'php';
await mkdir(archive);
await writeFile(join(archive, '1_01.php'), `<?php
echo empty($mogwai_profiles_enabled) ? 'Unfilled sample' : htmlspecialchars(json_encode(mogwai_correspondence_fields()));
`);
const socket = net.createServer();
await new Promise(resolve => socket.listen(0, '127.0.0.1', resolve));
const port = socket.address().port;
await new Promise(resolve => socket.close(resolve));
const origin = 'http://127.0.0.1:' + port;
const server = spawn(php, ['-S', '127.0.0.1:' + port, '-t', archive, router], {
  cwd:archive, env:{ ...process.env, MOGWAI_HOME_DB:database }, stdio:['ignore','ignore','pipe']
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
  const response = await fetch(origin + '/?mogwai-profiles=1&return=%2F');
  assert.equal(response.status, 200);
  assert.match(response.headers.get('cache-control'), /no-store/);
  assert.equal(response.headers.get('x-frame-options'), 'DENY');
  const cookie = response.headers.get('set-cookie').split(';')[0];
  const form = await response.text();
  assert.match(form, /People and correspondence/);
  const csrf = form.match(/name="csrf" value="([0-9a-f]+)"/)[1];
  await assert.rejects(stat(database), {code:'ENOENT'});
  const fields = new URLSearchParams({
    csrf, 'letter[person1]':'shannon', 'letter[person2]':'john',
    'letter[mailing_address]':'Synthetic address', 'letter[city_state_zip]':'Example, NM 00000',
    'letter[letter_date]':'2026-10-20'
  });
  for(const id of ['john','shannon']) {
    fields.set(`people[${id}][legal_name]`, `Example <${id}>`);
    fields.set(`people[${id}][dob]`, '1900-01-01');
    fields.set(`people[${id}][ssn]`, '000-00-0001');
    fields.set(`people[${id}][experian_report_number]`, '');
  }
  const headers = {Cookie:cookie, Origin:origin};
  let result = await fetch(origin + '/?mogwai-profiles=1', {method:'POST', headers, body:new URLSearchParams({...Object.fromEntries(fields),csrf:'wrong'})});
  assert.equal(result.status, 403);
  await assert.rejects(stat(database), {code:'ENOENT'});
  result = await fetch(origin + '/?mogwai-profiles=1', {method:'POST', headers:{...headers, Origin:'https://example.invalid'}, body:fields});
  assert.equal(result.status, 403);
  result = await fetch(origin + '/?mogwai-profiles=1', {method:'POST', headers, body:fields});
  assert.equal(result.status, 200);
  const saved = await result.text();
  assert.match(saved, /Saved\./);
  assert.match(saved, /Example &lt;john&gt;/);
  assert.match(saved, /type="password"/);
  assert.equal((await stat(database)).mode & 0o777, 0o600);
  const letter = await (await fetch(origin + '/')).text();
  assert.match(letter, /Example &lt;shannon&gt;/);
  assert.match(letter, /000-00-0001/);
  const before = await readFile(database);
  fields.set('people[john][dob]', '1900-02-29');
  result = await fetch(origin + '/?mogwai-profiles=1', {method:'POST', headers, body:fields});
  assert.equal(result.status, 400);
  assert.deepEqual(await readFile(database), before);
  // DNS-rebinding Host headers must not turn the local GUI into a profile API.
  result = await fetch(origin + '/?mogwai-profiles=1', {headers:{Host:'example.invalid:' + port}});
  assert.equal(result.status, 403);
  const publicView = await (await fetch(origin + '/', {headers:{Host:'example.invalid:' + port}})).text();
  assert.match(publicView, /Unfilled sample/);
  assert.doesNotMatch(publicView, /000-00-0001|Example &lt;john&gt;/);
  console.log('Profile GUI: local saves, CSRF/origin checks, escaped fields, persistence, file permissions and public-view exclusion passed.');
} finally {
  server.kill();
  await closed;
  await rm(temporary, {recursive:true, force:true});
}
