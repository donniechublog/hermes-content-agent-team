#!/usr/bin/env node
/*
 * frame.js — wrap a source image in a branded donniechu.com frame with a
 * mood-matched mascot watermark + @handle.
 *
 * One donniechu.com frame preset: a cream card with a black hard-offset shadow
 * and a macOS-style title bar. Fixed-height header + footer bands; the image
 * keeps its native aspect ratio and the canvas flexes to it.
 *
 *   header band : macOS window dots + @handle (right)
 *   image       : native aspect, floated, no border
 *   footer band : `>_ vibe working & agentic AI` (left) + mascot (straddling)
 *
 * The source image must already be on disk. This script only does the
 * deterministic compositing so the visual result is repeatable.
 *
 * Usage:
 *   node frame.js --image <src.png> --emoji "😂" --out <out.png>
 *
 * Options:
 *   --image        (required) path to the source image
 *   --out          output path (default: ./framed.png)
 *   --emoji        emoji whose mood matches the image; resolves a mascot avatar
 *   --avatar       explicit avatar png path (overrides --emoji)
 *   --avatar-index which avatar to pick from the emoji's list (default 0)
 *   --handle       header handle text (default @donniechublog)
 *   --no-mascot    render the frame + handle only, no mascot
 *
 * Mascot assets come from MascotStudio; override its location with MASCOT_DIR.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');

const MASCOT_DIR = process.env.MASCOT_DIR || '/Users/donniechu/Documents/Codex/MascotStudio';

const SKILL_ROOT = path.join(__dirname, '..');
const BUNDLED_AVATARS = path.join(SKILL_ROOT, 'assets', 'avatars');
const FONT_DIR = path.join(SKILL_ROOT, 'assets', 'fonts');

// Register the bundled brand font (JetBrains Mono) with fontconfig BEFORE sharp
// initialises librsvg — otherwise SVG <text> falls back to a generic mono. We
// point a private fontconfig at both the system font dirs and the skill's own
// font folder, so it stays portable (no need to install fonts system-wide).
try {
  if (fs.existsSync(FONT_DIR)) {
    const cacheDir = path.join(os.tmpdir(), 'umf-fontcache');
    fs.mkdirSync(cacheDir, { recursive: true });
    const conf = `<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <dir>/usr/share/fonts</dir>
  <dir>/usr/local/share/fonts</dir>
  <dir>/Library/Fonts</dir>
  <dir>/System/Library/Fonts</dir>
  <dir>${os.homedir()}/.fonts</dir>
  <dir>${os.homedir()}/.local/share/fonts</dir>
  <dir>${FONT_DIR}</dir>
  <cachedir>${cacheDir}</cachedir>
</fontconfig>`;
    const confPath = path.join(cacheDir, 'fonts.conf');
    fs.writeFileSync(confPath, conf);
    process.env.FONTCONFIG_FILE = confPath;
  }
} catch (e) { /* fall back to system fonts + generic monospace stack */ }

// Prefer sharp bundled with the skill (portable), then a global one, then
// MascotStudio's copy — so the skill runs on any machine after `npm i`.
let sharp;
for (const cand of [
  path.join(SKILL_ROOT, 'node_modules', 'sharp'),
  'sharp',
  path.join(MASCOT_DIR, 'node_modules', 'sharp'),
]) {
  try { sharp = require(cand); break; } catch (e) { /* try next */ }
}
if (!sharp) {
  console.error('Could not load "sharp". Run:  cd ' + SKILL_ROOT + ' && npm install');
  console.error('(or set MASCOT_DIR to a folder whose node_modules has sharp).');
  process.exit(1);
}

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  if (i === -1) return def;
  if (name === 'no-mascot') return true;
  return process.argv[i + 1];
}
const hasFlag = (name) => process.argv.includes('--' + name);

const imagePath = arg('image');
const outPath = arg('out', path.resolve('framed.png'));
const emoji = arg('emoji', '');
let avatarPath = arg('avatar', '');
const avatarIndex = parseInt(arg('avatar-index', '0'), 10) || 0;
const handle = arg('handle', '@donniechublog');
const noMascot = hasFlag('no-mascot');

if (!imagePath) { console.error('Missing required --image <path>'); process.exit(1); }
if (!fs.existsSync(imagePath)) { console.error('Image not found: ' + imagePath); process.exit(1); }

const CLEAN_DIR = path.join(MASCOT_DIR, 'assets', 'preview', 'clean');

