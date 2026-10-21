// Run with: node tests/directory-refresh.mjs (no packages required).
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source = readFileSync(new URL('../cruff/directory.js', import.meta.url), 'utf8');
function browser({protocol='http:', enabled=true, stamp='original'}={}) {
  let timer, reloads=0, calls=0, responseStamp=stamp, failure=false, options;
  const refresh={checked:true, dataset:{stamp}, addEventListener(type,handler){this[type]=handler;}};
  const storage=new Map(enabled ? [] : [['sbshell-refresh:/42/','off']]);
  const localStorage={getItem:key=>storage.get(key), setItem:(key,value)=>storage.set(key,value)};
  const location={href:protocol==='file:' ? 'file:///archive/42/index.html' : 'http://localhost/42/?view=week', pathname:'/42/', protocol, reload(){reloads++;}};
  vm.runInNewContext(source,{
    document:{getElementById:id=>id==='sb-directory' ? {querySelectorAll:()=>[]} : id==='auto-refresh' ? refresh : null},
    location, localStorage, sessionStorage:{getItem:()=>null,setItem(){}}, URL, AbortController,
    setTimeout(callback,delay){timer={callback,delay};return timer;},
    clearTimeout(){timer=null;},
    async fetch(url,request){
      calls++; options=request;
      assert.equal(url.searchParams.get('view'),'week');
      assert.equal(url.searchParams.get('sb-refresh'),'1');
      if(failure) throw new Error('server unavailable');
      return {ok:true,json:async()=>({stamp:responseStamp})};
    }
  });
  return {
    refresh,
    get timer(){return timer;}, get reloads(){return reloads;}, get calls(){return calls;},
    get options(){return options;},
    change(stamp){responseStamp=stamp;}, fail(){failure=true;}
  };
}
const page=browser();
assert.equal(page.timer.delay,10000);
await page.timer.callback();
assert.equal(page.calls,1);
assert.equal(page.reloads,0,'An unchanged semaphore must preserve the page.');
assert.equal(page.options.cache,'no-store');
page.change('modified');
await page.timer.callback();
assert.equal(page.reloads,1,'A changed semaphore must reload the page.');
page.refresh.checked=false;
page.refresh.change();
assert.equal(page.timer,null,'Turning refresh off must cancel its timer.');
const offline=browser();
offline.fail();
await offline.timer.callback();
assert.equal(offline.reloads,0,'A stopped local server must leave the current page open.');
assert.equal(offline.timer.delay,10000,'A failed check must retry.');
assert.equal(browser({enabled:false}).timer,null,'Remember the refresh-off preference.');
assert.equal(browser({protocol:'file:'}).timer,null,'Saved offline HTML must not poll a server.');
console.log('Refresh checks passed: stable/changed semaphore, polling interval, no cache, pause preference, retry and offline HTML.');
