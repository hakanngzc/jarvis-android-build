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


def fetch(url: str, referer: str | None = None):
    headers = {
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with opener.open(req, timeout=180) as r:
        return r.read(), r.geturl(), r.headers, r.status


page, page_final, _, page_status = fetch(PAGE)
page_text = html.unescape(page.decode("utf-8", "replace")).replace("\\/", "/")
print("MAIN_PAGE", page_status, page_final, "bytes=", len(page))

m = re.search(
    r"downloadAds\s*\(\s*event\s*,\s*['\"]([^'\"]*[?&]v=98774(?:&[^'\"]*)?)['\"]",
    page_text,
    re.I,
)
if not m:
    print("ERROR no v=98774 token endpoint")
    raise SystemExit(3)
endpoint = urllib.parse.urljoin(page_final, m.group(1))
print("TOKEN_ENDPOINT", endpoint)

raw, final, headers, status = fetch(endpoint, page_final)
ctype = headers.get("Content-Type") or ""
print("INTERMEDIATE", status, final, "ctype=", ctype, "bytes=", len(raw))
s = html.unescape(raw.decode("utf-8", "replace")).replace("\\/", "/")

print("\n===== TITLE / META REFRESH =====")
for pat in [
    r"<title[^>]*>(.*?)</title>",
    r"<meta[^>]+http-equiv=[\"']?refresh[\"']?[^>]*>",
    r"<meta[^>]+content=[\"'][^\"']*url=[^\"']+[\"'][^>]*>",
]:
    for x in re.finditer(pat, s, re.I | re.S):
        print(re.sub(r"\s+", " ", x.group(0))[:3000])

print("\n===== RELEVANT ANCHORS / FORMS / BUTTONS =====")
for tag_pat in [r"<a\b[^>]*>.*?</a>", r"<form\b[^>]*>.*?</form>", r"<button\b[^>]*>.*?</button>"]:
    for x in re.finditer(tag_pat, s, re.I | re.S):
        tag = re.sub(r"\s+", " ", x.group(0))
        if re.search(r"apk|xapk|depo|cdn|download|indir|devam|bekle|98774|token|dosya|file", tag, re.I):
            print(tag[:5000])

print("\n===== RELEVANT INLINE SCRIPTS =====")
for x in re.finditer(r"<script\b([^>]*)>(.*?)</script>", s, re.I | re.S):
    attrs, body = x.group(1), x.group(2)
    block = re.sub(r"\s+", " ", body)
    if re.search(r"apk|xapk|depo|cdn|download|indir|location|setTimeout|98774|token|href|window\.open|file", block, re.I):
        print("SCRIPT_ATTRS", re.sub(r"\s+", " ", attrs)[:1000])
        print("SCRIPT_BODY", block[:12000])

print("\n===== SCRIPT SRC =====")
for x in re.finditer(r"<script\b[^>]*src=[\"']([^\"']+)[\"'][^>]*>", s, re.I):
    print(urllib.parse.urljoin(final, x.group(1)))

print("\n===== TARGETED CONTEXTS =====")
needles = [
    ".apk", ".xapk", "depo.", "cdn", "download", "indir", "window.location",
    "location.href", "location=", "setTimeout", "98774", "token", "dosya", "fileUrl",
    "downloadUrl", "continue", "devam", "seconds", "countdown",
]
for needle in needles:
    matches = list(re.finditer(re.escape(needle), s, re.I))
    if not matches:
        continue
    print(f"--- {needle} ({len(matches)}) ---")
    for x in matches[:12]:
        frag = re.sub(r"\s+", " ", s[max(0, x.start()-1200):x.start()+3200])
        print(frag[:4400])

print("\n===== EXTRACTED URL-LIKE VALUES (FILTERED) =====")
vals = []
patterns = [
    r'''(?:href|src|action|data-url|data-href|data-download|data-file)\s*=\s*["']([^"']+)["']''',
    r'''(?:window\.)?location(?:\.href)?\s*=\s*["']([^"']+)["']''',
    r'''["'](https?://[^"'<>\s]+)["']''',
    r'''["']([^"']+\.(?:apk|xapk|zip)(?:\?[^"']*)?)["']''',
]
for pat in patterns:
    for x in re.finditer(pat, s, re.I):
        value = x.group(1).strip()
        u = urllib.parse.urljoin(final, value)
        if re.search(r"apk|xapk|depo|cdn|download|indir|98774|token|file", u, re.I) and u not in vals:
            vals.append(u)
for u in vals[:80]:
    print(u)

REPORT.write_text(
    "SOURCE_GATE=DIAGNOSTIC\n"
    f"main_page_status={page_status}\n"
    f"intermediate_status={status}\n"
    f"intermediate_bytes={len(raw)}\n"
    "target_version=4.31\n"
    "version_record=98774\n"
    "next=resolve_final_binary_from_intermediate\n",
    encoding="utf-8",
)
print("\n" + REPORT.read_text(encoding="utf-8"), end="")
raise SystemExit(3)
