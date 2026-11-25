(function(root){
  "use strict";
  const KEY="mogwai.tool-registry.v1";
  const FACTORY_URL="https://rigler.org/mogwai.json";
  const SCHEMA="mogwai.tool-catalog.v1";
  function label(v,max=120){
    if(typeof v!=="string" || !v.trim() || v.trim().length>max) throw Error("Invalid label");
    return v.trim();
  }
  function url(v){
    if(typeof v!=="string" || v.length>2048) throw Error("Invalid URL");
    const u=new URL(v);
    if(u.protocol!=="https:" || u.username || u.password) throw Error("Use an HTTPS URL without credentials");
    return u.href;
  }
  function providerURL(v){
    const u=new URL(url(v));
    if(u.hash) throw Error("Catalog URL cannot contain a fragment");
    return u.href;
  }
  function tool(v){
    if(!v || typeof v.id!=="string" || !/^[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}$/.test(v.id)) throw Error("Invalid tool ID");
    if(v.description!==undefined && (typeof v.description!=="string" || v.description.length>500)) throw Error("Invalid description");
    if(v.recommended!==undefined && typeof v.recommended!=="boolean") throw Error("Invalid recommendation");
    return {id:v.id,name:label(v.name),url:url(v.url),description:v.description||"",recommended:v.recommended===true};
  }
  function unique(items,key){
    if(new Set(items.map(key)).size!==items.length) throw Error("Duplicate entry");
    return items;
  }
  function catalog(v){
    if(!v || v.schema!==SCHEMA || !Array.isArray(v.tools) || v.tools.length>200) throw Error("Invalid tool catalog");
    return {schema:SCHEMA,name:label(v.name),tools:unique(v.tools.map(tool),t=>t.id)};
  }
  function provider(v){
    if(!v || typeof v.enabled!=="boolean") throw Error("Invalid provider");
    return {url:providerURL(v.url),name:label(v.name),enabled:v.enabled};
  }
  function installed(v){
    return {...tool(v),provider:v.provider===null?null:providerURL(v.provider)};
  }
  function config(v){
    if(!v || v.version!==1 || !Array.isArray(v.providers) || !Array.isArray(v.tools) || v.providers.length>30 || v.tools.length>200) throw Error("Invalid registry");
    return {version:1,providers:unique(v.providers.map(provider),p=>p.url),tools:unique(v.tools.map(installed),t=>JSON.stringify([t.provider,t.id]))};
  }
  function defaults(){return {version:1,providers:[{url:FACTORY_URL,name:"Rigler.org",enabled:true}],tools:[]};}
  function load(storage){
    const raw=storage.getItem(KEY);
    return raw===null?defaults():config(JSON.parse(raw));
  }
  function save(storage,state){const next=config(state);storage.setItem(KEY,JSON.stringify(next));return next;}
  function addProvider(state,value){const s=config(state);return config({...s,providers:[...s.providers,provider(value)]});}
  function removeProvider(state,value){const s=config(state),key=providerURL(value);return config({...s,providers:s.providers.filter(p=>p.url!==key)});}
  function restoreFactory(state){
    const s=config(state),p=defaults().providers[0];
    return config({...s,providers:s.providers.some(x=>x.url===p.url)?s.providers.map(x=>x.url===p.url?p:x):[...s.providers,p]});
  }
  function addTool(state,value,source=null){
    const s=config(state);
    const key=source===null?null:providerURL(source);
    if(key!==null && !s.providers.some(p=>p.url===key && p.enabled)) throw Error("Provider is not enabled");
    return config({...s,tools:[...s.tools,{...tool(value),provider:key}]});
  }
  function removeTool(state,id,source=null){
    const s=config(state),key=source===null?null:providerURL(source);
    return config({...s,tools:s.tools.filter(t=>t.id!==id || t.provider!==key)});
  }
  const api={KEY,FACTORY_URL,SCHEMA,url,providerURL,tool,catalog,config,defaults,load,save,addProvider,removeProvider,restoreFactory,addTool,removeTool};
  if(typeof module!=="undefined" && module.exports) module.exports=api;
  else root.MogwaiToolRegistry=api;
})(typeof window!=="undefined"?window:globalThis);
