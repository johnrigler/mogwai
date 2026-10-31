# Mogwai share receiver · 0.4.2

The default Chisel link now loads 2.8.13, which redirects successful sends to
Portal with a navy pending record and changes it to black after a matching
live ledger read. Existing saved 2.8.12 defaults are migrated.

## Metadata and TX Portal preview

YouTube shares now stay in Mogwai for review. The URL still fills OP_RETURN
when **Open in Chisel** is selected. The handoff also carries the reviewed
Portal summary, media cards and retrieved metadata to Chisel 2.8.13's expanded
record preview above **SEND**. Before that handoff, the app calls
`https://rigler.org/fileproxy/youtube-metadata?url=...` with only the normalized
video URL, retaining a supplied start time. Original receipt fields and plain
text are not uploaded. The thumbnail loads from YouTube's image host.

The page shows the title, channel, thumbnail, video ID, retrieval time and
whether the lookup used FileProxy's six-hour cache. **Retry metadata lookup**
requests `refresh=1` to fetch from YouTube again. An unavailable service shows
its failure; the URL remains usable and no fetched metadata is fabricated.

**TX portal records** displays the exact ASCII payload, UTF-8 byte count and
hex, alongside `summary.opReturnText`, `opReturnUrls`, `primaryUrl` and
`mediaCards`. These are the Portal media fields derived from the URL and the
same FileProxy card builder used for real transactions. TXID and coin remain
`null` until Chisel prepares/sends a real transaction. Inputs, outputs, fees,
block details and the complete transaction are Chisel's responsibility.
Metadata does not enlarge the on-chain payload. Copying the preview creates
no transaction and does not invoke a server write route.

FileProxy must be updated and its existing process restarted on rigler.org.
Its `/ping` advertises `capabilities.youtubeMetadata` once the new code is
running. This change does not deploy or restart that private server.

## Your Mogwai data

**Your Mogwai data** exposes the remembered checks as JSON, with **Remember
data checks**, export, import and erase controls. Remembering is enabled by
default. The first successful lookup establishes a baseline. Future lookups
compare the OP_RETURN URL, display metadata and Portal media-card fields
using SHA-256 over JSON with recursively sorted object keys. `fetchedAt` and
cache flags are excluded because they describe retrieval rather than content.
The schema tag is `mogwai-youtube-check-v1`.

A match means **unchanged relative to this device's saved baseline**. It does
not authenticate YouTube, rigler.org, the first response, the browser or the
ledger. A changed response shows both hashes and retains the saved value until
**Accept changed data** is selected. Ordinary provider edits can cause changes.
No hashes, cookies or baselines are added to OP_RETURN or sent to rigler.org.

`app/user-data.js` is the reusable vanilla-JavaScript store. It holds at most
100 entries under `mogwai.user-data.v1` in localStorage. Entries contain only
the SHA-256 subject, SHA-256 data hash and saved time. `mogwai_data_check` is a
first-party cookie containing the most recent accepted subject/hash/time;
it provides a single-entry fallback when localStorage is unavailable. The
remembering preference has its own `mogwai_data_preference` cookie and
`mogwai.user-data.enabled.v1` storage key so an opt-out can survive a return
visit. Cookies last 180 days, are scoped to the app directory, use
`SameSite=Strict`, and use `Secure` on HTTPS. They are not authentication data.

Disabling remembering erases the hash index and check cookie while retaining
the preference. **Forget this check** removes one baseline; **Erase saved
checks** removes all baselines without changing other Mogwai settings or
the share console. The current page does not immediately recreate an erased
baseline. A later successful lookup can establish a new one. When both storage
mechanisms are blocked, checks work in memory and the UI reports that limit.

Exports contain hashes and saved times, with no video titles, raw URLs,
receipt content or private keys. Import merges validated entries, refuses
conflicting existing hashes and strips unknown entry fields. Browser origins
and app-directory cookie scopes are separate; export/import moves checks
between GitHub Pages, IPFS hosts and devices. Hashing does not encrypt data.

