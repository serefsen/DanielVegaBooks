# -*- coding: utf-8 -*-
# GUNLUK: havuzdan 1 taze reklam uretir (ffmpeg + ElevenLabs + Whisper) ve 4 platforma postlar (Blotato).
# GitHub Actions cron gunde 3 kez calistirir. Env: ELEVENLABS_API_KEY, BLOTATO_API_KEY.
import os, sys, time, json, ssl, random, subprocess, urllib.request, urllib.error

CTX = ssl._create_unverified_context()
UA = "Mozilla/5.0"
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
BLOTATO_KEY = os.environ.get("BLOTATO_API_KEY", "").strip()
MANIFEST = "manifest.json"
STATE_FILE = "gunluk_state.json"   # kullanilan sahne hafizasi (tekrar onleme)
VO_FILE = "seslendirme.json"

VOICE_ID = "MFZUKuGQUsGJPQjTS4wC"
ELEVEN_MODEL = "eleven_v3"
COVER_URL = "https://danielvegabooks.com/image/186545.png"
BLOTATO_BASE = "https://backend.blotato.com/v2"

CAPTION = ("Your anxiety isn't broken - it's working exactly as designed. "
           '"Your Alarm Isn\'t Broken" by Daniel Vega. Save this for 3 a.m.')

# VO index'iyle esli baslik + aciklama (seslendirme.json sirasi)
META = [
    {"title": "Your anxiety isn't broken - it's working as designed",
     "caption": "It's not a glitch. It's an alarm - just set too loud. You can't switch it off, but you can train your response."},
    {"title": "Why your brain replays everything at 3 a.m.",
     "caption": "At 3 a.m. it replays everything at full volume. That's the alarm talking - not the truth."},
    {"title": "That voice narrating everything that could go wrong",
     "caption": "The narrator in your head listing everything that could go wrong is just the alarm, too loud. You can talk back."},
    {"title": "Why anxiety spikes right before they call your name",
     "caption": "Right before your name gets called, it spikes. That's not weakness - that's the alarm doing its job."},
    {"title": "That feeling everyone's watching you? It's lying",
     "caption": "The feeling that everyone's watching and judging is the alarm - lying about how loud it is."},
    {"title": "Avoiding it makes the alarm louder",
     "caption": "Every time you dodge what scares you, the alarm gets louder. Face it small - it quiets."},
    {"title": "Racing heart, tight chest - here's what it actually is",
     "caption": "Racing heart, tight chest. That's not you falling apart - that's the alarm doing its job."},
    {"title": "Your anxiety is a signal, not a flaw",
     "caption": "It's not a flaw - it's a signal, a little too sensitive. You can't delete it. You can only answer it."},
]
META_TAIL = "\n\n\u0022Your Alarm Isn't Broken\u0022 by Daniel Vega. Save this for 3 a.m."
HASHTAGS = "#anxiety #anxietyrelief #teenmentalhealth #mentalhealth #overthinking"
YT_TITLE = "Your anxiety isn't broken (save this for 3 a.m.)"
AMAZON = "https://www.amazon.com/dp/B0H5926917"

# --- Pinterest ---
PIN_TITLE = YT_TITLE
PIN_LINK = "https://danielvegabooks.com/books"   # claimli domain; amazon direkt linki Pinterest spam filtresine takildi
PIN_ALT = "A short video on why teen anxiety isn't broken - from Your Alarm Isn't Broken by Daniel Vega."
PINTEREST_BOARD_ID = ""   # bos = otomatik (ilk board). Belirli board icin ID yaz.
PINTEREST_ENABLED = True   # acik: her calismada video Pinterest'e de gider (gunde 3)

FALLBACK_VO = ("Your anxiety isn't broken. It's working exactly as designed. "
               "You can't switch it off - but you can train your response. "
               '"Your Alarm Isn\'t Broken," by Daniel Vega. Search it - save this for 3 a.m.')

COLOR_ORDER = {"soguk": 0, "gecis": 1, "sicak": 2}
BODY_TARGET = 5
HOOK_LEN = 2
BODY_LEN = 2
CLOSE_LEN = 4


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def http(url, method="GET", data=None, headers=None):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    with urllib.request.urlopen(r, context=CTX) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw.strip() else {}


# ---------- HAVUZ + MONTAJ ----------
def expand_pool(manifest):
    short, closing = [], []
    for m in manifest:
        if m["role"] == "kapanis":
            closing.append({"source": m["id"], "seek": 0, "len": CLOSE_LEN,
                            "role": m["role"], "color": m["color"], "url": m["url"]})
        else:
            for sk in (0, 2):
                short.append({"source": m["id"], "seek": sk, "len": BODY_LEN,
                              "role": m["role"], "color": m["color"], "url": m["url"]})
    return short, closing


