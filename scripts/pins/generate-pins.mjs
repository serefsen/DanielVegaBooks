import { chromium } from 'playwright';
import { posts } from '../../src/data/posts.js';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..', '..');
const OUT_DIR = join(ROOT, 'public', 'pins');
mkdirSync(OUT_DIR, { recursive: true });

const SITE = 'https://danielvegabooks.com';
const MODEL = process.env.OPENROUTER_MODEL || 'anthropic/claude-opus-4.8';
const OR_KEY = process.env.OPENROUTER_API_KEY;
if (!OR_KEY) { console.error('FATAL: OPENROUTER_API_KEY yok'); process.exit(1); }

// boardKey -> Pinterest board ID (Tailwind)
const BOARDS = {
  'teen-help':        '1097963652845484894',
  'coping':           '1097963652845484904',
  'calm-grounding':   '1097963652845484913',
  'social':           '1097963652845484920',
  'test-performance': '1097963652845484922',
  'parenting':        '1097963652845484924',
  'back-to-school':   '1097963652845484926',
};

const clean = (s) => String(s || '')
  .replace(/â€™/g, "'").replace(/â€œ/g, '"').replace(/â€\u009d/g, '"')
  .replace(/â€"/g, '—').replace(/Â/g, '').trim();
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const clamp = (s, n) => { s = String(s || '').trim(); return s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s; };

const post = posts[0];
if (!post) { console.error('FATAL: posts[0] yok'); process.exit(1); }
const title = clean(post.title);
const excerpt = clean(post.excerpt);
const tag = clean(post.tag) || 'Teen anxiety';
const bodySample = Array.isArray(post.body) ? clean(post.body.slice(0, 2).join('\n')) : '';
const destUrl = `${SITE}/blog/${post.slug}`;

// ---------- KITAP KAPAGI (her tip pininde ust yariyi kaplar) ----------
const COVERS = [
  '../../public/image/186545.png',
  '../../public/image/oubn.png',
  '../../public/image/q3nnp.png',
];
const COVER_BOX = {
  'tip-a': [620, 700, 60], 'tip-c': [600, 670, 60], 'tip-b': [560, 540, 200],
};
const coverDiv = (src, layout) => {
  const [w, h, t] = COVER_BOX[layout] || [600, 670, 60];
  return `<div style="position:absolute; left:50%; top:${t}px; transform:translateX(-50%); width:${w}px; height:${h}px; z-index:4;">` +
         `<img src="${src}" alt="" style="width:100%; height:100%; object-fit:contain; display:block;"></div>`;
};
let _ch = 0; for (const c of post.slug) _ch = (_ch * 31 + c.charCodeAt(0)) >>> 0;
const COVER_SRC = COVERS[_ch % COVERS.length];

// --- Dedup guard: ayni yaziyi iki kez pinleme ---
const STATE = join(OUT_DIR, 'last-pinned.json');
let lastSlug = null;
if (existsSync(STATE)) { try { lastSlug = JSON.parse(readFileSync(STATE, 'utf8')).slug; } catch {} }
if (post.slug === lastSlug) {
  console.log(`Bu yazi zaten pinlendi: ${post.slug} — atlaniyor (yeni yazi yok).`);
  writeFileSync('/tmp/pins.json', '[]');
  process.exit(0);
}

const sys = `You write Pinterest pin copy for "Daniel Vega Books" — calm, practical anxiety workbooks for teenagers (audience: parents, teachers, anxious teens). Return ONLY valid minified JSON (no markdown) with keys:
"pinHeadline" (<=46 chars, calm punchy hook for the pin image, sentence case, no quotation marks),
"pinSub" (<=90 chars, one supportive line for the image),
"ctaText" (<=26 chars, e.g. "Read the full post →"),
"pinterestTitle" (<=100 chars, keyword-rich, front-load keywords),
"pinterestDescription" (<=470 chars, keyword-rich and natural, mention a free anxiety toolkit softly, end with 3-5 relevant hashtags),
"altText" (<=120 chars, factual description of the pin image),
"boardKey" (exactly one of: ${Object.keys(BOARDS).join(', ')} — the single best topical fit).
Warm, non-cringe tone. Never sexualize or romantically address minors.`;

const usr = `Blog post:
Title: ${title}
Tag: ${tag}
Excerpt: ${excerpt}
Body sample: ${bodySample}
Destination URL: ${destUrl}`;

async function genCopy() {
  const r = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${OR_KEY}`, 'Content-Type': 'application/json', 'X-Title': 'DanielVegaBooks Pins' },
    body: JSON.stringify({ model: MODEL, temperature: 0.7, max_tokens: 1024, messages: [{ role: 'system', content: sys }, { role: 'user', content: usr }] }),
  });
  if (!r.ok) throw new Error(`OpenRouter ${r.status}: ${await r.text()}`);
  const data = await r.json();
  let txt = (data.choices?.[0]?.message?.content || '').replace(/```json/gi, '').replace(/```/g, '').trim();
  const a = txt.indexOf('{'), b = txt.lastIndexOf('}');
  if (a >= 0 && b >= 0) txt = txt.slice(a, b + 1);
  return JSON.parse(txt);
}

function pickLayout(slug) {
  const L = ['tip-a', 'tip-b', 'tip-c'];
  let h = 0; for (const c of slug) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return L[h % 3];
}

async function render(layout, f, outPath) {
  const tpl = readFileSync(join(__dirname, `${layout}.html`), 'utf8');
  const html = tpl
    .replaceAll('{{KICKER}}', esc(f.kicker))
    .replaceAll('{{HEADLINE}}', esc(f.headline))
    .replaceAll('{{SUB}}', esc(f.sub))
    .replaceAll('{{CTA}}', esc(f.cta))
    .replace('<div class="pin">', '<div class="pin">' + coverDiv(COVER_SRC, layout));
  const tmp = join(__dirname, '_render.html');
  writeFileSync(tmp, html);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1000, height: 1500 }, deviceScaleFactor: 2 });
  await page.goto('file://' + tmp, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(250);
  await page.screenshot({ path: outPath, clip: { x: 0, y: 0, width: 1000, height: 1500 } });
  await browser.close();
}

const copy = await genCopy();
const layout = pickLayout(post.slug);
const fileName = `${post.slug}-${layout}.png`;
const mediaPath = `public/pins/${fileName}`;

await render(layout, {
  kicker: tag,
  headline: clamp(copy.pinHeadline || title, 64),
  sub: clamp(copy.pinSub || excerpt, 110),
  cta: clamp(copy.ctaText || 'Read the full post →', 28),
}, join(OUT_DIR, fileName));

const meta = [{
  file: fileName,
  mediaPath,
  title: clamp(copy.pinterestTitle || title, 100),
  description: clamp(copy.pinterestDescription || excerpt, 490),
  url: destUrl,
  boardId: BOARDS[copy.boardKey] || BOARDS['teen-help'],
  altText: clamp(copy.altText || title, 120),
}];
writeFileSync('/tmp/pins.json', JSON.stringify(meta, null, 2));
writeFileSync(STATE, JSON.stringify({ slug: post.slug, at: new Date().toISOString() }, null, 2));
console.log(`OK pin: ${fileName} | layout: ${layout} | boardKey: ${copy.boardKey}`);
console.log(JSON.stringify(meta, null, 2));
