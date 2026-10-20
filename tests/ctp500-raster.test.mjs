import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

// Pixel-only canvas harness: exercises the browser encoder without dependencies.
class Canvas {
  constructor() { this.width = 0; this.height = 0; }
  getContext() {
    const c = this;
    if (!c.pixels || c.pixels.length !== c.width * c.height * 4) c.pixels = new Uint8ClampedArray(c.width * c.height * 4);
    return {
      fillStyle: '#fff',
      fillRect(x, y, w, h) {
        const color = this.fillStyle === '#fff' ? 255 : 0;
        for (let yy = y; yy < y + h; yy++) for (let xx = x; xx < x + w; xx++) c.pixels.set([color, color, color, 255], (yy * c.width + xx) * 4);
      },
      drawImage(source, ...a) {
        let sx = 0, sy = 0, sw = source.width, sh = source.height;
        let [dx, dy, dw = sw, dh = sh] = a;
        if (a.length === 8) [sx, sy, sw, sh, dx, dy, dw, dh] = a;
        for (let y = 0; y < dh; y++) for (let x = 0; x < dw; x++) {
          const src = ((sy + Math.floor(y * sh / dh)) * source.width + sx + Math.floor(x * sw / dw)) * 4;
          c.pixels.set(source.pixels.subarray(src, src + 4), ((dy + y) * c.width + dx + x) * 4);
        }
      },
      getImageData() { return { data: c.pixels.slice() }; },
      putImageData(image) { c.pixels.set(image.data); },
    };
  }
}
const root = new URL('../tools/ctp500-folded-letter/', import.meta.url);
const ctx = vm.createContext({ Uint8Array, document: { createElement: () => new Canvas() } });
for (const name of ['ctp500.js', 'ctp500-print.js', 'receipt.js']) {
  const source = (await readFile(new URL(name, root), 'utf8')).replace(/^import .*;\n/gm, '').replace(/^export /gm, '');
  vm.runInContext(source, ctx);
}
function decode(bytes) {
  let offset = 15; const rows = [];
  while (bytes[offset] === 29 && bytes[offset + 1] === 118) {
    const w = bytes[offset + 4] + 256 * bytes[offset + 5], h = bytes[offset + 6] + 256 * bytes[offset + 7]; offset += 8;
    assert(w > 0 && w <= 48);
    for (let y = 0; y < h; y++) { const row = new Uint8Array(48); row.set(bytes.subarray(offset, offset + w)); rows.push(...row); offset += w; }
  }
  return { rows, end: Array.from(bytes.subarray(offset)) };
}
test('fast output preserves pixels, row positions and feed for dense, sparse and white images', () => {
  for (const kind of ['dense', 'sparse', 'blank']) {
    const c = new Canvas(); c.width = 384; c.height = 167; const g = c.getContext();
    g.fillRect(0, 0, c.width, c.height); g.fillStyle = '#000';
    if (kind === 'dense') g.fillRect(0, 0, 384, 167);
    if (kind === 'sparse') { g.fillRect(0, 1, 1, 1); g.fillRect(383, 165, 1, 1); }
    ctx.source = c;
    const fast = vm.runInContext('ctp500PreparePrint(source)', ctx);
    const full = vm.runInContext('ctp500Encode(source, {feedLines:8, cut:false})', ctx);
    assert.deepEqual(decode(fast.bytes), decode(full));
    assert(fast.bytes.length <= full.length);
    assert.equal(decode(fast.bytes).rows.length, 167 * 48);
  }
});
test('receipt arithmetic uses cents and rejects invalid prices or quantities', () => {
  ctx.record = { merchant: 'DEMO', location: 'TEST', date: '2026-10-20', order: '1', items: [{ description: 'Test', quantity: 3, unitCents: 199 }], taxCents: 42 };
  const text = vm.runInContext('receiptText(record)', ctx);
  assert.match(text, /Subtotal\s+\$5\.97/); assert.match(text, /TOTAL\s+\$6\.39/);
  assert(text.split('\n').every(line => line.length <= 32));
  assert.match(vm.runInContext('SAMPLE_RECEIPT', ctx), /TOTAL\s+\$35\.65/);
  for (const patch of [{ quantity: 0, unitCents: 1 }, { unitCents: -1 }, { unitCents: 1.5 }]) {
    ctx.record.items = [{ description: 'Test', ...patch }];
    assert.throws(() => vm.runInContext('receiptText(record)', ctx));
  }
});
