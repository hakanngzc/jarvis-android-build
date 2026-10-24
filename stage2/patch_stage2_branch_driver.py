#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lifecycle'))
from patch_lifecycle_probe_v3 import patch_script as lifecycle_v3_patch
from patch_lifecycle_probe_v4 import FATAL_ANCHOR, harden_fatal_check
from patch_stage2_frida_smoke_driver import INSTALL_ANCHOR, INSTALL_REPLACEMENT, one_replace

KNOCKOUT_ANCHOR = '''python3 stage3/patch_stage3_knockout_apk.py "$MODE" "$WORK/base-career-probe.apk" "$WORK/base-knockout-probe.apk" \\
  --evidence "$OUT/STAGE3_KNOCKOUT_APK_PATCH.json" | tee "$OUT/STAGE3_KNOCKOUT_APK_PATCH.txt"'''
KNOCKOUT_REPLACEMENT = '''cp "$WORK/base-career-probe.apk" "$WORK/base-knockout-probe.apk"
python3 stage2/verify_stage2_writer_hashes.py "$WORK/xapk/com.newstargames.newstarsoccer.apk" "$WORK/base-knockout-probe.apk" \\
  --out "$OUT/STAGE2_WRITER_HASHES.json" | tee "$OUT/STAGE2_WRITER_HASHES.txt"'''

