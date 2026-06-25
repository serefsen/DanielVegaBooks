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
const NEWSLETTER = `${SITE}/newsletter`;
const BOARD = { printables: '1097963652845484908', quotes: '1097963652845484929', books: '1097963652845484930' };

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const clamp = (s, n) => { s = String(s || '').trim(); return s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s; };

// ---------- TOOLKIT (4 metin x 2 layout) -> /newsletter ----------
const TOOLKIT = [
  { id: 'tk1', kicker: 'Free printable', headline: '6 tools for when pressure hits', sub: 'Calm-down tools your teen can use the moment anxiety spikes - free, one page, ready to print.', badge: '2-page printable - 6 tools inside', cta: 'Get the free toolkit →', title: 'Free Teen Anxiety Toolkit - 6 Calm-Down Tools (Printable)', description: 'A free printable toolkit with six simple grounding tools to help your teen steady themselves when anxiety spikes. Great for parents, teachers, and school counselors - download and print in seconds. #TeenAnxiety #AnxietyRelief #ParentingTeens #CopingSkills #MentalHealthForTeens' },
  { id: 'tk2', kicker: 'Free download', headline: "When anxiety hits, they'll know what to do", sub: 'A free printable toolkit - six simple tools to help your teen steady themselves in the hard moments.', badge: 'Free - printable - 6 tools', cta: 'Download the free toolkit →', title: 'Free Printable Anxiety Toolkit for Teens (6 Coping Tools)', description: 'Six quick, practical tools your teen can reach for when anxiety hits. A free one-page printable from the Daniel Vega anxiety workbooks - perfect for the fridge, a binder, or a backpack. #AnxietyInTeens #TeenMentalHealth #CopingSkillsForTeens #ParentingAnxiousTeen #AnxietyToolkit' },
  { id: 'tk3', kicker: 'Free resource', headline: 'Six calm-down tools for anxious teens', sub: 'Print it, keep it close - practical tools your teen can use the moment pressure rises.', badge: 'One-page printable - free', cta: 'Grab the free toolkit →', title: '6 Calm-Down Tools for Anxious Teens - Free Printable', description: 'A free, printable one-pager with six grounding tools to help anxious teens calm down fast. Made for parents, teachers, and counselors who want something simple that actually helps. #TeenAnxiety #GroundingTechniques #AnxietyHelp #ParentingTeens #SchoolCounselor' },
  { id: 'tk4', kicker: 'For parents & teachers', headline: 'Help your teen through the hard moments', sub: 'A free one-page toolkit of grounding tools - ready to print and use the moment anxiety rises.', badge: 'Free printable - 6 tools', cta: 'Get the free toolkit →', title: 'Teen Anxiety Toolkit - Free Printable Grounding Tools', description: 'When your teen feels overwhelmed, these six simple tools give them a place to start. A free printable toolkit for parents and teachers supporting anxious teens. Download, print, and keep it handy. #AnxiousTeen #TeenAnxietyHelp #CopingSkills #MentalHealthForTeens #ParentingSupport' },
];
const TOOLKIT_LAYOUTS = ['toolkit-a', 'toolkit-b'];
const TOOLKIT_ALT = 'Calm cream-and-blue pin offering a free printable teen anxiety toolkit with six tools.';

// ---------- QUOTES (12 testimonial x 2 layout) -> ana sayfa ----------
const QUOTES = [
  { q: "I finished it in two sittings and felt like someone finally got it. I've reread the panic chapter more times than I can count.", name: 'Maya', role: 'Age 16' },
  { q: 'The first book I hand to anxious students that they actually come back and thank me for.', name: 'Ms. Alvarez', role: 'School counselor' },
  { q: "My son left it on my pillow with a sticky note: 'this is how I feel.' It opened a door we couldn't find before.", name: 'James', role: 'Dad of two' },
  { q: 'I keep it in my backpack like a security blanket. The breathing pages got me through finals week.', name: 'Devon', role: 'Age 15' },
  { q: "Finally a book about anxiety that doesn't talk down to teenagers. My whole class is passing it around.", name: 'Mr. Boyd', role: 'High school teacher' },
  { q: 'I underlined almost every page. It felt like a friend who had been exactly where I was.', name: 'Priya', role: 'Age 17' },
  { q: 'As a therapist I recommend it constantly. It does in 150 pages what takes me months to explain.', name: 'Dr. Nguyen', role: 'Adolescent therapist' },
  { q: 'My daughter actually started talking to me about her worries after reading this. That is everything.', name: 'Renata', role: 'Mom' },
  { q: 'I thought I was the only one whose brain did this. Turns out I am really, really not.', name: 'Cole', role: 'Age 14' },
  { q: 'Honest without being heavy. I laughed, I cried, I felt less alone at 2 a.m.', name: 'Sam', role: 'Age 16' },
  { q: 'We read a chapter together every Sunday. It has become our little ritual.', name: 'The Okafor family', role: 'Readers' },
  { q: 'It did not try to fix me. It just sat with me, and somehow that helped the most.', name: 'Lena', role: 'Age 15' },
];
const QUOTE_LAYOUTS = ['quote-a', 'quote-b'];
const QUOTE_KICKERS = ['What readers say', 'From a reader'];

