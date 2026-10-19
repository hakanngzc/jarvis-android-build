#!/usr/bin/env python3
import html
import re
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36"
PAGE = "https://www.tamindir.com/indir/new-star-soccer-apk/"

def fetch(url, referer=None):
    headers={"User-Agent":UA,"Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8"}
    if referer: headers["Referer"] = referer
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=90) as r:
        return r.read(),r.geturl(),r.headers

raw,final,headers=fetch(PAGE)
text=raw.decode("utf-8","replace")
print("page_status=OK")
print("final_url=",final)
print("bytes=",len(raw))

for pat in ["75.70", "75.7", "Normal İndirme", "Normal Indirme", "4.31", "download", "indir"]:
    print(f"===== CONTEXT {pat} =====")
    matches=list(re.finditer(re.escape(pat),text,re.I))
    print("matches=",len(matches))
    for m in matches[:20]:
        print(html.unescape(text[max(0,m.start()-900):m.end()+1800]).replace("\n"," "))

print("===== SCRIPTS =====")
scripts=[]
for m in re.finditer(r'''<script[^>]+src=["']([^"']+)["']''',text,re.I):
    u=html.unescape(m.group(1))
    u=urllib.parse.urljoin(PAGE,u)
    scripts.append(u)
    print(u)

keywords=re.compile(r"download|indir|apk|variant|version|file|endpoint|api",re.I)
for idx,u in enumerate(dict.fromkeys(scripts),1):
    if not ("tamindir" in u or "static" in u):
        continue
    try:
        b,fu,h=fetch(u,PAGE)
    except Exception as e:
        print("SCRIPT_FETCH_ERROR",u,repr(e)); continue
    if len(b)>3_000_000:
        print("SCRIPT_SKIP_LARGE",u,len(b)); continue
    s=b.decode("utf-8","replace")
    hits=list(keywords.finditer(s))
    if not hits: continue
    print(f"===== SCRIPT {idx} {u} bytes={len(b)} hits={len(hits)} =====")
    for m in hits[:80]:
        frag=s[max(0,m.start()-300):m.end()+700]
        if re.search(r"download|indir|apk|variant|version|file|endpoint|api",frag,re.I):
            print(frag.replace("\n"," "))
