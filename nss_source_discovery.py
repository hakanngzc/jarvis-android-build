#!/usr/bin/env python3
import hashlib
import html
import re
import urllib.request

EXPECTED = "0d7a2ae9b0b6e77155a77c0770be022771782bd0"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36"
BASE = "https://new-star-soccer.en.uptodown.com/android"
VERSION_ID = "1129097900"
CANDIDATES = [
    f"{BASE}/download/{VERSION_ID}",
    f"{BASE}/download/{VERSION_ID}-x",
    f"{BASE}/download/{VERSION_ID}-p",
    f"{BASE}/download?version={VERSION_ID}",
]

for i, url in enumerate(CANDIDATES, 1):
    print(f"===== candidate {i} =====")
    print("url=", url)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE})
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read()
            ctype = r.headers.get("Content-Type", "")
            print("status=", r.status)
            print("final_url=", r.geturl())
            print("content_type=", ctype)
    except Exception as e:
        print("fetch_error=", repr(e))
        continue
    print("bytes=", len(raw))
    print("sha256=", hashlib.sha256(raw).hexdigest())
    git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    print("git_blob_sha1=", git_blob)
    print("exact_private_base_match=", git_blob == EXPECTED)
    print("head=", raw[:16].hex())
    if raw[:2] != b"PK":
        text = raw.decode("utf-8", "replace")
        print("-- html candidate urls --")
        found = []
        for m in re.finditer(r'''(?:href|src|data-url|data-href)\s*=\s*["']([^"']+)["']''', text, re.I):
            v = html.unescape(m.group(1))
            if re.search(r"download|xapk|apk|1129097900", v, re.I):
                found.append(v)
        for m in re.finditer(r'''https?://[^"'<>\s]+''', text):
            v = html.unescape(m.group(0))
            if re.search(r"download|xapk|apk|1129097900", v, re.I):
                found.append(v)
        for v in dict.fromkeys(found):
            print(v)
