#!/usr/bin/env bash
# validate_video.sh — yayindan ONCE bozuk/eksik render yakalama kapisi.
# Kullanim: ./validate_video.sh <video.mp4> <beklenen_sure_saniye>
# Cikis: 0 = saglam, !=0 = BOZUK (yayinlama)

set -u
FILE="${1:-}"
EXPECTED="${2:-}"

if [ -z "$FILE" ] || [ -z "$EXPECTED" ]; then
  echo "Kullanim: $0 <video.mp4> <beklenen_sure_sn>"
  exit 99
fi

# 1) Dosya var mi ve 0-byte degil mi?
if [ ! -s "$FILE" ]; then
  echo "HATA 1: dosya yok veya 0-byte -> $FILE"
  exit 1
fi

# 2) Sure beklenenin %5 bandinda mi?
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$FILE" 2>/dev/null)
if [ -z "$DUR" ]; then
  echo "HATA 2: sure okunamadi (bozuk konteyner?)"
  exit 2
fi
OK=$(awk -v d="$DUR" -v e="$EXPECTED" 'BEGIN{ r=d/e; print (r<0.95 || r>1.05) ? "BAD" : "OK" }')
if [ "$OK" = "BAD" ]; then
  echo "HATA 2: sure sapmasi -> gercek=${DUR}sn beklenen=${EXPECTED}sn"
  exit 2
fi

# 3) Ses akisi var mi ve sessiz degil mi?
HAS_AUDIO=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$FILE" 2>/dev/null)
if [ -z "$HAS_AUDIO" ]; then
  echo "HATA 3: ses akisi YOK"
  exit 3
fi
# mean_volume dB degerini al; -60 dB altindaysa pratikte sessiz say
MEANVOL=$(ffmpeg -i "$FILE" -af volumedetect -f null - 2>&1 | grep -oE "mean_volume: -?[0-9]+(\.[0-9]+)?" | grep -oE "\-?[0-9]+(\.[0-9]+)?$" | head -n1)
if [ -z "$MEANVOL" ]; then
  echo "HATA 3: ses seviyesi okunamadi"
  exit 3
fi
SILENT=$(awk -v v="$MEANVOL" 'BEGIN{ print (v < -60) ? "YES" : "NO" }')
if [ "$SILENT" = "YES" ]; then
  echo "HATA 3: ses var ama pratikte SESSIZ (mean_volume=${MEANVOL} dB)"
  exit 3
fi

# 4) Video akisi var mi?
HAS_VIDEO=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$FILE" 2>/dev/null)
if [ -z "$HAS_VIDEO" ]; then
  echo "HATA 4: video akisi YOK"
  exit 4
fi

echo "SAGLAM: sure=${DUR}sn, ses=${HAS_AUDIO}, video=${HAS_VIDEO}"
exit 0
