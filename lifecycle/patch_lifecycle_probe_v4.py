#!/usr/bin/env python3
import sys
from pathlib import Path

from patch_lifecycle_probe_v3 import patch_script as v3_patch_script

CENTER_ANCHOR = r'''  size="$(adb shell wm size 2>/dev/null | tr -d '\r' | grep -Eo '[0-9]+x[0-9]+' | tail -1 || true)"
  [ -n "$size" ] || { echo "could not read display size for Recents ($tag)"; return 1; }
  w="${size%x*}"; h="${size#*x}"; x=$((w/2)); y=$((h/2))
  adb shell input tap "$x" "$y" >/dev/null 2>&1 || true
  sleep 4'''

FATAL_ANCHOR = r'''fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  if grep -qE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt"; then
    cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" || true
    echo 'NSS-owned crash/ANR detected'
    return 1
  fi
}'''

FATAL_REPLACEMENT = r'''fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  if grep -qE 'Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt"; then
    cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" || true
    echo 'NSS-owned crash/ANR detected'
    return 1
  fi
  local anr_count measurement_count
  anr_count="$(grep -cE 'ANR in com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt" || true)"
  measurement_count="$(grep -cE 'Reason: executing service com\.newstargames\.newstarsoccer/com\.google\.android\.gms\.measurement\.AppMeasurementService' "$WORK/live-logcat.txt" || true)"
  if [ "$anr_count" -gt 0 ]; then
    if [ "$anr_count" -eq "$measurement_count" ]; then
      cp "$WORK/live-logcat.txt" "$OUT/runtime-ignored-appmeasurement-anr.txt" || true
      echo 'Ignoring AppMeasurementService-only emulator ANR'
      return 0
    fi
    cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" || true
    echo 'NSS-owned crash/ANR detected'
    return 1
  fi
}'''

PLAY_EDGE_ANCHOR = 'press_play(){ local x y; read -r x y < <(logical_xy 553 829); press_physical "$x" "$y" "${1:-2}"; }'
PLAY_CENTER_REPLACEMENT = 'press_play(){ local x y; read -r x y < <(logical_xy 553 900); press_physical "$x" "$y" "${1:-2}"; }'

GL_DRIVER_ANCHOR = 'python3 tools/patch_trial_skip_for_persistence_test.py "$WORK/base-cloud-probe.apk" "$WORK/base-career-probe.apk"'
GL_DRIVER_REPLACEMENT = r'''python3 tools/patch_trial_skip_for_persistence_test.py "$WORK/base-cloud-probe.apk" "$WORK/base-career-probe-stock.apk"
python3 lifecycle/patch_gl_resume_race.py \
  "$WORK/base-career-probe-stock.apk" "$WORK/base-career-probe.apk" \
  --evidence "$OUT/LIFECYCLE_GL_RESUME_PATCH.json" \
  | tee "$OUT/LIFECYCLE_GL_RESUME_PATCH.txt"'''

CAREER_ROUNDTRIP_ANCHOR = 'shot career-gamemenu\nlifecycle_background_roundtrip career'
CAREER_ROUNDTRIP_REPLACEMENT = '''shot career-gamemenu
for lifecycle_cycle in 1 2 3 4 5; do
  lifecycle_background_roundtrip "career-${lifecycle_cycle}"
done'''

RENDER_ROUNDTRIP_ANCHOR = '''  foreground_from_recents "$tag" || return 1
  after="$(pid_one)"'''

