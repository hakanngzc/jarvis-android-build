#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

BOOT_RE = re.compile(
    r'''(?ms)^start_game fresh;.*?^START_EPOCH="\$\(date \+%s\)"; SEASON_SEEN=0; CYCLES=0$'''
)

SEED_BLOCK = r'''# DIAGNOSTIC ONLY: resume from run #290's real natural cycle-14 save.
# This branch/result must never count as the fresh Stage4 natural-season proof.
SEED_XML="${STAGE4_DIAGNOSTIC_SEED_XML:?missing cycle14 seed xml}"
echo 'STAGE4_DIAGNOSTIC_SEEDED_CYCLE14=1' | tee "$OUT/STAGE4_DIAGNOSTIC_SEEDED_CYCLE14.txt"
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
uid="$(adb shell dumpsys package "$PKG" 2>/dev/null | tr -d '\r' | sed -n 's/.*userId=\([0-9][0-9]*\).*/\1/p' | head -1)"
[[ "${uid:-}" =~ ^[0-9]+$ ]] || { echo 'diagnostic package uid unavailable'; exit 230; }
adb push "$SEED_XML" /data/local/tmp/stage4-cycle14.xml >/dev/null
adb shell "mkdir -p '/data/data/$PKG/shared_prefs'; cat /data/local/tmp/stage4-cycle14.xml > '/data/data/$PKG/shared_prefs/MonkeyGame.xml'; chown $uid:$uid '/data/data/$PKG/shared_prefs/MonkeyGame.xml'; chmod 660 '/data/data/$PKG/shared_prefs/MonkeyGame.xml'; rm -f /data/local/tmp/stage4-cycle14.xml" >/dev/null

clear_log
adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
autoload=0
mainmenu_seen=0
for seed_attempt in $(seq 1 30); do
  fatal_check || exit 231
  adb logcat -d -v brief > "$WORK/diagnostic-seed-state.txt" 2>/dev/null || true
  if grep -q 'LoadCareer saveslot: 0' "$WORK/diagnostic-seed-state.txt" \
     && grep -qiE 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' "$WORK/diagnostic-seed-state.txt"; then
    autoload=1
    break
  fi
  if grep -qiE 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' "$WORK/diagnostic-seed-state.txt"; then
    mainmenu_seen=1
    break
  fi
  sleep 1
done
if [ "$autoload" -eq 1 ]; then
  echo 'diagnostic cycle14 seed auto-load reached GameMenu' >> "$FLOW"
elif [ "$mainmenu_seen" -eq 1 ]; then
  echo 'diagnostic cycle14 seed reached MainMenu; using stock SaveSlot load' >> "$FLOW"
  open_slot0 diagnostic-cycle14
  load_existing diagnostic-cycle14
else
  cp "$WORK/diagnostic-seed-state.txt" "$OUT/diagnostic-seed-load-timeout.txt" 2>/dev/null || true
  shot diagnostic-seed-load-timeout
  exit 232
fi
fatal_check
capture_log 'diagnostic real cycle14 save -> GameMenu'
dump_save natural-baseline; checkpoint natural-baseline

# Preserve the same post-baseline marker discipline as the fresh gate.
BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
rm -f "$WORK/natural-fullres-ready.png"
timeout 8s adb exec-out screencap -p > "$WORK/natural-fullres-ready.png" 2>/dev/null || true
python3 stage4_tools/validate_frame_png.py "$WORK/natural-fullres-ready.png" >> "$FLOW" 2>&1 || exit 233
cp "$WORK/natural-fullres-ready.png" "$OUT/natural-fullres-ready.png"
test -n "$(adb shell pidof "$PKG" | tr -d '\r' || true)" || exit 234
capture_log 'diagnostic cycle14 full-resolution Career -> GameMenu'
BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''

FINAL_OLD = '''python3 stage4_tools/verify_stage4_natural_season.py --base "$OUT/natural-baseline.json" --post "$OUT/post-season.json" --restart "$OUT/post-season-restart.json" --meta "$OUT/natural-meta.json" --out "$OUT/natural-verdict.json" | tee "$OUT/STAGE4_NATURAL_SEASON_RESULT.txt"
grep -q 'STAGE4_NATURAL_SEASON_PASS' "$OUT/STAGE4_NATURAL_SEASON_RESULT.txt"
echo 'STAGE4_NATURAL_SEASON_PASS' '''.rstrip()

FINAL_NEW = '''python3 stage4_tools/verify_stage4_natural_season.py --base "$OUT/natural-baseline.json" --post "$OUT/post-season.json" --restart "$OUT/post-season-restart.json" --meta "$OUT/natural-meta.json" --out "$OUT/diagnostic-verdict.json" > "$OUT/diagnostic-verifier-raw.txt"
grep -q 'STAGE4_NATURAL_SEASON_PASS' "$OUT/diagnostic-verifier-raw.txt"
echo 'STAGE4_DIAGNOSTIC_RESUME_PASS' | tee "$OUT/STAGE4_DIAGNOSTIC_RESUME_RESULT.txt"'''


def harden(text: str) -> str:
    matches = list(BOOT_RE.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f'expected one fresh bootstrap-to-start block, found {len(matches)}')
    text = BOOT_RE.sub(lambda _m: SEED_BLOCK, text, count=1)
    if text.count(FINAL_OLD) != 1:
        raise SystemExit(f'expected one final natural verdict block, found {text.count(FINAL_OLD)}')
    text = text.replace(FINAL_OLD, FINAL_NEW, 1)
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_cycle14_resume_diagnostic.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied DIAGNOSTIC-ONLY real cycle14 resume: {dst}')


if __name__ == '__main__':
    main()
