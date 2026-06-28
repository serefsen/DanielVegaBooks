#!/usr/bin/env python3
"""
make_video.py â€” TEK bir videoyu bastan sona uretir.
Zincir: compliance lint -> Daniel klibi (HeyGen) -> b-roll sec -> ffmpeg montaj -> dogrula

Kullanim:
    python3 make_video.py --item content/item.json --out out/
    python3 make_video.py --item content/item.json --out out/ --local-daniel test_daniel.mp4
        (--local-daniel: HeyGen'i atla, hazir bir klip kullan; YEREL TEST icin)

item.json sema:
{
  "id": "v001",
  "arm": "avatar",                 # "avatar" | "faceless"
  "script": "When I was fifteen...",
  "srt": "1\n00:00:00,000 --> ...",   # altyazi (SRT govdesi)
  "expected_sec": 12,
  "avatar_id": "cc997a86...",      # arm=avatar ise
  "voice_id": "e209b585...",
  "ai_label": true                 # AI etiketi (etik/politika)
}

Cevre degiskenleri (GitHub Secrets):
  HEYGEN_API_KEY   â€” HeyGen API anahtari
  PEXELS_API_KEY   â€” Pexels API anahtari (b-roll cekmek icin; havuz boÅŸsa)
"""

import os, sys, json, time, subprocess, argparse, tempfile, urllib.request, urllib.parse

HEYGEN_KEY = os.environ.get("HEYGEN_API_KEY", "")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")
HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd, **kw):
    """Komut calistir, cikti+kod don."""
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# ---------- 1) COMPLIANCE LINT ----------
def lint_script(script_text):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(script_text)
        path = f.name
    r = run(["python3", os.path.join(HERE, "compliance_lint.py"), path])
    os.unlink(path)
    # exit 1 = block, 2 = warn, 0 = temiz
    return r.returncode, r.stdout


