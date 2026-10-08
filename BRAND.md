# Agent Stacks — brand and voice

The source of truth for how agent-stacks.org looks and sounds. If you are changing the site,
read this first, then `.claude/skills/agent-stacks-design/SKILL.md` for how to make the change.

---

## 1. What we are

An open specification for putting an agent's parts on disk as one unit: a harness, its plugins,
and the runtimes both need.

**What we are not:** a package manager, a product, a Flox feature, or a sandbox.

### The position

Agent parts should be composable and portable, so that people can see what their agent is made
of and change any part of it.

The page does not argue this. It shows it, through the problem and the solution: two users
whose agents differ, and one unit that makes them the same. That is the same call as leaving
the vision doc's three-word list off the page.

Do not frame the position against the frontier labs on the site. An earlier draft did, with
"one vendor, one bundle, one way", and it came off. The specification needs harness providers
to adopt it, and the vision doc does not take that line either.

### The commitment (proposed, not adopted)

**1.0.0 is reserved until at least one maintainer outside Flox owns part of this.**

This is a proposal. Do not print it. It is a governance promise made on Flox's behalf, and it
appears nowhere else: not in the specification, not on the live site, not in the vision doc.
Whether to make it is the team's decision, in the same way that a byline is the named person's.

It is worth proposing. A specification with one sponsor gains more from a commitment that costs
something than from any amount of copy. If the team adopts it, it is one sentence in "Open
development".

### The sponsor

Flox wrote the first implementation and pays for the infrastructure. Say so plainly, once, in
the footer and in the open-development section. Do not borrow Flox's purple, Flox's type, or
Flox's logo. A standard that looks like a vendor's product does not get adopted by that
vendor's competitors, and competitors adopting it is the entire goal.

---

## 2. Who reads this

Four audiences. The page serves them in this order.

| Audience | Wants | Lands on |
|---|---|---|
| **Agent users** | Minimal setup. Just run the thing. | The example command |
| **Agent maintainers** | Compose a stack, distribute it, update it | `mkAgentStack` |
| **Agent part authors** | Package and ship skills and MCP servers | `agent-stacks import` |
| **Implementers** | Should my package manager support this? | The spec |

Agent users may be non-technical. Everyone else is deep in a terminal. Write for the terminal
and keep the first command short enough that anyone can paste it.

---

## 3. Voice

Short sentences. Short phrases. Plain words, with the occasional ten-dollar word for texture.
Oxford commas. Grade-school reading level wherever the subject allows it.

### Steal from the repos before writing anything new

The project already writes better than most marketing sites. Use its own sentences.

> An agent is a stack of interchangeable components: a harness, skills, MCP servers,
> configuration, and runtimes. These stacks are traditionally assembled by hand, so no two
> machines run quite the same agent.

> One machine has a newer Claude Code, another is missing the `python3` that a skill's script
> needs, and a third has an older version of a plugin.

> A stack's closure bounds the agent, not every binary the agent can reach.

> a stack is neither a plugin nor an agent, it is the two of them wired together

> That's the whole upgrade!

### Do

- Name real things. `claude-code 2.1.284`, not "your favorite agent."
- Use real numbers. 307 plugins. 5 harnesses. 20 skills.
- State limits as sharply as capabilities. The honest boundary is the credibility.
- Let a sentence end early.

### Don't

- **No triads.** Three-part slogans read as generated. The vision doc's "inspectable, composable,
  reproducible" is left off the page on purpose: the page shows those qualities through the
  problem and the solution instead of naming them.
- **No balanced em-dash clauses.** The rhythm where every sentence has a turn in the middle.
- **No "seamlessly," "powerful," "robust," "effortlessly," "unlock," "leverage," "transform."**
- **No "In a world where…"** or any framing that starts above the problem.
- **No feature grid of four identical cards.** It is the reliable tell. Use prose, a table, or
  a transcript.
- **No claims without an artifact.** If we say it works, show the command and its output.
- **No invented community.** We have zero outside contributors today. The invitation is honest;
  the thriving ecosystem is not.

### Spelling

American English. Flox is a US company, Daniel writes American, and every adjacent site in this
ecosystem — agent-plugins.org, agentskills.io, modelcontextprotocol.io, agents.md — is American.
Behavior, organization, standardize, recognize, color, license.

### Terminology

We say **harness**. The spec says **agent client**, and explains the mapping itself in §3:
*"An implementation is free to call the same thing by a name its users will recognize."*

The page says harness everywhere and never says agent client, so there is nothing on it to
gloss. Keep it that way. If the page ever has to use "agent client", gloss it once, where it
first appears. `llms.txt` carries the mapping for agents that read both.

---

## 4. Accuracy constraints

These are enforced by `.claude/scripts/check-site.py`. They exist because the obvious copy
overstates, and overstating is how a spec site loses the only readers who matter.