def pick_scenes(manifest, rot):
    short, closing = expand_pool(manifest)
    hooks = [s for s in short if s["role"] == "hook"]
    body = [s for s in short if s["role"] in ("kaygi", "donusum")]
    if not hooks or not body or not closing:
        raise RuntimeError("Havuz eksik (hook/govde/kapanis).")
    seen = set(); hsrc = []
    for s in hooks:
        if s["source"] not in seen:
            seen.add(s["source"]); hsrc.append(s)

    # --- SAHNE HAFIZASI (gunluk_state.json): ardisik videolarda ortak sahne IMKANSIZ ---
    try:
        st = json.load(open(STATE_FILE, encoding="utf-8-sig"))
    except Exception:
        st = {}

    # HOOK: tum havuz donmeden ayni hook gelmez
    son_hook = st.get("son_hooklar", [])[-(len(hsrc) - 1):] if len(hsrc) > 1 else []
    aday = [s for s in hsrc if s["source"] not in son_hook]
    hook = aday[rot % len(aday)] if aday else hsrc[rot % len(hsrc)]
    used = {hook["source"]}
    chosen = [hook]

    # GOVDE: sabit renk yayi = 2 soguk + 2 gecis + 1 sicak (soguk->sicak).
    # Her renk kendi hafizasiyla doner (pencere = havuz boyutuna gore).
    govde_st = st.get("govde", {})
    PLAN = [("soguk", 2, 4), ("gecis", 2, 2), ("sicak", 1, 3)]  # (renk, adet, hafiza penceresi)
    random.shuffle(body)
    for renk, adet, pencere in PLAN:
        son = govde_st.get(renk, [])[-pencere:]
        havuz = [s for s in body if s["color"] == renk]
        taze = [s for s in havuz if s["source"] not in son and s["source"] not in used]
        yedek = [s for s in havuz if s["source"] not in used]
        alinan = 0
        for s in taze + [x for x in yedek if x not in taze]:
            if alinan >= adet:
                break
            if s["source"] in used:
                continue
            chosen.append(s); used.add(s["source"]); alinan += 1
            son = (son + [s["source"]])[-pencere:]
        govde_st[renk] = son

    # KAPANIS: son 4'te kullanilmayanlardan
    son_kapanis = st.get("son_kapanis", [])[-4:]
    kap_aday = [c for c in closing if c["source"] not in son_kapanis] or closing
    kapanis = random.choice(kap_aday)
    chosen.append(kapanis)

    # hafizayi kaydet
    st["son_hooklar"] = (son_hook + [hook["source"]])[-(len(hsrc) - 1):]
    st["govde"] = govde_st
    st["son_kapanis"] = (son_kapanis + [kapanis["source"]])[-4:]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    return chosen


def http_bytes(url, method="GET", data=None, headers=None):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    with urllib.request.urlopen(r, context=CTX) as resp:
        return resp.read()


def eleven_tts(text, out_path):
    """Daniel sesi: ElevenLabs'ten mp3 indir."""
    url = "https://api.elevenlabs.io/v1/text-to-speech/" + VOICE_ID
    raw = http_bytes(url, "POST", {"text": text, "model_id": ELEVEN_MODEL},
                     {"xi-api-key": ELEVEN_KEY})
    with open(out_path, "wb") as f:
        f.write(raw)
    return out_path


def whisper_words(audio_path):
    """Kelime bazli zaman damgalari (altyazi senkronu)."""
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, language="en", word_timestamps=True)
    words = []
    for seg in segments:
        for w in (seg.words or []):
            txt = w.word.strip()
            if txt:
                words.append((txt, float(w.start), float(w.end)))
    return words


def _ass_escape(s):
    return s.replace("\\", "").replace("{", "").replace("}", "")


def build_ass(words, out_path, font="Roboto"):
    """J2V gorunumu: alt-orta, 4 kelime/satir, konusulan kelime sari."""
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Alt,%s,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H7F000000,-1,0,0,0,100,100,0,0,1,5,2,2,60,60,300,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    ) % font

    def ts(sec):
        sec = max(0.0, sec)
        h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec % 60
        return "%d:%02d:%05.2f" % (h, m, s)

    lines = [words[i:i + 4] for i in range(0, len(words), 4)]
    ev = []
    for line in lines:
        line_end = line[-1][2]
        for wi, (txt, ws, we) in enumerate(line):
            start = ws
            end = line[wi + 1][1] if wi + 1 < len(line) else line_end
            if end <= start:
                end = start + 0.05
            parts = []
            for wj, (t2, _, _) in enumerate(line):
                t2 = _ass_escape(t2)
                if wj == wi:
                    parts.append("{\\1c&H00FFFF&}" + t2 + "{\\1c&HFFFFFF&}")
                else:
                    parts.append(t2)
            ev.append("Dialogue: 0,%s,%s,Alt,,0,0,0,,%s" % (ts(start), ts(end), " ".join(parts)))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(ev) + "\n")
    return out_path


