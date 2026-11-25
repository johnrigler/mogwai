(function (root) {
  "use strict";
  const KEY = "mogwai.targets.v1";
  const DEFAULT = {name:"Rigler.org", fileproxy:"https://rigler.org/fileproxy/", lantern:"https://rigler.org/lantern/"};
  const loopback = host => host === "localhost" || host === "[::1]" || /^127\.(?:\d{1,3}\.){2}\d{1,3}$/.test(host);
  function endpoint(value) {
    if (!String(value || "").trim()) return "";
    const url = new URL(String(value).trim());
    if (!["https:", "http:"].includes(url.protocol) || url.username || url.password || url.search || url.hash)
      throw Error("Use an HTTP(S) service base without credentials, query or fragment.");
    if (url.protocol === "http:" && !loopback(url.hostname)) throw Error("HTTP is only supported for loopback targets; use HTTPS for remote servers.");
    if (!url.pathname.endsWith("/")) url.pathname += "/";
    return url.href;
  }
  function profile(value) {
    const name = String(value?.name || "").trim();
    if (!name || name.length > 80) throw Error("Enter a profile name (1–80 characters).");
    const fileproxy = endpoint(value.fileproxy), lantern = endpoint(value.lantern);
    if (!fileproxy && !lantern) throw Error("Enter at least one service endpoint.");
    return {name, fileproxy, lantern};
  }
  function config(value) {
    if (!Array.isArray(value?.profiles) || !value.profiles.length || value.profiles.length > 30) throw Error("Use 1–30 server profiles.");
    const profiles = value.profiles.map(profile);
    if (new Set(profiles.map(p => p.name)).size !== profiles.length) throw Error("Profile names must be unique.");
    if (!Number.isInteger(value.active) || value.active < 0 || value.active >= profiles.length) throw Error("Invalid active profile.");
    return {profiles, active:value.active};
  }
  function defaults() { return {profiles:[{...DEFAULT}],active:0}; }
  function fetchOptions(url) { return url.protocol === "http:" && loopback(url.hostname) ? {targetAddressSpace:"loopback"} : {}; }
  function lanternURL(base) {
    const url = new URL("https://johnrigler.github.io/lantern/lantern.html");
    url.searchParams.set("server", endpoint(base));
    return url.href;
  }
  async function health(base, service, fetcher = root.fetch.bind(root)) {
    if (!base) return {ok:false,message:"Not configured"};
    const url = new URL(service === "lantern" ? "health" : "ping", endpoint(base));
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetcher(url.href,{signal:controller.signal,cache:"no-store",credentials:"omit",referrerPolicy:"no-referrer",...fetchOptions(url)});
      if (!response.ok) throw Error("HTTP " + response.status);
      const body = await response.json();
      if (body?.ok !== true || (service === "lantern" && body.service !== "lantern")) throw Error("Unexpected health response");
      if (service === "lantern") {
        const games = Object.values(body.games || {}).filter(g => g?.present === true).length;
        return {ok:true,message:body.dfrotz && games ? "Available · " + games + " game(s)" : "Server online · game runtime/files not confirmed"};
      }
      return {ok:true,message:"Available"};
    } catch(error) {
      return {ok:false,message:"Not verified · " + (error.name === "AbortError" ? "timeout" : error.message)};
    } finally { clearTimeout(timeout); }
  }
  let state = defaults(), storageOK = true, serial = 0;
  try { const saved = root.localStorage.getItem(KEY); if(saved) state = config(JSON.parse(saved)); } catch { storageOK=false; }
  const active = () => state.profiles[state.active];
  function metadataURL() {
    if (!active().fileproxy) throw Error("No FileProxy configured for this target");
    return new URL("youtube-metadata", active().fileproxy).href;
  }
  root.MogwaiTargets = {endpoint, profile, config, defaults, fetchOptions, lanternURL, health, active, metadataURL};
  if (!root.document) return;
  const $ = id => root.document.getElementById(id);
  if (!$("target-select")) return;
  function note(text) { $("target-status").textContent = text; }
  function render() {
    const select = $("target-select"); select.replaceChildren();
    state.profiles.forEach((p,i) => { const option = root.document.createElement("option"); option.value=String(i); option.textContent=p.name; select.appendChild(option); });
    select.value=String(state.active);
    const p=active();
    $("target-name").value=p.name; $("target-fileproxy").value=p.fileproxy; $("target-lantern").value=p.lantern;
    $("active-target-name").textContent=p.name;
    $("target-remove").disabled=state.profiles.length===1;
  }
  async function check() {
    const token=++serial, p=active();
    $("lantern-launch").hidden=true; $("lantern-launch").removeAttribute("href");
    $("lantern-state").textContent=p.lantern?"Checking…":"Not configured";
    $("fileproxy-state").textContent=p.fileproxy?"FileProxy · Checking…":"FileProxy · Not configured";
    await Promise.all([health(p.lantern,"lantern").then(result=>{
      if(token!==serial)return;
      $("lantern-state").textContent=result.message;
      if(result.ok){$("lantern-launch").href=lanternURL(p.lantern);$("lantern-launch").hidden=false;}
    }),health(p.fileproxy,"fileproxy").then(result=>{
      if(token===serial)$("fileproxy-state").textContent="FileProxy · "+result.message;
    })]);
  }
  function apply(next) {
    state=config(next);
    try { root.localStorage.setItem(KEY,JSON.stringify(state)); storageOK=true; } catch {storageOK=false;}
    render(); note(storageOK?"Saved on this device.":"Browser storage unavailable; changes last for this window.");
    check(); root.dispatchEvent(new Event("mogwai-target-change"));
  }
  function input() {return profile({name:$("target-name").value,fileproxy:$("target-fileproxy").value,lantern:$("target-lantern").value});}
  function attempt(fn) {try{fn();}catch(error){note(error.message);}}
  $("target-select").addEventListener("change",()=>attempt(()=>apply({...state,active:Number($("target-select").value)})));
  $("target-save").addEventListener("click",()=>attempt(()=>apply({...state,profiles:state.profiles.map((p,i)=>i===state.active?input():p)})));
  $("target-add").addEventListener("click",()=>attempt(()=>apply({profiles:[...state.profiles,input()],active:state.profiles.length})));
  $("target-remove").addEventListener("click",()=>attempt(()=>apply({profiles:state.profiles.filter((_,i)=>i!==state.active),active:0})));
  $("target-export").addEventListener("click",()=>{$("target-json").value=JSON.stringify(state,null,2);});
  $("target-import").addEventListener("click",()=>attempt(()=>apply(JSON.parse($("target-json").value))));
  $("target-reset").addEventListener("click",()=>attempt(()=>apply(defaults())));
  $("check-targets").addEventListener("click",check);
  render(); if(!storageOK)note("Saved target configuration unavailable; using the default.");
  check();
})(typeof window!=="undefined"?window:globalThis);
