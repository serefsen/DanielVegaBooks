# -*- coding: utf-8 -*-
"""
Daniel Vega - SON KARE DONSUN (end-card hold)
Mevcut voiced.mp4'un son karesini HOLD saniye dondurur; kitap + son yazi
o donmus karede kalir. Yeniden uretim YOK.
Calistir (C:\DanielVegaBooks icinden): python hold_end.py
"""
import os, sys, subprocess
try:
    import imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    print("HATA: imageio-ffmpeg yok -> python -m pip install imageio-ffmpeg"); sys.exit(1)

HOLD  = 3          # <-- son kare kac saniye donsun (degistir)
COVER = "public/image/oubn.png"
END   = 15 + HOLD

for f in ("voiced.mp4", COVER):
    if not os.path.exists(f):
        print("HATA: {} bulunamadi. C:\\DanielVegaBooks icinden calistir.".format(f)); sys.exit(1)

# altyazi - son satir HOLD boyunca da gorunsun diye sonu END'e uzatildi
def t(s):
    h = int(s // 3600); m = int((s % 3600) // 60); x = s % 60
    return "{:d}:{:02d}:{:05.2f}".format(h, m, x)
SUBS = [
    (0,  4,   "A racing heart isn't proof you'll fail; it's a sign that this moment matters."),
    (4,  7,   "Don't train the pressure - train your response."),
    (7,  11,  "Take that step anyway."),
    (11, END, "'Your Pressure Isn't Proof' by Daniel Vega. Available now."),
]
head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
    "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, "
    "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
    "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
    "Style: Def,Arial,64,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,4,1,2,60,60,130,1\n\n"
    "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
open("subs.ass", "w", encoding="utf-8").write(
    head + "".join("Dialogue: 0,{},{},Def,,0,0,0,,{}\n".format(t(s), t(e), x) for s, e, x in SUBS))

# 1) son kareyi dondur + sesi sessizlikle uzat
print("[1/2] son kare donduruluyor ({}sn)...".format(HOLD))
subprocess.run([FF, "-y", "-i", "voiced.mp4", "-filter_complex",
                "[0:v]tpad=stop_mode=clone:stop_duration={}[v];[0:a]apad=pad_dur={}[a]".format(HOLD, HOLD),
                "-map", "[v]", "-map", "[a]", "-t", str(END),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "voiced_hold.mp4"],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 2) altyazi + kitap (kitap son donmus karede de durur)
print("[2/2] altyazi + kitap...")
flt = ("[0:v]subtitles=subs.ass[s];[1:v]scale=520:-1[c];"
       "[s][c]overlay=x=W-w-70:y=(H-h)/2:enable='gte(t,11.0)'[outv]")
try:
    subprocess.run([FF, "-y", "-i", "voiced_hold.mp4", "-i", COVER,
                    "-filter_complex", flt, "-map", "[outv]", "-map", "0:a", "-t", str(END),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", "full_ad.mp4"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print("BITTI -> full_ad.mp4  ({}sn, son kare {}sn donuk)".format(END, HOLD))
except subprocess.CalledProcessError as e:
    err = (e.stderr or b"").decode("utf-8", "ignore")[-400:]
    print("Altyazili deneme patladi, kitabi altyazisiz bindiriyorum...")
    flt2 = "[1:v]scale=520:-1[c];[0:v][c]overlay=x=W-w-70:y=(H-h)/2:enable='gte(t,11.0)'[outv]"
    subprocess.run([FF, "-y", "-i", "voiced_hold.mp4", "-i", COVER,
                    "-filter_complex", flt2, "-map", "[outv]", "-map", "0:a", "-t", str(END),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", "full_ad.mp4"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("BITTI -> full_ad.mp4 (kitap var, altyazi yok). libass notu:", err)
