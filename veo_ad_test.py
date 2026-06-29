# -*- coding: utf-8 -*-
"""
Daniel Vega - Veo 3.1 Fast REKLAM ORNEGI (LOKAL, TEK DOSYA)
Akis: Veo 3.1 Fast text-to-video (4 prompt -> 4 klip, 9:16, 1080p, sessiz)
      -> kullanicinin timeline'ina kirp/birlestir (15sn)
      -> ElevenLabs ses + kullanicinin sabit zaman kodlu altyazilari
Cikti: full_ad.mp4 (15sn) / altyazi patlarsa voiced.mp4
Token: $env:REPLICATE_API_TOKEN="r8_..."  +  $env:ELEVENLABS_API_KEY="xi_..."
Kur  : python -m pip install imageio-ffmpeg
Calistir (C:\DanielVegaBooks icinden): python veo_ad_test.py
"""
import os, sys, json, base64, ssl, re, time, subprocess
import urllib.request, urllib.error

REP = os.environ.get("REPLICATE_API_TOKEN", "").strip()
XI  = os.environ.get("ELEVENLABS_API_KEY", "").strip()
if not REP or not XI:
    print("HATA: Anahtar eksik. Once PowerShell'de:")
    print('  $env:REPLICATE_API_TOKEN="r8_xxxxxxxx"')
    print('  $env:ELEVENLABS_API_KEY="xi_xxxxxxxx"'); sys.exit(1)
try:
    import imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    print("HATA: imageio-ffmpeg yok -> python -m pip install imageio-ffmpeg"); sys.exit(1)

CTX = ssl._create_unverified_context()

# ===================== KULLANICININ CREATIVE'I (AYNEN, DOKUNULMADI) =====================
PROMPTS = [
    "Cinematic close-up, teenager's hand trembling holding a pen over a blank exam paper. "
    "Moody classroom lighting, shallow depth of field, 4k.",
    "Anxious teenager staring blankly ahead, motion-blurred classroom background, dramatic "
    "contrast lighting, cinematically zoning out, 4k.",
    "Macro shot, teenager's hand pressing flat onto a solid wooden desk. Crisp shadows, "
    "cinematic grounding pose, 4k.",
    "Side profile, teenager writing confidently on paper under a bright desk lamp. "
    "Transitioning to a dark background on the right for book cover placeholder, 4k.",
]
# her sahnenin nihai suresi (saniye) - kullanicinin timeline'i: 4 + 3 + 4 + 4 = 15
SCENE_SECS = [4, 3, 4, 4]

SCRIPT = ("A racing heart isn't proof you'll fail; it's a sign that this moment matters. "
          "Don't train the pressure - train your response. Take that step anyway. "
          "'Your Pressure Isn't Proof' by Daniel Vega. Available now.")

SUBS = [  # (baslangic, bitis, metin) - kullanicinin sabit zaman kodlari
    (0,  4,  "A racing heart isn't proof you'll fail; it's a sign that this moment matters."),
    (4,  7,  "Don't train the pressure - train your response."),
    (7,  11, "Take that step anyway."),
    (11, 15, "'Your Pressure Isn't Proof' by Daniel Vega. Available now."),
]
VOICE_ID = "MFZUKuGQUsGJPQjTS4wC"
MODEL    = "eleven_v3"
VEO      = "google/veo-3.1-fast"
# =======================================================================================

RAPI = "https://api.replicate.com/v1/models/{}/predictions"
RHDR = {"Authorization": "Bearer " + REP, "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"}

def rep_post(model, payload):
    req = urllib.request.Request(RAPI.format(model),
        data=json.dumps({"input": payload}).encode("utf-8"), headers=RHDR, method="POST")
    try:
        with urllib.request.urlopen(req, context=CTX) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("\nHTTP {} -> {}".format(e.code, e.read().decode("utf-8", "ignore"))); sys.exit(1)

def rep_get(url):
    req = urllib.request.Request(url, headers=RHDR, method="GET")
    with urllib.request.urlopen(req, context=CTX) as r:
        return json.loads(r.read().decode("utf-8"))

