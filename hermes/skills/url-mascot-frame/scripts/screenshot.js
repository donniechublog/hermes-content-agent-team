#!/usr/bin/env node
/*
 * screenshot.js — high-DPR screenshot fallback.
 *
 * When a URL is NOT a single downloadable image (a text tweet, an article, a
 * generic page), we must screenshot it. A default 1x screenshot is soft; this
 * captures at deviceScaleFactor 3 (Retina), so the result is genuinely sharp
 * and needs no upscaler. Prefers the dominant content element (tweet/article/
 * main) over full-page chrome.
 *
 * Usage: node screenshot.js <url> <out.png>
 */
const path = require('path');

const url = process.argv[2];
const out = process.argv[3];
if (!url || !out) { console.error('usage: screenshot.js <url> <out.png>'); process.exit(1); }

const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36';

let chromium;
for (const cand of [path.join(__dirname, '..', 'node_modules', 'playwright'), 'playwright']) {
  try { ({ chromium } = require(cand)); break; } catch (e) { /* next */ }
}
if (!chromium) {
  console.error('playwright missing. Run: cd ' + path.join(__dirname, '..') +
                ' && npm i playwright && npx playwright install --with-deps chromium');
  process.exit(1);
}

(async () => {
  const browser = await chromium.launch({ args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  try {
    const ctx = await browser.newContext({
      deviceScaleFactor: 3,                       // Retina — 3x pixels, sharp
      viewport: { width: 820, height: 1100 },
      userAgent: UA,
    });
    const page = await ctx.newPage();
    await page.goto(url, { waitUntil: 'networkidle', timeout: 45000 }).catch(() => {});
    await page.waitForTimeout(1200);              // let late images/fonts settle

    // Prefer the dominant content block; fall back to the full page.
    let target = null;
    for (const sel of ['[data-testid="tweet"]', 'article', 'main', '.entry-content']) {
      const el = await page.$(sel);
      if (!el) continue;
      const box = await el.boundingBox().catch(() => null);
      if (box && box.width > 200 && box.height > 200) { target = el; break; }
    }
    if (target) await target.screenshot({ path: out });
    else await page.screenshot({ path: out, fullPage: true });

    console.log(out);
  } finally {
    await browser.close();
  }
})().catch((e) => { console.error(e && e.message ? e.message : e); process.exit(1); });
