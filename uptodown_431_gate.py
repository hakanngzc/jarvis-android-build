#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, io, re, sys, urllib.parse, urllib.request, http.cookiejar, zipfile
from pathlib import Path

PAGE = "https://www.tamindir.com/indir/new-star-soccer-apk/"
ORIGIN = "https://www.tamindir.com"
EXPECTED = "46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36"
OUT = Path(sys.argv[1])
REPORT = Path(sys.argv[2])

cookies = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))

def fetch(url: str, referer: str | None = None):
    headers = {
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with opener.open(req, timeout=240) as r:
        return r.read(), r.geturl(), r.headers, r.status

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def inspect(data: bytes, url: str) -> bool:
    digest = sha(data)
    print("PAYLOAD", url, "bytes=", len(data), "sha256=", digest)
    if digest == EXPECTED:
        OUT.write_bytes(data)
        REPORT.write_text(
            "SOURCE_GATE=PASS\nsource=tamindir\nmode=direct-apk\n"
            f"url={url}\nbase_sha256={digest}\nbinary_published=NO\n",
            encoding="utf-8",
        )
        return True
    if data[:2] != b"PK":
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            apks = [n for n in z.namelist() if n.lower().endswith(".apk")]
            print("ZIP_APKS", len(apks), apks[:30])
            for name in apks:
                payload = z.read(name)
                h = sha(payload)
                print("APK", name, len(payload), h, "EXPECTED", h == EXPECTED)
                if h == EXPECTED:
                    OUT.write_bytes(data)
                    REPORT.write_text(
                        "SOURCE_GATE=PASS\nsource=tamindir\nmode=archive\n"
                        f"url={url}\nentry={name}\narchive_sha256={digest}\n"
                        f"base_sha256={h}\napk_count={len(apks)}\nbinary_published=NO\n",
                        encoding="utf-8",
                    )
                    return True
    except zipfile.BadZipFile:
        pass
    return False

def extract_candidates(text: str, base: str) -> list[str]:
    text = html.unescape(text).replace("\\/", "/")
    out: list[str] = []
    patterns = [
        r'''(?:href|data-url|data-href)\s*=\s*["']([^"']+)["']''',
        r'''https?://[^"'<>\s]+''',
        r'''location(?:\.href)?\s*=\s*["']([^"']+)["']''',
        r'''(?:window\.)?open\(\s*["']([^"']+)["']''',
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.I):
            value = m.group(1) if m.lastindex else m.group(0)
            value = value.strip().rstrip(");,')\"")
            url = urllib.parse.urljoin(base, value)
            low = url.lower()
            if url.startswith("http") and any(k in low for k in ("apk", "download", "indir", "dosya", "file", "new-star", "newstar")) and url not in out:
                out.append(url)
    return out

try:
    raw, final, headers, status = fetch(PAGE)
    print("PAGE", status, final, headers.get("Content-Type"), "bytes=", len(raw))
    text = html.unescape(raw.decode("utf-8", "replace")).replace("\\/", "/")
    if 'data-version-name="4.31"' not in text and ">4.31<" not in text and "4.31 New Star Soccer" not in text:
        raise RuntimeError("Tamindir page no longer identifies version 4.31")

    # Exact legacy/normal 4.31 option. v=98774 is the observed Tamindir file-version id,
    # but the signed token is always parsed fresh from the live page.
    matches = re.findall(r'''downloadAds\(event,\s*["']([^"']*?/android/new-star-soccer-apk/indir/\?[^"']*\bv=98774(?:&[^"']*)?)["']\)''', text, re.I)
    if not matches:
        # Query parameter order can change, so fall back to any downloadAds URL containing v=98774.
        matches = [m for m in re.findall(r'''downloadAds\(event,\s*["']([^"']+)["']\)''', text, re.I) if re.search(r'''(?:\?|&)v=98774(?:&|$)''', m)]
    if not matches:
        raise RuntimeError("4.31 Normal Indirme endpoint (v=98774) not found")

    endpoint = urllib.parse.urljoin(ORIGIN, matches[0])
    print("NORMAL_431_ENDPOINT", endpoint)
    data, f2, h2, s2 = fetch(endpoint, final)
    ctype = h2.get("Content-Type") or ""
    disp = h2.get("Content-Disposition") or ""
    print("NORMAL_431_HTTP", s2, f2, ctype, disp, "bytes=", len(data))
    if inspect(data, f2):
        print(REPORT.read_text(encoding="utf-8"), end="")
        raise SystemExit(0)

    # Tamindir may return an intermediary ad/download HTML. Follow only bounded, explicit
    # download-like links; never recursively crawl the site.
    if len(data) <= 5_000_000:
        middle = data.decode("utf-8", "replace")
        candidates = extract_candidates(middle, f2)
        print("INTERMEDIATE_CANDIDATES", len(candidates))
        for i, url in enumerate(candidates[:20], 1):
            print("CANDIDATE", i, url)
            try:
                payload, f3, h3, s3 = fetch(url, f2)
            except Exception as exc:
                print("CANDIDATE_ERROR", i, type(exc).__name__, exc)
                continue
            print("CANDIDATE_HTTP", i, s3, f3, h3.get("Content-Type"), h3.get("Content-Disposition"), "bytes=", len(payload))
            if inspect(payload, f3):
                print(REPORT.read_text(encoding="utf-8"), end="")
                raise SystemExit(0)

    raise RuntimeError("Tamindir 4.31 endpoint did not yield payload containing expected base APK hash")
except SystemExit:
    raise
except Exception as exc:
    REPORT.write_text(
        "SOURCE_GATE=FAIL\nsource=tamindir\n"
        f"reason={type(exc).__name__}:{exc}\nexpected_base_sha256={EXPECTED}\n",
        encoding="utf-8",
    )
    print(REPORT.read_text(encoding="utf-8"), end="")
    raise SystemExit(3)
