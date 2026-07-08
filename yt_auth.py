# -*- coding: utf-8 -*-
# TEK SEFERLIK: YouTube OAuth yetkisi alir, REFRESH TOKEN basar.
# Kullanim: python yt_auth.py CLIENT_ID CLIENT_SECRET
import sys, ssl, json, webbrowser, urllib.request, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

CTX = ssl._create_unverified_context()
CID, CSEC = sys.argv[1], sys.argv[2]
SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
REDIR = "http://localhost:8765"
kod = {}

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        kod["code"] = q.get("code", [""])[0]
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(b"<h2>Tamam. Bu pencereyi kapat, PowerShell'e don.</h2>")
    def log_message(self, *a): pass

url = ("https://accounts.google.com/o/oauth2/v2/auth?client_id=" + CID
       + "&redirect_uri=" + urllib.parse.quote(REDIR)
       + "&response_type=code&scope=" + urllib.parse.quote(SCOPE)
       + "&access_type=offline&prompt=consent")
print("Tarayici aciliyor - Daniel Vega YouTube kanalinin sahibi Google hesabiyla gir...")
webbrowser.open(url)
HTTPServer(("localhost", 8765), H).handle_request()

body = urllib.parse.urlencode({"client_id": CID, "client_secret": CSEC, "code": kod["code"],
                               "grant_type": "authorization_code", "redirect_uri": REDIR}).encode()
r = urllib.request.Request("https://oauth2.googleapis.com/token", data=body,
    headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0"}, method="POST")
tok = json.loads(urllib.request.urlopen(r, context=CTX, timeout=30).read())
print("\n================ REFRESH TOKEN ================")
print(tok.get("refresh_token", "HATA: refresh_token gelmedi - prompt=consent ile tekrar dene"))
print("===============================================")
print("Bunu GitHub secret olarak ekle: YT_REFRESH_TOKEN")
