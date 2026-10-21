# Scan ingestion

Scanner output currently arrives in a form like:

```
scan_261005-191332_1.png
```

Interpretation:

- `scan` = source type
- `261005` = YYMMDD = 2026-10-05
- `191332` = HHMMSS = 19:13:32
- `1` = page number
- `.png` = source format

Files sharing the same timestamp belong to the same scan event/document unless later evidence says otherwise.

The original filename is provenance and should be preserved. Mogwai may add placement ordinals when the scan becomes part of a larger packet, but it should not destroy the scanner-generated identity.

A directory is considered in a solid state when its files and its checked-in `index.js` agree. Python, FileProxy, Termux, a fax receiver, or another ingestion tool may regenerate `index.js`, but no service is required to read the resulting directory afterward.

For evidence work, distinguish source capture time from later ingestion time. Do not silently replace one with the other.