## Share console

Open **☰ Tools → Share console** to dump incoming shares immediately. This
includes original `title`, `text`, `url`, unknown fields, unexpected file
metadata, and receiver errors. **Open in Chisel** performs the handoff when selected.

The toggle is remembered in browser settings. The last 20 receipts, bounded
to 200,000 UTF-8 bytes, are held in this window's session storage so shares
that navigate/reload the app do not erase the console. New fragment shares
are also processed while the same page remains open. These receipts are not
uploaded. **Clear console** erases its log; **Clear received data** also
erases it; turning the console off erases its history. All shares still stay
for review. Copying the console requires its own button.
Updating retains the log without appending the restored receipt a second time.

If browser storage is blocked, the toggle and log work for the current page
only. Cross-window history is not aggregated. The standard share fields still
cannot identify which app sent a share.

An installed receiver for shared **text and web links**. YouTube links,
other links and plain text stay in Mogwai for review. Unrecognized shares show the fields
received rather than disappearing into a URL error. This remains a small,
vanilla-JavaScript web app with no build or package dependencies.

## The next device test

1. Open <https://johnrigler.github.io/mogwai/app/> online and reload until
   **Share receiver · 0.4.2** appears at the top.
2. Choose **Open system share test**. This calls the device's system share API
   with a short plain-text message, independently of YouTube.
3. Choose **Mogwai**, if the system lists it. The receiving window should show
   **What Mogwai received**, **Plain text**, and the test message.
4. Share a YouTube video. Check the metadata and TX Portal preview, then choose
   **Open in Chisel**. Share it again to check its saved SHA-256; change data
   only through the explicit acceptance control. **Copy received fields**
   retains the original receipt for troubleshooting.

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
3. Choose **Mogwai**. Review the receipt, metadata and TX preview, then choose
   **Open in Chisel**.
4. Confirm the visible URL matches the chosen video. Normal funding, review,
   signing and sending remain in Chisel.

Run this check independently on Android and ChromeOS. Browser-side checks
cannot establish that an app is installed or present in a particular device's
system share menu. A home-screen bookmark alone may not register a share
target. If it is missing, confirm the PWA was installed using Chrome.

The manual text field exercises the same URL conversion and Chisel handoff.
**Chisel address** can select a local or IPFS-hosted copy. That copy needs
Chisel 2.8.10 or later for paragraph text. The default is the public Chisel GitHub Pages app.
Use Chisel 2.8.12 or later for the full picture and metadata preview. Older
copies still import the OP_RETURN text. No local FileProxy, Crostini, or
Termux process is required for the URL handoff.
The metadata lookup uses the FileProxy service on rigler.org.

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

Version 0.4.2 also supplies a `record` fragment parameter containing JSON:
`{schema:"chisel-shared-record-v1", opReturnText, summary, metadata}`. The
summary is the Portal preview's summary, with a retrieved title when available;
the original share receipt, cookies and saved integrity baselines are excluded.
The record must fit Chisel's 65,536-byte limit. Its metadata is for display;
it does not enlarge OP_RETURN or set transaction outputs, keys or fees.
Chisel consumes both markers and scrolls to the expanded record above Send.
The transport stays browser-only and works with custom static/IPFS hosts.

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
including unrecognized content. With the console off, a received record stays
in memory in the current window. With it on, bounded receipts also survive navigation in session storage.
Original share receipts are never written to a server. YouTube lookup results
are cached by FileProxy separately. Clearing the receipt also clears the
prepared content. A previous session link cannot fill an unknown share.

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
node --check app/user-data.js
node --check app/app.js
node --check app/sw.js
node --test tests/mogwai-share.test.cjs tests/mogwai-user-data.test.cjs
```

Keep the app files and icons together when serving on another static host
or HTTPS IPFS gateway. Its manifest, worker scope and assets use relative URLs.
