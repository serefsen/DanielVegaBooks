import { readFileSync } from 'node:fs';

const TW = process.env.TAILWIND_API_KEY;
const ACCT = process.env.TAILWIND_ACCOUNT_ID || '1646506';
const REPO = process.env.GITHUB_REPOSITORY || 'serefsen/DanielVegaBooks';
const BRANCH = process.env.GITHUB_REF_NAME || 'main';
if (!TW) { console.error('FATAL: TAILWIND_API_KEY yok'); process.exit(1); }

let pins;
try { pins = JSON.parse(readFileSync('/tmp/pins.json', 'utf8')); }
catch { console.error('FATAL: /tmp/pins.json yok'); process.exit(1); }
if (!pins.length) { console.log('Pin yok, cikiliyor.'); process.exit(0); }

console.log('Raw URL yayilmasi icin 8sn bekleniyor...');
await new Promise((r) => setTimeout(r, 8000));

// SmartSchedule slot'larini cek
let slots = [];
try {
  const r = await fetch(`https://api-v1.tailwind.ai/v1/accounts/${ACCT}/timeslots`, { headers: { Authorization: `Bearer ${TW}` } });
  const d = await r.json();
  slots = (d.data?.timeslots || []).map((s) => s.sendAt).filter(Boolean);
} catch (e) { console.error('timeslots cekilemedi:', e.message); }

const nowSec = Math.floor(Date.now() / 1000);
const future = slots.filter((s) => s > nowSec + 900).sort((a, b) => a - b);
console.log(`Ileri slot sayisi: ${future.length}`);

let ok = 0, fail = 0, i = 0;
for (const p of pins) {
  const mediaUrl = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/${p.mediaPath}`;
  const slotSec = future[i] ?? (nowSec + 3600 + i * 1800); // slot yoksa ~1sa+ sonra
  i++;
  const sendAt = new Date(slotSec * 1000).toISOString();
  const body = { mediaUrl, title: p.title, description: p.description, url: p.url, boardId: p.boardId, altText: p.altText, sendAt };
  try {
    const r = await fetch(`https://api-v1.tailwind.ai/v1/accounts/${ACCT}/posts`, {
      method: 'POST', headers: { Authorization: `Bearer ${TW}`, 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) { fail++; console.error(`HATA ${r.status}:`, JSON.stringify(data)); continue; }
    ok++;
    console.log(`ZAMANLANDI: status=${data.data?.post?.status} id=${data.data?.post?.id} sendAt=${sendAt} (SmartSchedule slot)`);
    console.log(`  media: ${mediaUrl}`);
  } catch (e) { fail++; console.error('HATA:', e.message); }
}
console.log(`Bitti. basarili=${ok} hatali=${fail}`);
