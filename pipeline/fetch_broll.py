import os, sys, json, ssl, urllib.request, urllib.parse
CTX = ssl._create_unverified_context()
KEY = os.environ.get("PEXELS_API_KEY","")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "broll")
os.makedirs(OUT, exist_ok=True)
QUERIES = {
  "anxious": ["rain window","dark clouds"],
  "hopeful": ["sunrise nature","open notebook writing"],
  "calm": ["still lake","quiet forest"],
  "neutral": ["desk workspace","plant home"],
  "transition": ["light leak","soft bokeh"],
}
def search(term):
    url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode(
        {"query": term, "orientation": "portrait", "size": "medium", "per_page": 2})
    req = urllib.request.Request(url, headers={"Authorization": KEY, "User-Agent": UA})
    return json.load(urllib.request.urlopen(req, context=CTX)).get("videos", [])
def pick(v):
    fs = [f for f in v["video_files"] if f.get("file_type")=="video/mp4" and f.get("height",0)>=f.get("width",0)]
    fs.sort(key=lambda f: abs((f.get("height") or 0)-1280))
    return fs[0]["link"] if fs else None
n=0
for tag,terms in QUERIES.items():
    for term in terms:
        try: vids=search(term)
        except Exception as e: print("  ! arama:",term,e); continue
        for v in vids:
            link=pick(v)
            if not link: continue
            dst=os.path.join(OUT,f"{tag}__{term.replace(' ','_')}_{v['id']}.mp4")
            if os.path.exists(dst): continue
            try:
                rq=urllib.request.Request(link, headers={"User-Agent": UA})
                with urllib.request.urlopen(rq,context=CTX) as r, open(dst,"wb") as o: o.write(r.read())
                n+=1; print("  +",os.path.basename(dst))
            except Exception as e: print("  ! indirme:",e)
print(f"\nToplam {n} klip -> {OUT}")

