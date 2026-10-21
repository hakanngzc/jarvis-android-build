#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import io
import json
import re
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://new-star-soccer.en.uptodown.com/android"
VERSION = "4.31"
EXPECTED_BASE_SHA256 = "46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4"
BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36"
DALVIK_UA = "Dalvik/2.1.0 (Linux; U; Android 10; Pixel 4 Build/QP1A.190711.020)"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/nss-4.31.xapk")
REPORT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/NSS_431_SOURCE_GATE.txt")


def fetch(url: str, *, referer: str | None = None, ua: str = BROWSER_UA) -> tuple[bytes, str, object, int]:
    headers = {
        "User-Agent": ua,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=240) as r:
        return r.read(), r.geturl(), r.headers, r.status


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def attr(tag: str, name: str) -> str | None:
    m = re.search(rf'''\b{name}\s*=\s*["']([^"']+)["']''', tag, re.I)
    return html.unescape(m.group(1)) if m else None


def tags_with(text: str, needle: str) -> list[str]:
    return re.findall(rf'''<[^>]*{re.escape(needle)}[^>]*>''', text, re.I)


def inspect_binary(data: bytes, url: str) -> bool:
    digest = sha_bytes(data)
    print("BINARY", url, "bytes=", len(data), "sha256=", digest)
    if digest == EXPECTED_BASE_SHA256:
        OUT.write_bytes(data)
        REPORT.write_text(
            "SOURCE_GATE=PASS\n"
            "source=uptodown\n"
            "mode=direct-apk\n"
            f"url={url}\n"
            f"base_sha256={digest}\n"
            "binary_published=NO\n",
            encoding="utf-8",
        )
        return True
    if data[:2] != b"PK":
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            apks = [n for n in z.namelist() if n.lower().endswith(".apk")]
            print("ZIP_APKS", len(apks), apks[:20])
            for name in apks:
                payload = z.read(name)
                apk_hash = sha_bytes(payload)
                print("APK", name, len(payload), apk_hash, "EXPECTED", apk_hash == EXPECTED_BASE_SHA256)
                if apk_hash == EXPECTED_BASE_SHA256:
                    OUT.write_bytes(data)
                    REPORT.write_text(
                        "SOURCE_GATE=PASS\n"
                        "source=uptodown\n"
                        "mode=xapk\n"
                        f"url={url}\n"
                        f"entry={name}\n"
                        f"xapk_sha256={digest}\n"
                        f"base_sha256={apk_hash}\n"
                        f"apk_count={len(apks)}\n"
                        "binary_published=NO\n",
                        encoding="utf-8",
                    )
                    return True
    except zipfile.BadZipFile:
        pass
    return False


