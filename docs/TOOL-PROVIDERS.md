# Mogwai tool providers and personal launcher

Design agreed 2026-11-24. Initial implementation is a standalone registry core, not a wired launcher.

## Roles

- Mogwai is a browser-first launcher and share receiver. Its local registry belongs to the user.
- A provider publishes a static JSON tool catalog; multiple providers may coexist.
- Rigler.org is the removable, restorable factory provider, not a mandatory service.
- The public GitHub Pages homepage is a human-readable project directory; each entry can eventually offer Add to Mogwai. A catalog can live on GitHub Pages, Rigler.org, or an HTTPS IPFS gateway.
- The existing server profiles (FileProxy and Lantern endpoints) are separate from tool catalog providers. Removing a catalog must not alter those settings.
- Preserve existing launcher tiles and settings on upgrade. A fresh install can use a factory selection; a deliberately empty saved list is valid and must not be reseeded on reload.

## Catalog v1

A catalog is JSON with schema "mogwai.tool-catalog.v1", a display name, and an array of tools. Each tool has an id, name, HTTPS launch URL, optional description, and optional recommended boolean. The catalog URL is its local provider key; a provider's tool ID is scoped to that URL. Store accepted launch descriptors locally so removal of a provider or an offline catalog doesn't silently delete the user's shortcuts. A catalog update is a suggestion, never a permission grant or silent replacement of an installed URL.

The Rigler.org catalog is intended to be published at https://rigler.org/mogwai.json; deployment there is not part of this commit. The repository contains a sample catalog for the initial tool set. Cross-origin catalogs require CORS; prefer explicit HTTPS gateway URLs for IPFS initially.

## Interaction

1. Provider manager: add by catalog URL, inspect available tools, disable/remove, explicitly restore factory provider. Do not reinsert removed providers automatically.
2. Tool manager: add by URL or select a catalog entry; deduplicate, remove, reorder, export/import local configuration. Existing launcher remains usable.
3. Homepage integration: explicit user-initiated Add to Mogwai link or share handoff, show destination and request confirmation in Mogwai before adding. No cross-origin storage hacks, no secrets in URLs, no auto-launch.
4. Tools open as separate applications, not scripts evaluated inside Mogwai. Chisel identity signing and action authorization remain separate; the Cue System is an optional independent consumer of Chisel.

## Test milestones

Validate schema, safe URLs, duplicate handling, multiple providers, deliberate empty state, removal without deleting installed tools, explicit restore, and export/import round trips. Then wire UI and browser persistence; test upgrade, offline behavior, cross-origin catalog fetch and phone/Chromebook handoff. Do not advertise the manager as deployed until UI and deployment are tested.
