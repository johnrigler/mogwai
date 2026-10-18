import assert from 'node:assert/strict';
import { readFile, mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import vm from 'node:vm';
const context={Blob,Uint8Array,TextEncoder,AbortController,URL,setTimeout,clearTimeout,fetch,btoa};vm.createContext(context);
vm.runInContext(await readFile(new URL('../tools/recast/storage.js',import.meta.url),'utf8'),context);
const S=context.MogwaiRecastStorage;
const date=(year,month,day)=>new Date(year,month-1,day,12);

function fakeDirectory(name) {
  const dirs=new Map(),files=new Map(),calls=[];
  const missing=()=>Object.assign(new Error('Missing'),{name:'NotFoundError'});
  return {name,dirs,files,calls,async getDirectoryHandle(key,options={}){
    calls.push({name:key,create:Boolean(options.create)});
    if(!dirs.has(key)){if(!options.create)throw missing();dirs.set(key,fakeDirectory(key));}return dirs.get(key);
  },async getFileHandle(key,options={}){
    if(!files.has(key)){if(!options.create)throw missing();files.set(key,null);}
    return {async createWritable(){let pending;return {async write(data){pending=typeof data==='string'?Buffer.from(data):Buffer.from(data);},async close(){files.set(key,pending);},async abort(){}};}};
  }};
}

test('weekly defaults use local ISO week/year, including all 53 weeks and the New Year boundary',()=>{
  for(const [day,year,week] of [[date(2026,10,17),2026,'42'],[date(2026,12,31),2026,'53'],[date(2027,1,1),2026,'53'],[date(2027,1,4),2027,'01'],[date(2024,12,30),2025,'01']]){
    const actual=S.defaults(day);assert.equal(actual.year,year);assert.equal(actual.folder,week);assert.equal(actual.directory,'daisy_'+year);assert.equal(actual.root,'daisy'+year);
  }
});

test('native folder access checks/creates the week, respects an exact working folder and preserves existing files',async()=>{
  const root=fakeDirectory('daisy_2026'),target=await S.directory(root,date(2026,10,17));
  assert.equal(target.label,'daisy_2026/42');assert.deepEqual(root.calls,[{name:'42',create:false},{name:'42',create:true}]);
  await target.write('snapshot/project.json','café\n');await target.write('snapshot/overlays/000.png',new Uint8Array([137,80,78,71,0,255]));
  const saved=root.dirs.get('42').dirs.get('snapshot');assert.equal(saved.files.get('project.json').toString(),'café\n');assert.deepEqual([...saved.dirs.get('overlays').files.get('000.png')],[137,80,78,71,0,255]);
  await assert.rejects(()=>target.write('snapshot/project.json','overwrite'),/already exists/);
  assert.equal(saved.files.get('project.json').toString(),'café\n');
  root.calls.length=0;await S.directory(root,date(2026,10,17));assert.deepEqual(root.calls,[{name:'42',create:false}]);
  const exact=fakeDirectory('42'),other=await S.directory(exact,date(2026,10,17));await other.write('p.json','x');assert.equal(exact.files.get('p.json').toString(),'x');assert.equal(exact.dirs.size,0);
  await assert.rejects(()=>S.directory(fakeDirectory('daisy_2025'),date(2026,10,17)),/daisy_2026/);
});

test('FileProxy writes real UTF-8/binary files beneath the selected week, uses the token header and refuses overwrites',async()=>{
  const folder=await mkdtemp(join(tmpdir(),'recast-fp-')),requests=[];
  const server=createServer(async(req,res)=>{
    let body='';for await(const chunk of req)body+=chunk;requests.push({url:req.url,method:req.method,token:req.headers['x-fileproxy-token'],body});
    res.setHeader('Content-Type','application/json');
    if(req.url==='/base/v1/health'){res.end(JSON.stringify({ok:true,service:'fileproxy',version:1,roots:['daisy2026']}));return;}
    if(req.url!=='/base/v1/put'||req.headers['x-fileproxy-token']!=='local-test-token'){res.writeHead(403).end(JSON.stringify({ok:false,error:'Write token required'}));return;}
    const value=JSON.parse(body),file=join(folder,value.path);await mkdir(join(file,'..'),{recursive:true});
    try{await writeFile(file,value.text!==undefined?Buffer.from(value.text):Buffer.from(value.base64,'base64'),{flag:'wx'});res.end(JSON.stringify({ok:true,path:value.path}));}
    catch{res.writeHead(409).end(JSON.stringify({ok:false,error:'File exists'}));}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const url='http://127.0.0.1:'+server.address().port+'/base/';
  try{
    const target=await S.proxy({url,root:'daisy2026',folder:'42',token:'local-test-token'});
    assert.equal(target.label,'daisy2026:42');
    await target.write('project.json','{"text":"café → next"}\n');await target.write('bundle/overlays/000.png',new Uint8Array([0,255,137,80,78,71]));
    assert.equal(await readFile(join(folder,'42/project.json'),'utf8'),'{"text":"café → next"}\n');assert.deepEqual([...await readFile(join(folder,'42/bundle/overlays/000.png'))],[0,255,137,80,78,71]);
    assert.equal(requests[0].token,undefined);assert(requests.slice(1).every(req=>req.token==='local-test-token'&&JSON.parse(req.body).overwrite===false));
    assert(requests.every(req=>!req.url.includes('local-test-token')));
    await assert.rejects(()=>target.write('project.json','other'),/File exists/);
    await assert.rejects(()=>S.proxy({url,root:'unknown',token:'local-test-token'}),/not registered/);
    const before=requests.length;await assert.rejects(()=>target.write('huge.png',new Uint8Array(10*1024*1024)),/12 MiB/);assert.equal(requests.length,before);
    await assert.rejects(()=>S.proxy({url,root:'daisy2026',folder:'../outside',token:'local-test-token'}),/relative/);
    await assert.rejects(()=>S.proxy({url:'http://example.test',root:'daisy2026',token:'secret'}),/HTTPS/);
    await assert.rejects(()=>S.proxy({url:'https://user:secret@example.test',root:'daisy2026',token:'secret'}),/HTTPS/);
  }finally{await new Promise(resolve=>server.close(resolve));await rm(folder,{recursive:true,force:true});}
});

test('snapshot names are whitespace-free and distinct; partial saves report their progress without retrying',async()=>{
  const day=date(2026,10,17),a=S.snapshot('some video.mp4',day),b=S.snapshot('some video.mp4',day);assert.notEqual(a,b);assert.match(a,/^some-video-recast-[A-Za-z0-9-]+$/);
  const written=[],target={label:'daisy2026:42',async write(name){written.push(name);if(written.length===2)throw new Error('Disk full');}};
  await assert.rejects(()=>S.bundle(target,'render',[{name:'project.json',data:'x'},{name:'render.py',data:'y'},{name:'overlays/000.png',data:'z'}]),/1\/3 files.*Disk full/);
  assert.deepEqual(written,['render/project.json','render/render.py']);
  for(const invalid of ['/root/file','../escape','x/../escape','x//file','a file','x\\file','C:folder','x/'])assert.throws(()=>S.path(invalid));
});
