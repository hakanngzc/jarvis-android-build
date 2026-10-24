#!/usr/bin/env python3
import sys
from pathlib import Path

from patch_lifecycle_probe_v3 import patch_script as v3_patch_script

CENTER_ANCHOR = r'''  size="$(adb shell wm size 2>/dev/null | tr -d '\r' | grep -Eo '[0-9]+x[0-9]+' | tail -1 || true)"
  [ -n "$size" ] || { echo "could not read display size for Recents ($tag)"; return 1; }
  w="${size%x*}"; h="${size#*x}"; x=$((w/2)); y=$((h/2))
  adb shell input tap "$x" "$y" >/dev/null 2>&1 || true
  sleep 4'''

PLAY_EDGE_ANCHOR = 'press_play(){ local x y; read -r x y < <(logical_xy 553 829); press_physical "$x" "$y" "${1:-2}"; }'
PLAY_CENTER_REPLACEMENT = 'press_play(){ local x y; read -r x y < <(logical_xy 553 900); press_physical "$x" "$y" "${1:-2}"; }'

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
  adb shell input tap "$x" "$y" >/dev/null 2>&1 || true
  sleep 4'''


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
