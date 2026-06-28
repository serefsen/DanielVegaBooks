#!/usr/bin/env bash
# validate_video.sh — yayindan ONCE bozuk/eksik render yakalama kapisi.
# Kullanim: ./validate_video.sh <video.mp4> [min_sn] [max_sn]
# Varsayilan kabul araligi: 5-90 saniye (kisa-video icin makul)
set -u
FILE="${1:-}"
MIN="${2:-5}"
MAX="${3:-90}"

if [ -z "$FILE" ]; then echo "Kullanim: $0 <video.mp4> [min_sn] [max_sn]"; exit 99; fi

# 1) Dosya var ve 0-byte degil
if [ ! -s "$FILE" ]; then echo "HATA 1: dosya yok veya 0-byte -> $FILE"; exit 1; fi

# 2) Sure makul aralikta mi?
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$FILE" 2>/dev/null)
if [ -z "$DUR" ]; then echo "HATA 2: sure okunamadi (bozuk konteyner?)"; exit 2; fi
OK=$(awk -v d="$DUR" -v lo="$MIN" -v hi="$MAX" 'BEGIN{ print (d<lo || d>hi) ? "BAD" : "OK" }')
if [ "$OK" = "BAD" ]; then echo "HATA 2: sure araligin disinda -> ${DUR}sn (kabul: ${MIN}-${MAX}sn)"; exit 2; fi

# 3) Ses var ve sessiz degil
HAS_AUDIO=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$FILE" 2>/dev/null)
if [ -z "$HAS_AUDIO" ]; then echo "HATA 3: ses akisi YOK"; exit 3; fi
MEANVOL=$(ffmpeg -i "$FILE" -af volumedetect -f null - 2>&1 | grep -oE "mean_volume: -?[0-9]+(\.[0-9]+)?" | grep -oE "\-?[0-9]+(\.[0-9]+)?$" | head -n1)
if [ -z "$MEANVOL" ]; then echo "HATA 3: ses seviyesi okunamadi"; exit 3; fi
SILENT=$(awk -v v="$MEANVOL" 'BEGIN{ print (v < -60) ? "YES" : "NO" }')
if [ "$SILENT" = "YES" ]; then echo "HATA 3: ses var ama SESSIZ (mean_volume=${MEANVOL} dB)"; exit 3; fi

# 4) Video akisi var
HAS_VIDEO=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$FILE" 2>/dev/null)
if [ -z "$HAS_VIDEO" ]; then echo "HATA 4: video akisi YOK"; exit 4; fi

echo "SAGLAM: sure=${DUR}sn, ses=${HAS_AUDIO}, video=${HAS_VIDEO}"
exit 0
