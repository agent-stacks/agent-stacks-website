# Agent-Stacks.org Website

The static site behind [agent-stacks.org](https://agent-stacks.org), hosted on
GitHub Pages.

No build step, no framework, no dependencies. Everything in `site/` is deployed
exactly as it sits on disk.

## Layout

```
site/                     # published docroot — everything here is deployed as-is
  index.html              # the page. markup only, no literal values
  components.html         # component gallery (noindex) — review changes here first
  tokens.css              # the ONLY file where a literal value may appear
  components.css          # every component class, built from tokens
  fonts/                  # self-hosted IBM Plex Mono (latin + box-drawing symbols)
  llms.txt                # the page as plain text, for the agents in the audience
  favicon.svg
  CNAME                   # custom domain (agent-stacks.org)
  .nojekyll               # serve files verbatim, no Jekyll processing

BRAND.md                  # positioning, voice, palette, and the claims the page may make
.claude/
  skills/agent-stacks-design/SKILL.md   # how to make a change without causing drift
  scripts/check-site.py                 # the drift alarm. stdlib only
  scripts/preview.py                    # local preview, DevTools pull, and autosave
.github/workflows/pages.yml
```

## Changing the site

Read [`BRAND.md`](BRAND.md) first, then
[`.claude/skills/agent-stacks-design/SKILL.md`](.claude/skills/agent-stacks-design/SKILL.md).

The short version: **a change lands at the highest level that can carry it.** A
color or a size is a token. How a kind of thing looks is a component. Only
content and structure are markup. If you are writing a value into `index.html`,
you are at the wrong level.

`components.html` and `index.html` load the same two stylesheets, so the gallery
and the page cannot drift apart visually. Review component changes in the
gallery, where every state sits side by side and a toggle switches themes.

## Checking

```sh
python3 .claude/scripts/check-site.py
```

Catches literal values outside `tokens.css`, undefined or dead tokens, WCAG
contrast failures in either theme, off-origin assets, components missing from
the gallery, un-underlined links, broken heading order, and copy that claims
more than the specification covers.

## Local preview

```sh
python3 .claude/scripts/preview.py
# then open http://localhost:8137
```

Serves `site/` with caching off, so an edit shows up on reload.

## Pulling edits back from DevTools

Tweak copy and design live in Chrome DevTools, then capture it. In the page:

```js
await eval(await (await fetch('/__dump.js')).text())
```

```sh
python3 .claude/scripts/pull-from-browser.py .claude/scratch/dump.json
```

The report classifies every difference as `TOKEN`, `COMPONENT`, `INLINE`,
`NEW`, or `COPY`, so each one gets applied at the level that makes it stick
instead of as a one-off patch. It reports; it never writes.

**Pull before you reload** — DevTools edits do not survive a refresh.

If they are lost anyway, to a stray click or a reload, the preview server has a copy. It
snapshots `index.html` every two seconds while it is being edited:

```sh
python3 .claude/scripts/pull-from-browser.py .claude/scratch/autosave.json
```

## Deploying

Every push to `main` runs `.github/workflows/pages.yml`, which uploads `site/`
and deploys it to GitHub Pages. It can also be triggered manually from the
Actions tab.

One-time repo setup: **Settings → Pages → Build and deployment → Source:
GitHub Actions**, then set the custom domain to `agent-stacks.org` and enable
"Enforce HTTPS" once the DNS check passes.
