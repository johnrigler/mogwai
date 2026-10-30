# Mogwai share receiver · 0.2.2

An installed receiver for shared **text and web links**. YouTube video links
still open Chisel Send automatically with OP_RETURN ASCII filled. Other links
and plain text stay in Mogwai for review. Unrecognized shares show the fields
received rather than disappearing into a URL error. This remains a small,
vanilla-JavaScript web app with no build or package dependencies.

## The next device test

1. Open <https://johnrigler.github.io/mogwai/app/> online and reload until
   **Share receiver · 0.2.2** appears at the top.
2. Choose **Open system share test**. This calls the device's system share API
   with a short plain-text message, independently of YouTube.
3. Choose **Mogwai**, if the system lists it. The receiving window should show
   **What Mogwai received**, **Plain text**, and the test message.
4. Alternatively, share from any app whose system chooser lists Mogwai. A
   normal page link stays for review; YouTube video links keep their automatic
   handoff. **Copy received fields** retains the receipt for troubleshooting.

The sending side cannot verify which destination received a share. The receipt
is the useful check. If this browser cannot open system sharing from a page,
the button reports that limitation; receiving shares from another app may still
work. YouTube's social-network panel has its own list and need not open the
system chooser.

**Update app** is always visible in the header. It checks the service-worker
registration, requests a fresh page with a unique update URL, and restores the
current receipt and prepared text through a temporary fragment. An update does
not automatically hand a restored YouTube link to Chisel. The version label is
plain text, not a home or update link.

**Install Mogwai** also stays visible. When Chrome supplies an installation
prompt, the button opens it; otherwise it opens installation instructions.
Chrome may stop offering a prompt once the app is installed. Installation and
updating are separate actions.

## Install and test on a device

1. In Chrome, open <https://johnrigler.github.io/mogwai/app/>. Install Mogwai
   using the page's install button or Chrome's app-install menu. Wait for
   **Share receiver ready** before trying the share flow.
2. Use an app or page that opens the **system** share menu. YouTube's own
   social-network panel is not evidence that the system chooser was opened.
3. Choose **Mogwai**. A YouTube video immediately opens Chisel. Other links
   and text show their receipt; choose **Open in Chisel** after reviewing them.
4. Confirm the visible URL matches the chosen video. Normal funding, review,
   signing and sending remain in Chisel.

Run this check independently on Android and ChromeOS. Browser-side checks
cannot establish that an app is installed or present in a particular device's
system share menu. A home-screen bookmark alone may not register a share
target. If it is missing, confirm the PWA was installed using Chrome.

The manual text field exercises the same URL conversion and Chisel handoff.
**Chisel address** can select a local or IPFS-hosted copy. That copy needs
Chisel 2.8.10 or later for paragraph text. The default is the public Chisel GitHub Pages app.
No FileProxy, Crostini, or Termux process is required for this share path.

The default hosted Chisel link includes a version marker for a fresh compatible
page load. An earlier saved default is migrated; custom hosts are retained.
Paragraphs require Chisel 2.8.10 or later.

## Handoff

The web manifest registers a POST share target for `title`, `text` and `url`.
Its scoped service worker handles the POST and redirects the app with the
shared values in a fragment. Shared POST bodies are not forwarded to a server.
The receiver checks all three fields because Android often puts a URL in
`text`. For a YouTube video it navigates to:

```text
https://johnrigler.github.io/chisel/?mode=send#opreturn=https%3A%2F%2Fyoutu.be%2FjNQXAC9IVRw
```

Chisel consumes `opreturn` through its existing text draft loader, clears
conflicting HEX input, opens Send and focuses the ASCII field. The marker is
removed after consumption. Query-form `?opreturn=...` is also supported for
URL openers. No cross-origin storage or messaging is required.

Plain text can use the same handoff after an explicit button press. Paragraphs,
Unicode, and final newlines are retained. The displayed UTF-8 byte count warns
when content exceeds 80 bytes; Chisel applies the selected chain's actual
payload rules. Handoff is disabled above Chisel's 4,096-byte URL-import limit,
while the full receipt remains available. Use Chisel 2.8.10 or later to retain
paragraph breaks in its ASCII field. The widget does not truncate text or send
a transaction.

## Received fields

The receipt shows the decoded `title`, `text`, and `url` values supplied by the
sender. Unrecognized fields, repeated field values, and any unexpected file
metadata remain visible under `additional_fields`. The manifest advertises
text and links; this change does not register a general file receiver. File
bytes are not read, uploaded, or retained by the receipt.

The standard share fields do not identify the app that sent them. Mogwai does
not guess a sender from a page title or hostname. JSON is rendered as text,
including unrecognized content. A received record is kept in the current
window, not written to a server or persistent storage. Clearing it also clears
the prepared content. A previous session link cannot fill an unknown share.

The receiver envelope has a 70,000-byte limit. Oversized URL-fragment inputs
show an explicitly truncated preview; failed POST decoding reports its error.
Copying a receipt is a separate user action. It may contain private content,
so review it before sharing it elsewhere.

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