def find_font():
    """Roboto Bold dosya yolu (drawtext icin); yoksa DejaVu Bold."""
    try:
        out = subprocess.run(["fc-match", "-f", "%{file}", "Roboto:bold"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        if out and os.path.exists(out):
            return out
    except Exception:
        pass
    return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def download_clips(scenes, workdir):
    paths = []
    cache = {}
    for i, s in enumerate(scenes):
        if s["url"] in cache:
            paths.append(cache[s["url"]]); continue
        p = os.path.join(workdir, "klip%02d.mp4" % i)
        with open(p, "wb") as f:
            f.write(http_bytes(s["url"]))
        cache[s["url"]] = p
        paths.append(p)
    return paths


def ffmpeg_render(scenes, vo, workdir="_is"):
    os.makedirs(workdir, exist_ok=True)
    total = sum(s["len"] for s in scenes)

    print("   ses: ElevenLabs...")
    voice = eleven_tts(vo, os.path.join(workdir, "voice.mp3"))
    print("   altyazi: Whisper zaman damgalari...")
    words = whisper_words(voice)
    ass = build_ass(words, os.path.join(workdir, "subs.ass"))
    print("   klipler indiriliyor (%d sahne)..." % len(scenes))
    clips = download_clips(scenes, workdir)

    cover = os.path.join(workdir, "kapak.png")
    with open(cover, "wb") as f:
        f.write(http_bytes(COVER_URL))

    font = find_font()
    fc = []
    for i, s in enumerate(scenes):
        fc.append(
            "[%d:v]trim=start=%s:duration=%s,setpts=PTS-STARTPTS,"
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            "fps=30,setsar=1[v%d]" % (i, s["seek"], s["len"], i))
    fc.append("".join("[v%d]" % i for i in range(len(scenes))) +
              "concat=n=%d:v=1:a=0[vc]" % len(scenes))
    fc.append("[%d:v]scale=500:-1[cov]" % len(scenes))
    fc.append("[vc][cov]overlay=290:250:enable='gte(t,%d)'[ov]" % (total - 2))
    fc.append(
        "[ov]drawtext=fontfile=%s:text='danielvegabooks.com':fontsize=88:fontcolor=white:"
        "x=(w-text_w)/2:y=880:shadowcolor=black@0.7:shadowx=3:shadowy=3:enable='gte(t,%d)'[tx]"
        % (font, total - 2))
    fc.append("[tx]ass=%s[vout]" % os.path.join(workdir, "subs.ass"))
    fc.append("[%d:a]apad[aout]" % (len(scenes) + 1))

    out = os.path.join(workdir, "reklam.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for c in clips:
        cmd += ["-i", c]
    cmd += ["-i", cover, "-i", voice,
            "-filter_complex", ";".join(fc),
            "-map", "[vout]", "-map", "[aout]",
            "-t", str(total), "-r", "30",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", out]
    t0 = time.time()
    print("   render: ffmpeg basladi...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg hatasi: " + (r.stderr or "")[-400:])
    print("   render: done  gecen %ssn" % int(time.time() - t0))
    return out


def blotato_upload(path):
    """mp4'u Blotato'ya yukle -> public URL."""
    resp = blotato("/media/uploads", "POST", {"filename": os.path.basename(path)})
    pre = resp.get("presignedUrl"); pub = resp.get("publicUrl")
    if not pre or not pub:
        raise RuntimeError("Blotato presigned yanit bozuk: " + json.dumps(resp)[:200])
    with open(path, "rb") as f:
        data = f.read()
    req = urllib.request.Request(pre, data=data, method="PUT",
                                 headers={"Content-Type": "video/mp4", "User-Agent": UA})
    with urllib.request.urlopen(req, context=CTX) as r:
        r.read()
    return pub


# ---------- BLOTATO DAGITIM ----------
def blotato(path, method="GET", data=None):
    url = path if path.startswith("http") else BLOTATO_BASE + path
    return http(url, method, data, {"blotato-api-key": BLOTATO_KEY})


def list_accounts():
    data = blotato("/users/me/accounts")
    items = data.get("items", []) if isinstance(data, dict) else (data or [])
    out = {}
    for a in items:
        out.setdefault((a.get("platform") or "").lower(), []).append(a)
    return out


def content_for(platform, media_url, meta=None):
    base = (meta["caption"] + META_TAIL) if meta else CAPTION
    text = base + "\n\n" + (AMAZON + "\n\n" if platform == "youtube" else "") + HASHTAGS
    return {"text": text, "mediaUrls": [media_url], "platform": platform}


def target_for(platform, board_id=None, meta=None):
    ttl = meta["title"] if meta else YT_TITLE
    if platform == "pinterest":
        return {"targetType": "pinterest", "boardId": board_id,
                "title": ttl, "link": PIN_LINK, "altText": PIN_ALT}
    if platform == "tiktok":
        return {"targetType": "tiktok", "privacyLevel": "PUBLIC_TO_EVERYONE",
                "disabledComments": False, "disabledDuet": False, "disabledStitch": False,
                "isBrandedContent": False, "isYourBrand": True, "isAiGenerated": True}
    if platform == "instagram":
        return {"targetType": "instagram", "mediaType": "reel"}
    if platform == "youtube":
        return {"targetType": "youtube", "title": ttl, "privacyStatus": "public",
                "shouldNotifySubscribers": False, "containsSyntheticMedia": True}
    return {"targetType": platform}


def poll_post(sub_id, tries=12, gap=5):
    for _ in range(tries):
        try:
            st = blotato("/posts/" + str(sub_id))
        except Exception:
            return "in-progress"
        status = st.get("status", "")
        if status == "published":
            return "published"
        if status == "failed":
            return "failed: " + str(st.get("errorMessage", ""))
        time.sleep(gap)
    return "in-progress"


def get_pinterest_board(account_id):
    if PINTEREST_BOARD_ID:
        return PINTEREST_BOARD_ID, "(sabit)"
    try:
        data = blotato("/social/pinterest/boards?accountId=" + str(account_id))
        items = data.get("items", []) if isinstance(data, dict) else (data or [])
        if items:
            return str(items[0]["id"]), items[0].get("name", "")
    except Exception as e:
        print("   pinterest board cekilemedi:", e)
    return None, None


def post_all(media_url, accounts, meta=None):
    pin_board = None
    if PINTEREST_ENABLED and accounts.get("pinterest"):
        pin_board, pin_name = get_pinterest_board(accounts["pinterest"][0]["id"])
        print("   pinterest board:", (pin_name + " (" + pin_board + ")") if pin_board else "bulunamadi - pinterest atlanacak")
    elif not PINTEREST_ENABLED:
        print("   pinterest: kapali (Blotato dogrulamasi bekleniyor)")
    for platform in ("tiktok", "instagram", "youtube", "pinterest"):
        if platform == "pinterest" and not pin_board:
            continue
        for a in accounts.get(platform, []):
            try:
                post = {"accountId": str(a["id"]),
                        "content": content_for(platform, media_url, meta),
                        "target": target_for(platform, pin_board, meta)}
                resp = blotato("/posts", "POST", {"post": post})
                sub = resp.get("postSubmissionId") or resp.get("id")
                print("   %s -> %s" % (platform, poll_post(sub) if sub else "submission yok"))
            except urllib.error.HTTPError as e:
                try:
                    msg = e.read().decode("utf-8")[:200]
                except Exception:
                    msg = e.reason
                print("   %s HATA %s: %s" % (platform, e.code, msg))
            except Exception as e:
                print("   %s HATA: %s" % (platform, e))


def main():
    if not ELEVEN_KEY or not BLOTATO_KEY:
        print("HATA: ELEVENLABS_API_KEY veya BLOTATO_API_KEY bos."); sys.exit(1)
    manifest = load_json(MANIFEST, [])
    if not manifest:
        print("HATA: manifest.json yok/bos."); sys.exit(1)
    vos = load_json(VO_FILE, []) or [FALLBACK_VO]

    gm = time.gmtime()
    h = gm.tm_hour
    slot = 0 if 16 <= h <= 21 else (1 if (h >= 22 or h <= 1) else 2)
    rot = gm.tm_yday * 3 + slot
    scenes = pick_scenes(manifest, rot)
    # VO hafizasi: tum varyantlar donmeden ayni VO/baslik gelmez
    try:
        _st = json.load(open(STATE_FILE, encoding="utf-8-sig"))
    except Exception:
        _st = {}
    son_vo = _st.get("son_vo", [])[-(len(vos) - 1):] if len(vos) > 1 else []
    vo_aday = [i for i in range(len(vos)) if i not in son_vo] or list(range(len(vos)))
    vo_idx = vo_aday[rot % len(vo_aday)]
    vo = vos[vo_idx]
    meta = META[vo_idx % len(META)]
    _st["son_vo"] = (son_vo + [vo_idx])[-(len(vos) - 1):]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(_st, f, ensure_ascii=False, indent=1)
    print("Sahneler:", [s["source"] for s in scenes], "| VO:", vo[:40], "...")
    out = ffmpeg_render(scenes, vo)
    print("   yukleniyor (Blotato)...")
    url = blotato_upload(out)
    print("Render bitti:", url)
    print("Dagitiliyor...")
    accounts = list_accounts()
    print("Hesaplar:", {p: len(v) for p, v in accounts.items()})
    post_all(url, accounts, meta)
    print("BITTI.")


if __name__ == "__main__":
    main()