// ---------- BOOKS (3) -> Amazon ----------
const BOOKS = [
  { n: 1, title: "Your Alarm Isn't Broken", sub: 'An anxiety workbook for teens who hate workbooks.', amazon: 'https://www.amazon.com/dp/B0H5926917', cover: '../../public/image/kitap-123-kapak.webp' },
  { n: 2, title: "Your Awkward Isn't Showing", sub: 'A social anxiety workbook for teens who hate workbooks.', amazon: 'https://www.amazon.com/dp/B0H5L55D31', cover: '../../public/image/kitap-223-kapak.webp' },
  { n: 3, title: "Your Pressure Isn't Proof", sub: 'A performance anxiety workbook for teens who hate workbooks.', amazon: 'https://www.amazon.com/dp/B0H65LW8SN', cover: '../../public/image/kitap-323-kapak.webp' },
];

// Rotasyon deseni: ardisik asla ayni URL olmasin (newsletter / home / amazon)
const PATTERN = ['toolkit', 'quote', 'book', 'quote'];

let st = { step: 0, ti: 0, qi: 0, bi: 0 };
if (existsSync(STATE)) { try { st = { ...st, ...JSON.parse(readFileSync(STATE, 'utf8')) }; } catch {} }

function pick() {
  const type = PATTERN[st.step % PATTERN.length];
  let layout, tokens, fileName, meta;
  if (type === 'toolkit') {
    const total = TOOLKIT.length * TOOLKIT_LAYOUTS.length;
    const c = st.ti % total;
    const v = TOOLKIT[Math.floor(c / TOOLKIT_LAYOUTS.length)];
    layout = TOOLKIT_LAYOUTS[c % TOOLKIT_LAYOUTS.length];
    fileName = `${v.id}-${layout}.png`;
    tokens = { KICKER: v.kicker, HEADLINE: v.headline, SUB: v.sub, BADGE: v.badge, CTA: v.cta };
    meta = { title: v.title, description: v.description, url: NEWSLETTER, boardId: BOARD.printables, altText: TOOLKIT_ALT };
    st.ti++;
  } else if (type === 'quote') {
    const total = QUOTES.length * QUOTE_LAYOUTS.length;
    const c = st.qi % total;
    const qd = QUOTES[Math.floor(c / QUOTE_LAYOUTS.length)];
    layout = QUOTE_LAYOUTS[c % QUOTE_LAYOUTS.length];
    fileName = `quote-${Math.floor(c / QUOTE_LAYOUTS.length)}-${layout}.png`;
    tokens = { KICKER: QUOTE_KICKERS[c % QUOTE_KICKERS.length], QUOTE: qd.q, ATTRIB: qd.name, ROLE: qd.role };
    meta = { title: 'Honest anxiety books for teens - what readers say', description: `"${qd.q}" - ${qd.name}, ${qd.role}. Calm, honest anxiety workbooks for teens who hate workbooks, from Daniel Vega. #TeenAnxiety #AnxietyBooks #MentalHealthForTeens #ParentingTeens #AnxiousTeen`, url: SITE, boardId: BOARD.quotes, altText: `Reader quote about Daniel Vega anxiety books for teens, from ${qd.name}.` };
    st.qi++;
  } else {
    const b = BOOKS[st.bi % BOOKS.length];
    layout = 'book-a';
    fileName = `book-${b.n}.png`;
    tokens = { KICKER: `Book ${b.n} · on Amazon`, COVER: b.cover, TITLE: b.title, SUBTITLE: b.sub, CTA: 'Get it on Amazon →' };
    meta = { title: `${b.title} - Anxiety Workbook for Teens`, description: `${b.sub} Honest, calming, and made for teens who hate workbooks - part of The Response Training Series by Daniel Vega. #TeenAnxiety #AnxietyWorkbook #BooksForTeens #MentalHealthForTeens #ParentingAnxiousTeen`, url: b.amazon, boardId: BOARD.books, altText: `Book cover of ${b.title}, an anxiety workbook for teens, available on Amazon.` };
    st.bi++;
  }
  st.step++;
  meta.title = clamp(meta.title, 100);
  meta.description = clamp(meta.description, 490);
  return { type, layout, tokens, fileName, meta };
}

const N = parseInt(process.env.PINS_PER_RUN || '1', 10);
const out = [];
const browser = await chromium.launch();
for (let k = 0; k < N; k++) {
  const item = pick();
  let html = readFileSync(join(__dirname, `${item.layout}.html`), 'utf8');
  for (const [key, val] of Object.entries(item.tokens)) {
    html = html.split('{{' + key + '}}').join(key === 'COVER' ? val : esc(val));
  }
  const tmp = join(__dirname, '_render.html');
  writeFileSync(tmp, html);
  const page = await browser.newPage({ viewport: { width: 1000, height: 1500 }, deviceScaleFactor: 2 });
  await page.goto('file://' + tmp, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  await page.screenshot({ path: join(OUT_DIR, item.fileName), clip: { x: 0, y: 0, width: 1000, height: 1500 } });
  await page.close();
  out.push({ file: item.fileName, mediaPath: `public/pins/${item.fileName}`, ...item.meta });
  console.log(`[${item.type}] ${item.fileName} | layout: ${item.layout} | url: ${item.meta.url}`);
}
await browser.close();

writeFileSync('/tmp/pins.json', JSON.stringify(out, null, 2));
writeFileSync(STATE, JSON.stringify({ ...st, lastAt: new Date().toISOString() }, null, 2));
console.log(`Toplam ${out.length} evergreen pin uretildi. State: step=${st.step} ti=${st.ti} qi=${st.qi} bi=${st.bi}`);
