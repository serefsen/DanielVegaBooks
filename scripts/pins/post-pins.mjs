import { readFileSync } from 'node:fs';

const TW = process.env.TAILWIND_API_KEY;
const ACCT = process.env.TAILWIND_ACCOUNT_ID || '1646506';
const REPO = process.env.GITHUB_REPOSITORY || 'serefsen/DanielVegaBooks';
const BRANCH = process.env.GITHUB_REF_NAME || 'main';
const DRAFT = (process.env.PINS_DRAFT || 'true') !== 'false';
if (!TW) { console.error('FATAL: TAILWIND_API_KEY yok'); process.exit(1); }

let pins;
try { pins = JSON.parse(readFileSync('/tmp/pins.json', 'utf8')); }
catch { console.error('FATAL: /tmp/pins.json okunamadi (once generate-pins calismali)'); process.exit(1); }

// Commit'lenen gorselin raw URL'i Tailwind tarafindan cekilebilsin diye kisa bekleme
console.log('Raw URL yayilmasi icin 8sn bekleniyor...');
await new Promise((r) => setTimeout(r, 8000));

let ok = 0, fail = 0;
for (const p of pins) {
  const mediaUrl = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/${p.mediaPath}`;
  const body = {
    mediaUrl,
    title: p.title,
    description: p.description,
    url: p.url,
    boardId: p.boardId,
    altText: p.altText,
  };
  // DRAFT mode: omit sendAt. (Scheduling/drip eklenince sendAt set edilecek.)
  try {
    const r = await fetch(`https://api-v1.tailwind.ai/v1/accounts/${ACCT}/posts`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${TW}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) { fail++; console.error(`HATA ${r.status}:`, JSON.stringify(data)); continue; }
    ok++;
    console.log(`OLUSTU: status=${data.data?.post?.status} id=${data.data?.post?.id} board=${p.boardId}`);
    console.log(`  media: ${mediaUrl}`);
  } catch (e) { fail++; console.error('HATA:', e.message); }
}
console.log(`Bitti. basarili=${ok} hatali=${fail} mod=${DRAFT ? 'DRAFT' : 'SCHEDULED'}`);
