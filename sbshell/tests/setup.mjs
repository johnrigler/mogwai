// Exercise the installer with real PHP and stub package commands, without apt writes.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync, existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const setup = fileURLToPath(new URL('../setup', import.meta.url));
const php = process.env.SB_PHP || 'php';
const version = spawnSync(php, ['-r', 'echo PHP_MAJOR_VERSION . "." . PHP_MINOR_VERSION;'], { encoding: 'utf8' });
assert.equal(version.status, 0, 'Run this test with a working PHP selected through SB_PHP.');
const scratch = mkdtempSync(join(tmpdir(), 'sbshell-setup-'));
try {
  const log = join(scratch, 'packages');
  writeFileSync(join(scratch, 'sudo'), '#!/bin/sh\nexec "$@"\n', { mode: 0o755 });
  for (const name of ['apt-get', 'phpenmod']) {
    writeFileSync(join(scratch, name), '#!/bin/sh\nprintf "%s" "${0##*/}" >> "$SB_TEST_LOG"\nprintf " <%s>" "$@" >> "$SB_TEST_LOG"\nprintf "\\n" >> "$SB_TEST_LOG"\n', { mode: 0o755 });
  }
  const env = { ...process.env, SB_PHP: php, SB_TEST_LOG: log, PATH: scratch + ':' + process.env.PATH };
  const run = (...args) => spawnSync('bash', [setup, ...args], { env, encoding: 'utf8' });
  const checked = run('check', scratch);
  assert.match(checked.stdout, /SB Shell PHP setup/);
  assert.equal(existsSync(log), false, 'A check must never invoke package commands.');
  assert.equal(run('unknown').status, 2, 'Reject unknown operations.');
  assert.equal(run('check', scratch, 'extra').status, 2, 'Reject extra arguments.');
  const installed = run('install', scratch);
  assert.match(installed.stdout, /SB Shell PHP setup/, installed.stderr);
  const calls = readFileSync(log, 'utf8').trim().split('\n');
  const v = version.stdout;
  assert.deepEqual(calls, [
    'apt-get <update>',
    `apt-get <install> <php${v}-cli> <php${v}-common> <php${v}-sqlite3> <php${v}-gd>`,
    `phpenmod <-v> <${v}> <-s> <cli> <sqlite3> <gd> <fileinfo>`
  ], 'Install and enable modules for the selected PHP version only.');
  assert.equal(installed.status, checked.status, 'Installation reruns the same readiness check.');
  writeFileSync(log, '');
  const termux = spawnSync('bash', [setup, 'install', scratch], {
    env: { ...env, PREFIX: '/data/data/com.termux/files/usr' }, encoding: 'utf8'
  });
  assert.equal(termux.status, 1);
  assert.equal(readFileSync(log, 'utf8'), '', 'Do not run Debian installation commands in Termux.');
  console.log('Setup commands: check-only behavior, PHP version matching, module enabling, validation and Termux guard passed.');
} finally {
  rmSync(scratch, { recursive: true, force: true });
}
