#!/usr/bin/env python3
"""
check-site.py — the drift alarm for agent-stacks.org.

Stdlib only. Run from the repo root:

    python3 .claude/scripts/check-site.py

It enforces the rules in BRAND.md so that fifty rounds of "make that tighter"
cannot quietly erode the system:

  1. Literal values live in tokens.css and nowhere else.
  2. No inline style= attributes.
  3. Every var(--x) used is defined; every token defined is used.
  4. WCAG contrast, computed, in both themes.
  5. Nothing on the page reaches outside the origin.
  6. Every component class is reviewable in components.html.
  7. Links stay underlined; headings stay in order.
  8. Claim lint: the page may not overstate what the spec covers.
"""
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
TOKENS = SITE / "tokens.css"
COMPONENTS = SITE / "components.css"
INDEX = SITE / "index.html"
GALLERY = SITE / "components.html"

fails: list[str] = []
warns: list[str] = []


def fail(check: str, msg: str) -> None:
    fails.append(f"{check}: {msg}")


def warn(check: str, msg: str) -> None:
    warns.append(f"{check}: {msg}")


def read(p: pathlib.Path) -> str:
    return p.read_text() if p.exists() else ""


# -- 1. literal values only in tokens.css ---------------------------------
# The one legitimate literal elsewhere is a stroke-width on SVG primitives and
# the 0/none/inherit family, which carry no design decision.
def strip_comments(css: str) -> str:
    """Multi-line aware. A line-based strip misses a px value sitting on the
    second line of a /* ... */ block and reports it as a stray literal."""
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
LEN = re.compile(r"(?<![\w-])\d*\.?\d+(px|rem|em|ch|vw|vh)\b")
# Custom properties are not readable inside @media conditions, so breakpoints
# are the one place a literal length is unavoidable. They are listed in the
# "breakpoints" comment block in tokens.css so there is still one place to look.
ALLOWED_LEN_PROPS = ("stroke-width", "stroke-dasharray", "@media")


def check_literals() -> None:
    # blank the comments but keep line numbering intact
    raw = read(COMPONENTS)
    blanked = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group()), raw, flags=re.S)
    for i, line in enumerate(blanked.splitlines(), 1):
        code = line
        if HEX.search(code):
            fail("literals", f"components.css:{i} hex color — move it to tokens.css")
        if LEN.search(code) and not any(p in code for p in ALLOWED_LEN_PROPS):
            fail("literals", f"components.css:{i} raw length — add a token instead")

    for p in (INDEX, GALLERY):
        html = read(p)
        for i, line in enumerate(html.splitlines(), 1):
            if "<style" in line or "style=" in line:
                fail("literals", f"{p.name}:{i} inline style — belongs in components.css")
            # hex inside inline SVG markup is a design decision in the wrong file
            if HEX.search(line) and "favicon" not in line:
                fail("literals", f"{p.name}:{i} hex color in markup — use a CSS class")


# -- 2 & 3. token hygiene --------------------------------------------------
DEF = re.compile(r"^\s*(--[\w-]+)\s*:", re.M)
USE = re.compile(r"var\(\s*(--[\w-]+)")


def check_tokens() -> None:
    tokens = read(TOKENS)
    defined = set(DEF.findall(tokens))
    if not defined:
        fail("tokens", "tokens.css defines nothing — is the file there?")
        return

    used: set[str] = set()
    for p in (COMPONENTS, INDEX, GALLERY, TOKENS):
        used |= set(USE.findall(read(p)))

    for t in sorted(used - defined):
        fail("tokens", f"{t} is used but never defined in tokens.css")
    for t in sorted(defined - used):
        warn("tokens", f"{t} is defined but never used — dead token")


# -- 4. contrast -----------------------------------------------------------
def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _lum(hexs: str) -> float:
    h = hexs.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a: str, b: str) -> float:
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# (foreground, background, minimum). 4.5 for text, 3.0 for structure.
PAIRS = [
    ("--text", "--ground", 4.5), ("--text", "--panel", 4.5),
    ("--muted", "--ground", 4.5), ("--muted", "--panel", 4.5),
    ("--accent", "--ground", 4.5), ("--accent", "--panel", 4.5),
    ("--line-2", "--ground", 3.0), ("--line-2", "--panel", 3.0),
]


def theme_palettes() -> dict[str, dict[str, str]]:
    """Pull the dark block and the [data-theme=light] block out of tokens.css."""
    css = read(TOKENS)
    blocks = {}
    m = re.search(r":root\s*\{(.*?)\n\}", css, re.S)
    if m:
        blocks["dark"] = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})", m.group(1)))
    m = re.search(r':root\[data-theme="light"\]\s*\{(.*?)\n\}', css, re.S)
    if m:
        blocks["light"] = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})", m.group(1)))
    return blocks


def check_contrast() -> None:
    for theme, pal in theme_palettes().items():
        for fg, bg, minimum in PAIRS:
            if fg not in pal or bg not in pal:
                fail("contrast", f"{theme}: {fg} or {bg} missing from the palette")
                continue
            r = contrast(pal[fg], pal[bg])
            if r < minimum:
                fail("contrast", f"{theme}: {fg} on {bg} is {r:.2f}:1, needs {minimum}:1")


# -- 5. no external requests ----------------------------------------------
EXTERNAL_IN_ASSETS = re.compile(r"(src|href)\s*=\s*[\"']https?://", re.I)
BANNED_HOSTS = ("fonts.googleapis", "fonts.gstatic", "cdn.", "cdnjs", "unpkg",
                "jsdelivr", "googletagmanager", "google-analytics", "plausible")


