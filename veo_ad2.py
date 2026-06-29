# -*- coding: utf-8 -*-
"""
Daniel Vega - Veo 3.1 Fast REKLAM #2 (Book 1 'Your Alarm Isn't Broken')
Veo text-to-video (4 prompt + kamera hareketleri, 9:16, 1080p, sessiz)
-> 15sn timeline (3+4+4+4) -> ElevenLabs ses + altyazi + kapak (sol, son 4sn)
Token: $env:REPLICATE_API_TOKEN="r8_..."  +  $env:ELEVENLABS_API_KEY="xi_..."
Calistir (C:\DanielVegaBooks icinden): python veo_ad2.py
"""
import os, sys, json, ssl, time, subprocess
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

# ===================== KULLANICININ CREATIVE'I (kamera hareketleri eklendi) =====================
PROMPTS = [
    ("A mind-bending cinematic shot of a teenager sitting in a completely silent, peaceful "
     "school library. Symmetrically above their head, a surreal, vibrant red emergency siren "
     "light spins violently, casting deep crimson shadows over their face. In the background, "
     "other students are blurred and carrying on completely normally, totally oblivious to the "
     "red alarm. Hyper-realistic, masterclass lighting contrast, 4k resolution film style. "
     "Camera movement: rapid fast zoom-in toward the spinning red siren, claustrophobic and shocking."),

    ("Extreme macro close-up of a human eye wide with anxiety, the pupil fully dilated. Reflected "
     "perfectly inside the iris is a chaotic, neon-glitched smartphone feed scrolling at "
     "hyper-speed with motion blur. RAW photo aesthetic, intense emotional depth, ultra-detailed "
     "skin pores and eyelashes, 4k film texture. Camera movement: the previous red light morphs "
     "seamlessly into the pupil; the phone feed swirls inside the iris with seamless motion physics."),

    ("Cinematic low-angle shot of a teenager's sneakers pressing heavily and firmly into a dark, "
     "textured concrete floor. Surreal wisps of pure white smoke and heat vapor gently evaporate "
     "from the shoes into the air, visually representing internal panic pressure dissipating into "
     "the ground. Moody, atmospheric depth, high shadow details, 4k. Camera movement: sharp crane "
     "shot moving downward, locking onto the sneakers; the vapor blends smoothly into the air."),

    ("A pristine, minimal dark studio background. A sharp, dramatic volumetric beam of pure "
     "cinematic light cuts through the darkness from above, perfectly illuminating the physical "
     "book cover of 'Your Alarm Isn't Broken' by Daniel Vega. Elegant, premium book commercial "
     "aesthetic, left side empty for clean graphic layout, 4k. Camera movement: noble slow "
     "dolly-in toward the book as the light focuses on the cover and the background sinks into darkness."),
]
SCENE_SECS = [3, 4, 4, 4]   # = 15sn

SCRIPT = ("Your internal alarm is blasting way too loud... but you are not broken. It's just "
          "sensitive. Stop fighting the wave - train your next move. Take back the controls. "
          "Read 'Your Alarm Isn't Broken' by Daniel Vega. Available now.")

SUBS = [  # seslendirme, kullanicinin 4 sahne penceresine bolundu
    (0,  3,  "Your internal alarm is blasting way too loud..."),
    (3,  7,  "but you are not broken. It's just sensitive."),
    (7,  11, "Stop fighting the wave - train your next move. Take back the controls."),
    (11, 15, "Read 'Your Alarm Isn't Broken' by Daniel Vega. Available now."),
]
VOICE_ID = "MFZUKuGQUsGJPQjTS4wC"
MODEL    = "eleven_v3"
VEO      = "google/veo-3.1-fast"
COVER    = "public/image/186545.png"
# ===============================================================================================

