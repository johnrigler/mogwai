# Mogwai Publication 42.B

The existing homepage and Canonical Vanilla stylesheet remain in place. `publication.html` adds a standalone vanilla-JS composition renderer.

Open `publication.html?page=publications/overview.json`, or `publication.html?page=publications/certledger.json`.

A JSON page contains `title` and an ordered `blocks` array. Blocks can be `hero`, `markdown`, `text`, `cards`, `table`, `list`, `directory`, `image`, `document`, or `include`. Sources resolve relative to the manifest's URL. Tables load JSON arrays or CSV files. A directory uses a root-relative `files.txt` inventory similar to SB Shell.

The browser fetches **published same-origin sources only**. A private DAISY repository cannot be read directly by a public static page. Material must be deliberately copied or published, or served by an authorized local mechanism. No DAISY content was copied for this demonstration.

The renderer does not use Node, PHP, React, wallet libraries, or the `lib` symlink. Run a static HTTP server or use an IPFS gateway. Browser `file://` fetches are commonly restricted. HTML previews run inside sandboxed iframes. Markdown is rendered as escaped text with headings, lists and code fences, not executed HTML. Source documents remain unchanged.

The initial repair also fixes the null-address query crash and removes private-key query logging from the homepage. The visible build is `42.B`.
