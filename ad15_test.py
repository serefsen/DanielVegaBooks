# -*- coding: utf-8 -*-
"""
Daniel Vega - SIFIRDAN 15sn TAM REKLAM (LOKAL, TEK DOSYA)
Akis: Nano Banana 4 kare -> Kling 3 gecis klibi (3x5sn=15sn) ->
      ElevenLabs ses + senkron altyazi -> ffmpeg montaj (kapak/CTA) -> 15sn
Cikti: full_ad.mp4 (altyazi+kapak olursa) / yoksa voiced.mp4 (ses+gorsel garanti)
Token: $env:REPLICATE_API_TOKEN="r8_..."  +  $env:ELEVENLABS_API_KEY="xi_..."
Kur  : python -m pip install imageio-ffmpeg
Calistir (C:\DanielVegaBooks icinden): python ad15_test.py
Sure : ~9-10 dk (4 kare + 3 Kling klibi). Sayaclar akar.
"""
import os, sys, json, base64, ssl, re, subprocess
import urllib.request, urllib.error

REP = os.environ.get("REPLICATE_API_TOKEN", "").strip()
XI  = os.environ.get("ELEVENLABS_API_KEY", "").strip()
if not REP or not XI:
    print("HATA: Anahtar eksik. Once PowerShell'de:")
    print('  $env:REPLICATE_API_TOKEN="r8_xxxxxxxx"')
    print('  $env:ELEVENLABS_API_KEY="xi_xxxxxxxx"')
    sys.exit(1)
try:
    import imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    print("HATA: imageio-ffmpeg yok -> python -m pip install imageio-ffmpeg")
    sys.exit(1)

CTX = ssl._create_unverified_context()

# ============================== SENARYO ==============================
SCRIPT = ("Your hands won't stop shaking. Your brain won't slow down. "
          "But your anxiety isn't broken - it's an alarm, just a little too loud. "
          "You can't shut it off. You can train what to do when it rings. "
          "The full toolkit - link in bio.")
VOICE_ID = "MFZUKuGQUsGJPQjTS4wC"
MODEL    = "eleven_v3"
COVER    = "pipeline/assets/kapak-alarm.png"
WPL      = 5

# ===================== 4 KARE (el+kalem, soguk->sicak, YUZSUZ) =====================
FRAMES = [
    # KARE 1 - HOOK / soguk mavi
    ("Vertical 9:16 cinematic extreme close-up, NO face, NO head. A teenager's hand, "
     "knuckles tense and slightly trembling, gripping the edge of a desk in a dark room "
     "before dawn. Cold blue light only. Soft film grain, shallow depth of field, "
     "handheld feel. Raw and intimate, NOT glossy, NOT corporate."),
    # KARE 2 - DONUSUM / soguk->notr
    ("Vertical 9:16 cinematic close-up, NO face. THE SAME hand, now calmer, picking up a "
     "pen and holding it over an open workbook page on the same desk. The cold blue light "
     "begins to soften toward neutral. Soft film grain, shallow depth of field, handheld "
     "feel. Raw, intimate, NOT glossy."),
    # KARE 3 - KULLANIM / isiniyor
    ("Vertical 9:16 cinematic close-up, NO face. THE SAME hand calmly writing with the pen "
     "in the open workbook on the same desk, steady and focused. Warm amber light grows in "
     "the room. Soft film grain, shallow depth of field, handheld feel. Raw, intimate, NOT glossy."),
    # KARE 4 - COZULME / sicak amber
    ("Vertical 9:16 cinematic close-up, NO face. THE SAME hand resting relaxed beside the "
     "open workbook and pen on the same desk, calm and settled. Soft warm amber morning "
     "light fills the frame. Soft film grain, shallow depth of field, handheld feel. "
     "Raw, intimate, NOT glossy."),
]
SEG_MOTIONS = [
    ("The trembling hand slowly steadies and reaches for the pen as the cold blue light "
     "softens. Subtle handheld micro-jitter, 24fps feel, dust drifting in the light. No face, no text."),
    ("The hand brings the pen to the page and begins to write, calm and deliberate, as the "
     "light warms. Gentle handheld drift, 24fps feel. No face, no text."),
    ("The writing slows and the hand settles to rest beside the workbook as warm amber "
     "morning light fills the room, calm and resolved. Soft handheld drift, 24fps feel. No face, no text."),
]
NEG = ("face, head, deformed hands, extra fingers, mutated fingers, text, watermark, logo, "
       "cartoon, oversaturated, glossy corporate look, distorted")