RENDER_HELPER = r'''assert_game_rendered(){
  local tag="$1" attempt png metrics
  metrics="$OUT/lifecycle-${tag}-render-metrics.txt"
  : > "$metrics"
  for attempt in 1 2 3 4 5; do
    png="$OUT/lifecycle-${tag}-render-attempt-${attempt}.png"
    adb exec-out screencap -p > "$png" 2>/dev/null || true
    if python3 - "$png" "$metrics" "$attempt" <<'PY'
from PIL import Image
from pathlib import Path
import sys
src,metric,attempt=sys.argv[1:]
try:
    im=Image.open(src).convert('RGB')
except Exception as e:
    with open(metric,'a',encoding='utf-8') as f: f.write(f'attempt={attempt} decode_error={e}\n')
    raise SystemExit(1)
w,h=im.size
box=(max(0,int(w*.05)),max(0,int(h*.06)),min(w,int(w*.95)),min(h,int(h*.86)))
crop=im.crop(box).resize((128,128))
pixels=list(crop.getdata())
nonblack=sum(1 for p in pixels if max(p)>24)/len(pixels)
mean=sum(sum(p)/3 for p in pixels)/len(pixels)
with open(metric,'a',encoding='utf-8') as f:
    f.write(f'attempt={attempt} nonblack_fraction={nonblack:.6f} mean_luma={mean:.3f}\n')
raise SystemExit(0 if nonblack>=0.10 and mean>=8.0 else 1)
PY
    then
      lifecycle_record "${tag}_render_visible" PASS
      echo "Visible NSS frame after resume ($tag), attempt $attempt"
      return 0
    fi
    sleep 1
  done
  lifecycle_record "${tag}_render_visible" FAIL
  echo "NSS foregrounded but game viewport stayed black ($tag)"
  return 1
}

'''

NAV_ANCHOR = r'''# Drive normal stock UI to the next playable match.
state=gamemenu
MATCH_REACHED=0
for step in $(seq 1 32); do
  clear_log
  case "$state" in
    gamemenu|leaguefixtures|league) press_play 3 ;;
    message) press_message_accept 3 ;;
    match) MATCH_REACHED=1; break ;;
    *) sleep 2 ;;
  esac
  state="$(wait_state 'match message leaguefixtures league gamemenu' 25 || true)"
  {
    echo "step=$step state=$state"
    adb logcat -d -v brief 2>/dev/null || true
  } >> "$OUT/navigation.log"
  if [ "$state" = match ]; then MATCH_REACHED=1; break; fi
done
[ "$MATCH_REACHED" -eq 1 ] || { echo 'No playable Career match reached'; shot no-match; exit 203; }'''

NAV_REPLACEMENT = r'''# Drive normal stock UI to the next playable match. Preserve the last known
# screen when a single emulator touch is dropped; retry that same action only
# within a strict budget instead of falling into a long unknown-state loop.
state=gamemenu
last_known=gamemenu
unknown_retries=0
MATCH_REACHED=0
for step in $(seq 1 32); do
  if [ "$state" = unknown ]; then state="$last_known"; fi
  clear_log
  case "$state" in
    gamemenu|leaguefixtures|league) press_play 3 ;;
    message) press_message_accept 3 ;;
    match) MATCH_REACHED=1; break ;;
    *) echo "unexpected navigation state=$state"; sleep 1 ;;
  esac
  next_state="$(wait_state 'match message leaguefixtures league gamemenu' 10 || true)"
  fatal_check
  {
    echo "step=$step state=$state next_state=$next_state last_known=$last_known unknown_retries=$unknown_retries"
    adb logcat -d -v brief 2>/dev/null || true
  } >> "$OUT/navigation.log"
  if [ "$next_state" = match ]; then state=match; last_known=match; MATCH_REACHED=1; break; fi
  if [ "$next_state" = unknown ]; then
    unknown_retries=$((unknown_retries+1))
    if [ "$unknown_retries" -le 3 ]; then
      state="$last_known"
      shot "navigation-${last_known}-retry-${unknown_retries}"
      continue
    fi
    echo "navigation touch/state retry budget exhausted at $last_known"
    shot navigation-retry-exhausted
    exit 203
  fi
  unknown_retries=0
  state="$next_state"
  last_known="$next_state"
done
[ "$MATCH_REACHED" -eq 1 ] || { echo 'No playable Career match reached'; shot no-match; exit 203; }'''