def check_external() -> None:
    for p in (INDEX, GALLERY, COMPONENTS, TOKENS):
        text = read(p)
        for host in BANNED_HOSTS:
            if host in text:
                fail("external", f"{p.name} references {host} — self-host it")
        if p.suffix == ".css":
            for m in re.finditer(r"url\(\s*[\"']?(https?://[^)\"']+)", text):
                fail("external", f"{p.name} loads {m.group(1)} — self-host it")
        else:
            for m in EXTERNAL_IN_ASSETS.finditer(text):
                line = text[: m.start()].count("\n") + 1
                tag = text[max(0, m.start() - 200) : m.start()]
                # <a href> to another site is content, not an asset request.
                if re.search(r"<a\b[^>]*$", tag, re.S):
                    continue
                fail("external", f"{p.name}:{line} loads an off-origin asset")


# -- 6. gallery coverage ---------------------------------------------------
def check_gallery() -> None:
    css = strip_comments(read(COMPONENTS))
    gallery = read(GALLERY)
    index = read(INDEX)
    # class selectors only: a dot preceded by selector punctuation, not a filename
    classes = set(re.findall(r"(?:^|[\s,>+~({])\.([a-z][\w-]*)", css, re.M))
    # pseudo/state selectors and the gallery harness itself are not components
    classes = {c for c in classes if not c.startswith("gal")}
    for c in sorted(classes):
        if c not in gallery:
            fail("gallery", f".{c} is styled but not shown in components.html")
    for c in sorted(classes):
        if c not in gallery and c not in index:
            warn("gallery", f".{c} is styled but used nowhere")


# -- 7. links and heading order -------------------------------------------
def check_links_and_headings() -> None:
    css = read(COMPONENTS)
    for i, line in enumerate(css.splitlines(), 1):
        if "text-decoration: none" in line and ".brand" not in css.splitlines()[max(0, i - 2)]:
            # .brand is the single documented exception: it is an image link.
            ctx = "\n".join(css.splitlines()[max(0, i - 3) : i])
            if ".brand" not in ctx:
                fail("links", f"components.css:{i} removes a link underline")

    for p in (INDEX, GALLERY):
        html = read(p)
        if not html:
            continue
        levels = [int(m) for m in re.findall(r"<h([1-6])\b", html)]
        if levels and levels[0] != 1:
            fail("headings", f"{p.name} does not start at h1")
        for a, b in zip(levels, levels[1:]):
            if b > a + 1:
                fail("headings", f"{p.name} jumps from h{a} to h{b}")
        if html.count("<h1") > 1:
            fail("headings", f"{p.name} has more than one h1")


# -- 8. claim lint ---------------------------------------------------------
# These may appear only inside the roadmap, which is the section that exists
# to say they are NOT covered yet. Anywhere else they overstate the spec.
ROADMAP_OPEN = re.compile(r'<section\b[^>]*\bid="roadmap"[^>]*>')
CLAIMS = ["sandbox", "secrets", "local model", "model routing", "hooks"]

# The lint cannot tell "the spec covers sandboxes" (overclaiming) from "an agent
# has a sandbox" (naming the problem). An escape hatch, with a toll: the reason
# has to be written down and has to say something. A bare marker does not pass.
CLAIM_OK = re.compile(r"<!--\s*claim-ok\(([a-z ]+?)\):\s*(.+?)\s*-->", re.I | re.S)
MIN_REASON = 25


def check_claims() -> None:
    html = read(INDEX)
    if not html:
        return
    roadmap = ""
    m = ROADMAP_OPEN.search(html)
    if m:
        end = html.find("</section>", m.start())
        roadmap = html[m.start() : end if end != -1 else len(html)]
    else:
        fail("claims", 'no <section id="roadmap"> found — the claim lint cannot scope itself')
    outside = html.replace(roadmap, "") if roadmap else html
    # strip the markers themselves: an excuse that mentions the word it
    # excuses would otherwise always satisfy its own check
    outside = CLAIM_OK.sub("", outside)

    excused = {}
    for word, reason in CLAIM_OK.findall(html):
        word = word.strip().lower()
        if len(reason.strip()) < MIN_REASON:
            fail("claims", f'claim-ok for "{word}" needs a real reason, not {reason.strip()!r}')
        else:
            excused[word] = reason.strip()

    for claim in CLAIMS:
        if claim not in outside.lower():
            continue
        if claim in excused:
            print(f'  note  claims: "{claim}" allowed outside the roadmap — {excused[claim]}')
            continue
        fail("claims", f'"{claim}" appears outside the roadmap — the spec does not cover it.\n'
                       f'        If this names a part of an agent rather than claiming spec\n'
                       f'        coverage, excuse it: <!-- claim-ok({claim}): why -->')

    for word in excused:
        if word not in outside.lower():
            warn("claims", f'claim-ok for "{word}" is no longer needed — remove it')

    if re.search(r"\b170\b\s*(\+|harness)", outside, re.I):
        fail("claims", "170 is the llm-agents.nix catalogue, not the harness count. Five work today.")
    for n in ("0.1.0",):
        if n not in html:
            warn("claims", f'"{n}" is missing from the page')


def main() -> int:
    for fn in (check_literals, check_tokens, check_contrast, check_external,
               check_gallery, check_links_and_headings, check_claims):
        fn()

    for w in warns:
        print(f"  warn  {w}")
    for f in fails:
        print(f"  FAIL  {f}")

    print()
    if fails:
        print(f"{len(fails)} failure(s), {len(warns)} warning(s)")
        return 1
    print(f"clean — {len(warns)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
