#!/usr/bin/env python3
import hashlib
import io
import re
import urllib.parse
import urllib.request
import zipfile

PAGE = "https://new-star-soccer.apkcafe.ae/"
DOWNLOAD = "https://apkcafe.ae/download?file_id=3343128%2Fnew-star-soccer"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36"
EXPECTED_BASE_SHA256 = "46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4"
EXPECTED_PACKAGE = "com.newstargames.newstarsoccer"


def fetch(url, referer=None):
    headers = {
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=240) as r:
        return r.read(), r.geturl(), r.headers, r.status


def inspect_zip(data, label):
    print(f"{label}_bytes=", len(data))
    print(f"{label}_sha256=", hashlib.sha256(data).hexdigest())
    if data[:2] != b"PK":
        print(f"{label}_zip_like=FALSE")
        return False
    print(f"{label}_zip_like=TRUE")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = z.namelist()
            print(f"{label}_entries=", len(names))
            for n in names[:80]:
                print("ENTRY", n)
            apk_names = [n for n in names if n.lower().endswith(".apk")]
            for n in apk_names:
                payload = z.read(n)
                sha = hashlib.sha256(payload).hexdigest()
                print("APK", n, "bytes=", len(payload), "sha256=", sha,
                      "expected_base_match=", sha == EXPECTED_BASE_SHA256)
                if sha == EXPECTED_BASE_SHA256:
                    print("EXACT_EXPECTED_BASE_APK_FOUND=TRUE")
                    return True
    except zipfile.BadZipFile:
        print(f"{label}_bad_zip=TRUE")
    return hashlib.sha256(data).hexdigest() == EXPECTED_BASE_SHA256


raw, final, headers, status = fetch(DOWNLOAD, PAGE)
print("first_status=", status)
print("first_final_url=", final)
print("first_content_type=", headers.get("Content-Type"))
print("first_content_disposition=", headers.get("Content-Disposition"))
print("first_bytes=", len(raw))

if inspect_zip(raw, "first"):
    raise SystemExit(0)

text = raw.decode("utf-8", "replace")
urls = []
for pat in [
    r'''href\s*=\s*["']([^"']+)["']''',
    r'''src\s*=\s*["']([^"']+)["']''',
    r'''https?://[^"'<>\s]+''',
]:
    for m in re.finditer(pat, text, re.I):
        value = m.group(1) if m.lastindex else m.group(0)
        value = value.replace("&amp;", "&")
        url = urllib.parse.urljoin(final, value)
        if re.search(r"download|\.apk|\.apks|\.xapk|file|cdn", url, re.I):
            if url not in urls and url != final:
                urls.append(url)

print("candidate_count=", len(urls))
for url in urls[:40]:
    print("CANDIDATE", url)

for i, url in enumerate(urls[:20], 1):
    try:
        data, f2, h2, s2 = fetch(url, final)
    except Exception as e:
        print("TRY", i, "ERROR", repr(e), url)
        continue
    print("TRY", i, "status=", s2, "final=", f2,
          "ctype=", h2.get("Content-Type"), "bytes=", len(data))
    if len(data) > 50_000_000 and inspect_zip(data, f"candidate_{i}"):
        print("SOURCE_GATE=PASS")
        raise SystemExit(0)

print("SOURCE_GATE=FAIL")
raise SystemExit(3)
