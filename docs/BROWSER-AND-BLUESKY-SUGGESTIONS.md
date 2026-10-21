# Mogwai suggestions: browser discussions and Bluesky

Recorded 2026-10-21 from the October 20–21 discussion.
Status: proposals only; no extension, Bluesky integration, or new storage
service is implemented by these notes.

## 1. Browser extension for contextual conversations

Offer Mogwai through a small JavaScript browser extension. On supported
pages, show a small button that opens messages and discussions from feeds
the reader chooses. Initial contexts discussed:

- YouTube: a conversation about an individual video or an entire channel.
- Bluesky: Mogwai discussion alongside a profile or post.
- Credit bureau sites: subscribed commentary and supporting public records
  about the organization, such as Experian or Equifax.

Use stable subject identifiers where available: YouTube video/channel IDs
and AT Protocol identities/record URIs. Titles and display names are labels.
Replies should reference their parent message so a thread can be rebuilt.

The reader chooses addresses, feeds and filters. Following an identity
should allow its full relevant public transaction stream to be inspected,
as in Chisel's "Show me my transactions"; ThunderWords are one filter,
not the only records considered. A transaction involving an address does
not by itself establish that the address authored every message in it.

Discussion records could initially live on rigler.org, with export and
mirrors elsewhere, following the portable-save idea discussed for Zorkmid.
The discussion should also open directly in Mogwai without its original
website. On-chain records may contain messages or commitments/references;
do not require every discussion message to be a blockchain transaction.

Separate public reading from signing/publishing. Identify what was
actually verified: record integrity, key control, chain inclusion and
identity association are distinct from the truth of a claim. Limit page
access to enabled sites; matching a page need not upload browsing history.

This extension could be an entry into Mogwai, with optional paid services
for document preparation, signing and publication. The service offering
and implementation remain undecided.

## 2. Bluesky / AT Protocol read and write support

Explore an API adapter that can:

- Read public posts, profiles and threads.
- Publish normal Bluesky posts and replies with account authorization.
- Define custom Mogwai discussion records in an AT Protocol repository,
  carrying a subject, message, reply reference and optional Mogwai signature.
- Export or mirror records on rigler.org or another chosen destination.

Custom AT Protocol records do not automatically appear in the normal
Bluesky timeline; Mogwai would supply their reader and any indexing needed.
A normal Bluesky post could link to the corresponding Mogwai record.

Keep AT Protocol storage, Mogwai signatures and blockchain anchoring
separate. A Bluesky account identity is not automatically a cryptocurrency
identity; an explicit signed association would be needed. Preserve record
URIs and content identifiers when mirroring. Public repository records are
not suitable for private case material, and remote hosting alone is not a
permanent archive.

API starting points checked during the discussion:

- [Public reads and authenticated writes](https://docs.bsky.app/docs/api/app-bsky-feed-get-author-feed)
- [Creating posts and replies](https://docs.bsky.app/docs/tutorials/creating-a-post)
- [AT Protocol records and custom application schemas](https://atproto.com/specs/atp)
- [Writing records](https://atproto.com/guides/writing-data)

The browser reader and adapters belong to Mogwai's tooling layer.
CertLedger remains finished work product. Existing runtime behavior is
unchanged; implementation details, authorization flow and distribution
are future decisions.
