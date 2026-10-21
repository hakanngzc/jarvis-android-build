#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import io
import re
import sys
import urllib.parse
import urllib.request
import http.cookiejar
import zipfile
from pathlib import Path

PAGE = "https://www.tamindir.com/indir/new-star-soccer-apk/"
EXPECTED_BASE_SHA256 = "46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141 Safari/537.36"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/nss-4.31.xapk")
REPORT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/NSS_431_SOURCE_GATE.txt")

cookies = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))


def fetch(url: str, referer: str | None = None) -> tuple[bytes, str, object, int]:
    headers = {
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with opener.open(req, timeout=300) as r:
        return r.read(), r.geturl(), r.headers, r.status


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate(data: bytes, final_url: str) -> tuple[bool, str]:
    whole = digest(data)
    print("PAYLOAD", final_url, "bytes=", len(data), "sha256=", whole)
    if whole == EXPECTED_BASE_SHA256:
        OUT.write_bytes(data)
        return True, f"mode=direct-apk\nurl={final_url}\nbase_sha256={whole}\n"
    if data[:2] != b"PK":
        return False, "not_zip_or_expected_apk"
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = z.namelist()
            apk_names = [n for n in names if n.lower().endswith(".apk")]
            print("ZIP entries=", len(names), "apk_entries=", len(apk_names))
            for name in apk_names:
                apk = z.read(name)
                h = digest(apk)
                print("APK", name, "bytes=", len(apk), "sha256=", h,
                      "expected=", h == EXPECTED_BASE_SHA256)
                if h == EXPECTED_BASE_SHA256:
                    OUT.write_bytes(data)
                    return True, (
                        "mode=xapk\n"
                        f"url={final_url}\n"
                        f"entry={name}\n"
                        f"xapk_sha256={whole}\n"
                        f"base_sha256={h}\n"
                    )
    except zipfile.BadZipFile:
        return False, "bad_zip"
    return False, "expected_base_hash_not_found"


page, page_final, page_headers, page_status = fetch(PAGE)
text = html.unescape(page.decode("utf-8", "replace")).replace("\\/", "/")
print("PAGE", page_status, page_final, "bytes=", len(page))

# Tamindir exposes the exact 4.31 alternate download as a fresh tokenized path.
# v=98774 is the 4.31 record shown beside the 75.70 MB Normal Download entry.
paths = []
for m in re.finditer(r"downloadAds\s*\(\s*event\s*,\s*['\"]([^'\"]+)['\"]", text, re.I):
    p = m.group(1)
    if re.search(r"(?:[?&])v=98774(?:&|$)", p):
        paths.append(p)
if not paths:
    REPORT.write_text(
        "SOURCE_GATE=FAIL\nreason=tamindir_431_token_path_not_found\n",
        encoding="utf-8",
    )
    print(REPORT.read_text(encoding="utf-8"), end="")
    raise SystemExit(3)

endpoint = urllib.parse.urljoin(page_final, paths[0])
print("TAMINDIR_431_ENDPOINT", endpoint)

# The token endpoint may return the binary directly, redirect to a CDN, or render
# one short intermediate page. Follow at most a few same-session hops.
queue = [endpoint]
seen = set()
last_reason = "no_payload"
for attempt in range(1, 8):
    if not queue:
        break
    url = queue.pop(0)
    if url in seen:
        continue
    seen.add(url)
    print("TRY", attempt, url)
    try:
        data, final, headers, status = fetch(url, page_final)
    except Exception as exc:
        print("ERROR", repr(exc))
        last_reason = f"fetch_error:{type(exc).__name__}"
        continue
    ctype = (headers.get("Content-Type") or "").lower()
    disp = headers.get("Content-Disposition") or ""
    print("HTTP", status, "final=", final, "ctype=", ctype, "disp=", disp,
          "bytes=", len(data))

    ok, detail = validate(data, final)
    if ok:
        REPORT.write_text(
            "SOURCE_GATE=PASS\n"
            "source=tamindir\n"
            "version=4.31\n"
            "version_record=98774\n" + detail,
            encoding="utf-8",
        )
        print(REPORT.read_text(encoding="utf-8"), end="")
        raise SystemExit(0)
    last_reason = detail

    # Intermediate HTML: collect redirect/meta/anchor/JS-location URLs, preferring
    # Tamindir/CDN/file-looking targets. Cookies and Referer are preserved.
    if len(data) <= 5_000_000 and ("html" in ctype or "text" in ctype or not ctype):
        s = html.unescape(data.decode("utf-8", "replace")).replace("\\/", "/")
        candidates: list[str] = []
        pats = [
            r'''(?:href|src|data-url|data-href|data-download|data-file)\s*=\s*["']([^"']+)["']''',
            r'''(?:window\.)?location(?:\.href)?\s*=\s*["']([^"']+)["']''',
            r'''content\s*=\s*["'][^"']*url=([^"';]+)''',
            r'''["'](https?://[^"'<>\s]+)["']''',
        ]
        for pat in pats:
            for m in re.finditer(pat, s, re.I):
                raw = m.group(1).strip()
                u = urllib.parse.urljoin(final, raw)
                low = u.lower()
                host = urllib.parse.urlparse(u).netloc.lower()
                if not u.startswith("http"):
                    continue
                if (
                    "tamindir" in host
                    or "depo." in host
                    or low.endswith((".apk", ".xapk", ".zip"))
                    or "download" in low
                    or "/indir/" in low
                ):
                    if u not in seen and u not in candidates:
                        candidates.append(u)
        print("INTERMEDIATE_CANDIDATES", len(candidates))
        for u in candidates[:12]:
            print("CANDIDATE", u)
            queue.append(u)

REPORT.write_text(
    "SOURCE_GATE=FAIL\n"
    "source=tamindir\n"
    "version=4.31\n"
    f"reason={last_reason}\n"
    f"expected_base_sha256={EXPECTED_BASE_SHA256}\n",
    encoding="utf-8",
)
print(REPORT.read_text(encoding="utf-8"), end="")
raise SystemExit(3)
