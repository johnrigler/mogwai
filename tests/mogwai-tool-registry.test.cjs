const test=require("node:test");
const assert=require("node:assert/strict");
const R=require("../app/tool-registry.js");
const fixture={schema:R.SCHEMA,name:"Example",tools:[{id:"cue",name:"Cue System",url:"https://example.test/cue/",recommended:true}]};
const store=()=>{const m=new Map();return {getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,v)};};
test("catalog validates HTTPS launch URLs and unique IDs",()=>{
  assert.equal(R.catalog(fixture).tools[0].id,"cue");
  for(const url of ["javascript:alert(1)","http://example.test/","https://user:pass@example.test/"]) assert.throws(()=>R.catalog({...fixture,tools:[{...fixture.tools[0],url}]}));
  assert.throws(()=>R.catalog({...fixture,tools:[fixture.tools[0],fixture.tools[0]]}));
});
test("first install is seeded; deliberate empty registry persists",()=>{
  const storage=store();
  assert.equal(R.load(storage).providers[0].url,R.FACTORY_URL);
  R.save(storage,R.removeProvider(R.load(storage),R.FACTORY_URL));
  assert.deepEqual(R.load(storage).providers,[]);
  assert.equal(R.restoreFactory(R.load(storage)).providers[0].url,R.FACTORY_URL);
});
test("multiple providers and installed tool snapshots survive provider removal",()=>{
  const key="https://example.test/catalog.json";
  let s=R.addProvider(R.defaults(),{url:key,name:"Other",enabled:true});
  s=R.addTool(s,fixture.tools[0],key);
  s=R.addTool(s,fixture.tools[0],R.FACTORY_URL);
  assert.equal(s.tools.length,2);
  assert.throws(()=>R.addTool(s,fixture.tools[0],key));
  s=R.removeProvider(s,key);
  assert.equal(s.providers.length,1);
  assert.equal(s.tools.length,2);
  assert.throws(()=>R.addTool(s,{...fixture.tools[0],id:"other"},key));
  assert.equal(R.removeTool(s,"cue",key).tools.length,1);
  assert.deepEqual(R.config(JSON.parse(JSON.stringify(s))),s);
});
test("corrupt saved data is not silently replaced with defaults",()=>{
  const storage=store();storage.setItem(R.KEY,"broken");
  assert.throws(()=>R.load(storage));
  assert.equal(storage.getItem(R.KEY),"broken");
});
