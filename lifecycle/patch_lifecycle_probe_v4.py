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

  # Crash markers are never ignored.
  if grep -qE 'Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt"; then
    cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" || true
    echo 'NSS-owned crash/ANR detected'
    return 1
  fi

  # API29 AOSP images have no Play Services. NSS 4.31's legacy measurement
  # service can therefore ANR even while the game's own process/UI remains
  # healthy. Ignore only that exact service-only ANR; every other NSS ANR
  # remains fail-closed.
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
GL_DRIVER_REPLACEMENT = '''python3 tools/patch_trial_skip_for_persistence_test.py "$WORK/base-cloud-probe.apk" "$WORK/base-career-probe-pre-gl.apk"
python3 lifecycle/patch_gl_resume_race.py "$WORK/base-career-probe-pre-gl.apk" "$WORK/base-career-probe.apk" \\
  --evidence "$OUT/LIFECYCLE_GL_RESUME_PATCH.json" | tee "$OUT/LIFECYCLE_GL_RESUME_PATCH.txt"'''

CAREER_ROUNDTRIP_ANCHOR = 'shot career-gamemenu\nlifecycle_background_roundtrip career'
CAREER_ROUNDTRIP_REPLACEMENT = '''shot career-gamemenu
for lifecycle_cycle in 1 2 3 4 5; do
  lifecycle_background_roundtrip "career-${lifecycle_cycle}"
done'''

HIERARCHY_REPLACEMENT = r'''  adb shell uiautomator dump /sdcard/nss-recents.xml >/dev/null 2>&1 || true
  adb shell cat /sdcard/nss-recents.xml > "$OUT/lifecycle-${tag}-recents-ui.xml" 2>/dev/null || true
  python3 - "$OUT/lifecycle-${tag}-recents-ui.xml" "$WORK/lifecycle-${tag}-recents-target.txt" <<'PY'
import re,sys,xml.etree.ElementTree as ET
from pathlib import Path
src,dst=sys.argv[1:]
try:
    root=ET.parse(src).getroot()
except Exception as e:
    raise SystemExit(f'cannot parse Recents UI hierarchy: {e}')

def bounds(node):
    m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',node.attrib.get('bounds',''))
    if not m:
        return None
    x1,y1,x2,y2=map(int,m.groups())
    if x2<=x1 or y2<=y1:
        return None
    return x1,y1,x2,y2

def center(node):
    b=bounds(node)
    if not b:
        return None
    x1,y1,x2,y2=b
    return (x1+x2)//2,(y1+y2)//2,(x2-x1)*(y2-y1),node.attrib.get('bounds','')

terms=('new star soccer','newstarsoccer')
named=[]
for node in root.iter('node'):
    attrs=node.attrib
    hay=' '.join((attrs.get('text',''),attrs.get('content-desc',''),attrs.get('resource-id',''),attrs.get('package',''))).lower()
    c=center(node)
    if c and any(t in hay for t in terms):
        named.append((*c,hay))

source='named'
candidates=named
if not candidates:
    # Android 14 launcher can expose task cards without app text/content-desc.
    # Fail closed unless there is exactly one structural task card: a clickable
    # FrameLayout directly under overview_panel containing a snapshot node.
    cards=[]
    for overview in root.iter('node'):
        if not overview.attrib.get('resource-id','').endswith('/overview_panel'):
            continue
        for child in list(overview):
            attrs=child.attrib
            if attrs.get('class')!='android.widget.FrameLayout' or attrs.get('clickable')!='true':
                continue
            has_snapshot=any(n.attrib.get('resource-id','').endswith('/snapshot') for n in child.iter('node'))
            c=center(child)
            if has_snapshot and c:
                cards.append((*c,'structural-task-card'))
    if len(cards)==1:
        candidates=cards
        source='unique-structural-task-card'
    elif len(cards)>1:
        raise SystemExit(f'multiple unlabeled Recents task cards ({len(cards)}); refusing to guess NSS target')
    else:
        raise SystemExit('no named or structural Recents task card found')

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
    count = text.count(CENTER_ANCHOR)
    if count != 1:
        raise ValueError(f'expected one Recents center-tap anchor, found {count}')
    text = text.replace(CENTER_ANCHOR, HIERARCHY_REPLACEMENT, 1)
    play_count = text.count(PLAY_EDGE_ANCHOR)
    if play_count > 1:
        raise ValueError(f'expected at most one play-button edge anchor, found {play_count}')
    if play_count == 1:
        text = text.replace(PLAY_EDGE_ANCHOR, PLAY_CENTER_REPLACEMENT, 1)
    return text


def harden_fatal_check(text: str) -> str:
    count = text.count(FATAL_ANCHOR)
    if count != 1:
        raise ValueError(f'expected one fatal_check anchor, found {count}')
    return text.replace(FATAL_ANCHOR, FATAL_REPLACEMENT, 1)


def inject_gl_resume_patch(text: str) -> str:
    count = text.count(GL_DRIVER_ANCHOR)
    if count != 1:
        raise ValueError(f'expected one GL driver anchor, found {count}')
    return text.replace(GL_DRIVER_ANCHOR, GL_DRIVER_REPLACEMENT, 1)


def inject_stress_roundtrips(text: str) -> str:
    count = text.count(CAREER_ROUNDTRIP_ANCHOR)
    if count != 1:
        raise ValueError(f'expected one Career roundtrip anchor, found {count}')
    return text.replace(CAREER_ROUNDTRIP_ANCHOR, CAREER_ROUNDTRIP_REPLACEMENT, 1)


def patch_script(text: str) -> str:
    generated = v3_patch_script(text)
    generated = harden_generated_script(generated)
    generated = harden_fatal_check(generated)
    generated = inject_gl_resume_patch(generated)
    generated = inject_stress_roundtrips(generated)
    return generated


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: patch_lifecycle_probe_v4.py INPUT_SH OUTPUT_SH')
    src,dst=map(Path,sys.argv[1:])
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(patch_script(src.read_text(encoding='utf-8')),encoding='utf-8')
    dst.chmod(0o755)
    print(f'patched lifecycle probe v4: {src} -> {dst}')


if __name__=='__main__':
    main()