HIERARCHY_REPLACEMENT = r'''  adb shell uiautomator dump /sdcard/nss-recents.xml >/dev/null 2>&1 || true
  adb shell cat /sdcard/nss-recents.xml > "$OUT/lifecycle-${tag}-recents-ui.xml" 2>/dev/null || true
  python3 - "$OUT/lifecycle-${tag}-recents-ui.xml" "$WORK/lifecycle-${tag}-recents-target.txt" <<'PY'
import re,sys,xml.etree.ElementTree as ET
from pathlib import Path
src,dst=sys.argv[1:]
try: root=ET.parse(src).getroot()
except Exception as e: raise SystemExit(f'cannot parse Recents UI hierarchy: {e}')
def bounds(node):
    m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',node.attrib.get('bounds',''))
    if not m:return None
    x1,y1,x2,y2=map(int,m.groups())
    return None if x2<=x1 or y2<=y1 else (x1,y1,x2,y2)
def center(node):
    b=bounds(node)
    if not b:return None
    x1,y1,x2,y2=b
    return (x1+x2)//2,(y1+y2)//2,(x2-x1)*(y2-y1),node.attrib.get('bounds','')
terms=('new star soccer','newstarsoccer'); named=[]
for node in root.iter('node'):
    attrs=node.attrib
    hay=' '.join((attrs.get('text',''),attrs.get('content-desc',''),attrs.get('resource-id',''),attrs.get('package',''))).lower()
    c=center(node)
    if c and any(t in hay for t in terms):named.append((*c,hay))
source='named'; candidates=named
if not candidates:
    cards=[]
    for overview in root.iter('node'):
        if not overview.attrib.get('resource-id','').endswith('/overview_panel'):continue
        for child in list(overview):
            attrs=child.attrib
            if attrs.get('class')!='android.widget.FrameLayout' or attrs.get('clickable')!='true':continue
            has_snapshot=any(n.attrib.get('resource-id','').endswith('/snapshot') for n in child.iter('node'))
            c=center(child)
            if has_snapshot and c:cards.append((*c,'structural-task-card'))
    if len(cards)==1:candidates=cards; source='unique-structural-task-card'
    elif len(cards)>1:raise SystemExit(f'multiple unlabeled Recents task cards ({len(cards)}); refusing to guess NSS target')
    else:raise SystemExit('no named or structural Recents task card found')
candidates.sort(key=lambda x:x[2],reverse=True)
x,y,area,bound,hay=candidates[0]
Path(dst).write_text(f'{x} {y}\n',encoding='utf-8')
print('recents_nss_target',source,x,y,bound,hay)
PY
  if [ ! -s "$WORK/lifecycle-${tag}-recents-target.txt" ]; then
    shot "lifecycle-${tag}-recents-target-missing"
    lifecycle_record "${tag}_recents_target_found" FAIL
    echo "NSS task target not found unambiguously in Recents ($tag)"
    return 1
  fi
  read -r x y < "$WORK/lifecycle-${tag}-recents-target.txt"
  lifecycle_record "${tag}_recents_target_found" PASS
  local recents_attempt
  for recents_attempt in 1 2 3; do
    adb shell input tap "$x" "$y" >/dev/null 2>&1 || true
    sleep 2
    adb shell dumpsys activity activities > "$WORK/lifecycle-${tag}-recents-attempt-${recents_attempt}.txt" 2>/dev/null || true
    if grep -qE 'ResumedActivity.*com\.newstargames\.newstarsoccer.*MonkeyGame|mResumedActivity.*com\.newstargames\.newstarsoccer.*MonkeyGame|topResumedActivity=.*com\.newstargames\.newstarsoccer.*MonkeyGame' "$WORK/lifecycle-${tag}-recents-attempt-${recents_attempt}.txt"; then
      echo "NSS foregrounded from verified Recents target on attempt $recents_attempt"
      break
    fi
  done
  sleep 1'''


