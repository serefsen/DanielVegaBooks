// Sadece kitap pinlerini (book-1/2/3.png) yeniden uretir.
// Rotasyon, state, OpenRouter, Tailwind posting YOK. 3D kapaklarla render + kaydet.
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = join(__dirname, '../../public/pins');

const BOOKS = [
  { n: 1, title: "Your Alarm Isn't Broken",   sub: 'An anxiety workbook for teens who hate workbooks.',            cover: '../../public/image/186545.png' },
  { n: 2, title: "Your Awkward Isn't Showing", sub: 'A social anxiety workbook for teens who hate workbooks.',      cover: '../../public/image/oubn.png' },
  { n: 3, title: "Your Pressure Isn't Proof",  sub: 'A performance anxiety workbook for teens who hate workbooks.', cover: '../../public/image/q3nnp.png' },
];

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const browser = await chromium.launch();
for (const b of BOOKS) {
  const tokens = {
    KICKER: `Book ${b.n} \u00b7 on Amazon`,
    COVER: b.cover,
    TITLE: b.title,
    SUBTITLE: b.sub,
    CTA: 'Get it on Amazon \u2192',
  };
  let html = readFileSync(join(__dirname, 'book-a.html'), 'utf8');
  for (const [k, v] of Object.entries(tokens)) {
    html = html.split('{{' + k + '}}').join(k === 'COVER' ? v : esc(v));
  }
  const tmp = join(__dirname, '_regen.html');
  writeFileSync(tmp, html);
  const page = await browser.newPage({ viewport: { width: 1000, height: 1500 }, deviceScaleFactor: 2 });
  await page.goto('file://' + tmp, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  await page.screenshot({ path: join(OUT_DIR, `book-${b.n}.png`), clip: { x: 0, y: 0, width: 1000, height: 1500 } });
  await page.close();
  console.log(`book-${b.n}.png yeniden uretildi -> ${b.title}`);
}
await browser.close();
console.log('BITTI: 3 kitap pini 3D kapakla yenilendi.');
