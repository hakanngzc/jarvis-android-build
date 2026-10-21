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
from collections import deque
from pathlib import Path

VERSION_ID = "1129097900"
BASE = "https://new-star-soccer.en.uptodown.com/android"
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
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with opener.open(req, timeout=240) as r:
        return r.read(), r.geturl(), r.headers, r.status


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect_payload(data: bytes, final_url: str) -> bool:
    direct = sha(data)
    print("PAYLOAD", final_url, "bytes=", len(data), "sha256=", direct)
    if direct == EXPECTED_BASE_SHA256:
        OUT.write_bytes(data)
        REPORT.write_text(
            f"SOURCE_GATE=PASS\nmode=direct-apk\nurl={final_url}\nbase_sha256={direct}\n",
            encoding="utf-8",
        )
        return True
    if data[:2] != b"PK":
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            apk_names = [n for n in z.namelist() if n.lower().endswith(".apk")]
            print("ZIP entries=", len(z.namelist()), "apks=", len(apk_names))
            for name in apk_names:
                payload = z.read(name)
                digest = sha(payload)
                print("APK", name, "bytes=", len(payload), "sha256=", digest,
                      "expected=", digest == EXPECTED_BASE_SHA256)
                if digest == EXPECTED_BASE_SHA256:
                    OUT.write_bytes(data)
                    REPORT.write_text(
                        "SOURCE_GATE=PASS\n"
                        "mode=xapk\n"
                        f"url={final_url}\n"
                        f"entry={name}\n"
                        f"xapk_sha256={direct}\n"
                        f"base_sha256={digest}\n",
                        encoding="utf-8",
                    )
                    return True
    except zipfile.BadZipFile:
        pass
    return False


def extract_links(text: str, base_url: str) -> list[str]:
    text = html.unescape(text).replace("\\/", "/")
    vals: list[str] = []
    patterns = [
        r'''(?:href|src|data-url|data-href|data-download|data-link)\s*=\s*["']([^"']+)["']''',
        r'''["'](https?://[^"'<>\\s]+)["']''',
        r'''["']((?:/[^"']*)?(?:download|dwn)[^"']*)["']''',
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.I):
            value = m.group(1).strip()
            if not value or value.startswith(("javascript:", "mailto:", "#")):
                continue
            url = urllib.parse.urljoin(base_url, value)
            if url.startswith("http") and url not in vals:
                vals.append(url)
    return vals


queue = deque([
    f"{BASE}/download/{VERSION_ID}",
    f"{BASE}/download?version={VERSION_ID}",
    f"{BASE}/download?id={VERSION_ID}",
    f"{BASE}/versions",
    BASE,
])
seen: set[str] = set()
parent = BASE
attempts = 0

while queue and attempts < 60:
    url = queue.popleft()
    if url in seen:
        continue
    seen.add(url)
    attempts += 1
    print(f"TRY {attempts}: {url}")
    try:
        data, final, headers, status = fetch(url, parent)
    except Exception as e:
        print("ERROR", repr(e))
        continue
    ctype = (headers.get("Content-Type") or "").lower()
    disp = headers.get("Content-Disposition") or ""
    print("HTTP", status, "final=", final, "ctype=", ctype, "disp=", disp, "bytes=", len(data))

    # Binary-looking response or a ZIP/APK: validate immediately.
    if data[:2] == b"PK" or "application/vnd.android" in ctype or "application/octet-stream" in ctype:
        if inspect_payload(data, final):
            print(REPORT.read_text(encoding="utf-8"), end="")
            raise SystemExit(0)

    # Parse only bounded HTML/text responses. Prefer links tied to the exact version id,
    # then Uptodown download/CDN links, while avoiding unrelated page navigation.
    if len(data) <= 5_000_000 and ("html" in ctype or "text" in ctype or not ctype):
        text = data.decode("utf-8", "replace")
        links = extract_links(text, final)
        ranked: list[str] = []
        for link in links:
            low = link.lower()
            if VERSION_ID in link:
                ranked.append(link)
        for link in links:
            low = link.lower()
            host = urllib.parse.urlparse(link).netloc.lower()
            if ("download" in low or "/dwn/" in low or low.endswith((".xapk", ".apk"))) and (
                "uptodown" in host or "utdstc" in host
            ):
                ranked.append(link)
        for link in ranked:
            if link not in seen and link not in queue:
                queue.append(link)
        # Log exact-version neighborhood for diagnosis if this is a version list page.
        pos = text.find(VERSION_ID)
        if pos >= 0:
            print("VERSION_ID_CONTEXT", re.sub(r"\s+", " ", text[max(0,pos-1000):pos+2500])[:3500])
    parent = final

REPORT.write_text(
    "SOURCE_GATE=FAIL\n"
    f"attempts={attempts}\n"
    f"expected_base_sha256={EXPECTED_BASE_SHA256}\n",
    encoding="utf-8",
)
print(REPORT.read_text(encoding="utf-8"), end="")
raise SystemExit(3)
