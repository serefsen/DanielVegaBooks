# -*- coding: utf-8 -*-
"""
Daniel Vega - i2v PROB testi (TEK DOSYA, pipeline'a DOKUNMAZ)
Akis : Nano Banana Pro (kare)  ->  Kling 3.0 i2v (klip)
Cikti: test_frame.png + test_clip.mp4 (calistigin klasore)
Token: once PowerShell'de ->  $env:REPLICATE_API_TOKEN="r8_xxx"
Calistir:  python i2v_test.py
Maliyet: ~ $1 alti (Nano Banana ~$0.06 + Kling pro 5sn)
"""
import os, sys, json, time, ssl, urllib.request, urllib.error

TOKEN = os.environ.get("REPLICATE_API_TOKEN", "").strip()
if not TOKEN:
    print("HATA: REPLICATE_API_TOKEN yok. Once PowerShell'de su komutu calistir:")
    print('  $env:REPLICATE_API_TOKEN="r8_xxxxxxxx"')
    sys.exit(1)

# Windows expired-cert sorununu by-pass (pipeline ile ayni desen)
CTX = ssl._create_unverified_context()
HDRS = {
    "Authorization": "Bearer " + TOKEN,
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0",
}
API = "https://api.replicate.com/v1/models/{}/predictions"

# ---------------- AD karesi (Book 1 / "alarm" temasi, YUZSUZ) ----------------
IMAGE_PROMPT = (
    "Vertical 9:16 cinematic photograph, no people, no faces. A dark teenage "
    "bedroom at 3 a.m.: a phone lying face-up on rumpled sheets, screen glowing "
    "cold blue, the light catching tangled bedding and a half-closed notebook. "
    "Moody and intimate, handheld feel, soft film grain, shallow depth of field, "
    "practical light only (phone glow plus faint streetlight through blinds). "
    "Raw and slightly imperfect, NOT glossy, NOT corporate. Cold blue tones."
)

# ---- Kling'e sadece HAREKET tarifi (gorseli kare zaten veriyor) ----
MOTION_PROMPT = (
    "Slow, subtle push-in toward the glowing phone. Gentle handheld micro-jitter, "
    "24fps feel. The phone screen flickers faintly; dust particles drift through "
    "the light beam; bedding shifts almost imperceptibly. A warm amber lamp slowly "
    "begins to glow at the edge of the frame, shifting the mood from cold to calm. "
    "Cinematic, atmospheric, no text overlays, no people."
)
NEG_PROMPT = (
    "people, faces, hands, text, watermark, logo, cartoon, "
    "oversaturated, glossy corporate look, distorted"
)

# ----------------------------- HTTP yardimcilari -----------------------------
def _post(model, payload):
    req = urllib.request.Request(
        API.format(model),
        data=json.dumps({"input": payload}).encode("utf-8"),
        headers=HDRS, method="POST")
    try:
        with urllib.request.urlopen(req, context=CTX) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Hangi alan yanlissa Replicate burada acikca soyler
        print("\nHTTP {} -> {}".format(e.code, e.read().decode("utf-8", "ignore")))
        sys.exit(1)

def _get(url):
    req = urllib.request.Request(url, headers=HDRS, method="GET")
    with urllib.request.urlopen(req, context=CTX) as r:
        return json.loads(r.read().decode("utf-8"))

def run(model, payload, label):
    print("\n[{}] baslatiliyor...".format(label))
    pred = _post(model, payload)
    get_url = pred["urls"]["get"]
    t0, n = time.time(), 0
    while True:
        p = _get(get_url)
        st = p["status"]; n += 1
        sys.stdout.write("\r  [{}] {:<10} gecen {}sn  kontrol #{}   ".format(
            label, st, int(time.time() - t0), n))
        sys.stdout.flush()
        if st == "succeeded":
            print("\n  [{}] TAMAM ({}sn)".format(label, int(time.time() - t0)))
            return p["output"]
        if st in ("failed", "canceled"):
            print("\n  [{}] HATA: {}".format(label, p.get("error")))
            sys.exit(1)
        time.sleep(3)

def first_url(out):
    return out[0] if isinstance(out, list) else out

def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=CTX) as r, open(path, "wb") as f:
        f.write(r.read())
    print("  kaydedildi -> {}".format(path))

# --------------------------------- AKIS --------------------------------------
# 1) KARE  (Nano Banana Pro)
img_out = run("google/nano-banana-pro", {
    "prompt": IMAGE_PROMPT,
    "aspect_ratio": "9:16",
    "output_format": "png",
}, "KARE / Nano Banana Pro")
img_url = first_url(img_out)
download(img_url, "test_frame.png")

# 2) KLIP  (Kling 3.0 i2v) - kareyi start_image olarak ver
vid_out = run("kwaivgi/kling-v3-video", {
    "prompt": MOTION_PROMPT,
    "start_image": img_url,
    "duration": 5,
    "mode": "pro",            # 1080p ; "standard" = 720p
    "generate_audio": False,  # sesi sonra ElevenLabs ekliyor
    "negative_prompt": NEG_PROMPT,
}, "KLIP / Kling 3.0 i2v")
vid_url = first_url(vid_out)
download(vid_url, "test_clip.mp4")

print("\nBITTI. Once test_frame.png'e bak (onay kapisi), sonra test_clip.mp4'u izle.")
