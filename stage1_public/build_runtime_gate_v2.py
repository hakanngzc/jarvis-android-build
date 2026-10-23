#!/usr/bin/env python3
from pathlib import Path

src=Path('stage1_public/runtime_gate.sh')
out=Path('stage1_public/runtime_gate_v2.sh')
s=src.read_text()

old='''sign_one(){
  local src="$1" dst="$2" aligned="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$aligned"
'''
new='''sign_one(){
  local src="$1"
  local dst="$2"
  local aligned="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$aligned"
'''
if old not in s: raise SystemExit('sign_one patch anchor missing')
s=s.replace(old,new,1)

old_hook='''python3 "$ROOT/stage1_public/patch_career_test_hook.py" "$BASE" "$WORK/base-hook.apk" | tee "$OUT/career-hook.txt"

python3 - "$WORK/base-hook.apk" "$WORK/base-test-unsigned.apk" "$WORK/onboardingmain.uih" "$WORK/consent.uih" <<'PY'
'''
new_hook='''python3 "$ROOT/stage1_public/patch_career_test_hook.py" "$BASE" "$WORK/base-hook.apk" | tee "$OUT/career-hook.txt"
python3 "$ROOT/stage1_public/patch_cloud_startup_bypass_for_persistence_test.py" \
  "$WORK/base-hook.apk" "$WORK/base-hook-cloud.apk" | tee "$OUT/cloud-harness.txt"

python3 - "$WORK/base-hook-cloud.apk" "$WORK/base-test-unsigned.apk" "$WORK/onboardingmain.uih" "$WORK/consent.uih" <<'PY'
'''
if old_hook not in s: raise SystemExit('cloud harness insertion anchor missing')
s=s.replace(old_hook,new_hook,1)

anchor='''wait_main_or_load(){
  wait_log 'Create Screen:[[:space:]]*mainmenu|Create Screen:mainmenu|LoadCareer saveslot:[[:space:]]*[0-2]' 150 'MainMenu or DirectCareerLoad'
}
'''
insert=anchor+r'''

CAREER_PROBE_N=0
press_career_when_ready(){
  local i target="$WORK/career-target.txt" png="$WORK/career-probe.png" x y
  CAREER_PROBE_N=$((CAREER_PROBE_N+1))
  for i in $(seq 1 45); do
    fatal_check || return 1
    adb exec-out screencap -p > "$png" 2>/dev/null || true
    if python3 - "$png" "$target" <<'PY'
from PIL import Image
import sys
im=Image.open(sys.argv[1]).convert('RGB'); w,h=im.size
x0,x1=int(w*.05),int(w*.75); y0,y1=int(h*.30),int(h*.70)
def green(p):
    r,g,b=p
    return g>=90 and g-r>=25 and g-b>=20 and g>=r*1.12
rows=[]
for y in range(y0,y1,2):
    hits=sum(green(im.getpixel((x,y))) for x in range(x0,x1,3))
    if hits>=max(16,int((x1-x0)/3*.07)): rows.append(y)
if not rows: raise SystemExit(1)
groups=[]
for y in rows:
    if not groups or y-groups[-1][-1]>4: groups.append([y])
    else: groups[-1].append(y)
groups=[g for g in groups if g[-1]-g[0]>=18]
if not groups: raise SystemExit(1)
# Career is the upper large green menu button. Prefer the first substantial band.
g=sorted(groups,key=lambda a:a[0])[0]
ya,yb=g[0],g[-1]
pts=[]
for y in range(ya,yb+1,3):
    for x in range(x0,x1,3):
        if green(im.getpixel((x,y))): pts.append((x,y))
if len(pts)<80: raise SystemExit(1)
xs=sorted(p[0] for p in pts); ys=sorted(p[1] for p in pts)
x=xs[len(xs)//2]; y=ys[len(ys)//2]
open(sys.argv[2],'w').write(f'{x} {y}\n')
print('career_green_target',x,y,'band',ya,yb,'points',len(pts))
PY
    then
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
if s.count(anchor)!=1: raise SystemExit(f'wait_main anchor count={s.count(anchor)}')
s=s.replace(anchor,insert,1)

old_press='press "$CAREER_X" "$CAREER_Y" 3'
count=s.count(old_press)
if count != 3: raise SystemExit(f'expected 3 Career fixed taps, got {count}')
s=s.replace(old_press,'press_career_when_ready')

out.write_text(s)
print(f'RUNTIME_GATE_V2_PATCHED=PASS career_taps={count} cloud_harness=enabled')
