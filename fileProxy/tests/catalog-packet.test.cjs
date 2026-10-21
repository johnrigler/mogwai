const {readFileSync} = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const test = require("node:test");
const {JSDOM} = require("jsdom");
const tick = () => new Promise(resolve => setImmediate(resolve));
const digest = "a".repeat(64);
const row = (name, bytes=40) => ({path:"case/"+name,root:"work",sha256:digest,bytes});
const fixture = `<div class="packet"><section class="page"><div class="addr">[NAME]<br>Mailing address</div>
 <p>Our response letter.</p><p>We are enclosing copies of material.</p><div class="footer">Old page 1 of 3</div></section>
 <section class="page"><h1>Specific Basis of Dispute</h1><p>Existing dispute text.</p></section>
 <section class="page"><h1>Enclosures and Document Integrity</h1><div class="exhibit">Lease agreement not attached</div></section></div>`;

async function page(t, file, initial, options={}) {
  let records=[...initial],folders=options.folders||["","case","case/ncs"];const calls=[];
  const dom=new JSDOM(readFileSync(path.join(__dirname,"../web/"+file),"utf8"),{
    url:"http://127.0.0.1:7799/"+(file==="catalog.html"?"catalog":"packet")+"?root=work&path=case",
    runScripts:"dangerously",beforeParse(window){
      window.confirm=()=>options.confirm!==false;
      window.fetch=async(url,init={})=>{
        calls.push({url,...init});
        if(url==="v1/health")return {ok:true,json:async()=>({ok:true,roots:["work"],writeTokenRequired:options.token===true})};
        if(url.startsWith("v1/index?")){const prefix=new URL(url,"http://localhost/").searchParams.get("prefix")||"";return {ok:true,json:async()=>({ok:true,entries:records.filter(row=>row.path.startsWith(prefix))})};}
        if(url.startsWith("v1/folders?"))return {ok:true,json:async()=>({ok:true,directories:folders})};
        if(url.startsWith("v1/file?"))return {ok:true,text:async()=>fixture,blob:async()=>new Blob([url.includes("evil.html")?"<script>parent.pwned=1</script><p>Preview</p>":"temporary shell output"],{type:"text/plain"})};
        if(url==="v1/trash"){
          const data=JSON.parse(init.body);records=records.filter(x=>x.path!==data.path);
          return {ok:true,json:async()=>({ok:true,...data,trashId:"b".repeat(32)})};
        }
        if(url==="v1/restore"){records=[...initial];return {ok:true,json:async()=>({ok:true})};}
        if(url==="v1/mkdir"){const data=JSON.parse(init.body);folders=[...folders,data.path];return {ok:true,json:async()=>({ok:true,...data})};}
        if(url==="v1/transfer"){const data=JSON.parse(init.body);return {ok:true,json:async()=>({ok:true,...data})};}
        if(url==="v1/packet")return {ok:true,json:async()=>({ok:true,root:"work",directory:"case/response-1",path:"case/response-1/index.html",letterPath:"case/response-1/letter.html",pages:4,draft:true,attachments:[{}]})};
        throw new Error("Unexpected request: "+url);
      };
    }
  });
  t.after(()=>dom.window.close());await tick();await tick();
  return {$:id=>dom.window.document.getElementById(id),window:dom.window,calls};
}

test("numeric shell files preview as text; delete and Undo update the listing",async t=>{
  const ui=await page(t,"catalog.html",[row("11703")]);
  ui.$("list").querySelector(".leaf a").click();await tick();
  assert.equal(ui.$("preview").hidden,false);
  assert.equal(ui.$("previewBody").querySelector("pre").textContent,"temporary shell output");
  assert.match(ui.$("download").getAttribute("href"),/download=1/);
  ui.$("delete").click();await tick();await tick();
  const removed=ui.calls.find(x=>x.url==="v1/trash");
  assert.deepEqual(JSON.parse(removed.body),{root:"work",path:"case/11703",sha256:digest});
  assert.equal(ui.$("list").querySelectorAll(".leaf").length,0);
  assert.equal(ui.$("undo").hidden,false);
  ui.$("restore").click();await tick();await tick();
  assert.equal(ui.$("list").querySelectorAll(".leaf").length,1);
});

test("canceling deletion performs no write",async t=>{
  const ui=await page(t,"catalog.html",[row("11703")],{confirm:false});
  ui.$("list").querySelector(".danger").click();await tick();
  assert.equal(ui.calls.filter(x=>x.method==="POST").length,0);
});

test("HTML preview is sandboxed and does not execute document scripts",async t=>{
  const ui=await page(t,"catalog.html",[row("evil.html")]);
  ui.$("list").querySelector(".leaf a").click();await tick();
  const frame=ui.$("previewBody").querySelector("iframe");
  assert.equal(frame.getAttribute("sandbox"),"");
  assert.match(frame.srcdoc,/default-src 'none'/);
  assert.equal(ui.window.pwned,undefined);
});

