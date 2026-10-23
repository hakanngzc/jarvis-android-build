#!/usr/bin/env python3
from pathlib import Path

src = Path('stage1_public/runtime_gate.sh')
out = Path('stage1_public/runtime_gate_v2.sh')
s = src.read_text()

old = '''sign_one(){
  local src="$1" dst="$2" aligned="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$aligned"
'''
new = '''sign_one(){
  local src="$1"
  local dst="$2"
  local aligned="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$aligned"
'''
if old not in s:
    raise SystemExit('sign_one patch anchor missing')
s = s.replace(old, new, 1)

anchor = '''wait_main_or_load(){
  wait_log 'Create Screen:[[:space:]]*mainmenu|Create Screen:mainmenu|LoadCareer saveslot:[[:space:]]*[0-2]' 150 'MainMenu or DirectCareerLoad'
}
'''
insert = anchor + r'''

CAREER_PROBE_N=0
press_career_when_ready(){
  local i target="$WORK/career-target.txt" png="$WORK/career-probe.png" x y
  CAREER_PROBE_N=$((CAREER_PROBE_N+1))
  for i in $(seq 1 45); do
    fatal_check || return 1
    adb exec-out screencap -p > "$png" 2>/dev/null || true
    if python3 "$ROOT/stage1_public/detect_stock_play.py" "$png" "$target"; then
      read -r x y < "$target"
      cp "$png" "$OUT/career-ready-${CAREER_PROBE_N}.png"
      printf 'career_probe_%s=%s,%s\n' "$CAREER_PROBE_N" "$x" "$y" | tee -a "$SUMMARY"
      press "$x" "$y" 3
      return 0
    fi
    sleep 2
  done
  cp "$png" "$OUT/career-not-rendered-${CAREER_PROBE_N}.png" 2>/dev/null || true
  echo 'Rendered stock Career/Play button was not detected'
  return 1
}
'''
if s.count(anchor) != 1:
    raise SystemExit(f'wait_main anchor count={s.count(anchor)}')
s = s.replace(anchor, insert, 1)

old_press = 'press "$CAREER_X" "$CAREER_Y" 3'
count = s.count(old_press)
if count != 3:
    raise SystemExit(f'expected 3 Career fixed taps, got {count}')
s = s.replace(old_press, 'press_career_when_ready')

out.write_text(s)
print(f'RUNTIME_GATE_V2_PATCHED=PASS career_taps={count}')