// Resolve an avatar filename to a real path: bundled copy first (portable),
// then MascotStudio's clean folder.
function avatarPathFor(file) {
  const bundled = path.join(BUNDLED_AVATARS, file);
  if (fs.existsSync(bundled)) return bundled;
  const external = path.join(CLEAN_DIR, file);
  if (fs.existsSync(external)) return external;
  return null;
}

// The bundled palette pins an exact avatar file per emoji (curated look).
function paletteFile(emojiKey) {
  try {
    const palette = JSON.parse(fs.readFileSync(path.join(SKILL_ROOT, 'assets', 'mood-palette.json'), 'utf8'));
    const hit = palette.find((e) => e.emoji === emojiKey);
    if (hit && hit.file) return avatarPathFor(hit.file);
  } catch (e) { /* no palette; fall through */ }
  return null;
}

function resolveAvatar(emojiKey, index) {
  if (index === 0) {
    const pinned = paletteFile(emojiKey);
    if (pinned) return pinned;
  }
  try {
    const emojiMap = JSON.parse(fs.readFileSync(path.join(MASCOT_DIR, 'metadata', 'emoji-map.json'), 'utf8'));
    const manifest = JSON.parse(fs.readFileSync(path.join(MASCOT_DIR, 'metadata', 'manifest.json'), 'utf8'));
    const id2file = {};
    manifest.forEach((e) => { id2file[e.id] = e.filename; });
    const ids = emojiMap[emojiKey];
    if (!ids || !ids.length) return paletteFile(emojiKey);
    const id = ids[index % ids.length];
    return avatarPathFor(id2file[id]);
  } catch (e) {
    return paletteFile(emojiKey);
  }
}

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// donniechu.com brand tokens (read from the live site's CSS).
const MONO = "'JetBrains Mono','JetBrainsMono-Regular','JetBrains Mono NL',ui-monospace,'DejaVu Sans Mono','Noto Sans Mono',monospace";
const PROMPT = '>_ vibe working & agentic AI';
const DOTS = ['#ff5f57', '#febc2e', '#28c840']; // macOS traffic lights

// The single donniechu.com frame preset: cream card, black hard offset shadow,
// macOS title bar. Brand tokens read from the live site's CSS. The image floats
// inside with NO border of its own.
const S = {
  bg: '#f7f5f0', windowBorder: '#0a0a0a', divider: '#0a0a0a',
  dotStroke: '#0a0a0a',
  handleColor: '#555555', promptColor: '#0a0a0a',
  cardRadiusK: 0.016, outerRadiusK: 0.014, shadowPadK: 0.028,
};