# ---------- 2) DANIEL KLIBI (HeyGen) ----------
def heygen_generate(avatar_id, voice_id, script, expected_sec):
    """HeyGen v2 ile photo-avatar konusan video uret, video_url don."""
    body = json.dumps({
        "video_inputs": [{
            "character": {"type": "talking_photo", "talking_photo_id": avatar_id},
            "voice": {"type": "text", "input_text": script, "voice_id": voice_id},
        }],
        "dimension": {"width": 720, "height": 1280},
        "video_engine": "avatar_iv",
    }).encode()
    req = urllib.request.Request(
        "https://api.heygen.com/v2/video/generate",
        data=body,
        headers={"X-Api-Key": HEYGEN_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    vid = json.load(urllib.request.urlopen(req))["data"]["video_id"]

    # poll
    for _ in range(120):  # ~10 dk tavan
        sreq = urllib.request.Request(
            f"https://api.heygen.com/v1/video_status.get?video_id={vid}",
            headers={"X-Api-Key": HEYGEN_KEY},
        )
        d = json.load(urllib.request.urlopen(sreq))["data"]
        if d["status"] == "completed":
            return d["video_url"]
        if d["status"] == "failed":
            raise RuntimeError(f"HeyGen render failed: {d.get('error')}")
        time.sleep(8)
    raise TimeoutError("HeyGen render zaman asimi")


def download(url, dst):
    urllib.request.urlretrieve(url, dst)
    return dst


# ---------- 3) B-ROLL SEC ----------
def pick_broll(script_path, broll_dir, state_path):
    r = run(["python3", os.path.join(HERE, "pick_broll.py"),
             script_path, broll_dir, state_path])
    if r.returncode != 0:
        raise RuntimeError(f"b-roll secimi basarisiz: {r.stderr}")
    return r.stdout.strip()


# ---------- 4) FFMPEG MONTAJ ----------
def composite(bg, daniel, srt_path, out, arm):
    """
    arm=avatar -> arka plan + kosede Daniel + altyazi
    arm=faceless -> arka plan + altyazi (Daniel yok); ses b-roll'da olmadigi icin
                    faceless kolda ses ayri voiceover olmali (ileride); simdilik bg sesi.
    Mikro-donusum: arka plana hafif olcek/hiz oynamasi (birebir tekrar kirma).
    """
    sub = (f"subtitles={srt_path}:force_style="
           "'FontName=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,"
           "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,"
           "Alignment=2,MarginV=90'")

    # Tam ekran b-roll + Daniel sesi + altyazi + SONDA kitap kapagi & CTA.
    # Kapak son ~4sn'de belirir (panel: kapak 11.sn'den once gorunmesin).
    cover = os.path.join(HERE, "assets", "kapak-alarm.png")
    cta_text = "The full toolkit \u2014 link in bio"
    # Daniel sesinin suresini al (kapagi sona hizalamak icin)
    probe = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", daniel])
    try:
        dur = float(probe.stdout.strip())
    except Exception:
        dur = 15.0
    cover_in = max(0.0, dur - 4.0)  # son 4 saniye
    cta = (f"drawtext=text='{cta_text}':fontcolor=white:fontsize=30:"
           f"x=(w-text_w)/2:y=h-180:box=1:boxcolor=black@0.5:boxborderw=12:"
           f"enable='gte(t,{cover_in})'")
    # b-roll'u Daniel ses suresine UZAT (son kare donuk kalmasin, ikisi esit bitsin).
    # tpad=stop_mode=clone son kareyi klonlayarak sureyi doldurur; sonra dur'a kirp.
    fc = (
        "[0:v]scale=720:1280:force_original_aspect_ratio=increase,"
        f"crop=720:1280,setsar=1,tpad=stop_mode=clone:stop_duration={dur}[bgv];"
        f"[bgv]trim=duration={dur},setpts=PTS-STARTPTS[bgt];"
        "[2:v]scale=460:-1[cov];"
        f"[bgt][cov]overlay=(W-w)/2:(H-h)/2-160:enable='gte(t,{cover_in})'[covered];"
        f"[covered]{sub},{cta}[out]"
    )
    cmd = ["ffmpeg", "-y", "-i", bg, "-i", daniel, "-i", cover,
           "-filter_complex", fc,
           "-map", "[out]", "-map", "1:a",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
           "-shortest", out, "-loglevel", "error"]
    r = run(cmd)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg montaj hatasi: {r.stderr}")
    return out


# ---------- 5) DOGRULA ----------
def validate(path, expected_sec):
    r = run(["bash", os.path.join(HERE, "validate_video.sh"), path])
    return r.returncode, r.stdout.strip()


# ---------- ANA AKIS ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", required=True)
    ap.add_argument("--out", default="out")
    ap.add_argument("--broll-dir", default=os.path.join(HERE, "broll"))
    ap.add_argument("--state", default=os.path.join(HERE, "broll_state.json"))
    ap.add_argument("--local-daniel", default=None,
                    help="HeyGen yerine hazir klip (yerel test)")
    ap.add_argument("--local-bg", default=None,
                    help="Pexels/havuz yerine hazir arka plan (yerel test)")
    args = ap.parse_args()

    item = json.load(open(args.item, encoding="utf-8-sig"))
    os.makedirs(args.out, exist_ok=True)
    vid_id = item["id"]
    arm = item.get("arm", "avatar")

    print(f"=== {vid_id} (kol: {arm}) ===")

    # 1) LINT
    code, report = lint_script(item["script"])
    if code == 1:
        print(f"[{vid_id}] ENGELLENDI (compliance). Atlandi.\n{report}")
        sys.exit(10)
    print(f"[{vid_id}] lint OK (kod {code})")

    # script'i dosyaya yaz (b-roll secimi icin lazim)
    spath = os.path.join(args.out, f"{vid_id}_script.txt")
    open(spath, "w", encoding="utf-8").write(item["script"])

    # srt'yi dosyaya yaz
    srt_path = os.path.join(args.out, f"{vid_id}.srt")
    # srt artik Whisper ile Daniel klibinden uretilecek (asagida)

    # 2) DANIEL
    daniel_path = None
    if args.local_daniel:
        daniel_path = args.local_daniel
        print(f"[{vid_id}] Daniel sesi: yerel ({daniel_path})")
    else:
        print(f"[{vid_id}] Daniel sesi: ElevenLabs...")
        daniel_path = elevenlabs_voice(item["script"], item["voice_id"],
                                       os.path.join(args.out, f"{vid_id}_daniel.mp3"))
        print(f"[{vid_id}] Daniel sesi hazir: {daniel_path}")

    # 3) B-ROLL (Seedance, script-ozel)
    if args.local_bg:
        bg_path = args.local_bg
        print(f"[{vid_id}] b-roll: yerel ({bg_path})")
    else:
        bprompt = item.get("broll_prompt")
        if not bprompt:
            raise ValueError(f"{vid_id}: broll_prompt yok (queue.json'a ekle)")
        bg_path = os.path.join(args.out, f"{vid_id}_broll.mp4")
        print(f"[{vid_id}] b-roll uretiliyor (Seedance)...")
        make_broll(bprompt, bg_path)
        print(f"[{vid_id}] b-roll hazir: {bg_path}")

    # 3.5) ALTYAZI (Whisper, Daniel klibinden senkron)
    if daniel_path:
        make_subtitles(daniel_path, srt_path)
        print(f"[{vid_id}] altyazi (whisper) OK")

    # 4) MONTAJ
    final = os.path.join(args.out, f"{vid_id}_final.mp4")
    composite(bg_path, daniel_path, srt_path, final, arm)
    print(f"[{vid_id}] montaj OK -> {final}")

    # 5) DOGRULA
    vcode, vreport = validate(final, item["expected_sec"])
    if vcode != 0:
        print(f"[{vid_id}] DOGRULAMA BASARISIZ -> YAYINLAMA\n{vreport}")
        sys.exit(20)
    print(f"[{vid_id}] dogrulama OK -> {vreport}")
    print(f"[{vid_id}] HAZIR: {final}")


# ---------- WHISPER OTOMATIK ALTYAZI ----------
def make_subtitles(media_path, out_srt):
    """Daniel klibinden sesi alip Whisper ile senkron SRT uretir."""
    import whisper
    model = whisper.load_model("base")
    result = model.transcribe(media_path, language="en", task="transcribe")
    def ts(sec):
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int((sec - int(sec)) * 1000)
        return "%02d:%02d:%02d,%03d" % (h, m, s, ms)
    lines = []
    idx = 1
    for seg in result["segments"]:
        words = seg["text"].strip().split()
        s, e = seg["start"], seg["end"]
        # her segmenti ~5 kelimelik parcalara bol, sureyi esit dagit
        chunk = 5
        groups = [words[j:j+chunk] for j in range(0, len(words), chunk)] or [[""]]
        dur = (e - s) / len(groups)
        for gi, g in enumerate(groups):
            gs = s + gi * dur
            ge = s + (gi + 1) * dur
            lines.append("%d\n%s --> %s\n%s\n" % (idx, ts(gs), ts(ge), " ".join(g)))
            idx += 1
    open(out_srt, "w", encoding="utf-8").write("\n".join(lines))
    return out_srt


# ---------- SEEDANCE B-ROLL (script-ozel, 480p, insansiz) ----------
def make_broll(prompt, out_path):
    """Seedance 2.0 ile script-ozel dikey b-roll uretir (480p, sessiz)."""
    import ssl, urllib.request
    ctx = ssl._create_unverified_context()
    token = os.environ.get("REPLICATE_API_TOKEN", "")
    ua = "Mozilla/5.0"
    h = {"Authorization": "Bearer " + token, "User-Agent": ua}
    version = "a6dcbae88b153e75fcccabacfb0eb430ab5be0a7ae27b316fc6f983658b349bc"
    body = {"version": version, "input": {
        "prompt": prompt, "duration": 15, "aspect_ratio": "9:16",
        "resolution": "480p", "generate_audio": False}}
    req = urllib.request.Request("https://api.replicate.com/v1/predictions",
        data=json.dumps(body).encode(),
        headers={**h, "Content-Type": "application/json"}, method="POST")
    pid = json.load(urllib.request.urlopen(req, context=ctx))["id"]
    url = "https://api.replicate.com/v1/predictions/" + pid
    start = time.time()
    for i in range(200):
        st = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=h), context=ctx))
        elapsed = int(time.time() - start)
        print("    [seedance] durum: %-12s | gecen: %3dsn" % (st["status"], elapsed))
        if st["status"] == "succeeded":
            out = st["output"]
            vurl = out if isinstance(out, str) else out[0]
            rq = urllib.request.Request(vurl, headers={"User-Agent": ua})
            with urllib.request.urlopen(rq, context=ctx) as r, open(out_path, "wb") as f:
                f.write(r.read())
            return out_path
        if st["status"] in ("failed", "canceled"):
            raise RuntimeError("Seedance hata: " + str(st.get("error")))
        time.sleep(6)
    raise TimeoutError("Seedance zaman asimi")