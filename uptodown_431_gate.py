#!/usr/bin/env python3
from __future__ import annotations
import hashlib, io, sys, urllib.request, zipfile
from pathlib import Path

URL = "https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137"
REFERER = "https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31"
EXPECTED_BASE = "46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4"
EXPECTED_XAPK = "afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36"
OUT = Path(sys.argv[1]); REPORT = Path(sys.argv[2])

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

try:
    req = urllib.request.Request(URL, headers={
        "User-Agent": UA,
        "Referer": REFERER,
        "Accept": "application/octet-stream,application/zip,*/*",
    })
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read(); final = r.geturl(); ctype = r.headers.get("Content-Type"); disp = r.headers.get("Content-Disposition")
    xhash = sha(data)
    print("DOWNLOAD", final, ctype, disp, "bytes=", len(data), "sha256=", xhash)
    print("EXPECTED_XAPK", EXPECTED_XAPK, "MATCH", xhash == EXPECTED_XAPK)
    if data[:2] != b"PK":
        raise RuntimeError("APKPure response is not ZIP/XAPK")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist(); apks = [n for n in names if n.lower().endswith('.apk')]
        print("ENTRIES", len(names), "APKS", len(apks))
        found = None
        for name in apks:
            payload = z.read(name); h = sha(payload)
            print("APK", name, "bytes=", len(payload), "sha256=", h, "EXPECTED_BASE=", h == EXPECTED_BASE)
            if h == EXPECTED_BASE:
                found = name
        if not found:
            raise RuntimeError("APKPure 4.31 XAPK downloaded, but expected base APK hash was not found")
    OUT.write_bytes(data)
    REPORT.write_text(
        "SOURCE_GATE=PASS\nsource=apkpure-direct\npackage=com.newstargames.newstarsoccer\n"
        "version_name=4.31\nversion_code=137\n"
        f"url={final}\nxapk_sha256={xhash}\nbase_entry={found}\nbase_sha256={EXPECTED_BASE}\n"
        f"apk_count={len(apks)}\nbinary_published=NO\n",
        encoding="utf-8",
    )
    print(REPORT.read_text(encoding="utf-8"), end="")
except Exception as exc:
    REPORT.write_text(
        "SOURCE_GATE=FAIL\nsource=apkpure-direct\n"
        f"reason={type(exc).__name__}:{exc}\nexpected_base_sha256={EXPECTED_BASE}\n",
        encoding="utf-8",
    )
    print(REPORT.read_text(encoding="utf-8"), end="")
    raise SystemExit(3)
