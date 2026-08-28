---
name: url-mascot-frame
description: >
  Turn any image URL (or web-page URL like an X/Twitter post) into a branded,
  shareable graphic: download/screenshot the source image, wrap it in a
  donniechu.com-branded frame (one of three styles: terminal / glow /
  brutalist), and stamp it with a @donniechublog handle plus a mascot avatar
  whose expression matches the vibe of the image. Use this
  whenever the user gives a URL and wants it "framed", "made into a post",
  "branded", given a "khung"/"frame"/"watermark", or turned into content for
  @donniechublog — even if they just paste a link and say "làm frame cho cái
  này" or "wrap this". Especially for troll/meme screenshots.
---

# URL → Mascot Frame

Wrap a source image in a donniechu.com-branded frame (terminal / glow /
brutalist) and stamp it with the `@donniechublog` handle + a vibe-matched
mascot. The header/footer bands and the margin around the image *are* the
frame; the image keeps its native aspect ratio.

## The pipeline (4 steps)

1. **Get the source image onto disk** (from the URL).
2. **Judge the vibe** of that image and pick one matching mascot emoji.
3. **Run `scripts/frame.js`** to composite the frame + watermark.
4. **Show the result** to the user.

---

## Step 1 — Get the source image

Two kinds of URL:

**A. Direct image URL** (ends in `.jpg .jpeg .png .webp .gif`, or a CDN image
link). Download it:

```bash
curl -L -A "Mozilla/5.0" -o /tmp/src.png "<URL>"
```

**B. Web-page URL** (an X/Twitter post, a Reddit thread, an article, etc.) —
the "image" is the visible content, so screenshot it with the browser:

- Open the in-app Browser: `preview_start` with `{url: "<URL>"}` (or `navigate`).
- If there's one dominant image/card (a tweet, a meme), use `read_page` +
  `find` to locate that element and `scroll_to` it, then take a `computer`
  `screenshot`. For a tweet, capture the post card itself (avatar + text +
  media) — that whole card becomes the framed image, exactly like the user's
  reference example.
- Save the screenshot bytes to `/tmp/src.png`. If the screenshot has extra
  chrome around it, crop to the content first (sharp or the browser's `zoom`
  region) so the frame hugs the real content.

If a page is really just a wrapper around one image, prefer grabbing the
underlying image file (its `src`) and downloading it per case A — it's sharper
than a screenshot.

Do not proceed until `/tmp/src.png` (or your chosen path) actually exists and is
a valid image.

---

## Step 2 — Pick the mascot expression

Look at the source image and choose the **one** emoji whose reaction best fits
the *joke or feeling the image gives the viewer* — not a literal description of
what's in it. Most of this account's images are troll/meme, so the palette is a
tight set of reaction faces:

| emoji | mood | reach for it when… |
|-------|------|--------------------|
| 😂 | laugh | it's straightforwardly funny / hits the punchline |
| 😅 | nervous-laugh | funny but a bit "oof", awkward, too real |
| 😎 | cool | flex, W, smug confidence, "we won" |
| 👍 | approve | wholesome, "based", agreeing, a clean take |
| 🤔 | thinking | makes you ponder, a genuine question, hmm |
| 🤨 | skeptical | side-eye, "sure buddy", doubtful, sus |
| 🙄 | eyeroll | tired of this, cliché, obvious ragebait |
| 😐 | deadpan | no-comment, the joke *is* the flatness |
| 🫠 | dead-inside | painful truth, "this is fine", burnout humor |
| 🤯 | mindblown | plot twist, wild fact, wtf-in-a-good-way |
| 🤡 | clown | self-own, cope, "we are the clowns", L take |
| 😜 | playful | silly, cheeky, chaotic-good energy |
| 🙈 | facepalm | secondhand embarrassment, cringe, "no…" |
| 💀 | dead | "I'm dead", brutally funny, savage |
| 😈 | mischief | trolling on purpose, mischievous, spicy |
| 🤖 | robot | AI/tech joke, "beep boop", automation, botposting |
| 👻 | ghost | ghosted, spooky, disappeared, dead silence |
| 🤑 | money | money/greed, "pay up", get-rich, $$$ energy |
| 😵‍💫 | dizzy | overwhelmed, information overload, spun-out, tilted |
| 😮‍💨 | exhausted | relief sigh, burnt out, "finally", exhausted |

