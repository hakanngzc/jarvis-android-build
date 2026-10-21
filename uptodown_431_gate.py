#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import io
import json
import re
import sys
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


def fetch(url: str, *, referer: str | None = None, ua: str = BROWSER_UA):
    headers = {"User-Agent": ua, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=240) as r:
        return r.read(), r.geturl(), r.headers, r.status


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def attr(tag: str, name: str) -> str | None:
    m = re.search(rf'''\b{name}\s*=\s*["']([^"']+)["']''', tag, re.I)
    return html.unescape(m.group(1)) if m else None


def inspect_binary(data: bytes, url: str) -> bool:
    digest = sha(data)
    print("BINARY", url, "bytes=", len(data), "sha256=", digest)
    if digest == EXPECTED_BASE_SHA256:
        OUT.write_bytes(data)
        REPORT.write_text(
            "SOURCE_GATE=PASS\nsource=uptodown\nmode=direct-apk\n"
            f"url={url}\nbase_sha256={digest}\nbinary_published=NO\n",
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
                apk_hash = sha(payload)
                print("APK", name, len(payload), apk_hash, "EXPECTED", apk_hash == EXPECTED_BASE_SHA256)
                if apk_hash == EXPECTED_BASE_SHA256:
                    OUT.write_bytes(data)
                    REPORT.write_text(
                        "SOURCE_GATE=PASS\nsource=uptodown\nmode=xapk\n"
                        f"url={url}\nentry={name}\nxapk_sha256={digest}\n"
                        f"base_sha256={apk_hash}\napk_count={len(apks)}\nbinary_published=NO\n",
                        encoding="utf-8",
                    )
                    return True
    except zipfile.BadZipFile:
        pass
    return False


def try_cdn_token(token: str, referer: str) -> bool:
    token = html.unescape(token).replace("\\/", "/").strip().lstrip("/")
    if token.startswith("dwn/"):
        token = token[4:]
    dl = token if token.startswith("http") else f"https://dw.uptodown.com/dwn/{token}"
    print("CDN", dl)
    for ua in (DALVIK_UA, BROWSER_UA):
        try:
            data, final, headers, status = fetch(dl, referer=referer, ua=ua)
        except Exception as exc:
            print("CDN_ERROR", type(exc).__name__, exc)
            continue
        print("CDN_HTTP", status, final, headers.get("Content-Type"), "bytes=", len(data))
        if inspect_binary(data, final):
            return True
    return False


def resolve_post_download(post_url: str, referer: str) -> bool:
    raw, final, headers, status = fetch(post_url, referer=referer)
    print("POST_DOWNLOAD", status, final, headers.get("Content-Type"), "bytes=", len(raw))
    if raw[:2] == b"PK":
        return inspect_binary(raw, final)
    text = raw.decode("utf-8", "replace")
    candidates: list[str] = []
    for tag in re.findall(r'''<[^>]*class=["'][^"']*post-download[^"']*["'][^>]*>''', text, re.I):
        value = attr(tag, "data-url") or attr(tag, "href")
        if value:
            candidates.append(value)
    for m in re.finditer(r'''https?://dw\.uptodown\.com/dwn/[^"'<>\s]+''', text, re.I):
        candidates.append(m.group(0))
    print("POST_DOWNLOAD_CANDIDATES", len(candidates))
    for value in dict.fromkeys(candidates):
        if try_cdn_token(value, final):
            return True
    return False


def resolve_version_page(page_url: str, parent: str) -> bool:
    raw, final, headers, status = fetch(page_url, referer=parent)
    print("PAGE", status, final, headers.get("Content-Type"), "bytes=", len(raw))
    text = raw.decode("utf-8", "replace")

    for tag in re.findall(r'''<[^>]*(?:id=["']detail-download-button["']|class=["'][^"']*post-download[^"']*["'])[^>]*>''', text, re.I):
        value = attr(tag, "data-url")
        if value and try_cdn_token(value, final):
            return True

    app_code = None
    for tag in re.findall(r'''<[^>]*(?:id=["']detail-app-name["']|class=["'][^"']*detail-app-name[^"']*["'])[^>]*>''', text, re.I):
        app_code = attr(tag, "data-code") or attr(tag, "code")
        if app_code:
            break
    data_version = None
    for tag in re.findall(r'''<[^>]*class=["'][^"']*(?:variants|button)[^"']*["'][^>]*>''', text, re.I):
        data_version = attr(tag, "data-version")
        if data_version:
            break
    print("VARIANT_META", "app_code=", app_code, "data_version=", data_version)
    if not app_code or not data_version:
        return False

    files_url = f"https://new-star-soccer.en.uptodown.com/app/{app_code}/version/{data_version}/files"
    blob, files_final, hh, ss = fetch(files_url, referer=final)
    print("FILES", ss, files_final, hh.get("Content-Type"), "bytes=", len(blob))
    obj = json.loads(blob.decode("utf-8", "replace"))
    content = html.unescape(str(obj.get("content", ""))).replace("\\/", "/")
    file_ids = list(dict.fromkeys(re.findall(r'''data-file-id\s*=\s*["']([^"']+)["']''', content, re.I)))
    print("FILE_IDS", file_ids)

    post_paths: list[str] = []
    for m in re.finditer(r'''(?:android/)?post-download/([^"'<>\s\\]+)''', content, re.I):
        post_paths.append(m.group(1))
    for m in re.finditer(r'''(?:href|data-url)\s*=\s*["']([^"']*post-download/[^"']+)["']''', content, re.I):
        path = html.unescape(m.group(1)).replace("\\/", "/")
        post_paths.append(path.split("post-download/", 1)[1])
    post_paths = list(dict.fromkeys(post_paths))
    print("POST_PATHS", post_paths)
    for token in post_paths:
        if resolve_post_download(f"{BASE}/post-download/{token}", final):
            return True

    for fid in file_ids[:12]:
        for suffix in ("-x", ""):
            page = f"{BASE}/download/{fid}{suffix}"
            p_raw, p_final, p_h, p_s = fetch(page, referer=final)
            print("FILE_PAGE", p_s, p_final, p_h.get("Content-Type"), "bytes=", len(p_raw))
            p_text = p_raw.decode("utf-8", "replace")
            for tag in re.findall(r'''<[^>]*(?:id=["']detail-download-button["']|class=["'][^"']*post-download[^"']*["'])[^>]*>''', p_text, re.I):
                value = attr(tag, "data-url")
                if value and try_cdn_token(value, p_final):
                    return True
            for m in re.finditer(r'''(?:android/)?post-download/([^"'<>\s\\]+)''', p_text, re.I):
                if resolve_post_download(f"{BASE}/post-download/{m.group(1)}", p_final):
                    return True
    return False


try:
    versions_raw, versions_final, _, versions_status = fetch(BASE + "/versions")
    print("VERSIONS", versions_status, versions_final, "bytes=", len(versions_raw))
    text = versions_raw.decode("utf-8", "replace")
    target = None
    for block in re.findall(r'''<div\b[^>]*data-version-id=["'][^"']+["'][^>]*>.*?</div>''', text, re.I | re.S):
        plain = re.sub(r"<[^>]+>", " ", block)
        if re.search(r"\b4\.31\b", html.unescape(plain)):
            target = block
            break
    if not target:
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
    if not resolve_version_page(page_url, versions_final):
        raise RuntimeError("no Uptodown payload contained the expected NSS 4.31 base APK")
    print(REPORT.read_text(encoding="utf-8"), end="")
except Exception as exc:
    REPORT.write_text(
        "SOURCE_GATE=FAIL\nsource=uptodown\n"
        f"version_name={VERSION}\nreason={type(exc).__name__}:{exc}\n"
        f"expected_base_sha256={EXPECTED_BASE_SHA256}\n",
        encoding="utf-8",
    )
    print(REPORT.read_text(encoding="utf-8"), end="")
    raise SystemExit(3)
