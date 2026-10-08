/* Keep a copy of DevTools edits on disk, so a stray click or a reload cannot
   lose them. preview.py adds this script to index.html as it serves it. It
   lives outside site/ and never ships.

   Every two seconds it takes the same snapshot browser-dump.js takes, and if
   the page has changed since the last one, POSTs it to preview.py, which
   writes .claude/scratch/autosave.json. It also saves on the way out of the
   page, which is the moment that matters.

   A freshly loaded page posts nothing until something is edited. That is the
   point: after an accident the reloaded page is clean, and a clean page must
   not overwrite the snapshot of the one that was lost.

   Recover with:
       python3 .claude/scripts/pull-from-browser.py .claude/scratch/autosave.json
*/
(async () => {
  if (window.top !== window) return;                          // not in an iframe
  if (!/^\/(index\.html)?$/.test(location.pathname)) return;  // the reconciler only knows the page

  const src = await (await fetch('/__dump.js')).text();
  const take = () => {
    globalThis.__SNAPSHOT_ONLY = true;
    try { return (0, eval)(src); } finally { delete globalThis.__SNAPSHOT_ONLY; }
  };

  // What the page was before anyone touched it. Every later snapshot carries
  // this along, and it has to be in place before `last` is taken, or the first
  // tick would see a "change" and save an unedited page over a lost one.
  const first = take();
  globalThis.__AT_LOAD = { css: first.css, html: first.html, loose: first.loose };

  const loadedAt = new Date().toISOString();
  let last = JSON.stringify(take());

  const save = leaving => {
    const snapshot = take();
    const key = JSON.stringify(snapshot);
    if (key === last) return;
    last = key;
    const body = JSON.stringify({ ...snapshot, loadedAt, savedAt: new Date().toISOString() });
    // a fetch started while the page is going away may never be sent
    if (leaving) navigator.sendBeacon('/__autosave', body);
    else fetch('/__autosave', { method: 'POST', body }).catch(() => {});
  };

  setInterval(() => save(false), 2000);
  addEventListener('pagehide', () => save(true));
})();
