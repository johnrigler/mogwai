# Prototype validation · 2026-10-18

Passed using the actual layout/encoder/UI modules, the vendored QRCode.js,
native canvas rendering and a minimal DOM/connection harness:

- Every sampled source-page pixel maps to the expected rotated strip panel
  in order 4, 1, 2, 3.
- Excess text throws an overflow error and disables saving/printing.
- Editing content invalidates the previously prepared bytes.
- Short QR payload retains a four-module white quiet zone and whole-dot
  modules; excessive density is rejected.
- A back-page image and QR render within their reserved column.
- Raster framing, row count and 160 blank feed rows match the existing encoder.
- Initial app build and numbered test both generate output.
- A simulated GATT connection receives the prepared bytes via ordered,
  acknowledged chunks of at most 20 bytes; success resets the UI state.
- JavaScript syntax checks pass.

The 800-dot panel test produces a 384 × 3200-dot strip and a 161,309-byte
printer stream including feed. That is substantially larger than the earlier
short CTP500 test. No actual throughput or print completion is claimed.

Full browser QA could not run: no Chromium binary was installed and its
download failed. Native canvas/module checks do not replace browser checks.
No CTP500 was connected. Physical fold alignment, legibility, QR scanning,
long-raster buffering and final paper feed remain unverified. Print the
numbered test first.

Unchanged source modules inspected before copying:

- `johnrigler/daisy_2026/42/ctp500.js` blob
  `89e720478760867e90420ca05738d6249298b040`.
- `johnrigler/daisy_2026/42/ctp500-ble.js` blob
  `12449619a7cdaeb5da560fd1a1f8118f296c8172`.
- `johnrigler/chisel/vendor/qrcode.min.js` blob
  `993e88f396640f881b69f98db7a4d17401ef83ca`.
