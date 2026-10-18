# CTP500 folded letter

Vanilla JavaScript prototype: plain letter text, one optional image and one QR
code become four landscape pages on a single thermal-paper strip. No build,
Node runtime, remote fonts, CDN, or server-side conversion is required.

Open `index.html` through an existing HTTPS or localhost server. BLE on the
phone and Web Serial on the Chromebook reuse the previously working CTP500
encoder/transport from `johnrigler/daisy_2026/42/`. The local copies here are
unchanged from the inspected source (2026-10-18). Vendored QRCode.js comes
from `johnrigler/chisel/vendor/qrcode.min.js`; its MIT license is included.
Keep this directory together when serving it or adding it to IPFS. Browser
Bluetooth/Serial access requires a supported Chromium browser and a secure
context; file:// is not the supported module/connection path.

## Use

1. Print **Numbered fold test** first.
2. Paste a letter, or load a text file. Set its title and optionally choose an
   image and enter QR text or a URL. Images and QR codes occupy page 4.
3. **Build letter** previews pages in reading order. Overflow blocks printing;
   increase page length, reduce text size, or shorten the letter to fit.
4. **Connect BLE (phone)**, select the printer, then **Print strip**. Serial
   is also available. Use slower BLE transfer if the output is incomplete.
5. Leave the page open until all bytes have been sent and printing completes.
   Tear off the extra blank feed. If transmission fails, restart the printer
   before sending a new raster; the tool does not retry interrupted jobs.

## Layout and folds

Each page is `pageLength × 384` dots, with text, fold and binding margins.
The default page length is 800 dots; it can be 640–1600. Body type is
16–28 dots, default 20. This is reflowed text, not a shrunken US Letter page.

Pages are placed in strip order **4, 1, 2, 3**, each rotated clockwise by 90°.
Dashed fold lines lie between panels. The printer canvas is 384 dots wide and
four page lengths long. The encoder adds 160 white feed rows after the strip.

Fold at the central line with the blank backs together, pairing page 2 behind
page 1 and page 3 behind page 4. Then fold at the remaining page boundary to
put page 1 on the front and page 4 on the back. Open at the second fold to
read pages 2 and 3. Staple close to this spine if desired, clear of the text.
This creates visible printing on both sides of the finished object from one
printable face; the printer does not perform duplex printing.

The numbered test has top markers, page numbers, cover/back labels and spine
edges. Validate that physical fold order before printing a real letter. A
simple two-fold strip creates four readable pages, not an eight-page zine.

## Limits and verification

Content exists in memory only; no automatic saving or uploading. The PNG
download contains the printed strip (without the trailing feed). The app
invalidates a prepared strip after edits, so stale text cannot be sent.
QR codes have a four-module white border, integer scaling and a minimum of
three dots per module; longer payloads are rejected. Images are thresholded
to black and white by the existing encoder; photographic detail may be lost.

Browser/layout checks do not establish paper dimensions, mechanical feed
accuracy, readable type, successful long-raster printing, or physical QR
scanning. Those remain physical acceptance checks for this prototype. The
previous short-image BLE/Serial tests are not evidence that this longer job
has already printed. Keep the tab open: printing does not continue after
navigation or app suspension.

Project record: `johnrigler/daisy_2026/427/ctp500-folded-letter/`.
