#!/usr/bin/env python3
from __future__ import annotations

import html
import re
import sys
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path

PAGE = "https://apkfab.com/new-star-soccer/com.newstargames.newstarsoccer"
TARGET_SHA1 = "abae9aad65e5e2ff55380bfaece7d406feb3d3f3"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141 Safari/537.36"
REPORT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/NSS_431_SOURCE_GATE.txt")

cookies = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))


def fetch(url: str, referer: str | None = None):
    headers = {
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with opener.open(req, timeout=180) as r:
        return r.read(), r.geturl(), r.headers, r.status


raw, final, headers, status = fetch(PAGE)
s = html.unescape(raw.decode("utf-8", "replace")).replace("\\/", "/")
print("APKFAB_PAGE", status, final, headers.get("Content-Type"), "bytes=", len(raw))

pos = s.lower().find(TARGET_SHA1)
print("TARGET_SHA1_POS", pos)
if pos >= 0:
    print("===== TARGET RECORD CONTEXT =====")
    print(re.sub(r"\s+", " ", s[max(0,pos-9000):pos+14000])[:23000])

print("\n===== 4.31 / TARGET DOWNLOAD TAGS =====")
for pat in [r"<a\b[^>]*>.*?</a>", r"<form\b[^>]*>.*?</form>", r"<button\b[^>]*>.*?</button>"]:
    for m in re.finditer(pat, s, re.I | re.S):
        tag = re.sub(r"\s+", " ", m.group(0))
        if TARGET_SHA1 in tag.lower() or re.search(r"4\.31|72\.16|download.*xapk|xapk.*download", tag, re.I):
            print(tag[:10000])

print("\n===== TARGETED URLS =====")
vals=[]
patterns=[
    r'''(?:href|action|data-url|data-href|data-download|data-file|data-apk|data-link)\s*=\s*["']([^"']+)["']''',
    r'''["'](https?://[^"'<>\s]+)["']''',
]
for pat in patterns:
    for m in re.finditer(pat,s,re.I):
        v=m.group(1).strip()
        u=urllib.parse.urljoin(final,v)
        low=u.lower()
        nearby=s[max(0,m.start()-800):m.end()+800].lower()
        if TARGET_SHA1 in low or TARGET_SHA1 in nearby or "4.31" in nearby or (
            re.search(r"download|xapk|apkcombo|apkfab|file",low) and "new-star" in low
        ):
            if u.startswith("http") and u not in vals:
                vals.append(u)
for u in vals[:100]: print(u)

print("\n===== INLINE SCRIPT CONTEXTS =====")
for m in re.finditer(r"<script\b([^>]*)>(.*?)</script>",s,re.I|re.S):
    body=m.group(2)
    if TARGET_SHA1 in body.lower() or re.search(r"4\.31|downloadUrl|download_url|xapk|versionCode|version_code",body,re.I):
        print("SCRIPT",re.sub(r"\s+"," ",body)[:16000])

print("\n===== KEY CONTEXTS =====")
for needle in [TARGET_SHA1,"4.31","72.16 MB","download","xapk","versionCode","version_code","package_version","file_url","download_url"]:
    mm=list(re.finditer(re.escape(needle),s,re.I))
    if not mm: continue
    print(f"--- {needle} ({len(mm)}) ---")
    for x in mm[:15]:
        print(re.sub(r"\s+"," ",s[max(0,x.start()-1600):x.start()+4200])[:5800])

REPORT.write_text(
    "SOURCE_GATE=DIAGNOSTIC\n"
    "source=apkfab\n"
    f"page_status={status}\n"
    f"target_sha1_found={str(pos >= 0).lower()}\n"
    "target_version=4.31\n"
    "next=resolve_apkfab_final_binary\n",
    encoding="utf-8",
)
print("\n"+REPORT.read_text(encoding="utf-8"),end="")
raise SystemExit(3)