- **5 harnesses, not 170.** `agent-pkgs/lib/mk-agent-stack.nix` defines
  `knownAdapters = [ "agent-deck" "claude" "codex" "opencode" "pi" ]`. The ~170 figure is
  `numtide/llm-agents.nix`'s whole catalogue. 56 of those are classified as agents. Five can be
  a stack's harness.
- **307 plugins.** The guides say "a couple hundred" and undercount their own repo.
- **No sandboxes, secrets, hooks, local models, or model routing as present features.**
  Spec §5.3: *"Not a sandbox. A stack bounds what its agent brings with it, not what the agent
  can reach once running."* These belong in the roadmap section and nowhere else.
- **A stack does not ship an operating system.** Nix pins a stack's dependencies instead of an
  OS image, on Linux down to glibc, so a stack does not ask for a particular OS and a co-worker
  on a different one gets the same stack. The drift diagram leaves the OS out for that reason,
  which is what lets the lede say a stack ships "all of these parts". Do not explain this in
  the hero; "above the OS" was tried there and it confused more than it clarified.
- **OS-specific parts are still fair game.** A stack can give one OS one package and another OS
  a different one, such as seatbelt on macOS and bubblewrap on Linux. That costs some
  reproducibility and is often worth it. Do not rule a part out because it is OS-specific.
- **Spec 0.1.0 is a draft**, described internally as an experiment that will change often. Never
  imply it is settled. The page carries no "draft" label; that came off the header and footer on
  purpose, to save space. The roadmap section does the job instead, by showing what is still in
  progress and planned. Proof that it is early beats a label saying so.
- **The spec defines no requirements of its own.** §2 says so. Every MUST comes from Agent
  Plugins, Agent Skills, or MCP.
- **Prerequisites are real.** Flakes enabled, git, three platforms. Intel Mac is explicitly
  unsupported.

---

## 5. Look

Dark is the default. Light is a designed variant, not an inversion.

### The motif

**The page renders like a document in a pager.** Headings carry a literal `#` prefix. Blockquotes
carry `>`. Lists carry `-`. Commands sit behind `$`.

It is instantly legible to developers, it is internally consistent, and it is not a thing that
gets produced by accident. That is the whole point.

### Color

Every value lives in `site/tokens.css` and nowhere else.

| Token | Dark | Light | Use |
|---|---|---|---|
| `--ground` | `#0C0D0E` | `#FAF9F6` | page background |
| `--panel` | `#141618` | `#F1EFEA` | terminal blocks, tables, diagrams |
| `--line` | `#23262A` | `#DFDBD2` | hairlines |
| `--text` | `#D6D6D2` | `#1A1917` | body |
| `--muted` | `#8E9398` | `#5A5751` | captions, output, labels |
| `--accent` | `#E8824F` | `#A63D16` | links, `#` prefixes, the mark, one emphasis per diagram |

Rust, because the field is already full of purple, blue, and monochrome. Flox owns `#711aff`
and magenta. Stay off both.

Accent is rationed. If it is on more than a tenth of the page, it is being misused.

### Type

One family: IBM Plex Mono, weights 400, 500, and 600. Self-hosted from `site/fonts/`, latin plus
a small symbol subset for box drawing. No Google Fonts, no CDN, no external request of any kind.

Prose at 16px with 1.75 line-height, capped at 72 characters. Monospace prose is only readable
if you give it room; do not tighten either number.

### Motion

None. No typing effect, no scroll reveal, no transition beyond an instant color change on hover.

Animation that delays interaction is banned outright. This is also quietly differentiating —
every competitor's terminal block types itself at you.

### Accessibility

Accessibility beats beauty whenever they disagree.

- Links are always underlined. Never `text-decoration: none` on an anchor.
- 4.5:1 contrast minimum on every pair, in both themes.
- Visible focus rings. Skip link. Sequential heading order.
- No meaning carried by color alone.
- Wide content scrolls inside its own container. The page body never scrolls sideways.

---

## 6. The anti-slop checklist

Before publishing a change, read the page and ask:

1. Is there a sentence here only a person with an opinion would write?
2. Is there a real artifact on screen — a command, a path, a version, a tree?
3. Does anything claim more than `check-site.py` allows?
4. Did a four-card grid sneak in?
5. Are there triads? Count them. The answer should be zero.

### On naming people

Every spec site that reads as human — semver.org, keepachangelog.com, mise.jdx.dev — names a
person, and every one that reads as generated does not. We know this and have chosen not to,
for now: the page carried a byline briefly and it came off, because attribution is the named
person's call and nobody has agreed to it.

So this is a decision, not an oversight. If attribution goes back on, confirm it with the people
named first. Until then item 1 is carrying the weight alone, which makes it matter more.