def download_from_page(page_url: str, parent: str) -> bool:
    raw, final, headers, status = fetch(page_url, referer=parent)
    print("PAGE", status, final, headers.get("Content-Type"), "bytes=", len(raw))
    if raw[:2] == b"PK":
        return inspect_binary(raw, final)
    text = raw.decode("utf-8", "replace")
    # Current Uptodown pages expose the CDN token in the main download button.
    candidates: list[str] = []
    for tag in tags_with(text, "detail-download-button"):
        v = attr(tag, "data-url") or attr(tag, "href")
        if v:
            candidates.append(v)
    for tag in tags_with(text, "post-download"):
        v = attr(tag, "data-url") or attr(tag, "href")
        if v:
            candidates.append(v)
    for m in re.finditer(r'''https?://dw\.uptodown\.com/dwn/[^"'<>\s]+''', text, re.I):
        candidates.append(html.unescape(m.group(0)))
    seen: set[str] = set()
    for value in candidates:
        if value in seen:
            continue
        seen.add(value)
        if value.startswith("http"):
            dl = value
        else:
            dl = "https://dw.uptodown.com/dwn/" + value.lstrip("/")
        print("DOWNLOAD_CANDIDATE", dl)
        for ua in (DALVIK_UA, BROWSER_UA):
            try:
                data, f2, h2, s2 = fetch(dl, referer=final, ua=ua)
            except Exception as exc:
                print("DOWNLOAD_ERROR", type(exc).__name__, exc)
                continue
            print("DOWNLOAD_HTTP", s2, f2, h2.get("Content-Type"), "bytes=", len(data))
            if inspect_binary(data, f2):
                return True
    # Variant pages: ask Uptodown for every file id and try each download page.
    app_code = None
    for tag in tags_with(text, "detail-app-name"):
        app_code = attr(tag, "data-code") or attr(tag, "code")
        if app_code:
            break
    data_version = None
    for tag in tags_with(text, "variants"):
        data_version = attr(tag, "data-version")
        if data_version:
            break
    print("VARIANT_META", "app_code=", app_code, "data_version=", data_version)
    if app_code and data_version:
        files_url = f"https://new-star-soccer.en.uptodown.com/app/{app_code}/version/{data_version}/files"
        try:
            blob, ff, hh, ss = fetch(files_url, referer=final)
            print("FILES", ss, ff, hh.get("Content-Type"), "bytes=", len(blob))
            obj = json.loads(blob.decode("utf-8", "replace"))
            content = html.unescape(str(obj.get("content", "")))
            file_ids = list(dict.fromkeys(re.findall(r'''data-file-id\s*=\s*["']([^"']+)["']''', content, re.I)))
            print("FILE_IDS", file_ids)
            for fid in file_ids[:12]:
                for suffix in ("-x", ""):
                    try:
                        if download_from_page(f"{BASE}/download/{fid}{suffix}", final):
                            return True
                    except Exception as exc:
                        print("FILE_PAGE_ERROR", fid, suffix, type(exc).__name__, exc)
        except Exception as exc:
            print("VARIANT_ERROR", type(exc).__name__, exc)
    return False


try:
    versions_raw, versions_final, _, versions_status = fetch(BASE + "/versions")
    print("VERSIONS", versions_status, versions_final, "bytes=", len(versions_raw))
    text = versions_raw.decode("utf-8", "replace")
    blocks = re.findall(r'''<div\b[^>]*data-version-id=["'][^"']+["'][^>]*>.*?</div>''', text, re.I | re.S)
    target = None
    for block in blocks:
        plain = re.sub(r"<[^>]+>", " ", block)
        if re.search(r"\b4\.31\b", html.unescape(plain)):
            target = block
            break
    if not target:
        # Fallback to the exact version id already observed on the live versions page.
        m = re.search(r'''<div\b[^>]*data-version-id=["']1129097900["'][^>]*>''', text, re.I)
        if not m:
            raise RuntimeError("4.31 version card not found")
        target = m.group(0)
    opening = target.split(">", 1)[0] + ">"
    version_id = attr(opening, "data-version-id")
    data_url = attr(opening, "data-url") or BASE
    extra = attr(opening, "data-extra-url") or "download"
    if not version_id:
        raise RuntimeError("4.31 data-version-id missing")
    page_url = data_url.rstrip("/") + "/" + extra.strip("/") + "/" + version_id
    print("VERSION_CARD", VERSION, version_id, data_url, extra)
    print("VERSION_PAGE", page_url)
    if not download_from_page(page_url, versions_final):
        raise RuntimeError("no Uptodown payload contained the expected NSS 4.31 base APK")
    print(REPORT.read_text(encoding="utf-8"), end="")
except Exception as exc:
    REPORT.write_text(
        "SOURCE_GATE=FAIL\n"
        "source=uptodown\n"
        f"version_name={VERSION}\n"
        f"reason={type(exc).__name__}:{exc}\n"
        f"expected_base_sha256={EXPECTED_BASE_SHA256}\n",
        encoding="utf-8",
    )
    print(REPORT.read_text(encoding="utf-8"), end="")
    raise SystemExit(3)
