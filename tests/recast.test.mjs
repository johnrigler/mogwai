import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import vm from 'node:vm';
const context = { Blob, TextEncoder, Uint8Array, DataView }; vm.createContext(context);
vm.runInContext(await readFile(new URL('../tools/recast/core.js', import.meta.url), 'utf8'), context);
const C = context.MogwaiRecast;
const project = () => ({ format:C.FORMAT,width:1280,height:720,source:{name:'apocalypseNewscast.mp4'},cues:[C.emptyCue(),{...C.emptyCue(),at:8,layout:'side'},{...C.emptyCue(),at:16,layout:'desk'}] });
test('cue playback and replacement use source times, including exact boundaries', () => {
  const p=C.validate(project());
  assert.equal(C.cueAt(p.cues,7.999).index,0); assert.equal(C.cueAt(p.cues,8).index,1); assert.equal(C.cueAt(p.cues,100).index,2);
  const cues=C.upsert(p.cues,{...C.emptyCue(),at:8.02,layout:'right'}); assert.equal(cues.length,3); assert.equal(cues[1].at,8); assert.equal(cues[1].layout,'right');
});
test('layouts partition the frame without stretched or off-frame rectangles', () => {
  for (const name of Object.keys(C.layouts)) {
    const g=C.geometry(name,1280,720);
    for(const rect of Object.values(g).filter(Boolean)){const[x,y,w,h]=rect;assert(x>=0&&y>=0&&x+w<=1280&&y+h<=720);assert.equal(w%2,0);assert.equal(h%2,0);}
  }
  assert.equal(C.geometry('desk',1920,1080).video[2],1280); assert.equal(C.geometry('desk',1920,1080).video[3],720);
});
test('project validation rejects executable image URLs, invalid times, duplicate cues and unsupported shapes', () => {
  for (const patch of [{width:1279},{height:NaN},{cues:[]},{cues:[{...C.emptyCue(),at:1}]},{cues:[C.emptyCue(),C.emptyCue()]},{cues:[{...C.emptyCue(),image:'javascript:alert(1)'}]},{cues:[{...C.emptyCue(),right:{html:'x'}}]},{cues:[{...C.emptyCue(),layout:'toString'}]},{cues:[{...C.emptyCue(),layout:'constructor'}]}]) assert.throws(()=>C.validate({...project(),...patch}));
  assert.equal(C.validate(project()).source.name,'apocalypseNewscast.mp4');
});
test('browser ZIPs round-trip with standard ZIP readers and preserve UTF-8 text and renderer bytes', async () => {
  const text='Instructions: café → next\n', python=await readFile(new URL('../tools/recast/render.py', import.meta.url),'utf8');
  const bytes=new Uint8Array(await C.zip([{name:'project.json',data:text},{name:'render.py',data:python}]).arrayBuffer());
  const path=join(tmpdir(),'recast-zip-'+process.pid+'.zip');await writeFile(path,bytes);
  const value=JSON.parse(execFileSync('python3',['-c','import zipfile,sys,json;z=zipfile.ZipFile(sys.argv[1]);print(json.dumps({n:z.read(n).decode() for n in z.namelist()}))',path],{encoding:'utf8'}));
  assert.equal(value['project.json'],text);assert.equal(value['render.py'],python);
  assert.throws(()=>C.zip([{name:'../bad',data:'x'}]));
});