test("token mode requires a token for delete controls",async t=>{
  const ui=await page(t,"catalog.html",[row("11703")],{token:true});
  assert.equal(ui.$("tokenField").hidden,false);
  assert.equal(ui.$("list").querySelector(".danger").disabled,true);
  ui.$("token").value="test-write-secret";
  ui.$("token").dispatchEvent(new ui.window.Event("input"));
  assert.equal(ui.$("list").querySelector(".danger").disabled,false);
});

test("packet letter excludes static enclosure claims and includes only added sources",async t=>{
  const ui=await page(t,"packet.html",[row("response.html",4000),row("ncs/01.pdf"),row("ncs/02.pdf")]);
  assert.doesNotMatch(ui.$("letter").textContent,/Lease agreement|Old page/);
  assert.match(ui.$("letter").textContent,/supporting records included/);
  assert.equal(ui.$("build").disabled,true);
  ui.$("available").querySelector(".source button").click();
  assert.equal(ui.$("added").querySelectorAll(".added").length,1);
  assert.equal(ui.$("build").disabled,false);
  ui.$("build").click();await tick();
  const payload=JSON.parse(ui.calls.find(x=>x.url==="v1/packet").body);
  assert.equal(payload.attachments.length,1);
  assert.equal(payload.attachments[0].path,"case/ncs/01.pdf");
  assert.doesNotMatch(JSON.stringify(payload.letter.blocks),/Lease agreement/);
  assert.equal(ui.$("result").hidden,false);
  assert.match(ui.$("result").textContent,/Draft response folder saved/);
  assert.match(ui.$("result").textContent,/Print \/ Save PDF/);
  assert.equal(payload.folderName,"response-1");
  assert.match(ui.$("result").querySelector("a").getAttribute("href"),/v1\/fs\/work\/case\/response-1\/index.html$/);
  assert.equal(ui.$("result").querySelector("iframe").getAttribute("sandbox"),"allow-same-origin allow-modals");
});

test("removing an enclosure removes it from the generated packet request",async t=>{
  const ui=await page(t,"packet.html",[row("response.html",4000),row("ncs/01.pdf"),row("ncs/02.pdf")]);
  ui.$("available").querySelectorAll(".source button")[0].click();
  ui.$("available").querySelectorAll(".source button")[1].click();
  ui.$("added").querySelectorAll(".added")[0].querySelectorAll("button")[2].click();
  ui.$("build").click();await tick();
  const payload=JSON.parse(ui.calls.find(x=>x.url==="v1/packet").body);
  assert.deepEqual(payload.attachments.map(x=>x.path),["case/ncs/02.pdf"]);
});

test("letter extraction follows HTML line breaks without doubling source indentation",async t=>{
  const ui=await page(t,"packet.html",[row("response.html",4000),row("ncs/01.pdf")]);
  const blocks=ui.window.extractLetter("<p>First line<br>\n    Second line</p>",true);
  assert.equal(blocks[0].text,"First line\nSecond line");
});

test("thumbnails and optional captions accompany documents placed inside the narrative",async t=>{
  const ui=await page(t,"packet.html",[row("response.html"),row("ncs/01.png"),row("ncs/02.pdf")]);
  assert.match(ui.$("available").querySelector('.source img').src,/v1\/file\?/);
  assert.match(ui.$("available").querySelectorAll('.source img')[1].src,/v1\/thumbnail\?/);
  ui.$("available").querySelector('.source button').click();
  const added=ui.$("added").querySelector('.added');
  added.querySelector('input').value='';added.querySelector('input').dispatchEvent(new ui.window.Event('input'));
  const select=added.querySelector('select');select.value='1';select.dispatchEvent(new ui.window.Event('change'));
  assert.equal(ui.$("letter").querySelectorAll('.inline-document').length,1);
  ui.$("build").click();await tick();
  const payload=JSON.parse(ui.calls.find(x=>x.url==='v1/packet').body);
  assert.equal(payload.attachments[0].afterBlock,1);
  assert.equal(payload.attachments[0].label,'');
  assert.doesNotMatch(JSON.stringify(payload.letter.blocks),/01\.png|inline-document/);
});

test("source-index pages and source captions do not become response text",async t=>{
  const ui=await page(t,"packet.html",[row("response.html")]);
  const text='<section class="page"><p>Current narrative.</p></section>'
    +'<section class="page"><h1>Additional Centro Source Index</h1><p>Old source hashes</p></section>'
    +'<section class="page scan-page"><p>Old scan caption</p></section>';
  const blocks=JSON.parse(JSON.stringify(ui.window.extractLetter(text,true)));
  assert.deepEqual(blocks,[{kind:'paragraph',text:'Current narrative.'}]);
});

