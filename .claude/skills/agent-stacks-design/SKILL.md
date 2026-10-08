---
name: agent-stacks-design
description: Read before changing anything under site/ on agent-stacks.org — the page, its styles, its copy, or the component gallery. Encodes the edit hierarchy (token, then component, then markup), the voice rules, the factual claims the page is allowed to make, and the preview loop. Use whenever the task touches site/index.html, site/components.html, site/tokens.css, site/components.css, site/llms.txt, or asks to adjust how the site looks, reads, or is worded.
---

# Changing agent-stacks.org

The site is deliberately plain: four files, no build step, no framework, no dependencies.
`site/` deploys verbatim to GitHub Pages. Keep it that way.

The look and feel will take many rounds. The system below exists so that round fifty is as
cheap as round one and nothing erodes along the way.

## Read first

- `BRAND.md` at the repo root — positioning, voice, palette rationale, accuracy constraints.
  That is the *what*. This file is the *how*.

## The edit hierarchy

Work top-down. Stop at the first level that can carry the change.

1. **A token** (`site/tokens.css`) — anything about color, size, spacing, or type.
   One edit, everything follows. This is where most feedback should land.
2. **A component** (`site/components.css`) — anything about how a kind of thing looks.
   Every instance follows. Never style an instance.
3. **Markup** (`site/index.html`) — only when the *content or structure* changes.

If you find yourself about to write a value into `index.html`, you are at the wrong level.
Go up.

## Routing vague feedback

| When the note is… | Edit |
|---|---|
| "too dark", "wrong orange", "needs more contrast" | `tokens.css` color block — **both themes** |
| "too cramped", "needs more air", "tighten that up" | `tokens.css` space scale, or the component's own padding |
| "text is too small/big", "hard to read" | `tokens.css` type scale. `--lh-body` and `--measure` are load-bearing for monospace prose; changing one usually means changing the other |
| "the terminal blocks look wrong" | `.term*` in `components.css` |
| "the diagram is confusing", "the roadmap looks wrong" | the inline SVG in `index.html` plus `.parts*` in `components.css`. The hero and the roadmap are the same component |
| "that sentence is off" | `index.html`, and mirror it into `site/llms.txt` |
| "it feels generic / like AI wrote it" | run the anti-slop checklist in `BRAND.md` §6 |

## Hard rules

- **No literal values outside `tokens.css`.** No hex, no px/rem/em/ch, no inline `style=`.
  The one exception is a `@media` breakpoint, because custom properties cannot be read inside
  a media condition. Record new breakpoints in the `breakpoints` comment in `tokens.css`.
- **No external requests.** No Google Fonts, no CDN, no analytics. Fonts are self-hosted in
  `site/fonts/`. Two cross-origin round trips before first paint is the exact latency this
  project argues against.
- **No motion.** No typing effect, no scroll reveal, no transition beyond an instant color
  change. This is a stated principle, not a preference.
- **Links stay underlined.** `.brand` is the single documented exception; it is an image link.
- **Every component appears in `components.html`.** If you add a class, add it to the gallery
  in all its states. The checker enforces this.
- **Dark and light are both designed.** Never ship a token change that only looks right in one.
- **Claims are constrained.** `sandbox`, `secrets`, `local model`, `model routing`, and `hooks`
  may appear only inside `<section id="roadmap">`. The spec does not cover them, and saying
  otherwise is the fastest way to lose the only readers who matter. The checker enforces this.

## The loop

```sh
python3 .claude/scripts/preview.py          # serves site/ on :8137, no caching
```

Then open **both** pages:

- `http://localhost:8137/components.html` — the gallery. Review component changes here first;
  it has a theme toggle so you can see dark and light without touching OS settings.
- `http://localhost:8137/index.html` — the page.

Check at **1440, 768, and 375** wide, in **both themes**. The body must never scroll
horizontally; wide things scroll inside their own container.

After every change: `python3 .claude/scripts/check-site.py`.

## Pulling DevTools edits back into source

Daniel tightens copy and design directly in Chrome DevTools. Those edits are real and they are
lost on reload, so pull them **before** anything reloads the tab.

The preview server also autosaves them, as a safety net and not as the workflow. See
"If the edits were lost" below.

**1. Snapshot the live page.** Run this one line in the page (via the browser tooling's
javascript tool, or paste it in the DevTools console):

```js
await eval(await (await fetch('/__dump.js')).text())
```

`preview.py` serves `browser-dump.js` at `/__dump.js` — it lives outside `site/` so it never
ships — and the snapshot POSTs itself back to `.claude/scratch/dump.json`.

**2. See what changed.**

```sh
python3 .claude/scripts/pull-from-browser.py .claude/scratch/dump.json
```

It reports, classified by where the fix belongs. It never writes.

| Bucket | What it means | Where it goes |
|---|---|---|
| `TOKEN` | a value changed in a `tokens.css` rule | the token — **and its other theme** |
| `COMPONENT` | a declaration changed in a `components.css` rule | the component |
| `INLINE` | an element gained a `style` attribute | **never copy across.** Promote it |
| `NEW` | DevTools created a rule | decide where it belongs first |
| `MARKUP` | a tag or attribute changed: an `href`, a class, an element added or removed | the markup |
| `COPY` | text differs from `index.html` | the markup, then mirror to `llms.txt` |