def rep_run(model, payload, label):
    print("\n[{}] baslatiliyor...".format(label))
    pred = rep_post(model, payload); g = pred["urls"]["get"]
    t0, n = time.time(), 0
    while True:
        p = rep_get(g); st = p["status"]; n += 1
        sys.stdout.write("\r  [{}] {:<11} gecen {}sn  kontrol #{}   ".format(
            label, st, int(time.time() - t0), n)); sys.stdout.flush()
        if st == "succeeded":
            print("\n  [{}] TAMAM ({}sn)".format(label, int(time.time() - t0))); return p["output"]
        if st in ("failed", "canceled"):
            print("\n  [{}] HATA: {}".format(label, p.get("error"))); sys.exit(1)
        time.sleep(4)

def first_url(o): return o[0] if isinstance(o, list) else o

def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=CTX) as r, open(path, "wb") as f:
        f.write(r.read())
    print("  kaydedildi -> {}".format(path))

def secs_to_ass(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return "{:d}:{:02d}:{:05.2f}".format(h, m, s)

def write_ass(lines):
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Def,Arial,64,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,4,1,2,60,60,130,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    body = "".join("Dialogue: 0,{},{},Def,,0,0,0,,{}\n".format(
        secs_to_ass(s), secs_to_ass(e), t.replace("\n", " ").strip()) for s, e, t in lines)
    open("subs.ass", "w", encoding="utf-8").write(head + body)

# ================================== AKIS ==================================
# 1) 4 VEO KLIBI (text-to-video, sessiz)
veo_files = []
for i, pr in enumerate(PROMPTS, 1):
    out = rep_run(VEO, {
        "prompt": pr, "aspect_ratio": "9:16", "resolution": "1080p",
        "duration": 4, "generate_audio": False,
    }, "VEO {} / 3.1 Fast".format(i))
    fn = "veo{}.mp4".format(i); download(first_url(out), fn); veo_files.append(fn)

# 2) ELEVENLABS SES
print("\n[SES] ElevenLabs...")
ehdr = {"xi-api-key": XI, "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
ebody = json.dumps({"text": SCRIPT, "model_id": MODEL}).encode("utf-8")
plain = "https://api.elevenlabs.io/v1/text-to-speech/{}".format(VOICE_ID)
req = urllib.request.Request(plain, data=ebody, headers=ehdr, method="POST")
try:
    with urllib.request.urlopen(req, context=CTX) as r:
        open("voice.mp3", "wb").write(r.read())
    print("  ses hazir.")
except urllib.error.HTTPError as e:
    print("HATA: ElevenLabs -> HTTP {} {}".format(e.code, e.read().decode("utf-8", "ignore"))); sys.exit(1)

# 3) ALTYAZI (kullanicinin sabit zaman kodlari)
write_ass(SUBS)

# 4) KLIPLERI KIRP + BIRLESTIR (15sn)
print("\n[MONTAJ] klipler kirpiliyor + birlestiriliyor...")
parts, inputs = [], []
for i, sec in enumerate(SCENE_SECS):
    inputs += ["-i", veo_files[i]]
    parts.append("[{}:v]trim=0:{},setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,"
                 "crop=1080:1920[v{}]".format(i, sec, i))
flt = ";".join(parts) + ";" + "".join("[v{}]".format(i) for i in range(4)) + "concat=n=4:v=1:a=0[v]"
subprocess.run([FF, "-y"] + inputs + ["-filter_complex", flt, "-map", "[v]", "broll.mp4"],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 5) SES + GORSEL (GARANTI, 15sn)
subprocess.run([FF, "-y", "-i", "broll.mp4", "-i", "voice.mp3",
                "-map", "0:v", "-map", "1:a", "-t", "15",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "voiced.mp4"],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 6) ALTYAZI BURN (15sn)
print("[MONTAJ] altyazi...")
try:
    subprocess.run([FF, "-y", "-i", "voiced.mp4", "-vf", "subtitles=subs.ass", "-t", "15",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", "full_ad.mp4"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print("\nBITTI -> full_ad.mp4  (15sn, Veo 3.1 + ElevenLabs ses + altyazi)")
except subprocess.CalledProcessError as e:
    err = (e.stderr or b"").decode("utf-8", "ignore")[-400:]
    print("\nAltyazi patladi (ffmpeg libass yok olabilir). AMA voiced.mp4 HAZIR (ses+gorsel).")
    print("ffmpeg notu:", err)