test("changing the letter resets placements and an empty paragraph remains editable",async t=>{
  const ui=await page(t,"packet.html",[row("response.html"),row("other.html"),row("01.png")]);
  ui.$("available").querySelector('.source button').click();
  const select=ui.$("added").querySelector('select');select.value='1';select.dispatchEvent(new ui.window.Event('change'));
  const paragraph=ui.$("letter").querySelector('p');paragraph.textContent='';paragraph.dispatchEvent(new ui.window.Event('input',{bubbles:true}));
  assert.equal(ui.$("letter").querySelectorAll('.inline-document').length,1);
  ui.$("source").value='case/other.html';ui.$("source").dispatchEvent(new ui.window.Event('change'));await tick();await tick();
  assert.equal(ui.$("letter").querySelectorAll('.inline-document').length,0);
  assert.equal(ui.$("added").querySelector('select').value,'');
  assert.match(ui.$("status").textContent,/Choose the document placements again/);
});

test("Add all includes one folder in natural numeric order",async t=>{
  const ui=await page(t,"packet.html",[row("response.html"),row("ncs/10.pdf"),row("ncs/2.pdf"),row("ncs/1.pdf"),row("other/04.pdf")]);
  ui.$("available").querySelector(".source-group > button").click();
  assert.equal(ui.$("added").querySelectorAll(".added").length,3);
  ui.$("build").click();await tick();
  const payload=JSON.parse(ui.calls.find(x=>x.url==="v1/packet").body);
  assert.deepEqual(payload.attachments.map(x=>x.path),["case/ncs/1.pdf","case/ncs/2.pdf","case/ncs/10.pdf"]);
});

test("saved response copies and rendered pages stay hidden until requested",async t=>{
  const ui=await page(t,"packet.html",[row("response.html"),row("01.png"),row("response-1/index.html"),
    row("response-1/letter.html"),row("response-1/001-01.png"),row("response-1/pages/002-page-1.png")]);
  assert.equal(ui.$("available").querySelectorAll('.source').length,1);
  ui.$("showSaved").checked=true;ui.$("showSaved").dispatchEvent(new ui.window.Event('change'));
  assert.equal(ui.$("available").querySelectorAll('.source').length,3);
});

test("saved letter preserves address lines and signatures without old draft and enclosure text",async t=>{
  const ui=await page(t,"packet.html",[row("letter.html"),row("ncs/01.pdf")]);
  const saved=`<section class="page response-letter"><div class="draft">DRAFT - complete the letter fields</div>
    <p class="addr">Jane\nAddress line</p><div class="signature"><p>Jane signature</p></div></section>
    <section class="page enclosures"><h1>Enclosures actually included</h1><p>Old enclosure</p></section>
    <section class="page scan-page"><img alt="Old scan"></section>`;
  const blocks=JSON.parse(JSON.stringify(ui.window.extractLetter(saved,true)));
  assert.deepEqual(blocks,[{kind:"address",text:"Jane\nAddress line"},{kind:"signature",text:"Jane signature"}]);
});

test("catalog selects, reorders, and copies documents in that order",async t=>{
  const ui=await page(t,"catalog.html",[row("02.pdf"),row("01.pdf"),row("11703")],{folders:["","case","case/response-1"]});
  ui.$("selectDocuments").click();
  assert.equal(ui.$("selectedFiles").querySelectorAll(".selected-row").length,2);
  ui.$("selectedFiles").querySelectorAll(".selected-row")[1].querySelector("button").click();
  ui.$("destination").value="case/response-1";ui.$("destination").dispatchEvent(new ui.window.Event("change"));
  ui.$("copyOrdered").click();await tick();await tick();
  const payload=JSON.parse(ui.calls.find(x=>x.url==="v1/transfer").body);
  assert.equal(payload.numbered,true);assert.equal(payload.operation,"copy");assert.equal(payload.destination,"case/response-1");
  assert.deepEqual(payload.files.map(x=>x.path),["case/02.pdf","case/01.pdf"]);
  assert.equal(ui.$("arrangePanel").hidden,true);
  assert.match(ui.$("notice").textContent,/2 file\(s\) copied/);
});

test("selection survives browsing to another folder",async t=>{
  const ui=await page(t,"catalog.html",[row("01.pdf"),row("ncs/02.pdf")]);
  ui.$("selectDocuments").click();
  ui.$("list").querySelector(".browse").click();await tick();await tick();
  assert.match(ui.$("title").textContent,/case\/ncs$/);
  ui.$("selectDocuments").click();
  assert.equal(ui.$("selectedFiles").querySelectorAll(".selected-row").length,2);
  assert.match(ui.$("selectedFiles").textContent,/case\/01.pdf/);
  assert.match(ui.$("selectedFiles").textContent,/case\/ncs\/02.pdf/);
});

test("New folder can create the suggested destination using taps",async t=>{
  const ui=await page(t,"catalog.html",[row("01.pdf")]);
  ui.$("newFolder").click();assert.equal(ui.$("arrangePanel").hidden,false);
  ui.$("createFolder").click();await tick();await tick();
  const payload=JSON.parse(ui.calls.find(x=>x.url==="v1/mkdir").body);
  assert.deepEqual(payload,{root:"work",path:"case/response-1"});
  assert.equal(ui.$("destination").value,"case/response-1");
  assert.match(ui.$("notice").textContent,/Folder created/);
});
