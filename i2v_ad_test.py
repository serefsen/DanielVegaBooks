# -*- coding: utf-8 -*-
"""
Daniel Vega - 3-KARE reklam PROB testi (TEK DOSYA, pipeline'a DOKUNMAZ)
Mimari : Nano Banana Pro -> 3 kare (bas/orta/son)
         Kling 3.0 -> ardisik kare ciftleri arasini doldurur (1->2, 2->3)
         ffmpeg -> uc uca ekler (varsa)
Cikti  : frame1/2/3.png + seg1.mp4 + seg2.mp4 (+ ffmpeg varsa ad_test.mp4)
Token  : once PowerShell'de ->  $env:REPLICATE_API_TOKEN="r8_xxx"
Calistir: python i2v_ad_test.py
Not    : Kling 720p "standard" (hizli/ucuz iterasyon). Final'de "pro" = 1080p.
"""
import os, sys, json, time, ssl, subprocess, urllib.request, urllib.error

TOKEN = os.environ.get("REPLICATE_API_TOKEN", "").strip()
if not TOKEN:
    print("HATA: REPLICATE_API_TOKEN yok. Once PowerShell'de:")
    print('  $env:REPLICATE_API_TOKEN="r8_xxxxxxxx"')
    sys.exit(1)

CTX  = ssl._create_unverified_context()
HDRS = {"Authorization": "Bearer " + TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"}
API  = "https://api.replicate.com/v1/models/{}/predictions"

# ============ 3 KARE (ayni masa/defter/kalem, soguk -> sicak, YUZSUZ) ============
# Koprü öğe = kalem + acik defter. Sahne tutarli kalsin diye AYNI dil tekrar ediyor.
FRAMES = [
    # KARE 1 - HOOK / soguk mavi / 3am gerilim
    ("Vertical 9:16 cinematic photo, no people, no faces. A teenage desk at 3 a.m.: "
     "an open notebook with a pen resting on it, a phone glowing cold blue beside it, "
     "scattered papers, tense restless mood. Cold blue light only (phone glow plus "
     "streetlight through blinds). Handheld feel, soft film grain, shallow depth of "
     "field. Raw, NOT glossy, NOT corporate."),

    # KARE 2 - DONUSUM / safak / soguk-notr, sakinlesmeye baslayan
    ("Vertical 9:16 cinematic photo, no people, no faces. THE SAME desk, THE SAME open "
     "notebook and pen as a continuous scene. The first pale dawn light now creeps "
     "through the blinds, the phone dimmer; a few words of handwriting visible on the "
     "page. Mood shifting from tense to calmer. Neutral cool-to-warm light. Handheld "
     "feel, soft film grain, shallow depth of field. Raw, NOT glossy."),

    # KARE 3 - KITAP KULLANIMI / sicak amber / cozulmus, sakin
    ("Vertical 9:16 cinematic photo, no people, no faces. THE SAME desk, THE SAME open "
     "notebook and pen as a continuous scene. Now soft warm amber morning light fills "
     "the room, the page covered with calm handwriting, the pen resting. Resolved, "
     "settled, hopeful mood. Warm amber tones. Handheld feel, soft film grain, shallow "
     "depth of field. Raw, NOT glossy."),
]

# ============ Kling'e segment HAREKETLERI (gorseli kareler veriyor) ============
SEG_MOTIONS = [
    # seg1: kare1 -> kare2
    ("Slow push-in across the desk as cold blue 3 a.m. light gradually gives way to the "
     "first hint of dawn through the blinds. The pen and open notebook stay in frame. "
     "Subtle handheld micro-jitter, 24fps feel, dust drifting in the light. "
     "No people, no text overlays."),
    # seg2: kare2 -> kare3
    ("The light keeps warming from pale dawn to soft amber morning over the same desk "
     "and open notebook; the scene settles, mood resolving from tense to calm. Gentle "
     "handheld drift, 24fps feel. No people, no text overlays."),
]
NEG = ("people, faces, hands, text, watermark, logo, cartoon, oversaturated, "
       "glossy corporate look, distorted")

# ------------------------------ HTTP yardimcilari ------------------------------
def _post(model, payload):
    req = urllib.request.Request(API.format(model),
        data=json.dumps({"input": payload}).encode("utf-8"),
        headers=HDRS, method="POST")
    try:
        with urllib.request.urlopen(req, context=CTX) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
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
        p = _get(get_url); st = p["status"]; n += 1
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

# ---------------------------------- AKIS ---------------------------------------
# 1) 3 KARE
frame_urls = []
for i, prompt in enumerate(FRAMES, 1):
    out = run("google/nano-banana-pro",
              {"prompt": prompt, "aspect_ratio": "9:16", "output_format": "png"},
              "KARE {} / Nano Banana Pro".format(i))
    url = first_url(out)
    frame_urls.append(url)
    download(url, "frame{}.png".format(i))

# 2) ARALARI DOLDUR - ardisik kare ciftleri (1->2, 2->3)
seg_files = []
for i, motion in enumerate(SEG_MOTIONS, 1):
    out = run("kwaivgi/kling-v3-video", {
        "prompt": motion,
        "start_image": frame_urls[i - 1],
        "end_image":   frame_urls[i],
        "duration": 5,
        "mode": "standard",        # hizli/ucuz ; final'de "pro" (1080p)
        "generate_audio": False,
        "negative_prompt": NEG,
    }, "DOLGU {} / Kling 3.0 (kare{}->kare{})".format(i, i, i + 1))
    fn = "seg{}.mp4".format(i)
    download(first_url(out), fn)
    seg_files.append(fn)

# 3) UC UCA EKLE (ffmpeg varsa)
print("\n[BIRLESTIR] ffmpeg deneniyor...")
try:
    cmd = ["ffmpeg", "-y",
           "-i", seg_files[0], "-i", seg_files[1],
           "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[outv]",
           "-map", "[outv]", "ad_test.mp4"]
    subprocess.run(cmd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("  TAMAM -> ad_test.mp4 (birlesik film)")
    print("\nBITTI. Izle: ad_test.mp4   (kareler: frame1/2/3.png)")
except (FileNotFoundError, subprocess.CalledProcessError):
    print("  ffmpeg yok/calismadi. Segmentleri SIRAYLA izle: seg1.mp4 -> seg2.mp4")
    print("\nBITTI. Kareler: frame1/2/3.png")
