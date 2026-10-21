<?php
// Transcript display from daisy_2026/42/sbshell-script-viewer.html.
function script_log($file){
	$script = file_get_contents($file);
?>
<div class="script-log" data-filename="<?php echo htmlspecialchars($file, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); ?>">
<div class="toolbar" role="toolbar" aria-label="Transcript controls" hidden>
<button type="button" data-control="terminalMode" aria-pressed="true">Terminal</button>
<button type="button" data-control="sectionsMode" aria-pressed="false">Sections</button>
<button type="button" data-control="prev">Previous</button>
<span data-control="stepLabel" aria-live="polite">Full session</span>
<button type="button" data-control="next">Next</button>
<button type="button" data-control="all">Show all</button>
</div>
<div class="stats" data-control="stats" aria-live="polite"></div>
<div class="view" data-control="viewer" aria-label="Transcript"></div>
<script type="application/json" class="script-source"><?php echo json_encode($script, JSON_HEX_TAG | JSON_INVALID_UTF8_SUBSTITUTE); ?></script>
<noscript><pre class="script-plain"><?php echo htmlspecialchars($script, ENT_NOQUOTES | ENT_SUBSTITUTE, 'UTF-8'); ?></pre></noscript>
</div>
<?php
}
?>
<style>
.script-log { min-width:0; max-width:100%; margin:12px 0; color:#e3e8ed; font:14px/1.45 system-ui,sans-serif; }
.script-log [hidden] { display:none; }
.script-log .toolbar { display:flex; align-items:center; flex-wrap:wrap; gap:8px; padding:10px 0; }
.script-log button { padding:6px 10px; cursor:pointer; border:1px solid #495665; border-radius:5px; background:#26313b; color:#f0f4f7; }
.script-log button:hover { background:#33424e; }
.script-log button:focus-visible { outline:2px solid #91c7ab; outline-offset:2px; }
.script-log button[aria-pressed="true"] { background:#2d5147; border-color:#82cbaa; }
.script-log button:disabled { opacity:.4; cursor:default; }
.script-log .stats { display:flex; flex-wrap:wrap; gap:8px 14px; padding-bottom:10px; color:#495665; font:12px/1.5 ui-monospace,monospace; overflow-wrap:anywhere; }
.script-log .view { box-sizing:border-box; width:calc(80ch + 50px); max-width:100%; font:16px/1.43 ui-monospace,SFMono-Regular,Consolas,'Liberation Mono',monospace; border:1px solid #33404e; border-radius:7px; background:#171d24; overflow:hidden; }
.script-log .view:empty { display:none; }
.script-log .terminal-header { background:#222d36; color:#c6d1d9; padding:8px 12px; font:12px/1.4 ui-monospace,monospace; }
.script-log .traffic { color:#e4a2a7; padding-right:10px; }
.script-log .terminal,.script-log .script-plain { box-sizing:border-box; min-width:0; max-width:100%; background:#0b0f13; color:#e2e5e9; padding:12px; overflow:auto; font:16px/1.43 ui-monospace,SFMono-Regular,Consolas,'Liberation Mono',monospace; tab-size:8; }
.script-log .term-line { width:max-content; min-width:100%; min-height:1.43em; }
.script-log .term-line,.script-log .term-line span { font:inherit; letter-spacing:normal; word-spacing:normal; white-space:pre; overflow-wrap:normal; word-break:normal; }
.script-log .sections { padding:12px; display:grid; grid-template-columns:minmax(0,1fr); gap:12px; }
.script-log .session-block { overflow:hidden; border-radius:5px; }
.script-log .command { background:#273541; color:#dff1e7; padding:8px 12px; font:inherit; overflow:auto; white-space:pre; }
.script-log .note { border-left:3px solid #91c7ab; background:#21312d; padding:12px; color:#d3e6dc; }
.script-log .note-label { color:#92cba9; font-size:11px; font-weight:650; padding-bottom:4px; }
.script-log .note-text { white-space:pre-wrap; overflow-wrap:anywhere; }
.script-log [data-control=stepLabel] { color:#495665; font:12px ui-monospace,monospace; }
@media print {
  .script-log .view,.script-log .terminal,.script-log .script-plain { font-size:9pt; }
  .script-log .view { width:auto; }
  .script-log .sections,.script-log .terminal,.script-log .command { padding:6px; }
  .script-log .toolbar,.script-log .stats { display:none; }
  .script-log .view,.script-log .terminal,.script-log .command { overflow:visible; }
  .script-log .term-line { width:auto; min-width:0; }
  .script-log .term-line,.script-log .term-line span,.script-log .command { white-space:pre-wrap; overflow-wrap:anywhere; }
  .script-log .view,.script-log .terminal,.script-log .terminal span,.script-log .command,.script-log .terminal-header,.script-log .note,.script-log .note-label { background:transparent !important; color:#000 !important; }
}
</style>
<script>
(() => {
'use strict';
const baseColors = ['#17191d','#ee6868','#8ccf91','#dbb96a','#84aaf3','#cd99dc','#77cfd9','#e2e5e9',
                    '#676e77','#ff8585','#a9efa9','#f2d888','#9bc1ff','#e9aff6','#95ecf3','#ffffff'];
function sgrToColor(n) {
  if (n >= 0 && n < 16) return baseColors[n];
  if (n >= 16 && n <= 231) {
    n -= 16; const c = [Math.floor(n / 36), Math.floor(n / 6) % 6, n % 6].map(k => k === 0 ? 0 : k * 40 + 55);
    return `rgb(${c.join(',')})`;
  }
  if (n >= 232 && n <= 255) { const c = (n - 232) * 10 + 8; return `rgb(${c},${c},${c})`; }
  return null;
}
// Collapse complete alternate-screen sessions (Vim, less, top, etc.).
// Keep the original recording unmodified. An incomplete session is left intact.
function markAlternateScreens(source) {
  const toggle = /\x1b\[\?(?:1049|1047|47)(?:;\d+)*[hl]/g;
  let match, opened = null, offset = 0, count = 0, result = '';
  while ((match = toggle.exec(source))) {
    const entering = match[0].endsWith('h');
    if (entering && opened === null) opened = match.index;
    else if (!entering && opened !== null) {
      result += source.slice(offset, opened);
      result += '\r\n-->> # [SB Shell: full-screen session begins]\r\n';
      result += '-->> # [SB Shell: full-screen session ends; display omitted]\r\n';
      offset = toggle.lastIndex;
      opened = null;
      count++;
    }
  }
  return { text: result + source.slice(offset), count };
}
function parseTerminal(source) {
  const output = [[]]; let x = 0, y = 0, i = 0;
  let style = { fg: null, bg: null, bold: false, underline: false, inverse: false };
  const line = () => { while (!output[y]) output.push([]); return output[y]; };
  const put = ch => { const l = line(); while (l.length < x) l.push({ch:' ', style:{}}); l[x++] = {ch, style:{...style}}; };
  const params = value => value.split(';').map(s => s === '' ? 0 : Number(s));
  function updateStyle(input) {
    const ps = params(input);
    for (let j = 0; j < ps.length; j++) {
      const p = ps[j];
      if (p === 0) style = {fg:null,bg:null,bold:false,underline:false,inverse:false};
      else if (p === 1) style.bold = true;
      else if (p === 4) style.underline = true;
      else if (p === 7) style.inverse = true;
      else if (p === 22) style.bold = false;
      else if (p === 24) style.underline = false;
      else if (p === 27) style.inverse = false;
      else if (p === 39) style.fg = null;
      else if (p === 49) style.bg = null;
      else if (p >= 30 && p <= 37) style.fg = baseColors[p - 30];
      else if (p >= 90 && p <= 97) style.fg = baseColors[p - 90 + 8];
      else if (p >= 40 && p <= 47) style.bg = baseColors[p - 40];
      else if (p >= 100 && p <= 107) style.bg = baseColors[p - 100 + 8];
      else if ((p === 38 || p === 48) && ps[j+1] === 5 && Number.isInteger(ps[j+2])) {
        style[p === 38 ? 'fg' : 'bg'] = sgrToColor(ps[j+2]); j += 2;
      } else if ((p === 38 || p === 48) && ps[j+1] === 2 && j + 4 < ps.length) {
        const color = ps.slice(j+2,j+5).map(v => Math.min(255,Math.max(0,v | 0)));
        style[p === 38 ? 'fg' : 'bg'] = `rgb(${color.join(',')})`; j += 4;
      }
    }
  }
  while (i < source.length) {
    const c = source[i++];
    if (c === '\x1b') {
      const kind = source[i++];
      if (kind === '[') {
        let sequence = '';
        while (i < source.length && !/[\x40-\x7e]/.test(source[i])) sequence += source[i++];
        const final = source[i++] || '';
        const ps = params(sequence.replace(/^[?>!]/,'')); const n = ps[0] || 1;
        if (final === 'm') updateStyle(sequence);
        else if (final === 'K') {
          if (ps[0] === 2) output[y] = [];
          else if (ps[0] === 1) for (let k=0;k<=x;k++) line()[k] = {ch:' ',style:{}};
          else line().length = Math.min(line().length,x);
        } else if (final === 'C') x += n;
        else if (final === 'D') x = Math.max(0,x-n);
        else if (final === 'G') x = Math.max(0,n-1);
        else if (final === 'A') y = Math.max(0,y-n);
        else if (final === 'B') y += n;
        else if (final === 'H' || final === 'f') {y=Math.max(0,n-1); x=Math.max(0,(ps[1]||1)-1);}
      } else if (kind === ']') {
        while (i < source.length) {
          if (source[i] === '\x07') { i++; break; }
          if (source[i] === '\x1b' && source[i+1] === '\\') { i += 2; break; }
          i++;
        }
      } else if (kind === 'P') { // DCS
        while (i < source.length && !(source[i] === '\x1b' && source[i+1] === '\\')) i++;
        i += 2;
      }
    } else if (c === '\r') x = 0;
    else if (c === '\n') { y++; x = 0; line(); }
    else if (c === '\b') x = Math.max(0,x-1);
    else if (c === '\t') x += 8 - (x % 8);
    else if (c >= ' ' && c !== '\x7f') put(c);
  }
  return output;
}
function lineText(r) { return r.map(cell => cell?.ch || ' ').join('').trimEnd(); }
function segment(r) {
  const out = []; let block = null;
  function flush() { if (block) out.push(block); block = null; }
  for (const row of r) {
    const text = lineText(row);
    if (text.startsWith('-->> ')) {
      flush();
      if (/^-->>\s*#+/.test(text)) out.push({type:'comment',prompt:row,text:text.replace(/^-->>\s*#+\s*/, '')});
      else block = {type:'command',prompt:row,body:[]};
    } else if (block) block.body.push(row);
    else if (out.length && out[out.length-1].type === 'meta') out[out.length-1].body.push(row);
    else out.push({type:'meta',body:[row]});
  }
  flush(); return out;
}
function styleKey(s) { return [s.fg||'',s.bg||'',s.bold?'1':'',s.underline?'1':'',s.inverse?'1':''].join('|'); }
function createLine(cells) {
  const el = document.createElement('div'); el.className = 'term-line';
  if (!cells.length) { el.textContent = ' '; return el; }
  let group = '', key = null, current = null;
  function appendSpan() {
    if (key === null) return;
    const span = document.createElement('span');
    span.textContent = group;
    if (current?.fg) span.style.color = current.fg;
    if (current?.bg) span.style.backgroundColor = current.bg;
    if (current?.bold) span.style.fontWeight = 'bold';
    if (current?.underline) span.style.textDecoration = 'underline';
    if (current?.inverse) {
      span.style.color = current?.bg || '#0b0f13';
      span.style.backgroundColor = current?.fg || '#e2e5e9';
    }
    el.appendChild(span); group = '';
  }
  for (const cell of cells) {
    const s = cell?.style || {}, k = styleKey(s);
    if (k !== key) {appendSpan(); key = k; current = s;}
    group += cell?.ch || ' ';
  }
  appendSpan(); return el;
}
function createTerminal(lines, extraClass='') {
  const terminal = document.createElement('div'); terminal.className = `terminal ${extraClass}`;
  for (const r of lines) terminal.appendChild(createLine(r));
  return terminal;
}
function termHeader(value) {
  const el = document.createElement('div'); el.className = 'terminal-header';
  const dots = document.createElement('span'); dots.className = 'traffic'; dots.textContent='● ● ●';
  const title = document.createElement('span'); title.textContent = value;
  el.append(dots,title); return el;
}
function scriptLog(host) {
  const $ = name => host.querySelector('[data-control="' + name + '"]');
  const viewer = $('viewer');
  let mode = 'terminal', rows = [], blocks = [], visibleBlocks = Infinity, filename = host.dataset.filename;
function render() {
  viewer.replaceChildren();
  const visible = Number.isFinite(visibleBlocks) ? blocks.slice(0,visibleBlocks) : blocks;
  $('terminalMode').setAttribute('aria-pressed',mode==='terminal');
  $('sectionsMode').setAttribute('aria-pressed',mode==='sections');
  $('stepLabel').textContent = visible.length===blocks.length ? 'Full session' : `${visible.length} / ${blocks.length} blocks`;
  $('prev').disabled = visible.length===0; $('next').disabled = visible.length===blocks.length;
  $('all').disabled = visible.length===blocks.length;
  if (mode === 'terminal') {
    viewer.appendChild(termHeader(filename));
    const all = visible.flatMap(b => b.type === 'command' ? [b.prompt,...b.body] : b.type === 'comment' ? [b.prompt] : b.body);
    viewer.appendChild(createTerminal(all));
  } else {
    viewer.appendChild(termHeader(`${filename} · sections`));
    const collection = document.createElement('div'); collection.className = 'sections';
    visible.forEach(block => {
      if (block.type === 'comment') {
        const note = document.createElement('div'); note.className='note';
        const label = document.createElement('div'); label.className='note-label'; label.textContent=block.text.startsWith('[SB Shell:') ? 'Full-screen boundary' : 'Session annotation';
        const body = document.createElement('div'); body.className='note-text'; body.textContent=block.text;
        note.append(label,body); collection.appendChild(note);
      } else if (block.type === 'meta') {
        const box = document.createElement('div'); box.className='session-block'; box.appendChild(createTerminal(block.body)); collection.appendChild(box);
      } else {
        const section = document.createElement('section'); section.className='session-block';
        const prompt = document.createElement('div'); prompt.className='command'; prompt.appendChild(createLine(block.prompt));
        section.appendChild(prompt);
        if (block.body.length) { const body = document.createElement('div');body.className='section-body';body.appendChild(createTerminal(block.body,'command-output'));section.appendChild(body); }
        collection.appendChild(section);
      }
    });
    viewer.appendChild(collection);
  }
}
function loadTranscript(contents, name) {
  const marked = markAlternateScreens(contents);
  rows = parseTerminal(marked.text); blocks = segment(rows); filename=name; visibleBlocks=Infinity;
  const ansi=(contents.match(/\x1b/g)||[]).length;
  const commands=blocks.filter(b=>b.type==='command').length;
  const annotations=blocks.filter(b=>b.type==='comment' && !b.text.startsWith('[SB Shell:')).length;
  $('stats').replaceChildren();
  for (const [label,value] of [['FILE',name],['LINES',String(rows.length)],['COMMANDS',String(commands)],['COMMENTS',String(annotations)],['FULL-SCREEN',String(marked.count)],['ESC',String(ansi)]]) {
    const item=document.createElement('span'); const strong=document.createElement('strong');strong.textContent=label;item.append(strong,document.createTextNode(' '+value));$('stats').appendChild(item);
  }
  render();
}
$('terminalMode').addEventListener('click',()=>{mode='terminal';render();});
$('sectionsMode').addEventListener('click',()=>{mode='sections';render();});
$('prev').addEventListener('click',()=>{visibleBlocks = Math.max(0, (Number.isFinite(visibleBlocks)?visibleBlocks:blocks.length)-1);render();});
$('next').addEventListener('click',()=>{visibleBlocks = Math.min(blocks.length,(Number.isFinite(visibleBlocks)?visibleBlocks:blocks.length)+1);render();});
$('all').addEventListener('click',()=>{visibleBlocks = Infinity;render();});
  loadTranscript(JSON.parse(host.querySelector('.script-source').textContent),filename);
  host.querySelector('.toolbar').hidden = false;
}
document.addEventListener('DOMContentLoaded',()=>document.querySelectorAll('.script-log').forEach(host => {
  const entry = host.closest('.sb-entry');
  function show() {
    if (host.dataset.ready || (entry && !entry.open)) return;
    host.dataset.ready = 'true';
    scriptLog(host);
  }
  if (entry) entry.addEventListener('toggle', show);
  show();
}));
})();
</script>
