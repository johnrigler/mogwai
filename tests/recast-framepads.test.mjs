import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
const require = createRequire(process.env.RECAST_TEST_DEPS ? process.env.RECAST_TEST_DEPS + '/package.json' : import.meta.url);
let JSDOM;
try { ({ JSDOM } = require('jsdom')); } catch { /* Installed in CI. */ }
const root = new URL('../tools/recast/', import.meta.url), tick = () => new Promise(resolve => setImmediate(resolve));
const frame = 1001/30000;

async function fixture({detect=true}={}) {
  const dom = new JSDOM(await readFile(new URL('index.html', root),'utf8'),{url:'https://example.test/',runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window, $=id=>w.document.getElementById(id), timers=new Map(); let nextTimer=1, loads=0, paused=true, clock=0;
  Object.defineProperty(w.performance,'now',{value:()=>clock});
  Object.assign(w,{TextEncoder,Blob,Uint8Array,DataView});
  w.URL.createObjectURL=()=> 'blob:private'; w.URL.revokeObjectURL=()=>{};
  const context={save(){},restore(){},beginPath(){},rect(){},clip(){},fillRect(){},clearRect(){},fillText(){},drawImage(){},measureText:t=>({width:t.length*14})};
  w.HTMLCanvasElement.prototype.getContext=()=>context;
  Object.defineProperty(w.HTMLMediaElement.prototype,'paused',{get:()=>paused});
  w.HTMLMediaElement.prototype.pause=function(){paused=true;this.dispatchEvent(new w.Event('pause'));};
  w.HTMLMediaElement.prototype.play=async function(){paused=false;this.dispatchEvent(new w.Event('play'));};
  w.HTMLMediaElement.prototype.load=function(){loads++;Object.defineProperties(this,{duration:{value:10,configurable:true},videoWidth:{value:480,configurable:true},videoHeight:{value:360,configurable:true}});this.dispatchEvent(new w.Event('loadedmetadata'));};
  for(const file of ['core.js','timing.js','storage.js','render-source.js']) w.eval(await readFile(new URL(file,root),'utf8'));
  w.MogwaiFrameTiming={...w.MogwaiFrameTiming,read:async()=>{if(!detect) throw new Error('Unsupported fixture');return {times:Float64Array.from({length:300},(_,i)=>i*frame),fps:1/frame,origin:'mp4'};}};
  w.setTimeout=(fn,delay)=>{const id=nextTimer++;timers.set(id,{fn,delay});return id;};
  w.clearTimeout=id=>timers.delete(id);
  w.eval(await readFile(new URL('recast.js',root),'utf8'));
  Object.defineProperty($('source'),'files',{value:[{name:'private.mp4'}]});$('source').dispatchEvent(new w.Event('change'));await tick();
  const app=w.MOGWAI_RECAST,C=w.MogwaiRecast;
  await app.loadProject({...app.state.project,cues:[C.emptyCue(),{...C.emptyCue(),at:10*frame,layout:'side',right:'Selected cue'},{...C.emptyCue(),at:30*frame,layout:'desk'}]});
  function pointer(target,type,id=1){const event=new w.MouseEvent(type,{button:0,bubbles:true,cancelable:true});Object.defineProperty(event,'pointerId',{value:id});target.dispatchEvent(event);}
  function fire(){assert.equal(timers.size,1);const [id,{fn,delay}]=timers.entries().next().value;timers.delete(id);clock+=delay;fn();return delay;}
  return {dom,w,$,app,pointer,fire,timers,loads:()=>loads};
}

test('thumb taps move the selected cue by real source frames without adding cues or losing selection/drafts', {skip:!JSDOM}, async()=>{
  const f=await fixture(),{dom,w,$,app}=f;
  try {
    $('cues').children[1].querySelector('button').click();
    assert.equal(app.state.selected,1);assert.equal($('video').paused,true);
    $('rightText').value='Draft stays here';$('rightText').dispatchEvent(new w.Event('input'));
    $('cueLater').click();await tick();
    assert.equal(app.state.project.cues[1].at,11*frame);assert.equal(app.state.project.cues.length,3);
    assert.equal(app.state.selected,1);assert.equal($('cues').children[1].querySelector('button').getAttribute('aria-pressed'),'true');
    assert.equal($('rightText').value,'Draft stays here');assert.equal(app.state.project.cues[1].right,'Selected cue');
    assert($('video').currentTime>11*frame && $('video').currentTime<12*frame);
    $('video').dispatchEvent(new w.Event('seeked'));assert.equal(app.state.selected,1);assert.equal(app.state.draft.layout,'side');
    $('cueEarlier').click();assert.equal(app.state.project.cues[1].at,10*frame);assert.equal(f.loads(),1);
    $('saveCue').click();await tick();assert.equal(app.state.project.cues.length,3);assert.equal(app.state.project.cues[1].right,'Draft stays here');
    const reopened=JSON.parse(JSON.stringify(app.state.project));await app.loadProject(reopened);app.selectCue(1);
    assert.equal(app.state.project.cues[1].at,10*frame);assert.equal($('cueLater').disabled,false);
  } finally {await tick();dom.window.close();}
});

test('held pads repeat, suppress a synthetic second tap, and stop on release/cancel/blur or playback', {skip:!JSDOM}, async()=>{
  const f=await fixture(),{dom,w,$,app,pointer,fire,timers}=f;
  try {
    app.selectCue(1);const later=$('cueLater'),time=()=>app.state.project.cues[1].at;
    pointer(later,'pointerdown');assert.equal(time(),11*frame);assert.equal(fire(),300);assert.equal(time(),12*frame);assert.equal(fire(),80);assert.equal(time(),13*frame);
    pointer(w,'pointerup',2);assert.equal(timers.size,1);pointer(w,'pointerup');assert.equal(timers.size,0);
    later.dispatchEvent(new w.MouseEvent('click',{bubbles:true,detail:1}));assert.equal(time(),13*frame);
    for(const reason of ['pointercancel','pointerleave','lostpointercapture']){
      pointer(later,'pointerdown');pointer(later,reason);assert.equal(timers.size,0,reason);
    }
    pointer(later,'pointerdown');w.dispatchEvent(new w.Event('blur'));assert.equal(timers.size,0);
    pointer(later,'pointerdown');Object.defineProperty(w.document,'hidden',{value:true,configurable:true});w.document.dispatchEvent(new w.Event('visibilitychange'));assert.equal(timers.size,0);
    pointer(later,'pointerdown');await $('video').play();assert.equal(timers.size,0);assert.equal($('video').paused,false);
    assert.equal(f.loads(),1);
  } finally {await tick();dom.window.close();}
});

test('rapid thumb taps stay at one frame, and long-press defaults are canceled only on the pads', {skip:!JSDOM}, async()=>{
  const f=await fixture(),{dom,w,$,app,pointer,timers}=f;
  try {
    app.selectCue(1);const later=$('cueLater');
    for(let i=0;i<6;i++){
      pointer(later,'pointerdown');
      for(const type of ['touchstart','contextmenu','selectstart','dragstart']){
        const event=new w.Event(type,{bubbles:true,cancelable:true});
        assert.equal(later.querySelector('span').dispatchEvent(event),false,type);assert.equal(event.defaultPrevented,true,type);
      }
      pointer(later,'pointerup');later.dispatchEvent(new w.MouseEvent('click',{bubbles:true,detail:1}));
      assert.equal(timers.size,0);assert.equal(app.state.project.cues[1].at,(11+i)*frame);
    }
    const outside=new w.Event('contextmenu',{bubbles:true,cancelable:true});
    assert.equal($('rightText').dispatchEvent(outside),true);assert.equal(outside.defaultPrevented,false);
  } finally {await tick();dom.window.close();}
});

for(const direction of [-1,1])test('a held pad accelerates after one second and still stops at its neighbor: '+direction, {skip:!JSDOM}, async()=>{
  const f=await fixture(),{dom,$,app,pointer,fire,timers}=f;
  try {
    const C=f.w.MogwaiRecast;
    await app.loadProject({...app.state.project,cues:[C.emptyCue(),{...C.emptyCue(),at:60*frame},{...C.emptyCue(),at:150*frame}]});
    app.selectCue(1);const pad=$(direction===1?'cueLater':'cueEarlier');pointer(pad,'pointerdown');
    assert.equal(app.state.project.cues[1].at,(60+direction)*frame);
    assert.equal(fire(),300);assert.equal(fire(),80);
    const delays=[];for(let i=0;i<11;i++)delays.push(fire());
    assert(delays.includes(80));assert.equal(delays.at(-1),30);
    while(timers.size)fire();
    assert.equal(app.state.project.cues[1].at,(direction===1?149:1)*frame);assert.equal(pad.disabled,true);
    pointer(pad,'pointerup');assert.equal(timers.size,0);
  } finally {await tick();dom.window.close();}
});

test('first cue is anchored, neighbors cannot cross, and unsupported sources need an explicit frame rate', {skip:!JSDOM}, async()=>{
  const f=await fixture({detect:false}),{dom,w,$,app}=f;
  try {
    app.selectCue(1);assert.equal($('cueLater').disabled,true);assert.match($('nudgeHint').textContent,/Select the source frame rate/);
    $('frameRate').value='30000/1001';$('frameRate').dispatchEvent(new w.Event('change'));
    assert.equal($('cueLater').disabled,false);assert.equal(app.state.project.source.frameRate,'30000/1001');
    app.selectCue(0);assert.equal($('cueEarlier').disabled,true);assert.equal($('cueLater').disabled,true);assert.equal(app.nudgeCue(1),false);
    app.selectCue(1);while(app.nudgeCue(-1)){}assert.equal(app.state.project.cues[1].at,frame);assert.equal($('cueEarlier').disabled,true);
    while(app.nudgeCue(1)){}assert(Math.abs(app.state.project.cues[1].at-29*frame)<1e-12);assert.equal($('cueLater').disabled,true);
    assert.equal(app.state.project.cues.length,3);
  } finally {await tick();dom.window.close();}
});
