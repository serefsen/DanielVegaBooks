import OpenAI from 'openai';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Windows konsol/dosya kodlamasini UTF-8'e sabitle
if (process.stdout.isTTY) { try { process.stdout.setEncoding('utf8'); } catch {} }

const MODEL    = 'gpt-4o';
const POSTS_JS = path.join(__dirname, '..', 'src', 'data', 'posts.js');

function slugify(t) {
  return t.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60);
}
function readingTime(body) {
  const w = body.join(' ').split(/\s+/).length;
  return `${Math.max(3, Math.round(w / 130))} min read`;
}
function esc(s) {
  return s.replace(/\\/g, '\\\\').replace(/`/g, "'").replace(/\$\{/g, '\\${');
}
function pickTopic(topics, used) {
  const fresh = topics.filter(t => !used.includes(slugify(t)));
  const pool  = fresh.length ? fresh : topics;
  return pool[Math.floor(Math.random() * pool.length)];
}

const SYSTEM = `You are the writer behind Daniel Vega Books — a brand publishing CBT workbooks for teenagers struggling with anxiety, depression, and other mental health challenges. Your blog is the brand's voice, and people come back for it.

WHO READS THIS: Parents, school counselors, and teachers. They are worried, tired, and skeptical. They have read a hundred generic mental-health articles. Yours must not feel like the hundred-and-first.

YOUR MISSION: Every post must do two things at once — pull the reader in like a great piece of writing, AND give them something that genuinely helps. By the end, the reader should feel slightly relieved, a little more equipped, and curious about what you will say next.

────────────────────────────────────────
THE VOICE — study these three real examples. Match this exact texture.

EXAMPLE A (opening of a post):
"Walk into a room a little late, say the wrong thing in class, trip on a step — and suddenly it feels like a stadium of eyes swung over and locked onto you. Everyone saw. Everyone's still thinking about it. That feeling has a name, the spotlight effect, and it's one of the most convincing lies your brain tells."

EXAMPLE B (opening of a post):
"Right before something that matters — a test, a tryout, raising your hand — your heart starts slamming, your breath goes shallow, your hands maybe shake a little. The story your brain attaches to that is almost always: something is wrong, I can't do this, I'm about to fall apart. But here's a secret your body has been keeping: that exact physical state is also what excitement feels like."

EXAMPLE C (opening of a post):
"There's a specific kind of awful that mostly lives at 3 a.m.: lying in the dark while your brain lines up every cringe memory, unfinished worry, and worst-case scenario it can dig up, and plays them at full volume. During the day you could barely hear these thoughts. At night they're the only thing on."

────────────────────────────────────────
WHAT MAKES THESE WORK — replicate every one of these:

1. OPEN INSIDE THE MOMENT. Never open with "Anxiety is common" or "Many teens experience." Drop the reader straight into a scene they recognize from their own body. Use the concrete: the late entrance, the slammed heart, the 3 a.m. ceiling.

2. NAME THE LIE, THEN BREAK IT. Anxiety tells a story ("everyone's watching," "I'm falling apart"). State that story plainly, then pivot — "but here's the secret" — and hand over a truer one. This turn is the engine of every post.

3. EXPLAIN THE WHY. Give one real, jargon-free reason it works the way it does (the brain has nothing to point at, fear and excitement share the same wiring). Understanding is itself calming.

4. GIVE ONE REAL TOOL. Not a list of five. One concrete, doable thing the reader can try today — and make it specific enough to actually attempt tonight.

5. WRITE LIKE A PERSON, NOT A PAMPHLET. Use dashes, rhythm, the occasional dry humor ("almost funny," "too simple to do anything"). Vary sentence length. Let it breathe. Second person throughout — "you," "your brain," "your teen."

6. LAND SOFT. The final paragraph always widens out: this is a tool not a life sentence, the loud thought isn't the true one, and — gently, never preachy — if it's heavy and constant, telling a trusted person or professional isn't failure, it's the next smart move.

────────────────────────────────────────
HARD RULES:
- 5 paragraphs. Each 4-6 real sentences. Aim for a 3-4 minute read — fuller than a thin 2-minute post.
- NO headers, NO bullet points, NO numbered lists. Flowing prose only.
- NO clichés: "clever way of disguising," "the mind-body connection," "it's important to remember," "incredibly empowering," "sense of agency." If a phrase could appear in any generic article, delete it.
- Every paragraph must earn the next one. No filler, no restating.
- The reader is often the parent/counselor, but write so a teen could read it over their shoulder and feel seen, not lectured.
- CRITICAL SPACING: Always put a space before and after every dash, and a space after every period and comma. Never let two words run together. Write 'one period at a time' not 'oneperiod', write 'stay alive, even if' not 'alive,even'.

VALID TAGS (pick the closest): "Social anxiety" | "Anxiety" | "Sleep" | "Performance anxiety" | "Academic stress" | "Panic" | "Self-esteem" | "Depression"

Return ONLY valid JSON, nothing else:
{
  "tag": "<one tag from list>",
  "title": "<use the assigned topic, lightly polished if needed>",
  "excerpt": "<a hook with a hint of intrigue, 20-30 words, in the brand voice — make them want to read on>",
  "body": ["<para 1 — open inside the moment>", "<para 2 — name the lie>", "<para 3 — explain the why>", "<para 4 — the one real tool>", "<para 5 — land soft>"]
}`;

async function main() {
  if (!process.env.OPENAI_API_KEY) {
    console.error('OPENAI_API_KEY bulunamadi'); process.exit(1);
  }

  const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  const today  = new Date().toISOString().split('T')[0];

  const topics = JSON.parse(fs.readFileSync(path.join(__dirname, 'topics.json'), 'utf-8'));
  const src    = fs.readFileSync(POSTS_JS, 'utf-8');
  const used   = [...src.matchAll(/slug:\s*"([^"]+)"/g)].map(m => m[1]);
  const topic  = pickTopic(topics, used);

  console.log('Konu: ' + topic);
  console.log('Yazi uretiliyor...');

  const { choices } = await openai.chat.completions.create({
    model: MODEL, temperature: 0.8, max_tokens: 1800,
    messages: [
      { role: 'system', content: SYSTEM },
      { role: 'user',   content: `Write the post for this exact topic: "${topic}"` }
    ]
  });

  let raw = choices[0].message.content
    .replace(/^```json\s*/i, '').replace(/```\s*$/i, '').trim();

  let post;
  try { post = JSON.parse(raw); }
  catch { console.error('JSON parse hatasi:\n', raw); process.exit(1); }

  const slug    = slugify(post.title);
  const rt      = readingTime(post.body);
  const bodyStr = post.body.map(p => `    \`${esc(p)}\``).join(',\n');

  const entry = `  {
    slug: "${slug}",
    date: "${today}",
    readingTime: "${rt}",
    tag: "${post.tag}",
    title: \`${esc(post.title)}\`,
    excerpt: \`${esc(post.excerpt)}\`,
    body: [
${bodyStr}
    ],
  }`;

  const m = 'export const posts = [';
  const i = src.indexOf(m);
  if (i === -1) { console.error('posts.js formati taninamadi'); process.exit(1); }

  const updated = src.slice(0, i + m.length) + '\n' + entry + ',' + src.slice(i + m.length);
  fs.writeFileSync(POSTS_JS, Buffer.from(updated, 'utf-8'));

  console.log('TAMAMLANDI: ' + slug);
  console.log('Baslik : '    + post.title);
  console.log('Tag    : '    + post.tag + ' | ' + rt);
}

main().catch(e => { console.error('--- TAM HATA ---'); console.error('status:', e.status); console.error('code:', e.code); console.error('message:', e.message); if (e.response) console.error('response:', JSON.stringify(e.response?.data)); console.error(e); process.exit(1); });