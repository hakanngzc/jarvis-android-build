#!/usr/bin/env python3
import sys
from pathlib import Path

from patch_lifecycle_probe_v3 import patch_script as v3_patch_script

CENTER_ANCHOR = r'''  size="$(adb shell wm size 2>/dev/null | tr -d '\r' | grep -Eo '[0-9]+x[0-9]+' | tail -1 || true)"
  [ -n "$size" ] || { echo "could not read display size for Recents ($tag)"; return 1; }
  w="${size%x*}"; h="${size#*x}"; x=$((w/2)); y=$((h/2))
  adb shell input tap "$x" "$y" >/dev/null 2>&1 || true
  sleep 4'''

HIERARCHY_REPLACEMENT = r'''  adb shell uiautomator dump /sdcard/nss-recents.xml >/dev/null 2>&1 || true
  adb shell cat /sdcard/nss-recents.xml > "$OUT/lifecycle-${tag}-recents-ui.xml" 2>/dev/null || true
  python3 - "$OUT/lifecycle-${tag}-recents-ui.xml" "$WORK/lifecycle-${tag}-recents-target.txt" <<'PY'
import re,sys,xml.etree.ElementTree as ET
src,dst=sys.argv[1:]
try:
    root=ET.parse(src).getroot()
except Exception as e:
    raise SystemExit(f'cannot parse Recents UI hierarchy: {e}')
terms=('new star soccer','newstarsoccer')
candidates=[]
for node in root.iter('node'):
    attrs=node.attrib
    hay=' '.join((attrs.get('text',''),attrs.get('content-desc',''),attrs.get('resource-id',''),attrs.get('package',''))).lower()
    if not any(t in hay for t in terms):
        continue
    m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',attrs.get('bounds',''))
    if not m:
        continue
    x1,y1,x2,y2=map(int,m.groups())
    if x2>x1 and y2>y1:
        candidates.append(((x2-x1)*(y2-y1), (x1+x2)//2, (y1+y2)//2, hay, attrs.get('bounds','')))
if not candidates:
    raise SystemExit('New Star Soccer task not found in Recents UI hierarchy')
# Prefer the largest matching task/card node over child labels/icons.
candidates.sort(reverse=True)
_,x,y,hay,bounds=candidates[0]
Path = __import__('pathlib').Path
Path(dst).write_text(f'{x} {y}\n',encoding='utf-8')
print('recents_nss_target',x,y,bounds,hay)
PY
  if [ ! -s "$WORK/lifecycle-${tag}-recents-target.txt" ]; then
    shot "lifecycle-${tag}-recents-target-missing"
    lifecycle_record "${tag}_recents_target_found" FAIL
    echo "NSS task target not found in Recents ($tag)"
    return 1
  fi
  read -r x y < "$WORK/lifecycle-${tag}-recents-target.txt"
  lifecycle_record "${tag}_recents_target_found" PASS
  adb shell input tap "$x" "$y" >/dev/null 2>&1 || true
  sleep 4'''


def harden_generated_script(text: str) -> str:
    count = text.count(CENTER_ANCHOR)
    if count != 1:
        raise ValueError(f'expected one Recents center-tap anchor, found {count}')
    return text.replace(CENTER_ANCHOR, HIERARCHY_REPLACEMENT, 1)


def patch_script(text: str) -> str:
    return harden_generated_script(v3_patch_script(text))


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
