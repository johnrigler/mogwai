import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import vm from 'node:vm';
const context={Blob,Uint8Array,DataView,Float64Array};vm.createContext(context);
vm.runInContext(await readFile(new URL('../tools/recast/timing.js',import.meta.url),'utf8'),context);
const T=context.MogwaiFrameTiming;
let ffmpeg=false;try{execFileSync('ffmpeg',['-version'],{stdio:'ignore'});execFileSync('ffprobe',['-version'],{stdio:'ignore'});ffmpeg=true;}catch{}

test('source-frame movement handles fractional and variable timing, neighbors and the end of the video',()=>{
  const step=1001/30000, timing=T.manual('30000/1001'), cues=[{at:0},{at:10*step},{at:12*step}];
  assert(Math.abs(T.move(cues,1,-1,timing,1).time-9*step)<1e-12);
  assert(Math.abs(T.move(cues,1,1,timing,1).time-11*step)<1e-12);
  assert.equal(T.move(cues,0,1,timing,1),null);assert.equal(T.move([{at:0},{at:step}],1,-1,timing,1),null);
  assert.equal(T.move([{at:0},{at:11*step},{at:12*step}],1,1,timing,1),null);
  assert.equal(T.move([{at:0},{at:29*step}],1,1,timing,30*step),null);
  const variable={times:Float64Array.from([0,.04,.08,.16,.2]),fps:null};
  assert.equal(T.move([{at:0},{at:.08}],1,1,variable,.24).time,.16);
  assert.equal(T.move([{at:0},{at:.2}],1,1,variable,.24),null);
  assert.equal(T.floor(variable,.15),.08);assert.equal(T.indexAt(variable,.08000000001),2);
  assert.equal(T.previewTime(variable,.08,.24),.12);
  for(const rate of ['0','1/0','Infinity','-2','241','29.97x'])assert.throws(()=>T.manual(rate));
});

for(const variable of [false,true])test('MP4 '+(variable?'variable':'fractional constant')+' presentation frames match ffprobe, including reordered H.264 and edit offsets',{skip:!ffmpeg},async()=>{
  const folder=await mkdtemp(join(tmpdir(),'recast-timing-'));
  try{
    const file=join(folder,'source.mp4');
    const args=['-v','error','-f','lavfi','-i','testsrc2=s=160x120:r=30000/1001:d=1'];
    if(variable)args.push('-vf',"select='not(mod(n,3))+eq(mod(n,10),0)'",'-fps_mode','vfr');
    args.push('-c:v','libx264','-bf','3','-threads','1','-y',file);
    execFileSync('ffmpeg',args);
    const input=new Blob([await readFile(file)]),requested=[];
    const indexed=await T.read({size:input.size,slice(start,end){requested.push(end-start);return input.slice(start,end);}});
    const probe=JSON.parse(execFileSync('ffprobe',['-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',file],{encoding:'utf8'}));
    const expected=probe.frames.map(frame=>Number(frame.best_effort_timestamp_time));
    assert.equal(indexed.times.length,expected.length);
    expected.forEach((time,i)=>assert(Math.abs(indexed.times[i]-time)<.000001,'frame '+i));
    assert.equal(indexed.variable,variable);
    if(!variable)assert.equal(indexed.fps,30000/1001);
    assert(requested.reduce((a,b)=>a+b,0)<input.size/2,'only headers and timing index are read');
    const moovBytes=await input.slice(input.size-requested.at(-1)).arrayBuffer();
    // A truncated timing box must fail closed rather than supply a guessed rate.
    assert.throws(()=>T.parseMoov(moovBytes.slice(0,20)));
  }finally{await rm(folder,{recursive:true,force:true});}
});

test('unsupported and malformed media require manual source timing',async()=>{
  await assert.rejects(()=>T.read(new Blob(['not a movie'])));
  await assert.rejects(()=>T.read({name:'only-a-name.mp4'}));
  assert.throws(()=>T.parseMoov(new Uint8Array([0,0,0,100,109,111,111,118]).buffer));
});
