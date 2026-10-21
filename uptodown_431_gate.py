#!/usr/bin/env python3
from __future__ import annotations

import html
import re
import sys
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path

PAGE = "https://apkcombo.com/nss/com.newstargames.newstarsoccer/"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141 Safari/537.36"
REPORT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/NSS_431_SOURCE_GATE.txt")

cookies = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))


def fetch(url: str, referer: str | None = None):
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with opener.open(req, timeout=180) as r:
        return r.read(), r.geturl(), r.headers, r.status

try:
    raw, final, headers, status = fetch(PAGE)
except Exception as exc:
    print("FETCH_ERROR", repr(exc))
    REPORT.write_text(f"SOURCE_GATE=FAIL\nsource=apkcombo\nreason={type(exc).__name__}:{exc}\n", encoding="utf-8")
    print(REPORT.read_text(encoding="utf-8"), end="")
    raise SystemExit(3)

print("APKCOMBO_PAGE", status, final, headers.get("Content-Type"), "bytes=", len(raw))
s = html.unescape(raw.decode("utf-8", "replace")).replace("\\/", "/")

print("===== 4.31 CONTEXT =====")
for needle in ["4.31", "137", "Nov 24, 2025", "72", "76 MB", "Old Versions"]:
    mm=list(re.finditer(re.escape(needle),s,re.I))
    if not mm: continue
    print(f"--- {needle} ({len(mm)}) ---")
    for m in mm[:12]:
        print(re.sub(r"\s+"," ",s[max(0,m.start()-2200):m.start()+5600])[:7800])

print("\n===== DOWNLOAD / VERSION TAGS =====")
for pat in [r"<a\b[^>]*>.*?</a>", r"<form\b[^>]*>.*?</form>", r"<button\b[^>]*>.*?</button>"]:
    for m in re.finditer(pat,s,re.I|re.S):
        tag=re.sub(r"\s+"," ",m.group(0))
        if re.search(r"4\.31|download|old.version|xapk|137",tag,re.I):
            print(tag[:12000])

print("\n===== CANDIDATE URLS =====")
urls=[]
patterns=[
    r'''(?:href|action|data-url|data-href|data-download|data-file|data-link|data-version|data-id)\s*=\s*["']([^"']+)["']''',
    r'''["'](https?://[^"'<>\s]+)["']''',
]
for pat in patterns:
    for m in re.finditer(pat,s,re.I):
        v=m.group(1).strip(); u=urllib.parse.urljoin(final,v)
        low=u.lower(); nearby=s[max(0,m.start()-1200):m.end()+1200].lower()
        if re.search(r"download|old-versions|xapk|apk|downloader",low) or "4.31" in nearby or "137" in nearby:
            if u.startswith("http") and u not in urls:
                urls.append(u)
for u in urls[:150]: print(u)

print("\n===== RELEVANT SCRIPTS =====")
for m in re.finditer(r"<script\b([^>]*)>(.*?)</script>",s,re.I|re.S):
    body=m.group(2)
    if re.search(r"4\.31|137|download|downloader|xapk|version_code|versionCode|package",body,re.I):
        print("SCRIPT_ATTRS",re.sub(r"\s+"," ",m.group(1))[:1000])
        print("SCRIPT_BODY",re.sub(r"\s+"," ",body)[:22000])

print("\n===== SCRIPT SRC =====")
for m in re.finditer(r'''<script\b[^>]*src=["']([^"']+)["'][^>]*>''',s,re.I):
    u=urllib.parse.urljoin(final,m.group(1))
    print(u)

REPORT.write_text(
    "SOURCE_GATE=DIAGNOSTIC\n"
    "source=apkcombo\n"
    f"page_status={status}\n"
    f"page_bytes={len(raw)}\n"
    "target_version=4.31\n"
    "target_version_code=137\n"
    "next=resolve_apkcombo_binary_url\n",
    encoding="utf-8",
)
print("\n"+REPORT.read_text(encoding="utf-8"),end="")
raise SystemExit(3)
