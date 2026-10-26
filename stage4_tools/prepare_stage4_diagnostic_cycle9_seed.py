#!/usr/bin/env python3
from pathlib import Path
import sys

OLD = '''dump_save natural-baseline; checkpoint natural-baseline
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''

NEW = '''echo "DIAGNOSTIC_ONLY: restoring naturally-produced cycle-9 save from run262; never count this run as final Stage4 PASS" >> "$FLOW"
adb push "$RUNNER_TEMP/stage4-cycle9-seed/cycle-9-MonkeyGame.xml" /data/local/tmp/stage4-cycle9-MonkeyGame.xml >/dev/null
adb shell "cat /data/local/tmp/stage4-cycle9-MonkeyGame.xml > /data/data/$PKG/shared_prefs/MonkeyGame.xml && chmod 660 /data/data/$PKG/shared_prefs/MonkeyGame.xml"
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
start_game diagnostic-cycle9
open_slot0 diagnostic-cycle9
load_existing diagnostic-cycle9
dump_save natural-baseline; checkpoint natural-baseline
python3 - "$OUT/natural-baseline.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1],encoding='utf-8'))
assert p['sdate']==99, p
assert p['careerapps']==9, p
print('DIAGNOSTIC_CYCLE9_SEED_OK', p['sdate'], p['careerapps'])
PY
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_diagnostic_cycle9_seed.py INPUT OUTPUT')
    src, dst = map(Path, sys.argv[1:])
    text = src.read_text(encoding='utf-8')
    if text.count(OLD) != 1:
        raise SystemExit(f'expected one baseline anchor, found {text.count(OLD)}')
    text = text.replace(OLD, NEW, 1)
    dst.write_text(text, encoding='utf-8')
    print(f'Applied DIAGNOSTIC-ONLY cycle9 natural-save continuation: {dst}')

if __name__ == '__main__':
    main()
