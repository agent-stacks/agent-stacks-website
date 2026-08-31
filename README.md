# Agent-Stacks.org Website

The static site behind [agent-stacks.org](https://agent-stacks.org), hosted on
GitHub Pages.

## Layout

```
site/                     # published docroot — everything here is deployed as-is
  index.html
  CNAME                   # custom domain (agent-stacks.org)
  .nojekyll               # serve files verbatim, no Jekyll processing
.github/workflows/pages.yml
```

## Local preview

Anything that serves a directory works:

```sh
python3 -m http.server -d site 8000
# then open http://localhost:8000
```

## Deploying

Every push to `main` runs `.github/workflows/pages.yml`, which uploads `site/`
and deploys it to GitHub Pages. It can also be triggered manually from the
Actions tab.

One-time repo setup: **Settings → Pages → Build and deployment → Source:
GitHub Actions**, then set the custom domain to `agent-stacks.org` and enable
"Enforce HTTPS" once the DNS check passes.
