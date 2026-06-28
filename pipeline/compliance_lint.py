#!/usr/bin/env python3
"""
compliance_lint.py — Daniel Vega video script kontrolu.
Amac: "anlatici" (I noticed / what helped me) tonunu gecirmek,
"terapist / recete" (you should / when you feel X, do Y) tonunu yakalamak.

Kullanim:
    python3 compliance_lint.py script.txt
    echo "metin" | python3 compliance_lint.py -
Cikis kodu: 0 = temiz, 1 = engellendi (block), 2 = uyari (warn)
"""

import sys
import re

# Saglik / kriz terimleri (kalip eslesmesinde kullanilir)
HEALTH = r"(anxiet\w*|panic|depress\w*|trauma|therapy|therapist|medicat\w*|diagnos\w*|disorder|suicid\w*|self.?harm|mental health)"

# --- BLOCK kurallari: recete / dayatma dili ---
BLOCK_PATTERNS = [
    # "you should/must/need to/have to ... [saglik]"
    (rf"\byou\s+(should|must|need to|have to|gotta|ought to)\b.{{0,40}}{HEALTH}",
     "Dayatma kipi + saglik terimi (recete gibi)"),
    # "when you feel/experience X, do/try/take Y" — kisisel gorunup recete olan kalip
    (r"\bwhen you (feel|experience|get|have)\b.{0,40}\b(do|try|take|use|practice|repeat)\b",
     "Kosullu talimat kalibi (when you... do...)"),
    # dogrudan emir + saglik: "manage your anxiety", "cure your panic"
    (rf"\b(manage|cure|fix|treat|heal|stop)\s+(your\s+)?{HEALTH}",
     "Dogrudan tedavi/emir vaadi"),
    # teshis: "you have anxiety", "you're depressed"
    (rf"\byou(?:'re| are| have)\b.{{0,15}}{HEALTH}",
     "Izleyiciye teshis koyma"),
]

# --- WARN kurallari: dikkat gerektiren ama otomatik blok degil ---
WARN_PATTERNS = [
    (r"\b(just|simply|all you have to)\b", "Sorunu kucumseyen dil (just/simply)"),
    (rf"\b(guarantee\w*|always works|will (fix|cure|stop))\b.{{0,20}}{HEALTH}", "Asiri vaat"),
    (r"\b(everyone|nobody|always|never)\b", "Mutlak ifade (kontrol et)"),
]

# --- Kriz dili: varsa kaynak dipnotu ZORUNLU ---
CRISIS = r"(suicid\w*|kill (yourself|myself)|end it all|self.?harm|hurt (yourself|myself))"
RESOURCE_HINT = r"(helpline|hotline|988|crisis|reach out|talk to someone|professional|doctor)"


def lint(text):
    t = text.lower()
    blocks, warns = [], []

    for pat, label in BLOCK_PATTERNS:
        for m in re.finditer(pat, t, re.IGNORECASE):
            blocks.append((label, m.group(0).strip()))

    for pat, label in WARN_PATTERNS:
        for m in re.finditer(pat, t, re.IGNORECASE):
            warns.append((label, m.group(0).strip()))

    # Kriz dili varsa ve kaynak yoksa -> block
    if re.search(CRISIS, t, re.IGNORECASE) and not re.search(RESOURCE_HINT, t, re.IGNORECASE):
        blocks.append(("Kriz dili var ama kaynak/dipnot YOK", "—"))

    return blocks, warns


def main():
    if len(sys.argv) < 2:
        print("Kullanim: python3 compliance_lint.py <dosya|->")
        sys.exit(2)
    src = sys.argv[1]
    text = sys.stdin.read() if src == "-" else open(src, encoding="utf-8").read()

    blocks, warns = lint(text)

    print("=" * 50)
    if blocks:
        print("SONUC: ENGELLENDI (block)\n")
        for label, snippet in blocks:
            print(f"  [BLOCK] {label}")
            print(f"          -> \"{snippet}\"")
    else:
        print("SONUC: TEMIZ (block yok)")

    if warns:
        print("\n  Uyarilar (insan gozuyle bak, otomatik blok degil):")
        for label, snippet in warns:
            print(f"  [warn]  {label} -> \"{snippet}\"")
    print("=" * 50)

    sys.exit(1 if blocks else (2 if warns else 0))


if __name__ == "__main__":
    main()
