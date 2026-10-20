#!/usr/bin/env python3
import hashlib
import io
import re
import urllib.parse
import urllib.request
import zipfile

PAGE = "https://apkcombo.com/nss/com.newstargames.newstarsoccer/old-versions/"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36"
EXPECTED_BASE_SHA256 = "46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4"


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
    direct = hashlib.sha256(data).hexdigest() == EXPECTED_BASE_SHA256
    if direct:
        print("DIRECT_EXPECTED_BASE_APK_FOUND=TRUE")
    return direct


raw, final, headers, status = fetch(PAGE)
print("page_status=", status)
print("page_final_url=", final)
print("page_content_type=", headers.get("Content-Type"))
print("page_bytes=", len(raw))
text = raw.decode("utf-8", "replace")

# Keep only URLs/paths near the exact 4.31 entry or explicit download endpoints.
urls = []
for m in re.finditer(r"4\.31", text, re.I):
    frag = text[max(0, m.start()-5000):m.end()+8000]
    for pat in [
        r'''(?:href|data-url|data-download|data-link)\s*=\s*["']([^"']+)["']''',
        r'''https?://[^"'<>\s]+''',
    ]:
        for u in re.finditer(pat, frag, re.I):
            value = u.group(1) if u.lastindex else u.group(0)
            value = value.replace("&amp;", "&").replace("\\/", "/")
            url = urllib.parse.urljoin(final, value)
            if re.search(r"download|apkcombo|xapk|apk", url, re.I) and url not in urls:
                urls.append(url)

# Also inspect explicit download-ish links on page in case version text and link are separated.
for pat in [
    r'''(?:href|data-url|data-download|data-link)\s*=\s*["']([^"']+)["']''',
    r'''https?://[^"'<>\s]+''',
]:
    for u in re.finditer(pat, text, re.I):
        value = u.group(1) if u.lastindex else u.group(0)
        value = value.replace("&amp;", "&").replace("\\/", "/")
        url = urllib.parse.urljoin(final, value)
        if re.search(r"4\.31|download|xapk", url, re.I) and url not in urls:
            urls.append(url)

print("candidate_count=", len(urls))
for i, url in enumerate(urls[:80], 1):
    print("CANDIDATE", i, url)

for i, url in enumerate(urls[:40], 1):
    try:
        data, f2, h2, s2 = fetch(url, final)
    except Exception as e:
        print("TRY", i, "ERROR", repr(e), url)
        continue
    print("TRY", i, "status=", s2, "final=", f2,
          "ctype=", h2.get("Content-Type"),
          "disp=", h2.get("Content-Disposition"),
          "bytes=", len(data))
    if inspect_zip(data, f"candidate_{i}"):
        print("SOURCE_GATE=PASS")
        raise SystemExit(0)

print("SOURCE_GATE=FAIL")
raise SystemExit(3)
