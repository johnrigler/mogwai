"use strict";
const CACHE = "mogwai-app-0.1.0";
const SHELL = ["./", "index.html", "app.css", "core.js", "app.js", "manifest.webmanifest", "icon.svg", "icon-192.png", "icon-512.png"];
const scope = self.registration.scope;
const shellURLs = new Set(SHELL.map(path => new URL(path, scope).href));

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith("mogwai-app-") && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  if (event.request.method === "POST" && url.href === new URL("share", scope).href) {
    event.respondWith((async () => {
      try {
        const form = await event.request.formData();
        const share = {};
        for (const key of ["title", "text", "url"]) {
          const value = form.get(key);
          if (value !== null && typeof value !== "string") throw new Error("Only links and text are supported");
          share[key] = value || "";
        }
        if (new TextEncoder().encode(JSON.stringify(share)).byteLength > 70000) throw new Error("Shared text is too large");
        // The fragment stays in the browser, including during offline redirects.
        return Response.redirect(scope + "#share=" + encodeURIComponent(JSON.stringify(share)), 303);
      } catch (error) {
        return Response.redirect(scope + "#share-error=" + encodeURIComponent(error.message), 303);
      }
    })());
    return;
  }
  // Cache this app shell only. Chisel and other sites keep their own behavior.
  if (event.request.method !== "GET" || !shellURLs.has(url.origin + url.pathname)) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const response = await fetch(event.request);
      if (response.ok && !url.search) await cache.put(url.origin + url.pathname, response.clone());
      return response;
    } catch (error) {
      const saved = await cache.match(url.origin + url.pathname);
      if (saved) return saved;
      throw error;
    }
  })());
});
