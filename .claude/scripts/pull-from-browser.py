#!/usr/bin/env python3
"""
pull-from-browser.py — reconcile DevTools edits with the files on disk.

    python3 .claude/scripts/pull-from-browser.py /path/to/dump.json

Reads the snapshot produced by browser-dump.js and reports what the live page
has that the source does not, classified by where the fix belongs:

    TOKEN      a value changed in tokens.css      -> edit the token
    COMPONENT  a declaration changed in a rule    -> edit the component
    INLINE     an element gained a style attr     -> promote to token/component
    MARKUP     a tag or attribute changed         -> edit index.html
    COPY       text differs from the source       -> edit index.html (+ llms.txt)

A declaration that was added or removed, and markup that changed without its
text changing, are found by comparing the page with itself at load. Those need
a snapshot from a page preview.py served, which is where that record is kept.

It reports; it does not write. Values are normalized loosely, so read the
output rather than trusting it blindly — the browser rewrites some values
(0 becomes 0px, colors may change case) and those show up as noise.
"""
import collections
import difflib
import html
import json
import pathlib
import re
import sys
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parents[2]
SITE = ROOT / "site"

# ---------------------------------------------------------------- css parsing
COMMENT = re.compile(r"/\*.*?\*/", re.S)


def parse_css(text: str) -> dict:
    """{(context, selector): [ {prop: value}, ... ]} — flattens one level of
    @media. The value is a LIST because a selector legitimately appears more
    than once: tokens.css has six separate :root blocks (palette, type, space,
    layout, ...), and collapsing them loses whichever came first."""
    text = COMMENT.sub("", text)
    out: dict = {}

    def rules(body: str, ctx: str) -> None:
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", body):
            selector = " ".join(m.group(1).split())
            if selector.startswith("@"):
                continue
            decls = {}
            for d in m.group(2).split(";"):
                if ":" not in d:
                    continue
                prop, _, val = d.partition(":")
                decls[prop.strip()] = " ".join(val.split())
            if decls:
                out.setdefault((ctx, selector), []).append(decls)

    # pull @media blocks out first, then parse what remains at top level
    depth, start, media = 0, None, []
    for i, ch in enumerate(text):
        if text.startswith("@media", i) and depth == 0:
            start = i
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                media.append(text[start : i + 1])
                start = None
    rest = text
    for block in media:
        rest = rest.replace(block, "")
        head, _, body = block.partition("{")
        rules(body.rsplit("}", 1)[0], " ".join(head.split()))
    rules(rest, "")
    return out


def split_decls(text: str) -> dict:
    """Split a declaration block on top-level semicolons. Depth- and
    quote-aware, so url(a;b) and content strings survive."""
    out, buf, depth, quote = {}, [], 0, ""
    for ch in text:
        if quote:
            if ch == quote:
                quote = ""
            buf.append(ch)
            continue
        if ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == ";" and depth == 0:
            d = "".join(buf)
            buf = []
            if ":" in d:
                prop, _, val = d.partition(":")
                out[prop.strip()] = " ".join(val.split())
            continue
        buf.append(ch)
    d = "".join(buf)
    if ":" in d:
        prop, _, val = d.partition(":")
        out[prop.strip()] = " ".join(val.split())
    return out


# The CSSOM rewrites some shorthands when it serialises them. These are not
# edits; they are the browser talking. Add to this table when a property shows
# up as a difference you did not make.
EQUIV = {
    "flex": {"none": "0 0 auto", "auto": "1 1 auto", "1": "1 1 0%"},
    "font": {},
    "background": {"none": "none"},
}


def norm(prop: str, v: str) -> str:
    v = v.replace(",", " ")                    # "3 3" vs "3, 3"
    v = " ".join(v.split()).strip().lower().rstrip(";")
    v = re.sub(r"\b0(px|rem|em|%)\b", "0", v)  # "0px" vs "0"
    v = v.replace('"', "'")                    # quote style in font stacks
    return EQUIV.get(prop, {}).get(v, v)


# ------------------------------------------------------------- html text pull
# Must mirror BLOCK in browser-dump.js exactly, including the nesting rule:
# an element inside an already-captured one is not captured again. Without
# that, the two sides disagree about ordering and the diff fills with phantom
# moves that bury the one line that actually changed.
BLOCK = {
    "h1": None, "h2": None, "h3": None, "p": None, "li": None,
    "pre": None, "figcaption": None,
    "span": {"chip", "term__label", "term__note", "quote__cite",
             "ledger__name", "ledger__note", "ledger__state",
             "impl__name", "impl__note", "impl__state"},
    "code": {"term__cmd"},
}
OWN_ROOTS = {"header", "main", "footer"}
COMMENT_HTML = re.compile(r"<!--.*?-->", re.S)


