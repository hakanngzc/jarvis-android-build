#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

BOOT_RE = re.compile(
    r'''(?ms)^start_game fresh;.*?^START_EPOCH="\$\(date \+%s\)"; SEASON_SEEN=0; CYCLES=0\s*$'''
)
LOOP_OLD = 'for cycle in $(seq 1 "$MAX_MATCH_CYCLES"); do'
FINAL_RE = re.compile(
    r'''(?ms)^python3 stage4_tools/verify_stage4_natural_season\.py .*?^echo 'STAGE4_NATURAL_SEASON_PASS'\s*$'''
)

BOOT_NEW = r'''SEED_XML="${STAGE4_DIAGNOSTIC_SEED_XML:?missing STAGE4_DIAGNOSTIC_SEED_XML}"
DIAG_START_CYCLE="${STAGE4_DIAGNOSTIC_START_CYCLE:-20}"
test -s "$SEED_XML"
[[ "$DIAG_START_CYCLE" =~ ^[0-9]+$ ]] || { echo 'invalid diagnostic start cycle' >> "$FLOW"; exit 229; }
[ "$DIAG_START_CYCLE" -lt "$MAX_MATCH_CYCLES" ] || { echo 'diagnostic start cycle must be before MAX_MATCH_CYCLES' >> "$FLOW"; exit 229; }
echo "DIAGNOSTIC ONLY: restoring verified natural cycle ${DIAG_START_CYCLE} save; not valid for final Stage4 PASS" >> "$FLOW"
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
adb root >/dev/null 2>&1 || true
adb wait-for-device
sleep 2
seed_owner="$(adb shell stat -c '%u:%g' "/data/data/$PKG" 2>/dev/null | tr -d '\r' | tail -1)"
[ -n "$seed_owner" ] || { echo 'diagnostic seed owner lookup failed' >> "$FLOW"; exit 230; }
adb push "$SEED_XML" /data/local/tmp/Stage4DiagnosticMonkeyGame.xml >/dev/null
adb shell mkdir -p "/data/data/$PKG/shared_prefs"
adb shell cp /data/local/tmp/Stage4DiagnosticMonkeyGame.xml "/data/data/$PKG/shared_prefs/MonkeyGame.xml"
adb shell chown "$seed_owner" "/data/data/$PKG/shared_prefs/MonkeyGame.xml"
adb shell chmod 660 "/data/data/$PKG/shared_prefs/MonkeyGame.xml"
adb shell restorecon -F "/data/data/$PKG/shared_prefs/MonkeyGame.xml" >/dev/null 2>&1 || true

diag_loaded=0
for diag_start in 1 2; do
  diag_mainmenu=0
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  clear_log
  rm -f "$OUT/runtime-fatal-logcat.txt"
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
  for diag_attempt in $(seq 1 30); do
    if ! fatal_check; then
      if [ -s "$OUT/runtime-fatal-logcat.txt" ]; then
        cp "$OUT/runtime-fatal-logcat.txt" "$OUT/diagnostic-seed-start-${diag_start}-fatal.txt" 2>/dev/null || true
        rm -f "$OUT/runtime-fatal-logcat.txt"
      fi
      echo "diagnostic seed start $diag_start crashed; controlled process restart" >> "$FLOW"
      break
    fi
    adb logcat -d -v brief > "$WORK/diagnostic-seed-load.txt" 2>/dev/null || true
    if grep -q 'LoadCareer saveslot: 0' "$WORK/diagnostic-seed-load.txt" \
       && grep -qiE 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' "$WORK/diagnostic-seed-load.txt"; then
      diag_loaded=1
      echo "diagnostic seed auto-load reached GameMenu on start $diag_start" >> "$FLOW"
      break
    fi
    if grep -qiE 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' "$WORK/diagnostic-seed-load.txt"; then
      diag_mainmenu=1
    fi
    sleep 1
  done
  [ "$diag_loaded" -eq 1 ] && break
  if [ "$diag_mainmenu" -eq 1 ]; then
    echo 'diagnostic seed auto-load not observed; using stock SaveSlot fallback' >> "$FLOW"
    open_slot0 diagnostic-seed
    load_existing diagnostic-seed
    diag_loaded=1
    break
  fi
  sleep 3
done
[ "$diag_loaded" -eq 1 ] || {
  cp "$WORK/diagnostic-seed-load.txt" "$OUT/diagnostic-seed-load-timeout.txt" 2>/dev/null || true
  shot diagnostic-seed-load-timeout
  exit 232
}

capture_log "diagnostic verified natural cycle ${DIAG_START_CYCLE} seed -> GameMenu"
dump_save natural-baseline
checkpoint natural-baseline
fatal_check
rm -f "$WORK/natural-fullres-ready.png"
timeout 8s adb exec-out screencap -p > "$WORK/natural-fullres-ready.png" 2>/dev/null || true
python3 stage4_tools/validate_frame_png.py "$WORK/natural-fullres-ready.png" >> "$FLOW" 2>&1 || exit 233
cp "$WORK/natural-fullres-ready.png" "$OUT/natural-fullres-ready.png"
BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES="$DIAG_START_CYCLE"'''