RAPI = "https://api.replicate.com/v1/models/{}/predictions"
RHDR = {"Authorization": "Bearer " + REP, "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

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
    pred = rep_post(model, payload); g = pred["urls"]["get"]; t0, n = time.time(), 0
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

def t(s):
    h = int(s // 3600); m = int((s % 3600) // 60); x = s % 60
    return "{:d}:{:02d}:{:05.2f}".format(h, m, x)

def write_ass(lines):
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Def,Arial,64,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,4,1,2,60,60,130,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    body = "".join("Dialogue: 0,{},{},Def,,0,0,0,,{}\n".format(t(s), t(e), x.strip()) for s, e, x in lines)
    open("subs.ass", "w", encoding="utf-8").write(head + body)

# ================================== AKIS ==================================
# 1) 4 VEO KLIBI
veo_files = []
for i, pr in enumerate(PROMPTS, 1):
    out = rep_run(VEO, {"prompt": pr, "aspect_ratio": "9:16", "resolution": "1080p",
                        "duration": 4, "generate_audio": False}, "VEO {} / 3.1 Fast".format(i))
    fn = "veo{}.mp4".format(i); download(first_url(out), fn); veo_files.append(fn)

# 2) ELEVENLABS SES
print("\n[SES] ElevenLabs...")
ehdr = {"xi-api-key": XI, "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
ebody = json.dumps({"text": SCRIPT, "model_id": MODEL}).encode("utf-8")
req = urllib.request.Request("https://api.elevenlabs.io/v1/text-to-speech/{}".format(VOICE_ID),
                             data=ebody, headers=ehdr, method="POST")
try:
    with urllib.request.urlopen(req, context=CTX) as r:
        open("voice.mp3", "wb").write(r.read())
    print("  ses hazir.")
except urllib.error.HTTPError as e:
    print("HATA: ElevenLabs -> HTTP {} {}".format(e.code, e.read().decode("utf-8", "ignore"))); sys.exit(1)

# 3) ALTYAZI
write_ass(SUBS)

# 4) KIRP + BIRLESTIR (15sn)
print("\n[MONTAJ] klipler kirpiliyor + birlestiriliyor...")
parts, inputs = [], []
for i, sec in enumerate(SCENE_SECS):
    inputs += ["-i", veo_files[i]]
    parts.append("[{}:v]trim=0:{},setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,"
                 "crop=1080:1920[v{}]".format(i, sec, i))
flt = ";".join(parts) + ";" + "".join("[v{}]".format(i) for i in range(4)) + "concat=n=4:v=1:a=0[v]"
subprocess.run([FF, "-y"] + inputs + ["-filter_complex", flt, "-map", "[v]", "broll.mp4"],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 5) SES + GORSEL (15sn)
subprocess.run([FF, "-y", "-i", "broll.mp4", "-i", "voice.mp3", "-map", "0:v", "-map", "1:a",
                "-t", "15", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "voiced.mp4"],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 6) ALTYAZI + KAPAK (sol, son 4sn)
print("[MONTAJ] altyazi + kapak (sol)...")
have_cover = os.path.exists(COVER)
try:
    if have_cover:
        flt2 = ("[0:v]subtitles=subs.ass[s];[1:v]scale=520:-1[c];"
                "[s][c]overlay=x=70:y=(H-h)/2:enable='gte(t,11.0)'[outv]")
        cmd = [FF, "-y", "-i", "voiced.mp4", "-i", COVER, "-filter_complex", flt2,
               "-map", "[outv]", "-map", "0:a", "-t", "15",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", "full_ad.mp4"]
    else:
        cmd = [FF, "-y", "-i", "voiced.mp4", "-vf", "subtitles=subs.ass", "-t", "15",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", "full_ad.mp4"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print("\nBITTI -> full_ad.mp4  (15sn, Veo 3.1 + ses + altyazi" + (" + kapak" if have_cover else "") + ")")
except subprocess.CalledProcessError as e:
    err = (e.stderr or b"").decode("utf-8", "ignore")[-400:]
    print("\nAltyazi patladi, kapagi altyazisiz bindiriyorum...")
    flt3 = "[1:v]scale=520:-1[c];[0:v][c]overlay=x=70:y=(H-h)/2:enable='gte(t,11.0)'[outv]"
    subprocess.run([FF, "-y", "-i", "voiced.mp4", "-i", COVER, "-filter_complex", flt3,
                    "-map", "[outv]", "-map", "0:a", "-t", "15",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", "full_ad.mp4"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("BITTI -> full_ad.mp4 (kapak var, altyazi yok). libass notu:", err)
