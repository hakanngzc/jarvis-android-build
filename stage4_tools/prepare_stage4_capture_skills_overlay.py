#!/usr/bin/env python3
from pathlib import Path
import sys

OLD = 'skillsshopoverlay) adb shell input keyevent 4 </dev/null || true; sleep 2; state=gamemenu;;'
NEW = 'skillsshopoverlay) shot "skills-shop-overlay"; capture_log "skills shop overlay captured"; echo "STAGE4_DIAGNOSTIC_SKILLS_OVERLAY_CAPTURED" >> "$FLOW"; return 97;;'


def harden(text: str) -> str:
    count = text.count(OLD)
    if count != 2:
        raise SystemExit(f'expected two SkillsShopOverlay handlers, found {count}')
    return text.replace(OLD, NEW)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_capture_skills_overlay.py INPUT OUTPUT')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied diagnostic SkillsShopOverlay capture trap: {dst}')


if __name__ == '__main__':
    main()
