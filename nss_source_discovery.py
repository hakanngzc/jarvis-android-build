#!/usr/bin/env python3
import html
import re
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36"
PAGES = [
    "https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31",
    "https://apkpure.net/tr/new-star-soccer/com.newstargames.newstarsoccer/download/4.31",
]

def get(url, referer=None):
    h={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Language":"en-US,en;q=0.9"}
    if referer: h["Referer"]=referer
    req=urllib.request.Request(url,headers=h)
    with urllib.request.urlopen(req,timeout=120) as r:
        return r.read(),r.geturl(),r.headers,r.status

for page in PAGES:
    print("===== PAGE",page,"=====")
    try:
        raw,final,headers,status=get(page)
    except Exception as e:
        print("ERROR",repr(e)); continue
    print("status=",status,"final=",final,"bytes=",len(raw),"ctype=",headers.get("Content-Type"))
    text=raw.decode("utf-8","replace")
    for pat in ["4.31","72.2","download.apkpure","d.apkpure","XAPK","SHA-256","SHA256","version"]:
        ms=list(re.finditer(re.escape(pat),text,re.I))
        print("PAT",pat,"COUNT",len(ms))
        for m in ms[:8]:
            print(html.unescape(text[max(0,m.start()-500):m.end()+1000]).replace("\n"," "))
    print("-- URLS --")
    vals=[]
    for m in re.finditer(r'''(?:href|src|data-url|data-dt-url|data-download-url)\s*=\s*["']([^"']+)["']''',text,re.I):
        vals.append(html.unescape(m.group(1)))
    for m in re.finditer(r'''https?:\\?/\\?/[^"'<>\s]+''',text):
        vals.append(html.unescape(m.group(0)).replace('\\/','/'))
    seen=set()
    for v in vals:
        v=urllib.parse.urljoin(final,v)
        if v in seen: continue
        seen.add(v)
        if re.search(r"download|xapk|apk|new-star|newstargames|4\.31",v,re.I):
            print(v)
