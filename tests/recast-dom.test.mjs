import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
const require = createRequire(process.env.RECAST_TEST_DEPS ? process.env.RECAST_TEST_DEPS + '/package.json' : import.meta.url);
let JSDOM;
try { ({ JSDOM } = require('jsdom')); } catch { /* Optional local dependency; installed in CI. */ }
const root = new URL('../tools/recast/', import.meta.url), tick = () => new Promise(resolve => setImmediate(resolve));

test('layout switches preserve one playing video, cues follow the playhead, and export excludes source media', { skip: !JSDOM }, async () => {
  const dom = new JSDOM(await readFile(new URL('index.html', root), 'utf8'), { url:'https://example.test/recast/',runScripts:'outside-only',pretendToBeVisual:true });
  const w=dom.window, $=id=>w.document.getElementById(id), calls={loads:0,plays:0,fetches:0};
  try {
    Object.assign(w,{TextEncoder,TextDecoder,Blob,Uint8Array,DataView});
    w.URL.createObjectURL=()=> 'blob:private-fixture';w.URL.revokeObjectURL=()=>{};
    w.fetch=()=>{calls.fetches++;throw new Error('No network request is expected.');};
    const context={save(){},restore(){},beginPath(){},rect(){},clip(){},fillRect(){},clearRect(){},fillText(){},drawImage(){},measureText:t=>({width:t.length*14})};
    w.HTMLCanvasElement.prototype.getContext=()=>context;
    w.HTMLCanvasElement.prototype.toBlob=function(callback){callback(new Blob([new Uint8Array([137,80,78,71])],{type:'image/png'}));};
    let paused=true;Object.defineProperty(w.HTMLMediaElement.prototype,'paused',{get:()=>paused});
    w.HTMLMediaElement.prototype.pause=function(){paused=true;this.dispatchEvent(new w.Event('pause'));};
    w.HTMLMediaElement.prototype.play=async function(){calls.plays++;paused=false;this.dispatchEvent(new w.Event('play'));};
    w.HTMLMediaElement.prototype.load=function(){calls.loads++;Object.defineProperties(this,{duration:{value:98.22,configurable:true},videoWidth:{value:480,configurable:true},videoHeight:{value:360,configurable:true}});this.dispatchEvent(new w.Event('loadedmetadata'));};
    for(const file of ['core.js','render-source.js','recast.js'])w.eval(await readFile(new URL(file,root),'utf8'));
    await tick();
    const app=w.MOGWAI_RECAST, video=$('video');
    Object.defineProperty($('source'),'files',{value:[{name:'apocalypseNewscast.mp4'}]});$('source').dispatchEvent(new w.Event('change'));await tick();
    video.currentTime=10.5;await video.play();const src=video.src;
    w.document.querySelector('[data-layout=side]').click();await tick();
    assert.equal($('video'),video);assert.equal(video.src,src);assert.equal(video.currentTime,10.5);assert.equal(video.paused,false);assert.equal(calls.loads,1);assert.equal(calls.plays,1);
    $('rightText').value='<img src=x onerror=bad>\nInstruction two';$('rightText').dispatchEvent(new w.Event('input'));$('saveCue').click();await tick();
    assert.equal(app.state.project.cues[1].right,$('rightText').value);assert.equal(w.document.querySelector('img'),null);
    video.currentTime=20.25;w.document.querySelector('[data-layout=desk]').click();await tick();
    video.currentTime=0;video.dispatchEvent(new w.Event('seeked'));await tick();assert.equal(app.state.draft.layout,'full');
    video.currentTime=11;video.dispatchEvent(new w.Event('timeupdate'));await tick();assert.equal(app.state.draft.layout,'side');
    const zip=await app.exportPackage();assert(zip.size>100);assert.equal(calls.fetches,0);
    $('record').checked=false;video.currentTime=30;w.document.querySelector('[data-layout=right]').click();await tick();
    assert.equal(app.state.project.cues.length,3);assert.equal(video.currentTime,30);assert.equal(video.paused,false);
    Object.defineProperties($('stage'),{clientWidth:{value:360,configurable:true},clientHeight:{value:640,configurable:true}});
    w.dispatchEvent(new w.Event('resize'));assert.equal(parseFloat($('overlay').style.width),360);assert.equal(parseFloat($('overlay').style.height),202.5);
    assert.equal(calls.loads,1);assert.equal(calls.plays,1);
  } finally { dom.window.close(); }
});
