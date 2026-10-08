/* Snapshot the live page so changes made in DevTools can be reconciled with
   the files on disk. Run this in the page; it POSTs itself to preview.py,
   which writes .claude/scratch/dump.json for pull-from-browser.py to read.

   Captures the three levels of the edit hierarchy:
     css     every rule in tokens.css / components.css as the CSSOM has it
             (this is where DevTools Styles-panel edits land)
     inline  elements carrying a style attribute — always a violation of the
             system, and the clearest signal of an instance-level tweak
     blocks  ordered text of each block element, for Elements-panel copy edits
     svg     the text of every diagram label, sorted
     html    the markup of header, main, and footer, without their text
             mattering: the reconciler reads only the tags
     loose   text that sits outside every block: the nav links, the footer,
             the brand name

   When browser-autosave.js is on the page it records css and html as they
   were at load, and this snapshot carries them along as css0, html0, and
   loose0. A
   comparison with the source files cannot see a declaration that was added
   to or removed from a rule, because the browser expands some shorthands and
   every one of those would look like an edit. Nor can it see an href or a
   class that changed. A comparison of the page with itself at load can.

   browser-autosave.js evaluates this same file with __SNAPSHOT_ONLY set and
   gets the snapshot back instead of a POST, so there is one definition of
   what a snapshot is.

   BLOCK must stay identical to the list in pull-from-browser.py, and both
   sides must skip elements nested inside an already-captured one. Otherwise
   the diff fills with phantom moves and the real change is buried.
*/
(() => {
  const BLOCK = 'h1,h2,h3,p,li,pre,figcaption,' +
    'span.chip,span.term__label,span.term__note,code.term__cmd,span.quote__cite,' +
    'span.ledger__name,span.ledger__note,span.ledger__state,' +
    'span.impl__name,span.impl__note,span.impl__state';

  // no location.href: a query string in the result trips the tooling's data guard
  const dump = { page: location.pathname, css: {}, inline: [], blocks: [] };
  const OWN = [...document.querySelectorAll('header, main, footer')];
  const ours = el => OWN.some(root => root.contains(el));

  for (const ss of document.styleSheets) {
    let rules;
    try { rules = [...ss.cssRules]; } catch { continue; }          // cross-origin
    const name = ss.href ? ss.href.split('/').pop().split('?')[0] : 'inspector';
    // the browser extension injects its own sheet; it is not ours
    if (rules.some(r => (r.cssText || '').includes('claude-pulse'))) continue;
    if (!ss.href && !rules.some(r => /^[.#]/.test(r.selectorText || ''))) continue;

    const flat = [];
    // r.style.cssText keeps the declarations AS AUTHORED. Iterating r.style
    // instead would hand back expanded longhands, and any shorthand written
    // with var() comes back empty -- border: var(--hair) solid var(--line)
    // becomes twelve blank border-* properties. Parse this on the Python side
    // with the same splitter used for the source file.
    const push = (ctx, r) => {
      if (!r.selectorText || !r.style) return;
      flat.push({ ctx, selector: r.selectorText, css: r.style.cssText });
    };
    for (const r of rules) {
      if (r.media && r.cssRules) {
        for (const inner of r.cssRules) push('@media ' + r.conditionText, inner);
      } else {
        push('', r);
      }
    }
    dump.css[name] = flat;
  }

  // only our own markup: the extension overlays its cursor and glow as fixed
  // divs with inline styles, and they are not edits anyone made
  for (const el of document.querySelectorAll('[style]')) {
    if (!ours(el)) continue;
    dump.inline.push({
      tag: el.tagName.toLowerCase(),
      cls: typeof el.className === 'string' ? el.className : '',
      text: (el.textContent || '').trim().slice(0, 50),
      style: el.getAttribute('style'),
    });
  }

  const captured = [];
  for (const el of document.querySelectorAll(BLOCK)) {
    if (!ours(el)) continue;
    if (captured.some(c => c.contains(el))) continue;   // nested inside a block
    captured.push(el);
    const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (text) {
      dump.blocks.push({
        tag: el.tagName.toLowerCase(),
        cls: typeof el.className === 'string' ? el.className : '',
        text,
      });
    }
  }

  // Diagram labels are copy too. They are kept apart from blocks and sorted,
  // because the hero diagram re-appends a layer on hover: document order in an
  // SVG is paint order, so it changes without anyone editing anything.
  dump.svg = [...document.querySelectorAll('svg text')]
    .filter(ours)
    .map(t => (t.textContent || '').replace(/\s+/g, ' ').trim())
    .filter(Boolean)
    .sort();

  // Markup, for the edits text cannot show. SVGs are left out: the hero
  // diagram toggles a class and re-appends a layer on hover. Buttons are left
  // out because the page's own script unhides and relabels them.
  dump.html = OWN.map(root => {
    const copy = root.cloneNode(true);
    copy.querySelectorAll('svg, button').forEach(n => n.remove());
    return copy.outerHTML.replace(/\s+/g, ' ');
  });
  // Text the BLOCK list does not reach. Renaming a nav link is a copy edit too.
  dump.loose = [];
  for (const root of OWN) {
    const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let node = walk.nextNode(); node; node = walk.nextNode()) {
      const text = node.nodeValue.replace(/\s+/g, ' ').trim();
      const el = node.parentElement;
      if (!text || !el) continue;
      if (el.closest('svg, button, script') || captured.some(c => c.contains(el))) continue;
      dump.loose.push(text);
    }
  }

  if (globalThis.__AT_LOAD) {
    dump.css0 = globalThis.__AT_LOAD.css;
    dump.html0 = globalThis.__AT_LOAD.html;
    dump.loose0 = globalThis.__AT_LOAD.loose;
  }

  if (globalThis.__SNAPSHOT_ONLY) return dump;

  const body = JSON.stringify(dump);
  return fetch('/__pull', { method: 'POST', body })
    .then(r => r.text())
    .then(t => `${t.trim()} — ${dump.blocks.length} text blocks, ` +
               `${dump.svg.length} diagram labels, ${dump.inline.length} inline styles`)
    .catch(e => 'POST failed (is preview.py running?): ' + e.message);
})()