TRUNCATE_ANCHOR = '''shot career-gamemenu
lifecycle_background_roundtrip career

# Drive normal stock UI to the next playable match.'''
TRUNCATE_REPLACEMENT = r'''shot career-gamemenu
SCENARIO="${STAGE2_SCENARIO:?STAGE2_SCENARIO is required}"
case "$SCENARIO" in accept|reject|transfer|retirement) ;; *) echo "bad Stage2 scenario: $SCENARIO"; exit 2;; esac

dismiss_measurement_anr_modal(){
  local attempt xml target live x y anr_count measurement_count
  xml="$OUT/stage2-${SCENARIO}-measurement-anr-ui.xml"
  target="$WORK/stage2-${SCENARIO}-measurement-anr-wait-target.txt"
  live="$OUT/stage2-${SCENARIO}-measurement-anr-live.log"
  for attempt in $(seq 1 90); do
    adb logcat -d -v threadtime > "$live" 2>/dev/null || true
    if ! grep -qE 'Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$live"; then
      anr_count="$(grep -cE 'ANR in com\.newstargames\.newstarsoccer' "$live" || true)"
      measurement_count="$(grep -cE 'Reason: executing service com\.newstargames\.newstarsoccer/com\.google\.android\.gms\.measurement\.AppMeasurementService' "$live" || true)"
      if [ "$anr_count" -gt 0 ] && [ "$anr_count" -eq "$measurement_count" ]; then
        adb shell uiautomator dump /sdcard/stage2-anr.xml >/dev/null 2>&1 || true
        adb shell cat /sdcard/stage2-anr.xml > "$xml" 2>/dev/null || true
        if grep -q 'text="Wait"' "$xml" && grep -qiE 'NSS[^<]*(isn.t|is not)[^<]*responding|NSS[^<]*responding' "$xml"; then
          python3 - "$xml" "$target" <<'PY'
import re,sys,xml.etree.ElementTree as ET
from pathlib import Path
src,dst=sys.argv[1:]
try:
    root=ET.parse(src).getroot()
except Exception:
    raise SystemExit(1)
for node in root.iter('node'):
    if node.attrib.get('text') != 'Wait':
        continue
    m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',node.attrib.get('bounds',''))
    if not m:
        continue
    x1,y1,x2,y2=map(int,m.groups())
    if x2>x1 and y2>y1:
        Path(dst).write_text(f'{(x1+x2)//2} {(y1+y2)//2}\n',encoding='utf-8')
        raise SystemExit(0)
raise SystemExit(1)
PY
          if [ -s "$target" ]; then
            read -r x y < "$target"
            adb shell input tap "$x" "$y" >/dev/null 2>&1 || true
            printf 'measurement_anr_wait_dismissed=PASS\n' | tee "$OUT/stage2-${SCENARIO}-measurement-anr-recovery.txt"
            return 0
          fi
        fi
      fi
    fi
    sleep 1
  done
  return 0
}

dump_stage2_save(){
  local tag="$1"
  local remote="/data/data/$PKG/shared_prefs/MonkeyGame.xml"
  local xml="$OUT/${tag}-MonkeyGame.xml"
  adb shell cat "$remote" > "$xml" 2>/dev/null || true
  grep -q 'monkeystate' "$xml" || { echo "Could not read $remote for $tag"; return 1; }
}

require_stage2_pid(){
  local tag="$1"
  STAGE2_PID="$(pid_one)"
  adb shell dumpsys activity activities > "$OUT/stage2-${SCENARIO}-${tag}-activity.txt" 2>/dev/null || true
  if [ -z "$STAGE2_PID" ]; then
    adb logcat -d -v threadtime > "$OUT/stage2-${SCENARIO}-${tag}-no-process.log" 2>/dev/null || true
    adb shell ps -A > "$OUT/stage2-${SCENARIO}-${tag}-ps.txt" 2>/dev/null || true
    echo "NSS process missing before Stage2 Frida attach ($SCENARIO/$tag)"
    return 1
  fi
  printf '%s\n' "$STAGE2_PID" > "$OUT/stage2-${SCENARIO}-${tag}-pid.txt"
  echo "stage2_${SCENARIO}_${tag}_pid=$STAGE2_PID"
}

dump_stage2_save baseline
sed "s/__SCENARIO__/${SCENARIO}/g" stage2/stage2_branch_scenario.js > "$WORK/stage2-${SCENARIO}.js"
clear_log
require_stage2_pid scenario
python3 stage2/run_frida_script.py \
  --package "$PKG" \
  --pid "$STAGE2_PID" \
  --script "$WORK/stage2-${SCENARIO}.js" \
  --event-type stage2-scenario \
  --timeout 30 \
  --out "$OUT/STAGE2_${SCENARIO}_SCENARIO.json"
wait_log 'QUICK SAVE' 15 "stage2-${SCENARIO}-quicksave"
fatal_check
dump_stage2_save post
shot "stage2-${SCENARIO}-post"

# Mandatory process restart and stock LoadCareer. AOSP API29 can surface a
# system ANR modal for the absent Google measurement service. The bounded
# watcher independently classifies live logcat with the same exact
# measurement-only rule before it may press Wait. Unknown ANRs and crashes are
# never acted on and remain fail-closed in the normal runtime gate.
rm -f "$OUT/stage2-${SCENARIO}-measurement-anr-recovery.txt" "$OUT/stage2-${SCENARIO}-measurement-anr-live.log"
dismiss_measurement_anr_modal &
STAGE2_ANR_WATCHER_PID=$!
if ! reload_saved_career_after_setup; then
  kill "$STAGE2_ANR_WATCHER_PID" >/dev/null 2>&1 || true
  wait "$STAGE2_ANR_WATCHER_PID" 2>/dev/null || true
  exit 1
fi
kill "$STAGE2_ANR_WATCHER_PID" >/dev/null 2>&1 || true
wait "$STAGE2_ANR_WATCHER_PID" 2>/dev/null || true

dump_stage2_save reload
require_stage2_pid reload
python3 stage2/run_frida_script.py \
  --package "$PKG" \
  --pid "$STAGE2_PID" \
  --script stage2/frida_smoke.js \
  --event-type stage2-smoke \
  --timeout 20 \
  --out "$OUT/STAGE2_${SCENARIO}_RELOAD_RUNTIME.json"
fatal_check

python3 stage2/verify_stage2_branch_runtime.py "$SCENARIO" \
  "$OUT/baseline-MonkeyGame.xml" "$OUT/post-MonkeyGame.xml" "$OUT/reload-MonkeyGame.xml" \
  "$OUT/STAGE2_${SCENARIO}_SCENARIO.json" "$OUT/STAGE2_${SCENARIO}_RELOAD_RUNTIME.json" \
  | tee "$OUT/STAGE2_${SCENARIO}_RESULT.txt"
grep -q "VERDICT=STAGE2_${SCENARIO^^}_PASS" "$OUT/STAGE2_${SCENARIO}_RESULT.txt"
adb shell cat /data/local/tmp/frida-server.log > "$OUT/frida-server.log" 2>/dev/null || true
echo "VERDICT=STAGE2_${SCENARIO^^}_RUNTIME_PASS"
exit 0

# Stage3 tail intentionally disabled for Stage2 branch verification.'''


def adapt_generated_script(text: str) -> str:
    text = one_replace(text, KNOCKOUT_ANCHOR, KNOCKOUT_REPLACEMENT, 'Stage3 patch block')
    text = one_replace(text, INSTALL_ANCHOR, INSTALL_REPLACEMENT, 'Frida install block')
    text = one_replace(text, TRUNCATE_ANCHOR, TRUNCATE_REPLACEMENT, 'post-Career tail')
    return text


def patch_script(text: str) -> str:
    generated = lifecycle_v3_patch(text)
    generated = harden_fatal_check(generated)
    return adapt_generated_script(generated)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: patch_stage2_branch_driver.py INPUT_SH OUTPUT_SH')
    src, dst = map(Path, sys.argv[1:])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(patch_script(src.read_text(encoding='utf-8')), encoding='utf-8')
    dst.chmod(0o755)
    print(f'patched Stage2 branch driver: {src} -> {dst}')


if __name__ == '__main__':
    main()
