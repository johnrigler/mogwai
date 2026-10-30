# Mogwai share widget · 0.1.0

The acceptance path is **YouTube → system Share → Mogwai → Chisel Send**,
with the video URL already entered in **OP_RETURN ASCII**. This is a small,
installable vanilla-JavaScript web app, with no build or package dependencies.

## Install and test on a device

1. In Chrome, open <https://johnrigler.github.io/mogwai/app/>. Install Mogwai
   using the page's install button or Chrome's app-install menu. Wait for
   **Share receiver ready** before trying the share flow.
2. Open a video in YouTube. Use Share and, where necessary, the panel's
   option for more apps to open the **system** share menu.
3. Choose **Mogwai**. The receiver extracts the link and immediately opens
   Chisel with **Send** selected and **OP_RETURN ASCII** filled.
4. Confirm the visible URL matches the chosen video. Normal funding, review,
   signing and sending remain in Chisel.

Run this check independently on Android and ChromeOS. Browser-side checks
cannot establish that an app is installed or present in a particular device's
system share menu. A home-screen bookmark alone may not register a share
target. If it is missing, confirm the PWA was installed using Chrome.

The manual paste field exercises the same URL conversion and Chisel handoff.
**Chisel address** can select a local or IPFS-hosted copy. That copy needs
Chisel 2.8.9 or later. The default is the public Chisel GitHub Pages app.
No FileProxy, Crostini, or Termux process is required for this share path.

## Handoff

The web manifest registers a POST share target for `title`, `text` and `url`.
Its scoped service worker handles the POST and redirects the app with the
shared values in a fragment. Shared POST bodies are not forwarded to a server.
The receiver checks all three fields because Android often puts a URL in
`text`. It then navigates to:

```text
https://johnrigler.github.io/chisel/?mode=send#opreturn=https%3A%2F%2Fyoutu.be%2FjNQXAC9IVRw
```

Chisel consumes `opreturn` through its existing text draft loader, clears
conflicting HEX input, opens Send and focuses the ASCII field. The marker is
removed after consumption. Query-form `?opreturn=...` is also supported for
URL openers. No cross-origin storage or messaging is required.

Recognized YouTube watch, Shorts, live and embed URLs become
`https://youtu.be/VIDEO_ID`, retaining a valid `t`/`start` time as seconds and
removing tracking and playlist parameters. Other HTTP(S) links are preserved
as web links. Long URLs remain visible and are subject to Chisel's chain
payload checks; nothing is silently truncated.

The service worker caches only this app's shell under `app/`; it does not
cache Chisel or operate its transaction controls. Installability and system
sharing require a secure HTTPS origin (or localhost where supported).
Chisel's own availability determines whether the final page can open offline.

## Checks

```bash
node --check app/core.js
node --check app/app.js
node --check app/sw.js
node --test tests/mogwai-share.test.cjs
```

Keep the app files and icons together when serving on another static host
or HTTPS IPFS gateway. Its manifest, worker scope and assets use relative URLs.
