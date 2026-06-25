import { readFileSync } from 'node:fs';

const TW = process.env.TAILWIND_API_KEY;
const ACCT = process.env.TAILWIND_ACCOUNT_ID || '1646506';
const REPO = process.env.GITHUB_REPOSITORY || 'serefsen/DanielVegaBooks';
const BRANCH = process.env.GITHUB_REF_NAME || 'main';
const DELAY_MIN = parseInt(process.env.PINS_DELAY_MIN || '20', 10); // >=15 olmali
if (!TW) { console.error('FATAL: TAILWIND_API_KEY yok'); process.exit(1); }

let pins;
try { pins = JSON.parse(readFileSync('/tmp/pins.json', 'utf8')); }
catch { console.error('FATAL: /tmp/pins.json okunamadi (once generate-pins calismali)'); process.exit(1); }

console.log('Raw URL yayilmasi icin 8sn bekleniyor...');
await new Promise((r) => setTimeout(r, 8000));

let ok = 0, fail = 0, offset = 0;
for (const p of pins) {
  const mediaUrl = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/${p.mediaPath}`;
  const sendAt = new Date(Date.now() + (DELAY_MIN + offset) * 60000).toISOString();
  offset += 10; // birden fazla pin olursa araya 10dk koy
  const body = {
    mediaUrl, title: p.title, description: p.description,
    url: p.url, boardId: p.boardId, altText: p.altText, sendAt,
  };
  try {
    const r = await fetch(`https://api-v1.tailwind.ai/v1/accounts/${ACCT}/posts`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${TW}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) { fail++; console.error(`HATA ${r.status}:`, JSON.stringify(data)); continue; }
    ok++;
    console.log(`ZAMANLANDI: status=${data.data?.post?.status} id=${data.data?.post?.id} sendAt=${sendAt} board=${p.boardId}`);
    console.log(`  media: ${mediaUrl}`);
  } catch (e) { fail++; console.error('HATA:', e.message); }
}
console.log(`Bitti. basarili=${ok} hatali=${fail} (~${DELAY_MIN}dk+ sonrasina zamanlandi)`);