A declaration shows up under `TOKEN` or `COMPONENT` whether its value changed, it was added
(`(not set) -> value`), or it was removed (`value -> (removed)`). Unchecking a declaration in the
Styles panel counts as removing it.

**3. Apply through the hierarchy, not literally.** The report tells you what the browser has;
it does not tell you where the change belongs. A padding tweaked on one `.term` is usually a
token or a component change, not a one-off. An `INLINE` finding is *always* a prompt to ask
"which token or component should carry this?" — the system forbids inline style, and copying
it across would be the first crack.

**4. `check-site.py`, then reload** to confirm the file now produces what the browser had.

### If the edits were lost

A stray click on a link, or a reload, throws the page away. `preview.py` adds a script to
`index.html` as it serves it (the file on disk is untouched) that snapshots the page every two
seconds while it is being edited, and once more on the way out. The latest snapshot is at
`.claude/scratch/autosave.json`:

```sh
python3 .claude/scripts/pull-from-browser.py .claude/scratch/autosave.json
```

The report starts with when the snapshot was saved. Read that line: an autosave from before the
last sync reports edits that were already applied. A freshly loaded page saves nothing until it
is edited, so the reloaded page cannot overwrite the copy of the one that was lost. If editing
did resume after the accident, the lost page is one generation back, in `autosave.prev.json`.
Delete both files once they have been reconciled.

Autosave runs on `index.html` only, because that is the only page the reconciler knows.

### Gotchas, learned the hard way

- **Reloading discards everything.** Pull first. Autosave is the fallback, not the plan.
- **Added and removed declarations, and `MARKUP`, come from comparing the page with itself at
  load**, not with the source files. The browser expands some shorthands (`font: inherit` becomes
  eleven longhands), so against the source every one of those would read as an edit. The
  autosave script records the page at load, which means a snapshot only has these checks when it
  was taken from `index.html` as `preview.py` served it. The report says so when they are
  missing. This was added after a pull missed a `border-top` that had been removed.
- **Header and footer text is not a block.** Nav links, the footer, and the brand name sit
  outside the `BLOCK` list, so they are compared with the page at load and reported under `COPY`
  as loose text.
- **`MARKUP` does not look inside SVGs or at buttons.** The hero diagram toggles a class and
  re-appends a layer on hover, and the page's own script relabels the copy buttons. Geometry
  edited in a diagram by hand in DevTools will not be reported.
- **Diagram labels are compared as a bag of strings, not in order.** The hero diagram re-appends
  a layer on hover, which reorders the SVG without anyone editing it. A changed label shows up as
  a `(diagram)` line in `COPY`.
- Iterating a CSSOM rule gives expanded *longhands*, and any shorthand written with `var()`
  comes back empty — `border: var(--hair) solid var(--line)` becomes twelve blank `border-*`
  properties. `browser-dump.js` captures `r.style.cssText` instead, which is the authored form.
  Do not "simplify" it back.
- `tokens.css` has six separate `:root` blocks on purpose. The reconciler keeps all of them and
  matches by property overlap; collapsing them by selector loses the palette.
- The CSSOM rewrites some shorthands when it serialises (`flex: none` becomes `0 0 auto`).
  Those are the browser talking, not an edit. Add them to `EQUIV` in
  `pull-from-browser.py` when a property you did not touch shows up as a difference.
- The `BLOCK` selector list in `browser-dump.js` and in `pull-from-browser.py` must stay
  identical, nesting rule included. If they drift, the copy diff fills with phantom moves and
  buries the one line that actually changed.

## What the checker catches

`python3 .claude/scripts/check-site.py` — stdlib only, no dependencies.

Literal values outside tokens · undefined or dead tokens · WCAG contrast computed for every
declared pair in both themes · off-origin assets · components missing from the gallery ·
un-underlined links · heading order · and the claim lint above.

A warning is worth reading. A failure means do not commit.

## Things that are the way they are on purpose

Do not "fix" these without asking:

- **One font family.** Monospace for everything, including prose. It is the motif.
- **`--measure: 72ch` and `--lh-body: 1.75`.** Monospace prose is only readable with room.
- **The `#` / `##` heading prefixes** use `content: "##" / ""` so screen readers hear the
  heading and not the punctuation. Keep the empty alt text.
- **The page is short.** Hero, the problem, an example stack, where to start, the roadmap,
  open development. It was three times this long once, with a summary of the
  specification, an implementations table, and a diagram of package managers and harnesses.
  Those were cut on purpose: the page states the problem, the solution, and the next step, and
  the specification speaks for itself. Do not add a section back without asking.
- **The roadmap is the hero's diagram with a status per layer**, not a list. Today, in
  progress, and planned are each carried by the bar's outline and by a word. It is the one
  place that says what is covered today.
- **Dashed bars in the roadmap** are planned layers. Dashed has always meant "not built yet"
  on this site.
- **The brand mark is three bands with a hollow middle**, sized at `--mark` (28px). Below that
  the bands stop reading. It was redrawn once already for exactly this reason.

## On release day

When a capability ships, the site diff is small and obvious: in the roadmap diagram, give its
bar `parts__bar--shipped` and its status word `parts__label--shipped`, and move the bar's
`<rect>` to the end of the group so its outline paints last. Add it to the list in the
roadmap's intro sentence, and mirror both into `site/llms.txt`. That is the whole change.
