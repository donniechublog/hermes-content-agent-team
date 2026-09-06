---
name: url-mascot-frame
description: >
  Turn any image URL (or web-page URL like an X/Twitter post) into a branded,
  shareable graphic: download/screenshot the source image, wrap it in a
  donniechu.com-branded frame (a cream card with a macOS-style title bar), and
  stamp it with a @donniechublog handle plus a mascot avatar
  whose expression matches the vibe of the image. Use this
  whenever the user gives a URL and wants it "framed", "made into a post",
  "branded", given a "khung"/"frame"/"watermark", or turned into content for
  @donniechublog — even if they just paste a link and say "làm frame cho cái
  này" or "wrap this". Especially for troll/meme screenshots.
---

# URL → Mascot Frame

Wrap a source image in the donniechu.com frame — a cream card with a black
hard-offset shadow and a macOS-style title bar — and stamp it with the
`@donniechublog` handle + a vibe-matched mascot. The header/footer bands and
the margin around the image *are* the frame; the image keeps its native aspect
ratio.

## The pipeline (4 steps)

1. **Get the source image onto disk** (from the URL).
2. **Judge the vibe** of that image and pick one matching mascot emoji.
3. **Run `scripts/frame.js`** to composite the frame + watermark.
4. **Show the result** to the user.

---

## Step 1 — Get the ORIGINAL source onto disk

Always fetch the CDN original — a platform-compressed variant or a screenshot is
soft, and no upscaler recovers detail that was never downloaded. Use the
deterministic resolver instead of hand-rolling curl:

```bash
python3 scripts/get_source.py "<URL>" /tmp/src.png
```

It handles every case: `pbs.twimg.com` → `name=orig` (full upload resolution);
an `x.com`/`instagram.com` **post** URL → social-crawl → the `media[]` CDN
original; any direct image URL → downloaded by **content-type** (works for
extensionless CDN links too).

For an **X photo post** the crawl endpoint hands back an empty `media[]`, and
`og:image` there is no longer the photo — X now serves a rendered card
(`jf.x.com/images/post/<id>.png`: author, truncated text, and a cropped, faded
thumbnail). So the resolver reads the `pbs.twimg.com/media/<id>` reference out of
the page HTML and rebuilds it at `name=orig`. Frame that, never the card.

For a **page** (a tweet, an article, a Facebook/social post) it grabs the post's
**own image** first — the `og:image`, fetched with a crawler UA (Facebook only
serves og tags / lookaside media to crawlers) — so you frame the picture in the
post, not a screenshot of the whole page. A **high-DPR (3×) screenshot** is the
last resort, used only when the page has no such image. All of this is inside
`get_source.py`; it exits non-zero only when the URL is genuinely unreachable.

Do not proceed until `/tmp/src.png` exists and is a valid image.

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
| 👋 | wave | a greeting, "hi/gm", welcome, hello-there |
| 🤫 | shush | a secret, "keep it quiet", don't-tell, low-key |
| 😤 | stern | not impressed, tough stance, "we don't do that here", arms-crossed |
| 😶 | speechless | no words, blank stare, "…", left speechless |
| 😇 | angel | wholesome/innocent, "who, me?", blessed, halo energy |
| 😗 | whistle | playing innocent, whistling away, "nothing to see here" |
| 🤓 | nerd | ackshually, technical/smart, spec detail, well-actually |
| 🤩 | starstruck | hyped, "let's gooo", amazed, big W excitement |
| 🫡 | salute | respect, "o7", acknowledged, aye-aye |
| 😱 | shock | scared/screaming, "oh no", horror, wtf-in-a-bad-way |
| 😮 | surprised | mild "oh!", a reveal, huh-didn't-expect-that |
| 💩 | poop | crap take, "this is garbage", trash, hot mess |

The full machine-readable list is in [assets/mood-palette.json](assets/mood-palette.json),
and [assets/mood-palette-sheet.png](assets/mood-palette-sheet.png) shows what each
one looks like. `frame.js` resolves the emoji → an actual mascot PNG on its own
via MascotStudio's `emoji-map.json`; you only choose the emoji.

If you cannot place the mood in the image, use 🙄 (eyeroll). It is the one
reaction that works in every situation, which is exactly why it is the fallback:
😂 is a specific claim that something is funny, and lands wrong on an image that
is not. Only reach for 😂 when the image really is a punchline. If two fit, pick
the funnier one — savage/absurd leans 💀, confusing leans 🤨/🤯.

---

## Step 3 — Composite the frame

```bash
node ~/.hermes/profiles/bob/skills/url-mascot-frame/scripts/frame.js \
  --image /tmp/src.png \
  --emoji "🙄" \
  --out ./framed.png
```

One donniechu.com preset: a cream card (`#f7f5f0`) with a black hard-offset
shadow and a macOS-style title bar, in JetBrains Mono. Fixed-height header +
footer bands, and **the canvas flexes to the source's native aspect ratio** —
no cropping to a square:

```
  ● ● ●            @donniechublog        ← header: macOS dots (left) + handle (right)
  ┌─────────────────────────┐
  │   source image, native  │           ← floated, no border, the star
  │   aspect, is the star   │
  └──────────────────────🤯─┘           ← mascot straddles the image's bottom-right
  >_ vibe working & agentic AI           ← footer: prompt
```

Options: `--avatar <png>` to force a specific mascot file, `--avatar-index N`
to pick a different avatar for that emoji, `--no-mascot` for text-only.
`--handle` defaults to `@donniechublog`. The header handle and the footer
prompt `>_ vibe working & agentic AI` are fixed brand marks; the mascot stays
your vibe-matched pick from Step 2, straddling the image's bottom-right corner
on the top layer so nothing clips it.

Prints a JSON summary (output path, canvas size, which avatar it used).

**Dependency:** the script needs `sharp`. The 20 palette avatars are **bundled**
in `assets/avatars/`, so the skill is self-contained and portable — copy the
folder to any machine and it works. It loads `sharp` from the skill's own
`node_modules` first (run `npm install` inside the skill folder once), then a
global `sharp`, then MascotStudio's copy. To pick an avatar *outside* the 20-mood
palette (rare), the script reads MascotStudio's `emoji-map.json`; set
`MASCOT_DIR=/path/to/MascotStudio` if that repo lives elsewhere. For the normal
troll palette you do **not** need MascotStudio present.

**Screenshot fallback (optional):** `get_source.py` only needs the browser for the
rare case where the URL is a page, not an image — it shells out to `screenshot.js`
(Playwright, deviceScaleFactor 3 for a sharp capture). Enable it once with:

```bash
npm install playwright && npx playwright install --with-deps chromium
```

If Playwright/Chromium is absent, direct-image and social-media resolution still
work; only the page-screenshot fallback is skipped (`get_source.py` then exits
non-zero for a page URL).

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
