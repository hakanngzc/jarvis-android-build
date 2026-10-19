#!/usr/bin/env python3
import html
import re
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36"
BASE = "https://new-star-soccer.en.uptodown.com/android"
PAGE = f"{BASE}/download/1129097900"
JS = "https://stc.utdstc.com/1792141145773/download.js"

def fetch(url, referer=None):
    headers={"User-Agent":UA}
    if referer: headers["Referer"] = referer
    req=urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read(), r.geturl(), r.headers

for label,url,ref in [("page",PAGE,BASE),("js",JS,PAGE)]:
    print(f"===== {label} =====")
    try:
        raw,final,headers=fetch(url,ref)
    except Exception as e:
        print("fetch_error=",repr(e)); continue
    print("final_url=",final)
    print("bytes=",len(raw))
    print("content_type=",headers.get("Content-Type"))
    text=raw.decode("utf-8","replace")
    if label=="page":
        pats=["turnstile","download","1129097900","version-id","versionId","data-url","data-version","package","captcha"]
        for pat in pats:
            print(f"-- context {pat} --")
            for m in list(re.finditer(re.escape(pat),text,re.I))[:12]:
                print(html.unescape(text[max(0,m.start()-350):m.end()+700]).replace("\n"," "))
    else:
        print("-- JS endpoint/string candidates --")
        strings=re.findall(r'''["']([^"']{3,500})["']''',text)
        for s in strings:
            if re.search(r"api|download|turnstile|captcha|version|file|ajax|fetch|xhr|token",s,re.I):
                print(html.unescape(s))
        print("-- fetch/xhr/ajax contexts --")
        for pat in ["fetch(","XMLHttpRequest","axios","$.ajax","turnstile","download"]:
            for m in list(re.finditer(re.escape(pat),text,re.I))[:25]:
                print(text[max(0,m.start()-300):m.end()+700].replace("\n"," "))
