#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lifecycle'))
from patch_lifecycle_probe_v3 import patch_script as lifecycle_v3_patch

KNOCKOUT_ANCHOR = '''python3 stage3/patch_stage3_knockout_apk.py "$MODE" "$WORK/base-career-probe.apk" "$WORK/base-knockout-probe.apk" \\
  --evidence "$OUT/STAGE3_KNOCKOUT_APK_PATCH.json" | tee "$OUT/STAGE3_KNOCKOUT_APK_PATCH.txt"'''
KNOCKOUT_REPLACEMENT = '''cp "$WORK/base-career-probe.apk" "$WORK/base-knockout-probe.apk"
printf '%s\\n' 'Stage2 smoke: no Stage3 match patch applied' > "$OUT/STAGE2_BASELINE.txt"'''

INSTALL_ANCHOR = '''adb install-multiple -r "$SIGNED/base.apk" "$SIGNED/config.tr.apk" "$SIGNED/config.xxhdpi.apk" >/dev/null
adb shell pm clear "$PKG" >/dev/null || true'''
INSTALL_REPLACEMENT = r'''FRIDA_VERSION=17.24.3
FRIDA_XZ="$WORK/frida-server-${FRIDA_VERSION}-android-x86_64.xz"
FRIDA_BIN="$WORK/frida-server-${FRIDA_VERSION}-android-x86_64"
curl -fL --retry 3 "https://github.com/frida/frida/releases/download/${FRIDA_VERSION}/frida-server-${FRIDA_VERSION}-android-x86_64.xz" -o "$FRIDA_XZ"
xz -dc "$FRIDA_XZ" > "$FRIDA_BIN"
chmod +x "$FRIDA_BIN"
adb root >/dev/null 2>&1 || true
adb wait-for-device
adb push "$FRIDA_BIN" /data/local/tmp/frida-server >/dev/null
adb shell chmod 755 /data/local/tmp/frida-server
adb shell 'pkill frida-server >/dev/null 2>&1 || true'
adb shell 'nohup /data/local/tmp/frida-server >/data/local/tmp/frida-server.log 2>&1 &' >/dev/null 2>&1
sleep 2
adb shell 'pidof frida-server || true' > "$OUT/frida-server-pid.txt"
test -s "$OUT/frida-server-pid.txt" || { adb shell cat /data/local/tmp/frida-server.log > "$OUT/frida-server-start-failed.log" 2>/dev/null || true; echo 'Frida server did not start'; return 1; }
adb install-multiple -r "$SIGNED/base.apk" "$SIGNED/config.tr.apk" "$SIGNED/config.xxhdpi.apk" >/dev/null
adb shell pm clear "$PKG" >/dev/null || true'''

TRUNCATE_ANCHOR = '''shot career-gamemenu
lifecycle_background_roundtrip career

# Drive normal stock UI to the next playable match.'''
TRUNCATE_REPLACEMENT = r'''shot career-gamemenu
STAGE2_SMOKE_PID="$(pid_one)"
if ! test -n "$STAGE2_SMOKE_PID"; then
  adb logcat -d -v threadtime > "$OUT/stage2-smoke-no-process.log" 2>/dev/null || true
  adb shell ps -A > "$OUT/stage2-smoke-no-process-ps.txt" 2>/dev/null || true
  echo 'NSS process missing before Stage2 Frida smoke attach'
  exit 1
fi
printf '%s\n' "$STAGE2_SMOKE_PID" > "$OUT/stage2-smoke-pid.txt"
python3 stage2/run_frida_script.py \
  --package "$PKG" \
  --pid "$STAGE2_SMOKE_PID" \
  --script stage2/frida_smoke.js \
  --out "$OUT/STAGE2_FRIDA_SMOKE.json"
fatal_check
adb shell cat /data/local/tmp/frida-server.log > "$OUT/frida-server.log" 2>/dev/null || true
echo 'VERDICT=STAGE2_FRIDA_SMOKE_PASS' | tee "$OUT/STAGE2_FRIDA_SMOKE_RESULT.txt"
exit 0

# Stage3 tail intentionally disabled for this Stage2 smoke driver.'''


def one_replace(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f'expected one {label} anchor, found {count}')
    return text.replace(old, new, 1)


def adapt_generated_script(text: str) -> str:
    text = one_replace(text, KNOCKOUT_ANCHOR, KNOCKOUT_REPLACEMENT, 'Stage3 patch block')
    text = one_replace(text, INSTALL_ANCHOR, INSTALL_REPLACEMENT, 'install block')
    text = one_replace(text, TRUNCATE_ANCHOR, TRUNCATE_REPLACEMENT, 'post-Career tail')
    return text


def patch_script(text: str) -> str:
    return adapt_generated_script(lifecycle_v3_patch(text))


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: patch_stage2_frida_smoke_driver.py INPUT_SH OUTPUT_SH')
    src, dst = map(Path, sys.argv[1:])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(patch_script(src.read_text(encoding='utf-8')), encoding='utf-8')
    dst.chmod(0o755)
    print(f'patched Stage2 Frida smoke driver: {src} -> {dst}')


if __name__ == '__main__':
    main()
