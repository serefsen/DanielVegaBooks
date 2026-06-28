#!/usr/bin/env python3
"""
pick_broll.py â€” script duygusuna uygun, son 14 gunde kullanilmamis b-roll sec.

Kullanim:
    python3 pick_broll.py <script.txt> [broll_dir] [state.json]
Cikti (stdout): secilen klibin dosya yolu (ffmpeg'e verilecek)

Mantik:
  1) Script'ten duygu etiketi cikar (kelime tabanli)
  2) O etikete uygun, cooldown'da olmayan kliplerden rastgele sec
  3) Bos kalirsa neutral -> transition'a dus
  4) Secimi state.json'a yaz (last_used = bugun)
"""

import sys, os, json, re, random, datetime, glob

COOLDOWN_DAYS = 14

# Script -> duygu etiketi (kelime tabanli, basit ve seffaf)
EMOTION_KEYWORDS = {
    "anxious":  ["worry", "spiral", "panic", "racing", "afraid", "scared", "overwhelm", "dread"],
    "hopeful":  ["better", "progress", "small win", "helped", "learned", "grew", "wrote", "changed"],
    "calm":     ["breath", "pause", "quiet", "slow", "still", "rest", "settle"],
}
FALLBACK_ORDER = ["neutral", "transition"]

# Klip dosya adi konvansiyonu: <etiket>__<isim>.mp4  ornek: anxious__rain_window.mp4
def clip_tag(path):
    base = os.path.basename(path)
    return base.split("__")[0] if "__" in base else "neutral"

def detect_emotion(text):
    t = text.lower()
    scores = {emo: sum(t.count(w) for w in words) for emo, words in EMOTION_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "neutral"

def load_state(path):
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8-sig"))
        except Exception:
            return {}
    return {}

def save_state(path, state):
    json.dump(state, open(path, "w", encoding="utf-8-sig"), indent=2)

def in_cooldown(clip_id, state, today):
    last = state.get(clip_id, {}).get("last_used")
    if not last:
        return False
    last_d = datetime.date.fromisoformat(last)
    return (today - last_d).days < COOLDOWN_DAYS

def pick(script_path, broll_dir="broll", state_path="broll_state.json"):
    text = open(script_path, encoding="utf-8-sig").read()
    emotion = detect_emotion(text)
    state = load_state(state_path)
    today = datetime.date.today()

    all_clips = glob.glob(os.path.join(broll_dir, "*.mp4"))
    if not all_clips:
        print(f"HATA: {broll_dir} icinde klip yok", file=sys.stderr)
        sys.exit(1)

    for tag in [emotion] + FALLBACK_ORDER:
        candidates = [c for c in all_clips
                      if clip_tag(c) == tag and not in_cooldown(c, state, today)]
        if candidates:
            chosen = random.choice(candidates)
            state[chosen] = {"last_used": today.isoformat(), "tag": tag}
            save_state(state_path, state)
            print(f"[secim] duygu={emotion} -> kullanilan etiket={tag}", file=sys.stderr)
            print(chosen)  # stdout: ffmpeg'e gidecek yol
            return

    # Her sey cooldown'da: en eski kullanilani sec (acil durum)
    oldest = min(all_clips, key=lambda c: state.get(c, {}).get("last_used", "0000-01-01"))
    state[oldest] = {"last_used": today.isoformat(), "tag": clip_tag(oldest)}
    save_state(state_path, state)
    print(f"[secim] TUM klipler cooldown'da, en eski kullanilan secildi", file=sys.stderr)
    print(oldest)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanim: python3 pick_broll.py <script.txt> [broll_dir] [state.json]")
        sys.exit(2)
    pick(sys.argv[1],
         sys.argv[2] if len(sys.argv) > 2 else "broll",
         sys.argv[3] if len(sys.argv) > 3 else "broll_state.json")