(async () => {
  if (!noMascot && !avatarPath && emoji) {
    avatarPath = resolveAvatar(emoji, avatarIndex);
    if (!avatarPath) console.error('Note: no mascot found for emoji "' + emoji + '", rendering without one.');
  }

  // --- load + normalize source ---
  let srcBuf = await sharp(imagePath).rotate().toBuffer();
  let meta = await sharp(srcBuf).metadata();
  const MAXW = 1600;
  if (meta.width > MAXW) {
    srcBuf = await sharp(srcBuf).resize({ width: MAXW }).toBuffer();
    meta = await sharp(srcBuf).metadata();
  }
  const W = meta.width, H = meta.height;
  const short = Math.min(W, H);
  const R = Math.round;

  // --- frame geometry (header + image + footer; canvas flexes to the image) ---
  const side = R(short * 0.09);
  // Top/bottom bands kept close to the side margin so the frame reads balanced
  // on all four edges (they used to be much thicker than the left/right margin).
  const headerH = R(short * 0.10);      // thin title bar: dots + @handle
  const footerH = R(short * 0.10);      // thin footer: prompt (mascot overlaps the image)
  const radius = Math.max(8, R(short * S.cardRadiusK));   // source card corners
  const outerR = Math.max(6, R(short * S.outerRadiusK));  // card / window corners
  const thick = Math.max(2, R(short * 0.005));            // black window border + divider (halved)
  const gapTop = R(short * 0.04);                        // breathing room below the title bar
  const cardW = W + side * 2;
  const cardH = H + headerH + gapTop + footerH;
  const shadowPad = R(short * S.shadowPadK);              // hard offset shadow room
  const CW = cardW + shadowPad;
  const CH = cardH + shadowPad;
  const imgTop = headerH + gapTop;                       // push the image clear of the toolbar

  // --- background: cream card, black hard offset shadow, black title-bar rule
  const hw = thick / 2;
  const bgInner = `
  <rect x="${shadowPad}" y="${shadowPad}" width="${cardW}" height="${cardH}" rx="${outerR}" ry="${outerR}" fill="#0a0a0a"/>
  <rect x="${hw}" y="${hw}" width="${cardW - thick}" height="${cardH - thick}" rx="${outerR}" ry="${outerR}" fill="${S.bg}" stroke="${S.windowBorder}" stroke-width="${thick}"/>
  <line x1="0" y1="${headerH}" x2="${cardW}" y2="${headerH}" stroke="${S.divider}" stroke-width="${thick}"/>`;
  const bgSvg = Buffer.from(`<svg width="${CW}" height="${CH}" xmlns="http://www.w3.org/2000/svg">${bgInner}
</svg>`);
  const base = sharp(bgSvg).png();

  const layers = [];

  // --- source image: rounded corners, NO border, floated in the card ---
  const mask = Buffer.from(
    `<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg"><rect width="${W}" height="${H}" rx="${radius}" ry="${radius}"/></svg>`
  );
  const card = await sharp(srcBuf).composite([{ input: mask, blend: 'dest-in' }]).png().toBuffer();
  layers.push({ input: card, left: side, top: imgTop });

  // --- header: macOS dots + @handle ---
  const dotD = Math.max(6, R(headerH * 0.28));
  const dotR = dotD / 2;
  const dotGap = R(dotD * 0.7);
  const dotCy = R(headerH / 2);
  let dotsSvg = '';
  for (let i = 0; i < 3; i++) {
    const cx = side + dotR + i * (dotD + dotGap);
    const stroke = S.dotStroke ? ` stroke="${S.dotStroke}" stroke-width="${Math.max(1, R(thick / 2))}"` : '';
    dotsSvg += `<circle cx="${cx}" cy="${dotCy}" r="${dotR}" fill="${DOTS[i]}"${stroke}/>`;
  }
  // @handle: smaller text, anchored to the RIGHT edge of the header (dots left,
  // handle right → the title bar is balanced at both ends).
  const headerFont = R(headerH * 0.34);
  const headerBase = R(headerH / 2 + headerFont * 0.35);
  const headerWeight = 700;
  const handleRight = cardW - side;
  const headerSvg = Buffer.from(`<svg width="${CW}" height="${CH}" xmlns="http://www.w3.org/2000/svg">
  ${dotsSvg}
  <text x="${handleRight}" y="${headerBase}" text-anchor="end" font-family="${MONO}" font-size="${headerFont}" font-weight="${headerWeight}" letter-spacing="0.3" fill="${S.handleColor}">${esc(handle)}</text>
</svg>`);
  layers.push({ input: headerSvg, left: 0, top: 0 });

  // --- footer: `>_ vibe working & agentic AI` (left) + mascot (right) ---
  const footFont = R(footerH * 0.36);
  const footBase = cardH - R(footerH / 2) + R(footFont * 0.35);
  const footWeight = 700;
  const promptSvg = Buffer.from(`<svg width="${CW}" height="${CH}" xmlns="http://www.w3.org/2000/svg">
  <text x="${side}" y="${footBase}" font-family="${MONO}" font-size="${footFont}" font-weight="${footWeight}" fill="${S.promptColor}">${esc(PROMPT)}</text>
</svg>`);
  layers.push({ input: promptSvg, left: 0, top: 0 });

  // mascot watermark — bottom-right corner (inset by `side`, unchanged). It
  // STRADDLES the seam between the footer band and the image: vertical centre
  // sits exactly on the image's bottom edge, so the lower half is on the border
  // and the upper half is on the image. Pushed LAST → top-most layer, so the
  // image can't clip the half that sits over it.
  let chosenAvatar = null;
  if (!noMascot && avatarPath && fs.existsSync(avatarPath)) {
    chosenAvatar = avatarPath;
    const avH = R(short * 0.16);
    const avBuf = await sharp(avatarPath).resize({ height: avH }).png().toBuffer();
    const am = await sharp(avBuf).metadata();
    const seamY = cardH - footerH;            // image bottom edge = footer top
    const avX = cardW - side - am.width;      // bottom-right, inset by side
    const avY = seamY - R(am.height / 2);      // centre on the seam: half border, half image
    layers.push({ input: avBuf, left: Math.max(0, avX), top: Math.max(0, avY) });
  }

  await base.composite(layers).png().toFile(outPath);

  console.log(JSON.stringify({
    out: outPath,
    frame: 'donnie',
    canvas: { width: CW, height: CH },
    source: { width: W, height: H },
    emoji: emoji || null,
    avatar: chosenAvatar ? path.basename(chosenAvatar) : null,
    handle,
  }, null, 2));
})().catch((e) => { console.error(e); process.exit(1); });
