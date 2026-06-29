# -*- coding: utf-8 -*-
"""
Daniel Vega - KAPAK EKLE (yeniden uretim YOK)
Mevcut voiced.mp4 + subs.ass uzerine 3D kitabi (public/image/oubn.png)
son 4 saniyede SAG tarafa bindirir -> full_ad.mp4
Calistir (C:\DanielVegaBooks icinden): python add_cover.py
"""
import os, sys, subprocess
try:
    import imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    print("HATA: imageio-ffmpeg yok -> python -m pip install imageio-ffmpeg"); sys.exit(1)

COVER = "public/image/oubn.png"
for f in ("voiced.mp4", "subs.ass", COVER):
    if not os.path.exists(f):
        print("HATA: {} bulunamadi. Bu scripti C:\\DanielVegaBooks icinden calistir.".format(f)); sys.exit(1)

# kitap sag tarafta, son 4sn (t>=11), dikey ortali
flt = ("[0:v]subtitles=subs.ass[s];"
       "[1:v]scale=520:-1[c];"
       "[s][c]overlay=x=W-w-70:y=(H-h)/2:enable='gte(t,11.0)'[outv]")

print("[MONTAJ] altyazi + kitap (sag, son 4sn)...")
try:
    subprocess.run([FF, "-y", "-i", "voiced.mp4", "-i", COVER,
                    "-filter_complex", flt, "-map", "[outv]", "-map", "0:a", "-t", "15",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", "full_ad.mp4"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print("BITTI -> full_ad.mp4  (15sn, ses + altyazi + kitap)")
except subprocess.CalledProcessError as e:
    err = (e.stderr or b"").decode("utf-8", "ignore")[-400:]
    print("Altyazili deneme patladi, kapagi altyazisiz bindiriyorum...")
    flt2 = "[1:v]scale=520:-1[c];[0:v][c]overlay=x=W-w-70:y=(H-h)/2:enable='gte(t,11.0)'[outv]"
    subprocess.run([FF, "-y", "-i", "voiced.mp4", "-i", COVER,
                    "-filter_complex", flt2, "-map", "[outv]", "-map", "0:a", "-t", "15",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", "full_ad.mp4"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("BITTI -> full_ad.mp4 (kitap var, altyazi yok). libass notu:", err)
