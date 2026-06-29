# -*- coding: utf-8 -*-
"""
Daniel Vega - DUZELTME (yeni Veo YOK, sadece montaj)
1) Gercek kapagi ORTAYA buyuk koyup Veo'nun uydurma kitabini kapatir
2) Son kareyi dondurup TUM seslendirmeyi oynatir (ses kesilmez)
Girdi (diskte): broll.mp4 + voice.mp3 + public/image/186545.png
Cikti: full_ad.mp4
Calistir (C:\DanielVegaBooks icinden): python fix_ad.py
"""
import os, sys, re, subprocess
try:
    import imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    print("HATA: imageio-ffmpeg yok -> python -m pip install imageio-ffmpeg"); sys.exit(1)

COVER = "public/image/186545.png"
for f in ("broll.mp4", "voice.mp3", COVER):
    if not os.path.exists(f):
        print("HATA: {} yok. C:\\DanielVegaBooks icinden calistir.".format(f)); sys.exit(1)

def get_dur(path):
    p = subprocess.run([FF, "-i", path], stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
    m = re.search(rb"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
    if not m: return 15.0
    h, mi, s = m.groups(); return int(h) * 3600 + int(mi) * 60 + float(s)

N = get_dur("voice.mp3")
END = max(15.0, N + 0.4)          # ses bitene kadar uzat
HOLD = max(0.0, END - 15.0)       # 15sn sonrasi donuk kuyruk
print("ses suresi: {:.1f}sn -> video: {:.1f}sn (son {:.1f}sn donuk)".format(N, END, HOLD))

# altyazi - son satir END'e kadar dursun
def t(s):
    h = int(s // 3600); m = int((s % 3600) // 60); x = s % 60
    return "{:d}:{:02d}:{:05.2f}".format(h, m, x)
SUBS = [
    (0,  3,   "Your internal alarm is blasting way too loud..."),
    (3,  7,   "but you are not broken. It's just sensitive."),
    (7,  11,  "Stop fighting the wave - train your next move. Take back the controls."),
    (11, END, "Read 'Your Alarm Isn't Broken' by Daniel Vega. Available now."),
]
head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
    "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, "
    "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
    "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
    "Style: Def,Arial,60,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,4,1,2,60,60,120,1\n\n"
    "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
open("subs.ass", "w", encoding="utf-8").write(
    head + "".join("Dialogue: 0,{},{},Def,,0,0,0,,{}\n".format(t(s), t(e), x) for s, e, x in SUBS))

# 1) broll'u dondurarak uzat + tum sesi koy (kesme yok)
print("[1/2] son kare donduruluyor + tam ses...")
subprocess.run([FF, "-y", "-i", "broll.mp4", "-i", "voice.mp3", "-filter_complex",
                "[0:v]tpad=stop_mode=clone:stop_duration={:.2f}[v];[1:a]apad=whole_dur={:.2f}[a]".format(HOLD, END),
                "-map", "[v]", "-map", "[a]", "-t", "{:.2f}".format(END),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "voiced.mp4"],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 2) altyazi + gercek kapak ORTAYA buyuk (Veo'nun kitabini kapatir), son 4sn+kuyruk
print("[2/2] altyazi + gercek kapak (ortada, buyuk)...")
flt = ("[0:v]subtitles=subs.ass[s];[1:v]scale=780:-1[c];"
       "[s][c]overlay=x=(W-w)/2:y=(H-h)/2+40:enable='gte(t,11.0)'[outv]")
try:
    subprocess.run([FF, "-y", "-i", "voiced.mp4", "-i", COVER, "-filter_complex", flt,
                    "-map", "[outv]", "-map", "0:a", "-t", "{:.2f}".format(END),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", "full_ad.mp4"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print("\nBITTI -> full_ad.mp4  ({:.1f}sn, tek kitap + tam ses)".format(END))
except subprocess.CalledProcessError as e:
    err = (e.stderr or b"").decode("utf-8", "ignore")[-400:]
    print("\nAltyazi patladi, kapagi altyazisiz koyuyorum...")
    flt2 = "[1:v]scale=780:-1[c];[0:v][c]overlay=x=(W-w)/2:y=(H-h)/2+40:enable='gte(t,11.0)'[outv]"
    subprocess.run([FF, "-y", "-i", "voiced.mp4", "-i", COVER, "-filter_complex", flt2,
                    "-map", "[outv]", "-map", "0:a", "-t", "{:.2f}".format(END),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", "full_ad.mp4"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("BITTI -> full_ad.mp4 (tek kitap, altyazi yok). libass notu:", err)
