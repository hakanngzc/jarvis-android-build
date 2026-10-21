#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

URL = "https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137"
EXPECTED_BASE_SHA256 = "46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4"
EXPECTED_VERSION = "4.31"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36"
REPORT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/NSS_431_APKPURE_GATE.txt")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(reason: str) -> None:
    REPORT.write_text(
        "SOURCE_GATE=FAIL\n"
        "source=apkpure\n"
        f"reason={reason}\n"
        f"expected_base_sha256={EXPECTED_BASE_SHA256}\n",
        encoding="utf-8",
    )
    print(REPORT.read_text(encoding="utf-8"), end="")
    raise SystemExit(3)


req = urllib.request.Request(
    URL,
    headers={
        "User-Agent": UA,
        "Accept": "application/octet-stream,application/zip,*/*",
        "Referer": "https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31",
    },
)
try:
    with urllib.request.urlopen(req, timeout=300) as r:
        payload = r.read()
        final_url = r.geturl()
        ctype = r.headers.get("Content-Type") or ""
        disp = r.headers.get("Content-Disposition") or ""
        status = r.status
except Exception as exc:
    fail(f"download:{type(exc).__name__}:{exc}")

print("HTTP_STATUS", status)
print("FINAL_URL", final_url)
print("CONTENT_TYPE", ctype)
print("CONTENT_DISPOSITION", disp)
print("XAPK_BYTES", len(payload))
print("XAPK_SHA256", sha256(payload))

if not payload.startswith(b"PK"):
    fail("payload-is-not-zip")

try:
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        names = z.namelist()
        apk_names = [n for n in names if n.lower().endswith(".apk")]
        print("ZIP_ENTRIES", len(names))
        print("APK_COUNT", len(apk_names))
        if not apk_names:
            fail("no-apk-inside-xapk")
        matches = []
        rows = []
        for name in apk_names:
            data = z.read(name)
            digest = sha256(data)
            rows.append((name, len(data), digest))
            is_match = digest == EXPECTED_BASE_SHA256
            print("APK", name, "bytes=", len(data), "sha256=", digest, "EXPECTED_BASE_MATCH=", is_match)
            if is_match:
                matches.append((name, len(data), digest))
except zipfile.BadZipFile as exc:
    fail(f"bad-xapk:{exc}")

if len(matches) != 1:
    fail(f"expected-one-base-match-found-{len(matches)}")

name, size, digest = matches[0]
REPORT.write_text(
    "SOURCE_GATE=PASS\n"
    "source=apkpure\n"
    f"version_name={EXPECTED_VERSION}\n"
    f"url={URL}\n"
    f"final_url={final_url}\n"
    f"xapk_sha256={sha256(payload)}\n"
    f"base_entry={name}\n"
    f"base_bytes={size}\n"
    f"base_sha256={digest}\n"
    f"apk_count={len(rows)}\n"
    "binary_published=NO\n",
    encoding="utf-8",
)
print(REPORT.read_text(encoding="utf-8"), end="")