# ============================ Replicate yardimcilari ============================
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
    import time; t0, n = time.time(), 0
    while True:
        p = rep_get(g); st = p["status"]; n += 1
        sys.stdout.write("\r  [{}] {:<10} gecen {}sn  kontrol #{}   ".format(
            label, st, int(time.time() - t0), n)); sys.stdout.flush()
        if st == "succeeded":
            print("\n  [{}] TAMAM ({}sn)".format(label, int(time.time() - t0))); return p["output"]
        if st in ("failed", "canceled"):
            print("\n  [{}] HATA: {}".format(label, p.get("error"))); sys.exit(1)
        time.sleep(3)

def first_url(o): return o[0] if isinstance(o, list) else o

def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=CTX) as r, open(path, "wb") as f:
        f.write(r.read())
    print("  kaydedildi -> {}".format(path))

# ============================ Altyazi / ffmpeg yardimcilari ============================
def secs_to_ass(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return "{:d}:{:02d}:{:05.2f}".format(h, m, s)

def write_ass(lines):
    head = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Def,Arial,46,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,95,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    body = "".join("Dialogue: 0,{},{},Def,,0,0,0,,{}\n".format(
        secs_to_ass(s), secs_to_ass(e), t.replace("\n", " ").strip()) for s, e, t in lines)
    with open("subs.ass", "w", encoding="utf-8") as fp: fp.write(head + body)

def get_dur(path):
    p = subprocess.run([FF, "-i", path], stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
    m = re.search(rb"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
    if not m: return 0.0
    h, mi, s = m.groups(); return int(h) * 3600 + int(mi) * 60 + float(s)

# ================================== AKIS ==================================
# 1) 4 KARE
frame_urls = []
for i, pr in enumerate(FRAMES, 1):
    out = rep_run("google/nano-banana-pro",
                  {"prompt": pr, "aspect_ratio": "9:16", "output_format": "png"},
                  "KARE {} / Nano Banana".format(i))
    u = first_url(out); frame_urls.append(u); download(u, "frame{}.png".format(i))

# 2) 3 GECIS KLIBI (5sn x 3 = 15sn)
seg_files = []
for i, mo in enumerate(SEG_MOTIONS, 1):
    out = rep_run("kwaivgi/kling-v3-video", {
        "prompt": mo, "start_image": frame_urls[i - 1], "end_image": frame_urls[i],
        "duration": 5, "mode": "standard", "generate_audio": False, "negative_prompt": NEG,
    }, "KLIP {} / Kling (kare{}->kare{})".format(i, i, i + 1))
    fn = "seg{}.mp4".format(i); download(first_url(out), fn); seg_files.append(fn)

# 3) SES + ALTYAZI (ElevenLabs timestamps, Whisper YOK)
print("\n[SES] ElevenLabs + zaman damgalari...")
ehdr = {"xi-api-key": XI, "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
ebody = json.dumps({"text": SCRIPT, "model_id": MODEL}).encode("utf-8")
ts_url = "https://api.elevenlabs.io/v1/text-to-speech/{}/with-timestamps".format(VOICE_ID)
got = False
try:
    req = urllib.request.Request(ts_url, data=ebody, headers=ehdr, method="POST")
    with urllib.request.urlopen(req, context=CTX) as r:
        d = json.loads(r.read().decode("utf-8"))
    open("voice.mp3", "wb").write(base64.b64decode(d["audio_base64"]))
    al = d.get("alignment") or d.get("normalized_alignment")
    chars, cs, ce = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    words, cur, ws = [], "", None
    for i, ch in enumerate(chars):
        if ch == " ":
            if cur: words.append((cur, ws, ce[i - 1])); cur, ws = "", None
        else:
            if not cur: ws = cs[i]
            cur += ch
    if cur: words.append((cur, ws, ce[-1]))
    lines = [(words[i][1], words[min(i + WPL, len(words)) - 1][2],
              " ".join(w[0] for w in words[i:i + WPL])) for i in range(0, len(words), WPL)]
    write_ass(lines); got = True; print("  ses + senkron altyazi hazir.")
except urllib.error.HTTPError as e:
    print("  with-timestamps yok (HTTP {}), duz sese dusuyorum.".format(e.code))
if not got:
    plain = "https://api.elevenlabs.io/v1/text-to-speech/{}".format(VOICE_ID)
    req = urllib.request.Request(plain, data=ebody, headers=ehdr, method="POST")
    try:
        with urllib.request.urlopen(req, context=CTX) as r:
            open("voice.mp3", "wb").write(r.read())
    except urllib.error.HTTPError as e:
        print("HATA: ElevenLabs -> HTTP {} {}".format(e.code, e.read().decode("utf-8", "ignore"))); sys.exit(1)
    dur = get_dur("voice.mp3"); wlist = SCRIPT.split()
    n = max(1, (len(wlist) + WPL - 1) // WPL); per = dur / n
    lines = []
    for i in range(n):
        ck = wlist[i * WPL:(i + 1) * WPL]
        if ck: lines.append((i * per, (i + 1) * per, " ".join(ck)))
    write_ass(lines); print("  ses hazir, altyazi YAKLASIK.")

# 4) B-ROLL BIRLESTIR (15sn)
print("\n[MONTAJ] segmentler birlestiriliyor...")
subprocess.run([FF, "-y", "-i", "seg1.mp4", "-i", "seg2.mp4", "-i", "seg3.mp4",
                "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
                "-map", "[v]", "broll.mp4"], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 5) SES + GORSEL (GARANTI, tam 15sn)
subprocess.run([FF, "-y", "-i", "broll.mp4", "-i", "voice.mp3",
                "-map", "0:v", "-map", "1:a", "-t", "15",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "voiced.mp4"],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 6) ALTYAZI + KAPAK/CTA (son 4sn), tam 15sn
print("[MONTAJ] altyazi + kapak/CTA...")
have_cover = os.path.exists(COVER)
try:
    if have_cover:
        flt = ("[0:v]subtitles=subs.ass[s];[1:v]scale=480:-1[c];"
               "[s][c]overlay=(W-w)/2:(H-h)/2-150:enable='gte(t,11.0)'[outv]")
        cmd = [FF, "-y", "-i", "voiced.mp4", "-i", COVER, "-filter_complex", flt,
               "-map", "[outv]", "-map", "0:a", "-t", "15",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", "full_ad.mp4"]
    else:
        cmd = [FF, "-y", "-i", "voiced.mp4", "-vf", "subtitles=subs.ass", "-t", "15",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", "full_ad.mp4"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print("\nBITTI -> full_ad.mp4  (15sn, ses + altyazi" + (" + kapak/CTA" if have_cover else "") + ")")
except subprocess.CalledProcessError as e:
    err = (e.stderr or b"").decode("utf-8", "ignore")[-400:]
    print("\nAltyazi/kapak adimi patladi (ffmpeg libass yok olabilir).")
    print("AMA voiced.mp4 HAZIR (15sn, ses+gorsel) - reklami degerlendirebilirsin.")
    print("ffmpeg notu:", err)