def harden_generated_script(text: str) -> str:
    count=text.count(CENTER_ANCHOR)
    if count!=1:raise ValueError(f'expected one Recents center-tap anchor, found {count}')
    text=text.replace(CENTER_ANCHOR,HIERARCHY_REPLACEMENT,1)
    play_count=text.count(PLAY_EDGE_ANCHOR)
    if play_count>1:raise ValueError(f'expected at most one play-button edge anchor, found {play_count}')
    if play_count==1:text=text.replace(PLAY_EDGE_ANCHOR,PLAY_CENTER_REPLACEMENT,1)
    return text

def harden_fatal_check(text: str) -> str:
    count=text.count(FATAL_ANCHOR)
    if count!=1:raise ValueError(f'expected one fatal_check anchor, found {count}')
    return text.replace(FATAL_ANCHOR,FATAL_REPLACEMENT,1)

def inject_gl_resume_order_patch(text: str) -> str:
    count=text.count(GL_DRIVER_ANCHOR)
    if count!=1:raise ValueError(f'expected one GL driver anchor, found {count}')
    return text.replace(GL_DRIVER_ANCHOR,GL_DRIVER_REPLACEMENT,1)

def inject_stress_roundtrips(text: str) -> str:
    count=text.count(CAREER_ROUNDTRIP_ANCHOR)
    if count!=1:raise ValueError(f'expected one Career roundtrip anchor, found {count}')
    return text.replace(CAREER_ROUNDTRIP_ANCHOR,CAREER_ROUNDTRIP_REPLACEMENT,1)

def inject_render_gate(text: str) -> str:
    helper_anchor='foreground_from_recents(){'
    if text.count(helper_anchor)!=1:raise ValueError(f'expected one foreground helper anchor, found {text.count(helper_anchor)}')
    text=text.replace(helper_anchor,RENDER_HELPER+helper_anchor,1)
    if text.count(RENDER_ROUNDTRIP_ANCHOR)!=1:raise ValueError(f'expected one render roundtrip anchor, found {text.count(RENDER_ROUNDTRIP_ANCHOR)}')
    replacement='''  foreground_from_recents "$tag" || return 1\n  assert_game_rendered "$tag" || return 1\n  after="$(pid_one)"'''
    return text.replace(RENDER_ROUNDTRIP_ANCHOR,replacement,1)

def retarget_activity_launches(text: str) -> str:
    if text.count('$PKG/.MonkeyGame')<1:raise ValueError('expected at least one MonkeyGame launch')
    text=text.replace('$PKG/.MonkeyGame','$PKG/.RebornGame')
    text=text.replace('newstarsoccer.*MonkeyGame','newstarsoccer.*RebornGame')
    return text

def harden_match_navigation(text: str) -> str:
    count=text.count(NAV_ANCHOR)
    if count!=1:raise ValueError(f'expected one match navigation anchor, found {count}')
    return text.replace(NAV_ANCHOR,NAV_REPLACEMENT,1)

def patch_script(text: str) -> str:
    generated=v3_patch_script(text)
    generated=harden_generated_script(generated)
    generated=harden_fatal_check(generated)
    generated=inject_gl_resume_order_patch(generated)
    generated=inject_stress_roundtrips(generated)
    generated=harden_match_navigation(generated)
    generated=inject_render_gate(generated)
    return generated

def main() -> None:
    if len(sys.argv)!=3:raise SystemExit('usage: patch_lifecycle_probe_v4.py INPUT_SH OUTPUT_SH')
    src,dst=map(Path,sys.argv[1:]); dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(patch_script(src.read_text(encoding='utf-8')),encoding='utf-8'); dst.chmod(0o755)
    print(f'patched lifecycle probe v4: {src} -> {dst}')

if __name__=='__main__':main()