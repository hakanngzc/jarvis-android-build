#!/usr/bin/env python3
import html
import re
import urllib.request

SOURCES = {
    "tamindir": "https://www.tamindir.com/indir/new-star-soccer-apk/",
    "uptodown": "https://new-star-soccer.en.uptodown.com/android",
    "apkcombo": "https://apkcombo.com/nss/com.newstargames.newstarsoccer/",
}

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36"

for name, url in SOURCES.items():
    print(f"===== {name} =====")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = r.read()
            print("status=", r.status)
            print("final_url=", r.geturl())
    except Exception as e:
        print("fetch_error=", repr(e))
        continue
    print("bytes=", len(raw))
    text = raw.decode("utf-8", "replace")
    low = text.lower()
    pos = low.find("4.31")
    if pos >= 0:
        print("-- 4.31 context --")
        print(html.unescape(text[max(0, pos-700):pos+1600]).replace("\n", " "))
    print("-- candidate URLs --")
    found = []
    for m in re.finditer(r'''(?:href|src|data-url|data-href)\s*=\s*["']([^"']+)["']''', text, re.I):
        v = html.unescape(m.group(1))
        if re.search(r"download|indir|apk|xapk|new-star|newstargames", v, re.I):
            found.append(v)
    for m in re.finditer(r'''https?://[^"'<>\s]+''', text):
        v = html.unescape(m.group(0))
        if re.search(r"download|indir|apk|xapk|new-star|newstargames", v, re.I):
            found.append(v)
    seen = set()
    for v in found:
        if v in seen:
            continue
        seen.add(v)
        print(v)
        if len(seen) >= 120:
            break
