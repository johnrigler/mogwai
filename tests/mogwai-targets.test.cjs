const assert = require("node:assert/strict");
const test = require("node:test");
const vm = require("node:vm");
const fs = require("node:fs");
const path = require("node:path");
const context = vm.createContext({URL, AbortController, setTimeout, clearTimeout});
vm.runInContext(fs.readFileSync(path.join(__dirname,"../app/targets.js"),"utf8"),context);
const T=context.MogwaiTargets;
test("target endpoints allow only HTTPS or loopback HTTP, without credentials",()=>{
  for(const url of ["http://localhost:7788","http://127.0.0.1:7788","http://[::1]:7788","https://example.test/lantern"]) assert(T.endpoint(url).endsWith("/"));
  for(const url of ["http://example.test","http://localhost.example.test","https://user:pass@example.test/","https://example.test/?token=x","javascript:alert(1)"]) assert.throws(()=>T.endpoint(url));
});
test("multiple profiles are validated, including local services and unique names",()=>{
  const c=T.config({active:1,profiles:[T.defaults().profiles[0],{name:"Local",lantern:"http://127.0.0.1:7788"}]});
  assert.equal(c.profiles[c.active].lantern,"http://127.0.0.1:7788/");
  assert.throws(()=>T.config({active:0,profiles:[c.profiles[0],c.profiles[0]]}));
  assert.equal(new URL(T.lanternURL(c.profiles[1].lantern)).searchParams.get("server"),c.profiles[1].lantern);
});
test("Lantern discovery requires an actual Lantern response",async()=>{
  const base="https://rigler.org/lantern/";
  let url;
  const healthy=await T.health(base,"lantern",async u=>{url=u;return {ok:true,json:async()=>({ok:true,service:"lantern",dfrotz:"/bin/dfrotz",games:{zork1:{present:true}}})};});
  assert.equal(url,base+"health");assert.equal(healthy.ok,true);assert.match(healthy.message,/1 game/);
  assert.equal((await T.health(base,"lantern",async()=>({ok:true,json:async()=>({ok:true,service:"other"})}))).ok,false);
  assert.equal((await T.health(base,"lantern",async()=>({ok:false,status:503}))).ok,false);
});
