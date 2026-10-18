import { buildLetter, makeQR } from './layout.js';
import { ctp500Encode } from './ctp500.js';
import { ctp500ConnectBLE } from './ctp500-ble.js';

const $ = id => document.getElementById(id);
let image = null, prepared = null, ble = null, port = null, busy = false, revision = 0;
const status = message => { $('status').textContent = message; };
function buttons() {
  $('connect-ble').disabled = busy || !window.isSecureContext || !navigator.bluetooth;
  $('connect-serial').disabled = busy || !window.isSecureContext || !navigator.serial;
  $('print').disabled = busy || !prepared || !(port || ble?.device.gatt.connected);
  $('save').disabled = busy || !prepared;
  $('disconnect').disabled = busy || !(port || ble);
  for (const id of ['build', 'calibrate', 'title', 'letter', 'length', 'font-size', 'image-file', 'text-file', 'qr-text', 'clear-image', 'slow']) $(id).disabled = busy;
}
function invalidate() {
  revision++;
  prepared = null; buttons(); status('Content changed. Build the letter again before printing or saving.');
}
function build(calibration = false) {
  prepared = null;
  try {
    const result = buildLetter({ title: $('title').value, text: $('letter').value, width: Number($('length').value), fontSize: Number($('font-size').value), image: calibration ? null : image, qr: calibration ? null : makeQR($('qr-text').value), calibration });
    const preview = $('pages'); preview.replaceChildren();
    result.pages.forEach((page, i) => {
      const figure = document.createElement('figure'), caption = document.createElement('figcaption');
      caption.textContent = `Page ${i + 1}${i === 0 ? ' · cover' : i === 3 ? ' · back' : ''}`;
      figure.append(caption, page); preview.append(figure);
    });
    const strip = $('strip'); strip.width = result.strip.width; strip.height = result.strip.height;
    strip.getContext('2d').drawImage(result.strip, 0, 0);
    prepared = { bytes: ctp500Encode(strip, { feedRows: 160 }), calibration };
    status(`${calibration ? 'Fold test' : 'Letter'} ready: four ${result.pages[0].width} × 384-dot pages; ${prepared.bytes.length.toLocaleString()} bytes including trailing feed.`);
  } catch (error) { status(error.message); }
  buttons();
}
function disconnect() { ble?.disconnect(); ble = null; port = null; }
async function connect(kind) {
  busy = true; buttons(); disconnect();
  try {
    if (kind === 'ble') {
      const connection = await ctp500ConnectBLE(); ble = connection;
      connection.device.addEventListener('gattserverdisconnected', () => {
        if (ble !== connection) return;
        ble = null; status('Printer disconnected.'); buttons();
      });
      status('BLE connected: ' + (connection.device.name || 'printer'));
    } else { port = await navigator.serial.requestPort(); status('Serial port selected.'); }
  } catch (error) { status('Connection: ' + error.message); }
  finally { busy = false; buttons(); }
}
async function print() {
  if (busy || !prepared || !(port || ble?.device.gatt.connected)) return;
  const bytes = prepared.bytes, serialPort = port, connection = ble;
  let writer;
  busy = true; buttons();
  try {
    status('Sending strip… keep this page open.');
    if (connection) {
      let previous = -1;
      await connection.write(bytes, (sent, total) => {
        const percentage = Math.floor(sent / total * 100);
        if (percentage !== previous) { status('Sending strip: ' + percentage + '%'); previous = percentage; }
      }, { compatibilityPacing: $('slow').checked });
    } else {
      await serialPort.open({ baudRate: 9600 });
      writer = serialPort.writable.getWriter();
      for (let i = 0; i < bytes.length; i += 512) {
        await writer.write(bytes.subarray(i, i + 512));
        status('Sending strip: ' + Math.floor(Math.min(i + 512, bytes.length) / bytes.length * 100) + '%');
        await new Promise(resolve => setTimeout(resolve, 20));
      }
    }
    status('All bytes sent. Wait for the printer to finish, then tear and fold.');
  } catch (error) { status('Print interrupted: ' + error.message + ' Restart the printer before sending a fresh strip.'); }
  finally {
    writer?.releaseLock();
    if (serialPort?.readable || serialPort?.writable) try { await serialPort.close(); } catch (error) { status('Port close: ' + error.message); }
    busy = false; buttons();
  }
}
for (const id of ['title', 'letter', 'length', 'font-size', 'qr-text']) $(id).addEventListener('input', invalidate);
$('text-file').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  invalidate(); const current = revision;
  try { const text = await file.text(); if (current === revision) { $('letter').value = text; invalidate(); } }
  catch (error) { status('Text file: ' + error.message); }
});
$('image-file').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  invalidate(); const current = revision;
  try {
    const bitmap = await createImageBitmap(file);
    if (current !== revision) { bitmap.close(); return; }
    image?.close(); image = bitmap; invalidate();
  } catch (error) { status('Image file: ' + error.message); }
});
$('clear-image').addEventListener('click', () => { image?.close(); image = null; $('image-file').value = ''; invalidate(); });
$('build').addEventListener('click', () => build());
$('calibrate').addEventListener('click', () => build(true));
$('connect-ble').addEventListener('click', () => connect('ble'));
$('connect-serial').addEventListener('click', () => connect('serial'));
$('disconnect').addEventListener('click', () => { disconnect(); buttons(); status('Disconnected.'); });
$('print').addEventListener('click', print);
$('save').addEventListener('click', () => {
  if (!prepared) return;
  const name = prepared.calibration ? 'ctp500-fold-test.png' : 'ctp500-folded-letter.png';
  $('strip').toBlob(blob => {
    if (!blob) return;
    const url = URL.createObjectURL(blob), anchor = document.createElement('a');
    anchor.href = url; anchor.download = name; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }, 'image/png');
});
window.addEventListener('pagehide', disconnect);
window.addEventListener('beforeunload', event => { if (busy) { event.preventDefault(); event.returnValue = ''; } });
build();