The full machine-readable list is in [assets/mood-palette.json](assets/mood-palette.json),
and [assets/mood-palette-sheet.png](assets/mood-palette-sheet.png) shows what each
one looks like. `frame.js` resolves the emoji → an actual mascot PNG on its own
via MascotStudio's `emoji-map.json`; you only choose the emoji.

If none fit, 😂 is a safe default for this account. If two fit, pick the funnier
one — savage/absurd leans 💀, confusing leans 🤨/🤯.

---

## Step 3 — Composite the frame

```bash
node ~/.hermes/profiles/bob/skills/url-mascot-frame/scripts/frame.js \
  --image /tmp/src.png \
  --frame terminal \
  --emoji "😂" \
  --out ./framed.png
```

The frame carries the donniechu.com brand voice (deep navy, cyan, JetBrains
Mono, macOS window chrome). Layout is a fixed-height header + footer wrapping
the image, and **the canvas flexes to the source's native aspect ratio** — no
cropping to a square:

```
  ● ● ●   @donniechublog                 ← header: macOS dots + handle
  ┌─────────────────────────┐
  │   source image, native  │           ← floated, per-style border
  │   aspect, is the star   │
  └─────────────────────────┘
  >_ vibe working & agentic AI     🤯    ← footer: prompt (cyan) + mascot
```

Three styles via `--frame` (default `terminal`):
- **`terminal`** — dark `#0e1117` code-window: title-bar divider, rounded image
  card, soft drop shadow, cyan prompt. The everyday dark card.
- **`glow`** — deeper `#0a0a14`, cyan glow top-left + blue glow bottom-right, no
  divider. Minimal; lets a striking image breathe.
- **`brutalist`** — light cream `#f7f5f0`, thick black border + hard offset
  shadow, black-outlined dots. Bold; for light feeds / carousels.

Other options: `--avatar <png>` to force a specific mascot file, `--avatar-index
N` to pick a different avatar for that emoji, `--no-mascot` for text-only.
`--handle` defaults to `@donniechublog`. The header handle and the footer
prompt `>_ vibe working & agentic AI` are fixed brand marks; the mascot
(bottom-right) stays your vibe-matched pick from Step 2.

Prints a JSON summary (output path, canvas size, which avatar it used).

**Dependency:** the script needs `sharp`. The 20 palette avatars are **bundled**
in `assets/avatars/`, so the skill is self-contained and portable — copy the
folder to any machine and it works. It loads `sharp` from the skill's own
`node_modules` first (run `npm install` inside the skill folder once), then a
global `sharp`, then MascotStudio's copy. To pick an avatar *outside* the 20-mood
palette (rare), the script reads MascotStudio's `emoji-map.json`; set
`MASCOT_DIR=/path/to/MascotStudio` if that repo lives elsewhere. For the normal
troll palette you do **not** need MascotStudio present.

---

## Step 4 — Show the result

Send the finished PNG to the user with `SendUserFile` (display `render`) so they
see it inline. Mention which expression you picked and why in one line, so they
can ask for a different mood if they disagree. If they want a tweak, re-run
Step 3 with a different `--emoji` or `--avatar-index` — no need to re-download.

## Notes & good defaults

- Output naming: default `./framed.png`; if you make several in one session,
  number them (`framed-1.png`, …) so nothing gets overwritten.
- Very tall or very wide sources still work; the frame scales to the shorter
  side, and sources wider than 1600px are downscaled for a sane output size.
- Keep the handle exactly `@donniechublog` unless the user says otherwise.
- This skill only brands images the user brings via a URL. It is not for
  designing graphics from scratch — for that, reach for a design tool instead.
