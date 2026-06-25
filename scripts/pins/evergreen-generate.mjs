import { chromium } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..', '..');
const OUT_DIR = join(ROOT, 'public', 'pins');
mkdirSync(OUT_DIR, { recursive: true });
const STATE = join(OUT_DIR, 'evergreen-state.json');

const SITE = 'https://danielvegabooks.com';
const BOARD_PRINTABLES = '1097963652845484908'; // Anxiety Worksheets & Printables

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// Toolkit metin varyantlari (LLM yok — sabit asset, elle yazildi)
const TOOLKIT = [
  {
    id: 'tk1', kicker: 'Free printable', headline: '6 tools for when pressure hits',
    sub: 'Calm-down tools your teen can use the moment anxiety spikes - free, one page, ready to print.',
    badge: '2-page printable - 6 tools inside', cta: 'Get the free toolkit →',
    title: 'Free Teen Anxiety Toolkit - 6 Calm-Down Tools (Printable)',
    description: 'A free printable toolkit with six simple grounding tools to help your teen steady themselves when anxiety spikes. Great for parents, teachers, and school counselors - download and print in seconds. #TeenAnxiety #AnxietyRelief #ParentingTeens #CopingSkills #MentalHealthForTeens',
  },
  {
    id: 'tk2', kicker: 'Free download', headline: "When anxiety hits, they'll know what to do",
    sub: 'A free printable toolkit - six simple tools to help your teen steady themselves in the hard moments.',
    badge: 'Free - printable - 6 tools', cta: 'Download the free toolkit →',
    title: 'Free Printable Anxiety Toolkit for Teens (6 Coping Tools)',
    description: 'Six quick, practical tools your teen can reach for when anxiety hits. A free one-page printable from the Daniel Vega anxiety workbooks - perfect for the fridge, a binder, or a backpack. #AnxietyInTeens #TeenMentalHealth #CopingSkillsForTeens #ParentingAnxiousTeen #AnxietyToolkit',
  },
  {
    id: 'tk3', kicker: 'Free resource', headline: 'Six calm-down tools for anxious teens',
    sub: 'Print it, keep it close - practical tools your teen can use the moment pressure rises.',
    badge: 'One-page printable - free', cta: 'Grab the free toolkit →',
    title: '6 Calm-Down Tools for Anxious Teens - Free Printable',
    description: 'A free, printable one-pager with six grounding tools to help anxious teens calm down fast. Made for parents, teachers, and counselors who want something simple that actually helps. #TeenAnxiety #GroundingTechniques #AnxietyHelp #ParentingTeens #SchoolCounselor',
  },
  {
    id: 'tk4', kicker: 'For parents & teachers', headline: 'Help your teen through the hard moments',
    sub: 'A free one-page toolkit of grounding tools - ready to print and use the moment anxiety rises.',
    badge: 'Free printable - 6 tools', cta: 'Get the free toolkit →',
    title: 'Teen Anxiety Toolkit - Free Printable Grounding Tools',
    description: 'When your teen feels overwhelmed, these six simple tools give them a place to start. A free printable toolkit for parents and teachers supporting anxious teens. Download, print, and keep it handy. #AnxiousTeen #TeenAnxietyHelp #CopingSkills #MentalHealthForTeens #ParentingSupport',
  },
];
const LAYOUTS = ['toolkit-a', 'toolkit-b'];
const ALT = 'Calm cream-and-blue pin offering a free printable teen anxiety toolkit with six tools.';

let index = 0;
if (existsSync(STATE)) { try { index = JSON.parse(readFileSync(STATE, 'utf8')).index || 0; } catch {} }

const total = TOOLKIT.length * LAYOUTS.length; // 8 farkli creative
const combo = index % total;
const variant = TOOLKIT[Math.floor(combo / LAYOUTS.length)];
const layout = LAYOUTS[combo % LAYOUTS.length];

const fileName = `${variant.id}-${layout}.png`;
const mediaPath = `public/pins/${fileName}`;

const html = readFileSync(join(__dirname, `${layout}.html`), 'utf8')
  .split('{{KICKER}}').join(esc(variant.kicker))
  .split('{{HEADLINE}}').join(esc(variant.headline))
  .split('{{SUB}}').join(esc(variant.sub))
  .split('{{BADGE}}').join(esc(variant.badge))
  .split('{{CTA}}').join(esc(variant.cta));
const tmp = join(__dirname, '_render.html');
writeFileSync(tmp, html);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1000, height: 1500 }, deviceScaleFactor: 2 });
await page.goto('file://' + tmp, { waitUntil: 'load' });
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(250);
await page.screenshot({ path: join(OUT_DIR, fileName), clip: { x: 0, y: 0, width: 1000, height: 1500 } });
await browser.close();

const meta = [{
  file: fileName, mediaPath,
  title: variant.title, description: variant.description,
  url: `${SITE}/newsletter`, boardId: BOARD_PRINTABLES, altText: ALT,
}];
writeFileSync('/tmp/pins.json', JSON.stringify(meta, null, 2));
writeFileSync(STATE, JSON.stringify({ index: index + 1, lastAt: new Date().toISOString() }, null, 2));
console.log(`Evergreen toolkit pin: ${fileName} | variant: ${variant.id} | layout: ${layout} | index: ${index}→${index + 1}`);
console.log(JSON.stringify(meta, null, 2));
