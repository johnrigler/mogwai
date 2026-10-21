import { requireRecord, requireMailRecord, emailBody, emailDispatch, phpDispatch, receiptLines } from './record.js';
import { ctp500PreparePrint, ctp500ConnectPrinter, ctp500BeginPrintSession } from './ctp500-print.js';

const $ = id => document.getElementById(id);
const key = 'certledger-editions:' + location.pathname;
const empty = edition => ({ edition, filename:'', bytes:0, sha256:'', certledger_id:'', sticker_id:'', network:'Litecoin', transaction_id:'', transaction_url:'' });
let state = { email:empty('email'), mail:empty('mail'), to:'', sent_at:'' };
try { state = { ...state, ...JSON.parse(localStorage.getItem(key) || '{}') }; } catch {}
const checked = new Set();
let printer, busy = false;

function status(message, error = false) {
  $('status').textContent = message;
  $('status').classList.toggle('error', error);
}
function save() { try { localStorage.setItem(key, JSON.stringify(state)); } catch {} }
function download(name, data, type) {
  const url = URL.createObjectURL(new Blob([data], { type }));
  const link = document.createElement('a');
  link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function dispatch() { return emailDispatch(current('email'), state.to, state.sent_at); }
function current(edition) {
  if (!checked.has(edition)) throw Error('Select the ' + edition + ' PDF to check its bytes first.');
  return requireRecord(state[edition]);
}
function selected() {
  const edition = $('edition').value;
  const record = current(edition);
  if (edition === 'mail') requireMailRecord(record, current('email'), state.to, state.sent_at);
  return record;
}
function act(callback) {
  return async () => { try { await callback(); } catch (error) { status(error.message, true); } };
}
function fillForms() {
  document.querySelectorAll('fieldset[data-edition]').forEach(group => {
    const record = state[group.dataset.edition];
    group.querySelectorAll('input[data-field]').forEach(input => {
      if (input.dataset.field !== 'file') input.value = record[input.dataset.field] || '';
    });
    group.querySelector('output').textContent = record.sha256
      ? record.filename + ' — re-select the PDF to check these saved bytes.\nSHA-256: ' + record.sha256
      : 'No PDF selected.';
  });
  $('email-to').value = state.to;
  $('email-sent').value = state.sent_at;
}
fillForms();

document.querySelectorAll('fieldset[data-edition]').forEach(group => {
  const edition = group.dataset.edition;
  group.addEventListener('input', event => {
    const field = event.target.dataset.field;
    if (!field || field === 'file') return;
    state[edition][field] = event.target.value.trim();
    save();
  });
  group.querySelector('[data-field=file]').addEventListener('change', act(async () => {
    const input = group.querySelector('[data-field=file]');
    const file = input.files[0];
    if (!file) return;
    checked.delete(edition);
    const bytes = await file.arrayBuffer();
    if (new TextDecoder().decode(bytes.slice(0, 5)) !== '%PDF-') throw Error('Choose a PDF file.');
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    if (input.files[0] !== file) return;
    const sha256 = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
    const record = state[edition];
    if (record.sha256 && record.sha256 !== sha256) {
      record.certledger_id = ''; record.transaction_id = ''; record.transaction_url = '';
      for (const field of ['certledger_id', 'transaction_id', 'transaction_url']) group.querySelector('[data-field=' + field + ']').value = '';
      if (edition === 'email') {
        state.to = ''; state.sent_at = '';
        $('email-to').value = ''; $('email-sent').value = '';
      }
      status('Different PDF bytes selected. Enter a separate registration for this version.');
    } else status(edition + ' PDF fingerprint checked.');
    Object.assign(record, { filename:file.name, bytes:file.size, sha256 });
    checked.add(edition);
    group.querySelector('output').textContent = file.name + ' · ' + file.size + ' bytes\nSHA-256: ' + sha256;
    save();
  }));
});
$('email-to').addEventListener('input', () => { state.to = $('email-to').value.trim(); save(); });
$('email-sent').addEventListener('input', () => { state.sent_at = $('email-sent').value.trim(); save(); });

// Draw whole QR modules with a four-module white border for paper scanning.
function qrCanvas(text) {
  const holder = document.createElement('div');
  const code = new QRCode(holder, { text, width:256, height:256, correctLevel:QRCode.CorrectLevel.M });
  const matrix = code._oQRCode;
  const count = matrix.getModuleCount();
  const cell = Math.floor(352 / (count + 8));
  if (cell < 2) throw Error('Use a shorter transaction URL for a readable receipt QR.');
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = (count + 8) * cell;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = 'white'; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = 'black';
  for (let row = 0; row < count; row++) for (let col = 0; col < count; col++) {
    if (matrix.isDark(row, col)) ctx.fillRect((col + 4) * cell, (row + 4) * cell, cell, cell);
  }
  return canvas;
}
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function render() {
  const record = selected();
  const sheet = $('sheet');
  sheet.replaceChildren(node('h1', 'CertLedger Registration'), node('p', record.edition.toUpperCase() + ' edition — separate registration sheet'));
  sheet.append(node('p', 'This sheet references the PDF identified below. It is additional to that PDF and is outside the bytes covered by its SHA-256 fingerprint.'));
  const values = [
    ['PDF', record.filename], ['CertLedger ID', record.certledger_id],
    ['SHA-256', record.sha256], ['Ledger', record.network],
    ['Transaction', record.transaction_id], ['Transaction URL', record.transaction_url],
    ['Sticker ID', record.sticker_id || 'Not recorded']
  ];
  if (record.edition === 'mail') {
    const email = dispatch();
    values.push(['Email reference', email.to + ' · ' + email.sent_at], ['Email PDF', email.pdf], ['Email SHA-256', email.sha256]);
  }
  const list = node('dl');
  for (const [label, value] of values) list.append(node('dt', label), node('dd', value));
  sheet.append(list);
  const references = node('div', undefined, 'references');
  references.append(node('div', 'Optional location for the preprinted colored QR sticker · 2 × 2 inches', 'sticker'));
  const qr = node('div', undefined, 'qr');
  qr.append(qrCanvas(record.transaction_url));
  references.append(qr);
  sheet.append(references, node('p', 'Scan the transaction QR for the ledger reference. The colored sticker is the physical packet identifier.'));
  sheet.append(node('p', 'Registration records a document fingerprint. Email transmission, mailing, delivery and responses are recorded as separate events.'));
  sheet.append(node('div', '', 'signature'), node('p', 'Signature / printed name / date (if used)'));

  const lines = receiptLines(record).flatMap(line => line.match(/.{1,34}/gu) || ['']);
  const image = qrCanvas(record.transaction_url);
  const canvas = $('receipt');
  canvas.width = 384; canvas.height = 32 + lines.length * 23 + image.height + 32;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = 'white'; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = 'black'; ctx.font = '16px monospace'; ctx.textBaseline = 'top';
  lines.forEach((line, i) => ctx.fillText(line, 16, 16 + i * 23));
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(image, Math.floor((384 - image.width) / 2), 24 + lines.length * 23);
  status('Separate ' + record.edition + ' registration sheet and transaction receipt prepared.');
  return record;
}
$('render').addEventListener('click', act(render));
$('print-sheet').addEventListener('click', act(() => { render(); window.print(); }));
$('email-body').addEventListener('click', act(() => {
  $('body-draft').value = emailBody(current('email'));
  status('Email body draft prepared. Attach the exact selected email PDF when sending.');
}));
$('dispatch').addEventListener('click', act(() => {
  download('email-dispatch.php', phpDispatch(dispatch()), 'text/plain');
  status('Actual email reference exported. Place it beside the letter parts and rebuild the mail edition.');
}));
$('download-record').addEventListener('click', act(() => {
  const record = selected();
  const value = { ...record };
  if (record.edition === 'mail') value.email_reference = dispatch();
  download('experian-dispute-' + record.edition + '.record.json', JSON.stringify(value, null, 2) + '\n', 'application/json');
}));
$('import-record').addEventListener('click', () => $('record-file').click());
$('record-file').addEventListener('change', act(async () => {
  const file = $('record-file').files[0];
  if (!file) return;
  const record = JSON.parse(await file.text());
  if (!['email', 'mail'].includes(record.edition)) throw Error('Choose an email or mail edition record.');
  for (const field of ['filename','sha256','certledger_id','sticker_id','network','transaction_id','transaction_url']) {
    if (typeof record[field] !== 'string') throw Error('The edition record has an invalid field.');
  }
  state[record.edition] = { ...empty(record.edition), ...record };
  checked.delete(record.edition);
  if (record.email_reference) {
    state.to = record.email_reference.to || ''; state.sent_at = record.email_reference.sent_at || '';
  }
  save(); fillForms(); status('Record loaded. Re-select its PDF to check the bytes before preparing receipts.');
}));
$('download-receipt').addEventListener('click', act(async () => {
  const record = render();
  const blob = await new Promise(resolve => $('receipt').toBlob(resolve, 'image/png'));
  download('experian-dispute-' + record.edition + '-transaction-receipt.png', blob, 'image/png');
}));
$('connect').addEventListener('click', act(async () => {
  if (busy) return;
  if (printer?.connected) await printer.disconnect();
  printer = await ctp500ConnectPrinter({ transport:$('transport').value });
  status('Connected: ' + printer.label);
}));
$('disconnect').addEventListener('click', act(async () => { await printer?.disconnect(); printer = null; status('Printer disconnected.'); }));
$('print-receipt').addEventListener('click', act(async () => {
  if (busy) return;
  render();
  if (!printer?.connected) throw Error('Connect the printer first.');
  const feed = document.createElement('canvas');
  feed.width = 384; feed.height = $('receipt').height + 160;
  const ctx = feed.getContext('2d');
  ctx.fillStyle = 'white'; ctx.fillRect(0, 0, feed.width, feed.height);
  ctx.drawImage($('receipt'), 0, 0);
  const job = ctp500PreparePrint(feed, { mode:'acknowledged' });
  busy = true; $('print-receipt').disabled = true;
  const finish = ctp500BeginPrintSession();
  try {
    await printer.write(job.bytes, (sent, total) => status('Sending receipt: ' + sent + ' / ' + total + ' bytes'), { mode:'acknowledged' });
    status('Receipt bytes sent to the printer. Keep the printed transaction receipt with the separate registration sheet.');
  } finally {
    await finish(); busy = false; $('print-receipt').disabled = false;
  }
}));