def _is_block(tag: str, cls: str) -> bool:
    if tag not in BLOCK:
        return False
    allowed = BLOCK[tag]
    if allowed is None:
        return True
    return bool(allowed & set(cls.split()))


class Blocks(HTMLParser):
    VOID = {"br", "img", "hr", "meta", "link", "input", "source", "use", "path",
            "polygon", "rect", "circle", "line", "area", "col", "embed"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0            # nesting depth of any open tag
        self.in_own = 0           # inside header/main/footer
        self.capturing = None     # [tag, cls, depth, parts] or None
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        self.depth += 1
        if tag in OWN_ROOTS:
            self.in_own += 1
            return
        if self.capturing is None and self.in_own:
            cls = dict(attrs).get("class", "")
            if _is_block(tag, cls):
                self.capturing = [tag, cls, self.depth, []]

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if self.capturing and self.capturing[2] == self.depth:
            t, cls, _, parts = self.capturing
            text = " ".join("".join(parts).split())
            if text:
                self.out.append({"tag": t, "cls": cls, "text": text})
            self.capturing = None
        if tag in OWN_ROOTS and self.in_own:
            self.in_own -= 1
        self.depth -= 1

    def handle_data(self, data):
        if self.capturing:
            self.capturing[3].append(data)


def source_blocks(path: pathlib.Path) -> list:
    p = Blocks()
    p.feed(path.read_text())
    return p.out


# -------------------------------------------------------------------- compare
def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    dump = json.loads(pathlib.Path(sys.argv[1]).read_text())
    findings = {"TOKEN": [], "COMPONENT": [], "INLINE": [], "MARKUP": [], "COPY": [], "NEW": []}
    if dump.get("savedAt"):
        # an autosave, not a snapshot taken just now: say how old it is, because
        # a stale one reports edits that were already applied
        print(f'autosave from {dump["savedAt"]}  (page loaded {dump.get("loadedAt", "?")})')

    for name, live_rules in dump.get("css", {}).items():
        label = "TOKEN" if name == "tokens.css" else "COMPONENT"
        src_path = SITE / name
        if not src_path.exists():
            if name == "inspector":
                for r in live_rules:
                    findings["NEW"].append(f'new rule {r["selector"]} -> {r.get("css","")}')
            continue
        src = parse_css(src_path.read_text())
        for rule in live_rules:
            key = (rule["ctx"], rule["selector"])
            blocks = src.get(key)
            if blocks is None:
                # the CSSOM reorders selector lists; try a set-equal match
                for k, v in src.items():
                    if k[0] == rule["ctx"] and sorted(
                        x.strip() for x in k[1].split(",")
                    ) == sorted(x.strip() for x in rule["selector"].split(",")):
                        blocks = v
                        break
            if not blocks:
                continue
            # several blocks may share a selector; the right one is whichever
            # declares the most of the same properties
            live = split_decls(rule.get("css", ""))
            live_props = set(live)
            want = max(blocks, key=lambda b: len(live_props & set(b)))
            if not (live_props & set(want)):
                continue
            for prop, value in live.items():
                if prop not in want:
                    continue
                if norm(prop, value) != norm(prop, want[prop]):
                    ctx = f'{rule["ctx"]} ' if rule["ctx"] else ""
                    findings[label].append(
                        f'{name}  {ctx}{rule["selector"]}\n'
                        f'      {prop}:  {want[prop]}   ->   {value}'
                    )

    # Declarations added to or removed from a rule. The loop above only sees a
    # property that is on both sides, and has to: the browser expands some
    # shorthands (font: inherit becomes eleven longhands), so against the source
    # file every one of those would read as an edit. Against the page's own CSS
    # at load there is nothing to mistake.
    for name, live_rules in dump.get("css", {}).items():
        if "css0" not in dump:
            break
        label = "TOKEN" if name == "tokens.css" else "COMPONENT"
        load_rules = dump["css0"].get(name, [])
        if [(r["ctx"], r["selector"]) for r in load_rules] != [(r["ctx"], r["selector"]) for r in live_rules]:
            findings["NEW"].append(f"{name}: a rule was added, removed, or had its selector edited")
            continue
        for was_rule, now_rule in zip(load_rules, live_rules):
            was, now = split_decls(was_rule.get("css", "")), split_decls(now_rule.get("css", ""))
            ctx = f'{now_rule["ctx"]} ' if now_rule["ctx"] else ""
            for prop in was.keys() - now.keys():
                findings[label].append(
                    f'{name}  {ctx}{now_rule["selector"]}\n'
                    f'      {prop}:  {was[prop]}   ->   (removed)')
            for prop in now.keys() - was.keys():
                findings[label].append(
                    f'{name}  {ctx}{now_rule["selector"]}\n'
                    f'      {prop}:  (not set)   ->   {now[prop]}')

    # Tags and attributes: an href, a class, an element added or taken away.
    # Text is not compared here; COPY has it.
    if "html0" in dump:
        def tags(parts):
            return [t for part in parts for t in re.findall(r"<[^>]+>", part)]
        was_tags, now_tags = tags(dump["html0"]), tags(dump.get("html", []))
        sm = difflib.SequenceMatcher(None, was_tags, now_tags, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            for line in was_tags[i1:i2]:
                findings["MARKUP"].append(f"- {line}")
            for line in now_tags[j1:j2]:
                findings["MARKUP"].append(f"+ {line}")

    # Text outside every block: nav links, the footer, the brand name. The
    # source parser only knows blocks, so this too is the page against itself.
    if "loose0" in dump:
        was_loose, now_loose = dump["loose0"], dump.get("loose", [])
        sm = difflib.SequenceMatcher(None, was_loose, now_loose, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            for line in was_loose[i1:i2]:
                findings["COPY"].append(f"- (header, footer, or other loose text) {line}")
            for line in now_loose[j1:j2]:
                findings["COPY"].append(f"+ (header, footer, or other loose text) {line}")

    for el in dump.get("inline", []):
        findings["INLINE"].append(
            f'<{el["tag"]} class="{el["cls"]}">  style="{el["style"]}"\n'
            f'      near: {el["text"]!r}'
        )

    def flat(b):
        return " ".join(b["text"].replace("\u00a0", " ").split())

    live_text = [flat(b) for b in dump.get("blocks", [])]
    src_text = [flat(b) for b in source_blocks(SITE / "index.html")]
    sm = difflib.SequenceMatcher(None, src_text, live_text, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        for line in src_text[i1:i2]:
            findings["COPY"].append(f"- {line}")
        for line in live_text[j1:j2]:
            findings["COPY"].append(f"+ {line}")

    # Diagram labels. Compared as a bag of strings, not in order: the hero
    # diagram re-appends a layer on hover, which reorders the DOM by itself.
    if "svg" in dump:
        src_svg = collections.Counter(
            " ".join(html.unescape(t).split())
            for t in re.findall(r"<text\b[^>]*>(.*?)</text>",
                                COMMENT_HTML.sub("", (SITE / "index.html").read_text()), re.S)
        )
        live_svg = collections.Counter(dump["svg"])
        for line in sorted((src_svg - live_svg).elements()):
            findings["COPY"].append(f"- (diagram) {line}")
        for line in sorted((live_svg - src_svg).elements()):
            findings["COPY"].append(f"+ (diagram) {line}")

    order = ["TOKEN", "COMPONENT", "INLINE", "NEW", "MARKUP", "COPY"]
    hints = {
        "TOKEN":     "edit site/tokens.css — remember BOTH themes",
        "COMPONENT": "edit site/components.css — every instance follows",
        "INLINE":    "do NOT copy these across. Promote to a token or a component",
        "NEW":       "rules DevTools created. Decide where they belong first",
        "MARKUP":    "tags or attributes changed. Edit site/index.html",
        "COPY":      "edit site/index.html, then mirror into site/llms.txt",
    }
    total = 0
    for k in order:
        if not findings[k]:
            continue
        total += len(findings[k])
        print(f"\n=== {k} ({len(findings[k])})  — {hints[k]}")
        for f in findings[k]:
            print(f"  {f}")

    if "css0" not in dump:
        print("\nnote: this snapshot has no record of the page at load, so a declaration that was")
        print("      added or removed, a changed href or class, and text in the header or footer")
        print("      cannot be seen. Take it from a page preview.py served.")
    print(f"\n{total} change(s) to reconcile." if total else "\nNo differences from source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
