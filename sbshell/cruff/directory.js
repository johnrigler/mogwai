(() => {
  const menu = document.getElementById('sb-menu');
  if (menu) {
    document.addEventListener('click', event => { if (!menu.contains(event.target)) menu.open = false; });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && menu.open) {
        menu.open = false;
        menu.querySelector('summary').focus();
      }
    });
  }
  const directory = document.getElementById('sb-directory');
  const entries = [...directory.querySelectorAll('.sb-entry')];
  const selections = [...directory.querySelectorAll('.sb-select')];
  const copySelected = document.getElementById('sb-copy-selected');
  const clipboardStatus = document.getElementById('sb-clipboard-status');
  let copying = false;
  const selectionKey = 'sbshell-selected:' + location.pathname;
  let selected = [];
  try { selected = JSON.parse(sessionStorage.getItem(selectionKey) || '[]'); } catch {}
  function rememberSelection() {
    const files = selections.filter(input => input.checked).map(input => input.value);
    const count = document.getElementById('sb-selected-count');
    if (count) count.textContent = files.length + ' selected';
    const expandSelected = document.getElementById('sb-expand-selected');
    if (expandSelected) expandSelected.disabled = !entries.some(entry => files.includes(entry.dataset.file));
    if (copySelected) copySelected.disabled = copying || !files.length || !/^https?:$/.test(location.protocol);
    try { sessionStorage.setItem(selectionKey, JSON.stringify(files)); } catch {}
  }
  selections.forEach(input => {
    input.checked = Array.isArray(selected) && selected.includes(input.value);
    input.addEventListener('change', rememberSelection);
  });
  rememberSelection();
  if (copySelected) copySelected.addEventListener('click', async () => {
    const files = selections.filter(input => input.checked).map(input => input.value);
    if (copying || !files.length) return;
    copying = true;
    rememberSelection();
    clipboardStatus.textContent = 'Saving .clip…';
    delete clipboardStatus.dataset.error;
    const url = new URL(location.href);
    url.searchParams.set('sb-clipboard', '1');
    try {
      const response = await fetch(url, {method:'POST', cache:'no-store', headers:{'Content-Type':'application/json'}, body:JSON.stringify({files})});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Could not save .clip.');
      clipboardStatus.textContent = 'Saved ' + result.count + (result.count === 1 ? ' entry' : ' entries') + ' to .clip';
    } catch (error) {
      clipboardStatus.textContent = error.message || 'Could not save .clip.';
      clipboardStatus.dataset.error = 'true';
    } finally { copying = false; rememberSelection(); }
  });
  if (selections.length) {
    document.getElementById('sb-file-controls').hidden = false;
    document.getElementById('sb-select-all').addEventListener('click', () => {
      directory.open = true;
      selections.forEach(input => { input.checked = true; });
      rememberSelection();
    });
    document.getElementById('sb-unselect-all').addEventListener('click', () => {
      selections.forEach(input => { input.checked = false; });
      rememberSelection();
    });
    document.getElementById('sb-expand-all').disabled = !entries.length;
    document.getElementById('sb-collapse-all').disabled = !entries.length;
  }
  const openKey = 'sbshell-open:' + location.pathname;
  let saved = [];
  try { saved = JSON.parse(sessionStorage.getItem(openKey) || '[]'); } catch {}
  function loadMedia(entry) {
    if (!entry.open) return;
    entry.querySelectorAll('[data-src]').forEach(media => {
      if (media.tagName === 'OBJECT' && navigator.pdfViewerEnabled === false) media.classList.add('sb-pdf-fallback');
      media.setAttribute(media.tagName === 'OBJECT' ? 'data' : 'src', media.dataset.src);
      delete media.dataset.src;
    });
  }
  function remember() {
    try { sessionStorage.setItem(openKey, JSON.stringify(entries.filter(entry => entry.open).map(entry => entry.dataset.file))); } catch {}
  }
  entries.forEach(entry => {
    entry.open = Array.isArray(saved) && saved.includes(entry.dataset.file);
    loadMedia(entry);
    entry.addEventListener('toggle', () => { loadMedia(entry); remember(); });
  });
  if (entries.length) {
    document.getElementById('sb-expand-selected').addEventListener('click', () => {
      directory.open = true;
      const files = selections.filter(input => input.checked).map(input => input.value);
      entries.forEach(entry => {
        if (files.includes(entry.dataset.file)) { entry.open = true; loadMedia(entry); }
      });
      remember();
    });
    document.getElementById('sb-expand-all').addEventListener('click', () => {
      directory.open = true;
      entries.forEach(entry => { entry.open = true; loadMedia(entry); });
      remember();
    });
    document.getElementById('sb-collapse-all').addEventListener('click', () => {
      entries.forEach(entry => { entry.open = false; });
      remember();
    });
  }

  const refresh = document.getElementById('auto-refresh');
  const key = 'sbshell-refresh:' + location.pathname;
  const refreshUrl = new URL(location.href);
  refreshUrl.searchParams.set('sb-refresh', '1');
  let timer, controller;
  try { refresh.checked = localStorage.getItem(key) !== 'off'; } catch {}
  async function check() {
    if (!refresh.checked) return;
    if (copying) { schedule(); return; }
    controller = new AbortController();
    try {
      const response = await fetch(refreshUrl, {cache:'no-store', signal:controller.signal});
      if (response.ok) {
        const result = await response.json();
        if (refresh.checked && !copying && result.stamp && result.stamp !== refresh.dataset.stamp) {
          remember();
          rememberSelection();
          location.reload();
          return;
        }
      }
    } catch { /* Keep the current page when the local server is unavailable. */ }
    finally { controller = null; schedule(); }
  }
  function schedule() {
    clearTimeout(timer);
    if (refresh.checked && refresh.dataset.stamp && /^https?:$/.test(location.protocol)) timer = setTimeout(check, 10000);
  }
  refresh.addEventListener('change', () => {
    controller?.abort();
    try { localStorage.setItem(key, refresh.checked ? 'on' : 'off'); } catch {}
    schedule();
  });
  schedule();
})();
