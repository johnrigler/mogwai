// Development check only; the application itself runs in the browser.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const source = await fs.readFile(new URL('../tools/packet-registration/record.js', import.meta.url), 'utf8');
const { requireRecord, requireMailRecord, emailBody, emailDispatch, phpDispatch, receiptLines } =
  await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const email = {
  edition:'email', filename:'email.pdf', sha256:'a'.repeat(64), certledger_id:'test-email',
  sticker_id:'test-sticker', network:'Litecoin', transaction_id:'1'.repeat(64),
  transaction_url:'https://example.invalid/tx/' + '1'.repeat(64)
};
const mail = { ...email, edition:'mail', filename:'mail.pdf', sha256:'b'.repeat(64), certledger_id:'test-mail', transaction_id:'2'.repeat(64) };
assert.equal(requireRecord(email), email);
assert.throws(() => requireRecord({ ...email, sha256:'' }), /final PDF/);
assert.throws(() => requireRecord({ ...email, transaction_id:'' }), /transaction ID/);
assert.throws(() => requireRecord({ ...email, transaction_url:'javascript:alert(1)' }), /HTTP/);
const sentAt = '2026-10-18T17:30:00-06:00'; // Synthetic test fixture, not an event record.
const reference = emailDispatch(email, 'recipient@example.invalid', sentAt);
assert.equal(reference.pdf, email.filename);
assert.equal(reference.sha256, email.sha256);
assert.throws(() => emailDispatch(email, 'not-an-email', sentAt), /address/);
assert.throws(() => emailDispatch(email, 'recipient@example.invalid', '2026-10-18T17:30'), /time zone/);
assert.equal(requireMailRecord(mail, email, reference.to, sentAt), mail);
assert.throws(() => requireMailRecord({ ...mail, sha256:email.sha256 }, email, reference.to, sentAt), /separate/);
assert.throws(() => requireMailRecord({ ...mail, transaction_id:email.transaction_id }, email, reference.to, sentAt), /own ledger transaction/);
const body = emailBody(email);
assert(body.includes(email.filename) && body.includes(email.sha256) && body.includes(email.transaction_id));
assert(!body.includes(mail.sha256));
const receipt = receiptLines(mail).join('\n');
assert(receipt.includes(mail.sha256.slice(0, 32)) && receipt.includes(mail.transaction_id));
assert(!receipt.includes('confirmed') && !receipt.includes('delivered'));
const php = phpDispatch({ ...reference, certledger_id:"record's \\ reference" });
assert(php.startsWith('<?php') && php.includes("record\\'s \\\\ reference"));
assert(!php.includes('example.invalid/verify/invented'));
console.log('Registration checks passed: separate hashes/transactions, actual dispatch fields, email body, receipt identity and PHP escaping.');
