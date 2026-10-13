/* Mogwai publication reader 42.B. Static HTML + JSON/CSV + text, no libraries. */
(function () {
"use strict";
const mount=document.getElementById("publication");
function el(tag,cls,value){const e=document.createElement(tag);if(cls)e.className=cls;if(value!==undefined)e.textContent=String(value);return e;}
function local(path,base){
  const u=new URL(path,base||document.baseURI);
  if(u.origin!==location.origin||!["http:","https:","file:"].includes(u.protocol))throw Error("Source must be published on this origin");
  return u;
}
async function load(url,json=false){const r=await fetch(url,{cache:"no-store"});if(!r.ok)throw Error("HTTP "+r.status+": "+url.pathname);return json?r.json():r.text();}
function link(path,label,base){const a=el("a","",label);a.href=local(path,base).href;return a;}
function wrap(heading,body,hero=false){
 const section=el("section","pub-block"+(hero?" p-strip--suru":"")),inner=el("div","u-fixed-width");
 if(heading)inner.appendChild(el(hero?"h1":"h2","",heading));
 inner.appendChild(body);section.appendChild(inner);return section;
}
function markdown(text){
 const box=el("div","pub-prose"),lines=text.replace(/\r\n?/g,"\n").split("\n");
 let pending=[],list=null,code=null;
 const flush=()=>{if(pending.length)box.appendChild(el("p","",pending.join(" ")));pending=[];list=null;};
 for(const line of lines){
   if(line.startsWith("~~~")){flush();if(code){box.appendChild(code);code=null;}else code=el("pre");continue;}
   if(code){code.appendChild(document.createTextNode(line+"\n"));continue;}
   if(!line.trim()){flush();continue;}
   const h=line.match(/^(#{1,4})\s+(.*)$/);
   if(h){flush();box.appendChild(el("h"+Math.min(h[1].length+1,6),"",h[2]));continue;}
   const b=line.match(/^\s*[-*]\s+(.*)$/);
   if(b){if(pending.length)flush();if(!list){list=el("ul");box.appendChild(list);}list.appendChild(el("li","",b[1]));continue;}
   if(list)list=null;
   pending.push(line.trim());
 }
 flush();if(code)box.appendChild(code);
 return box;
}
function csv(text){
 const out=[],row=[];let f="",q=false;
 for(let i=0;i<text.length;i++){
   const c=text[i];
   if(q){if(c==='"'&&text[i+1]==='"'){f+='"';i++;}else if(c==='"')q=false;else f+=c;}
   else if(c==='"')q=true;
   else if(c===","){row.push(f);f="";}
   else if(c==="\n"||c==="\r"){
     if(c==="\r"&&text[i+1]==="\n")i++;
     row.push(f);if(row.some(x=>x!==""))out.push(row.splice(0));else row.length=0;f="";
   }else f+=c;
 }
 row.push(f);if(row.some(x=>x!==""))out.push(row);
 const heads=out.shift()||[];
 return out.map(values=>Object.fromEntries(heads.map((h,i)=>[h,values[i]||""])));
}
function preview(u,title){
 if(/\.(png|jpe?g|gif|webp|svg)$/i.test(u.pathname)){const x=el("img","pub-image");x.src=u.href;x.alt=title||"Image";return x;}
 if(/\.(pdf|html?)$/i.test(u.pathname)){const x=el("iframe","pub-frame");x.src=u.href;x.title=title||"Document";if(/\.html?$/i.test(u.pathname))x.setAttribute("sandbox","");return x;}
 return null;
}
async function directory(block,base){
 const index=local(block.src,base),raw=await load(index);
 const paths=raw.split(/\r?\n/).map(x=>x.trim().replace(/^\.\//,"").replace(/\/$/,"")).filter(x=>x&&!x.startsWith("/")&&!x.split("/").some(z=>z==="."||z===".."||!z));
 const prefix=block.prefix?block.prefix.replace(/\/?$/,"/"):"";
 let here=prefix;
 const frame=el("div","pub-directory"),nav=el("nav"),view=el("div","pub-preview");
 view.textContent="Choose a file to preview.";frame.append(nav,view);
 function source(path){return local(path.split("/").map(encodeURIComponent).join("/"),index);}
 async function show(path){
   const u=source(path);
   view.replaceChildren(link(u.href,"Open source: "+path));
   const media=preview(u,path);
   if(media)view.appendChild(media);
   else if(/\.(md|txt|json|csv|js|css|sh|py)$/i.test(path)){
     try{view.appendChild(markdown(await load(u)));}catch(err){view.appendChild(el("p","pub-error",err.message));}
   }
 }
 function draw(){
   nav.replaceChildren(el("strong","",here||"/"));
   if(here!==prefix){const up=el("button","","← ..");up.onclick=()=>{
     here=here.replace(/\/$/,"").split("/").slice(0,-1).join("/");
     here=here?here+"/":"";
     if(!here.startsWith(prefix))here=prefix;
     draw();
   };nav.appendChild(up);}
   const names=new Map();
   paths.forEach(p=>{
     if(!p.startsWith(here))return;
     const rest=p.slice(here.length),name=rest.split("/")[0];
     if(name)names.set(name,rest.includes("/")||names.get(name)||false);
   });
   [...names].sort((a,b)=>a[0].localeCompare(b[0],undefined,{numeric:true})).forEach(([name,isDir])=>{
     const b=el("button","",(isDir?"▸ ":"")+name);
     b.onclick=()=>{if(isDir){here+=name+"/";draw();}else show(here+name);};
     nav.appendChild(b);
   });
   if(!names.size)nav.appendChild(el("p","","No files in this directory."));
 }
 draw();return frame;
}
async function block(b,base,seen){
 if(b.type==="include"){
   const u=local(b.src,base);
   if(seen.has(u.href)||seen.size>8)throw Error("Recursive include");
   const val=await load(u,true),next=new Set(seen);next.add(u.href);
   const fragment=document.createDocumentFragment();
   for(const item of (Array.isArray(val)?val:(val.blocks||[val])))fragment.appendChild(await block(item,u.href,next));
   return fragment;
 }
 let body=el("div");
 if(b.type==="hero"){
   body=el("div");
   if(b.lead)body.appendChild(el("p","pub-intro",b.lead));
   for(const a of b.actions||[]) {const x=link(a.href,a.label,base);x.className="p-button";body.appendChild(x);}
 }else if(b.type==="markdown")body=markdown(await load(local(b.src,base)));
 else if(b.type==="text"){body=el("div","pub-prose");for(const p of b.paragraphs||[])body.appendChild(el("p","",p));}
 else if(b.type==="table"){
   const u=local(b.src,base),v=/\.csv$/i.test(u.pathname)?csv(await load(u)):await load(u,true);
   const rows=Array.isArray(v)?v:v.rows;
   if(!Array.isArray(rows))throw Error("Expected table rows array");
   const cols=b.columns||Object.keys(rows[0]||{}).map(key=>({key,label:key}));
   body=el("div","pub-scroll");const t=el("table","p-table pub-table"),head=el("thead"),tr=el("tr");
   cols.forEach(c=>tr.appendChild(el("th","",typeof c==="string"?c:c.label||c.key)));head.appendChild(tr);t.appendChild(head);
   const tb=el("tbody");
   rows.forEach(row=>{const line=el("tr");cols.forEach(c=>{const key=typeof c==="string"?c:c.key;line.appendChild(el("td","",row[key]??""));});tb.appendChild(line);});
   t.appendChild(tb);body.appendChild(t);
 }else if(b.type==="cards"){
   body=el("div","pub-cards");
   for(const item of b.items||[]){const c=el("article","pub-card");c.appendChild(el("h3","",item.title));if(item.text)c.appendChild(el("p","",item.text));if(item.href)c.appendChild(link(item.href,item.label||"Open",base));body.appendChild(c);}
 }else if(b.type==="directory")body=await directory(b,base);
 else if(b.type==="image"||b.type==="document"){
   body=preview(local(b.src,base),b.title);
   if(!body)throw Error("Unsupported preview type");
 }else if(b.type==="list"){
   body=el("ul","p-list");
   const items=b.src?await load(local(b.src,base),/\.json$/i.test(b.src)):b.items||[];
   const list=typeof items==="string"?items.split(/\r?\n/).filter(Boolean):items;
   for(const item of list){const li=el("li","p-list__item");if(typeof item==="string")li.textContent=item;else if(item.href)li.appendChild(link(item.href,item.label||item.href,base));else li.textContent=item.label||"";body.appendChild(li);}
 }else throw Error("Unknown block type: "+b.type);
 return wrap(b.heading||b.title,body,b.type==="hero");
}
async function start(){
 try{
   const selected=new URLSearchParams(location.search).get("page")||"publications/overview.json";
   const u=local(selected),data=await load(u,true),out=document.createDocumentFragment();
   if(!Array.isArray(data.blocks))throw Error("Manifest requires blocks array");
   for(const b of data.blocks){
     try{out.appendChild(await block(b,u.href,new Set([u.href])));}
     catch(err){out.appendChild(wrap(b.heading||b.type,el("p","pub-error",err.message)));}
   }
   mount.replaceChildren(out);document.title=(data.title||"Publication")+" · Mogwai";
 }catch(err){mount.replaceChildren(el("p","pub-error",err.message));console.error("Publication 42.B",err);}
}
start();
}());
