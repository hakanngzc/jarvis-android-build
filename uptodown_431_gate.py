#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

PKG = "com.newstargames.newstarsoccer"
VERSION_CODE = "137"
ARCH = "arm64"
EXPECTED_BASE_SHA256 = "46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4"
REPORT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/NSS_431_SOURCE_GATE.txt")
WORK = Path("/tmp/nss431-play")
WORK.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    cp = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(cp.stdout, end="")
    if check and cp.returncode != 0:
        raise RuntimeError(f"command failed rc={cp.returncode}: {' '.join(cmd)}")
    return cp


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

try:
    run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "goopdl==1.2.1"])

    delivery = WORK / "delivery.json"
    run([
        "goopdl", "inspect-delivery", PKG,
        "--arch", ARCH,
        "--version", VERSION_CODE,
        "--json", "--output", str(delivery),
    ])
    meta = json.loads(delivery.read_text(encoding="utf-8"))
    print("DELIVERY_JSON", json.dumps(meta, sort_keys=True))
    version = meta.get("version") or {}
    got_code = str(version.get("code", ""))
    got_name = str(version.get("name", ""))
    if got_code != VERSION_CODE:
        raise RuntimeError(f"Play returned unexpected version code {got_code!r}")
    if got_name and got_name != "4.31":
        raise RuntimeError(f"Play returned unexpected version name {got_name!r}")

    run([
        "goopdl", "download", PKG,
        "--arch", ARCH,
        "--version", VERSION_CODE,
        "--output", str(WORK / "apks"),
        "--no-extras",
    ])

    files = sorted((WORK / "apks").glob("*.apk"))
    if not files:
        raise RuntimeError("goopdl returned no APK files")
    print("DOWNLOADED_APKS")
    for p in files:
        print(p.name, p.stat().st_size, sha256(p))

    base_candidates = [
        p for p in files
        if p.name == f"{PKG}-{VERSION_CODE}.apk"
        or ("config." not in p.name and "asset" not in p.name)
    ]
    if len(base_candidates) != 1:
        raise RuntimeError(f"could not uniquely identify base APK: {[p.name for p in base_candidates]}")
    base = base_candidates[0]
    base_hash = sha256(base)
    if base_hash != EXPECTED_BASE_SHA256:
        raise RuntimeError(
            f"base APK hash mismatch: got {base_hash}, expected {EXPECTED_BASE_SHA256}"
        )

    REPORT.write_text(
        "SOURCE_GATE=PASS\n"
        "source=google-play-via-goopdl\n"
        f"package={PKG}\n"
        "version_name=4.31\n"
        f"version_code={VERSION_CODE}\n"
        f"auth_arch={ARCH}\n"
        f"base_file={base.name}\n"
        f"base_sha256={base_hash}\n"
        f"apk_count={len(files)}\n"
        "binary_published=NO\n",
        encoding="utf-8",
    )
    print(REPORT.read_text(encoding="utf-8"), end="")
except Exception as exc:
    REPORT.write_text(
        "SOURCE_GATE=FAIL\n"
        "source=google-play-via-goopdl\n"
        f"package={PKG}\n"
        f"version_code={VERSION_CODE}\n"
        f"auth_arch={ARCH}\n"
        f"reason={type(exc).__name__}:{exc}\n"
        f"expected_base_sha256={EXPECTED_BASE_SHA256}\n",
        encoding="utf-8",
    )
    print(REPORT.read_text(encoding="utf-8"), end="")
    raise SystemExit(3)
