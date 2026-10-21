#!/usr/bin/env python3
from __future__ import annotations

import html
import re
import sys
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path

PAGE = "https://www.tamindir.com/indir/new-star-soccer-apk/"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141 Safari/537.36"
REPORT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/NSS_431_SOURCE_GATE.txt")

cookies = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))

def fetch(url, referer=None):
    headers = {
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with opener.open(req, timeout=120) as r:
        return r.read(), r.geturl(), r.headers, r.status

raw, final, headers, status = fetch(PAGE)
text = raw.decode("utf-8", "replace")
dec = html.unescape(text).replace("\\/", "/")
print("PAGE", status, final, headers.get("Content-Type"), "bytes=", len(raw))

for needle in ["4.31", "Normal İndirme", "Normal &#x130;ndirme", "75.70", "75.7 MB", "app-version-display"]:
    print("\n===== CONTEXT", needle, "=====")
    start = 0
    count = 0
    while True:
        p = dec.lower().find(needle.lower(), start)
        if p < 0:
            break
        count += 1
        frag = re.sub(r"\s+", " ", dec[max(0,p-1800):p+3500])
        print(f"OCCURRENCE {count} POS {p}: {frag[:5300]}")
        start = p + len(needle)
        if count >= 8:
            break
    if count == 0:
        print("NOT_FOUND")

print("\n===== FORMS / BUTTONS / DATA ATTRIBUTES NEAR DOWNLOAD WORDS =====")
for m in re.finditer(r"<(?:a|button|form|div|li)[^>]{0,2500}>", dec, re.I):
    tag = m.group(0)
    low = tag.lower()
    if any(k in low for k in ["download", "indir", "4.31", "75.70", "data-version", "data-file"]):
        print(re.sub(r"\s+", " ", tag)[:2500])

print("\n===== CANDIDATE URLS =====")
urls=[]
for pat in [
    r'''(?:href|src|action|data-url|data-href|data-download|data-link|data-file|data-api)\s*=\s*["']([^"']+)["']''',
    r'''https?://[^"'<>\s]+''',
]:
    for m in re.finditer(pat, dec, re.I):
        v = m.group(1) if m.lastindex else m.group(0)
        u = urllib.parse.urljoin(final, v.strip())
        if re.search(r"indir|download|apk|api|new-star|tamindir", u, re.I) and u not in urls:
            urls.append(u)
            print(u)

print("\n===== INLINE API/FETCH/AJAX SNIPPETS =====")
for key in ["fetch(", "axios", "ajax", "/api/", "download", "indir/", "fileUrl", "downloadUrl"]:
    for m in list(re.finditer(re.escape(key), dec, re.I))[:20]:
        frag = re.sub(r"\s+", " ", dec[max(0,m.start()-700):m.start()+1800])
        print(key, frag[:2500])

# Fetch same-origin JavaScript files and look for the client-side download endpoint.
print("\n===== TAMINDIR JS DOWNLOAD LOGIC =====")
js_urls=[]
for m in re.finditer(r'''<script[^>]+src=["']([^"']+)["']''', dec, re.I):
    u=urllib.parse.urljoin(final,m.group(1))
    if urllib.parse.urlparse(u).netloc.endswith("tamindir.com") and u not in js_urls:
        js_urls.append(u)
print("JS_COUNT", len(js_urls))
for u in js_urls[:40]:
    try:
        data,f2,h2,s2=fetch(u, final)
    except Exception as e:
        print("JS_ERROR",u,repr(e)); continue
    s=data.decode("utf-8","replace")
    hits=[k for k in ["download", "indir", "/api/", "fetch(", "ajax", "fileUrl", "downloadUrl"] if re.search(re.escape(k),s,re.I)]
    if not hits:
        continue
    print("JS",u,"bytes=",len(data),"hits=",hits)
    emitted=0
    for m in re.finditer(r"download|indir|/api/|fileUrl|downloadUrl",s,re.I):
        frag=re.sub(r"\s+"," ",s[max(0,m.start()-900):m.start()+2200])
        print("JS_CONTEXT",frag[:3100])
        emitted+=1
        if emitted>=8: break

REPORT.write_text(
    "SOURCE_GATE=DIAGNOSTIC\n"
    f"page_status={status}\n"
    "target_version=4.31\n"
    "next=resolve_tamindir_download_endpoint\n",
    encoding="utf-8",
)
print(REPORT.read_text(encoding="utf-8"), end="")
raise SystemExit(3)