FINAL_NEW = r'''for setup_n in 1 2 3 4; do
  grep -q "NewSeasonSetUp${setup_n}" "$FLOW" || {
    echo "diagnostic missing NewSeasonSetUp${setup_n}" >> "$FLOW"
    exit 234
  }
done
python3 - "$OUT/post-season.json" "$OUT/post-season-restart.json" "$OUT/seasonend-diagnostic.json" "$DIAG_START_CYCLE" <<'PY'
import json,sys
from pathlib import Path
post_path,restart_path,out_path=map(Path,sys.argv[1:4])
seed_cycle=int(sys.argv[4])
post=json.loads(post_path.read_text(encoding='utf-8'))
restart=json.loads(restart_path.read_text(encoding='utf-8'))
fields=[
    'sdate','clubnationid','clubid','fullname','shortname','careerapps',
    'goalbonus','wage','lastnegotiations','lasttransferdate',
    'playerrecordsha256','clubrecordsha256','competitionrecordsha256',
    'additionalclubrecordsha256',
]
mismatches={k:{'post':post.get(k),'restart':restart.get(k)} for k in fields if post.get(k)!=restart.get(k)}
result={'diagnostic_only':True,'seed':f'verified-natural-cycle-{seed_cycle}','stable_fields':fields,'mismatches':mismatches,'restart_equal':not mismatches}
out_path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
if mismatches:
    print('STAGE4_SEASONEND_DIAGNOSTIC_RESTART_MISMATCH')
    raise SystemExit(1)
print('STAGE4_SEASONEND_DIAGNOSTIC_PASS')
PY
'''


def harden(text: str) -> str:
    boot_matches=list(BOOT_RE.finditer(text))
    if len(boot_matches)!=1:
        raise SystemExit(f'expected one natural bootstrap span, found {len(boot_matches)}')
    text=BOOT_RE.sub(BOOT_NEW,text,count=1)
    if text.count(LOOP_OLD)!=1:
        raise SystemExit(f'expected one natural cycle loop, found {text.count(LOOP_OLD)}')
    text=text.replace(LOOP_OLD,'for cycle in $(seq $((DIAG_START_CYCLE + 1)) "$MAX_MATCH_CYCLES"); do',1)
    final_matches=list(FINAL_RE.finditer(text))
    if len(final_matches)!=1:
        raise SystemExit(f'expected one final Stage4 verifier block, found {len(final_matches)}')
    text=FINAL_RE.sub(lambda _: FINAL_NEW,text,count=1)
    if 'STAGE4_NATURAL_SEASON_PASS' in FINAL_NEW:
        raise SystemExit('diagnostic must never emit final natural PASS marker')
    return text


def main() -> None:
    if len(sys.argv)!=3:
        raise SystemExit('usage: prepare_stage4_seed_continuation.py INPUT_GATE OUTPUT_GATE')
    src,dst=map(Path,sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')),encoding='utf-8')
    print(f'Applied diagnostic-only verified natural seed continuation: {dst}')


if __name__=='__main__':
    main()
