#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

INSERT_BEFORE = '''dump_save natural-baseline; checkpoint natural-baseline
# Only season-transition evidence emitted after the baseline checkpoint counts.
# This excludes NewSeasonSetUp markers that may occur during fresh-Career bootstrap.
BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''

INSERT_AFTER = r'''# DIAGNOSTIC ONLY: restore a save produced by a prior natural Stage4 run.
# This is used only to discover later stock UI blockers faster. It must never
# be accepted as the final natural full-season proof.
[ -n "${STAGE4_RESUME_SEED:-}" ] || { echo 'STAGE4_RESUME_SEED missing'; exit 230; }
[ -f "$STAGE4_RESUME_SEED" ] || { echo "resume seed not found: $STAGE4_RESUME_SEED"; exit 231; }
echo "DIAGNOSTIC_ONLY restoring natural cycle-9 seed: $STAGE4_RESUME_SEED" >> "$FLOW"
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
adb root >/dev/null 2>&1 || true
adb wait-for-device
adb push "$STAGE4_RESUME_SEED" /data/local/tmp/stage4-cycle9-MonkeyGame.xml >/dev/null
uid="$(adb shell stat -c %u "/data/data/$PKG" 2>/dev/null | tr -d '\r')"
[ -n "$uid" ] || { echo 'could not resolve package uid'; exit 232; }
adb shell mkdir -p "/data/data/$PKG/shared_prefs"
adb shell cp /data/local/tmp/stage4-cycle9-MonkeyGame.xml "/data/data/$PKG/shared_prefs/MonkeyGame.xml"
adb shell chown "$uid:$uid" "/data/data/$PKG/shared_prefs/MonkeyGame.xml"
adb shell chmod 600 "/data/data/$PKG/shared_prefs/MonkeyGame.xml"
adb shell restorecon -RF "/data/data/$PKG/shared_prefs" >/dev/null 2>&1 || true
clear_log
adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
if wait_log 'LoadCareer saveslot: 0|Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 60 resume-autoload; then
  wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 45 resume-gamemenu
else
  wait_log 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 30 resume-mainmenu
  open_slot0 resume
  load_existing resume
fi
capture_log 'DIAGNOSTIC_ONLY cycle-9 seed loaded'
dump_save resume-seeded; checkpoint resume-seeded
python3 - "$OUT/resume-seeded.json" <<'PY'
import json, sys
d=json.load(open(sys.argv[1], encoding='utf-8'))
assert d['sdate'] == 99, d
assert d['careerapps'] == 9, d
assert d['clubnationid'] == 2, d
print('DIAGNOSTIC_SEED_OK', d['sdate'], d['careerapps'], d['clubid'])
PY
cp "$OUT/resume-seeded-MonkeyGame.xml" "$OUT/natural-baseline-MonkeyGame.xml"
cp "$OUT/resume-seeded.json" "$OUT/natural-baseline.json"
# Scope season markers from the seeded diagnostic baseline, not the fresh bootstrap.
BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''

TAIL_OLD = '''python3 stage4_tools/verify_stage4_natural_season.py --base "$OUT/natural-baseline.json" --post "$OUT/post-season.json" --restart "$OUT/post-season-restart.json" --meta "$OUT/natural-meta.json" --out "$OUT/natural-verdict.json" | tee "$OUT/STAGE4_NATURAL_SEASON_RESULT.txt"
grep -q 'STAGE4_NATURAL_SEASON_PASS' "$OUT/STAGE4_NATURAL_SEASON_RESULT.txt"
echo 'STAGE4_NATURAL_SEASON_PASS' '''

TAIL_NEW = '''set +e
python3 stage4_tools/verify_stage4_natural_season.py --base "$OUT/natural-baseline.json" --post "$OUT/post-season.json" --restart "$OUT/post-season-restart.json" --meta "$OUT/natural-meta.json" --out "$OUT/natural-verdict.json" | tee "$OUT/STAGE4_RESUME_DIAGNOSTIC_RESULT.txt"
verify_rc=${PIPESTATUS[0]}
set -e
echo "DIAGNOSTIC_ONLY verifier_rc=$verify_rc" >> "$FLOW"
python3 - "$OUT/STAGE4_RESUME_DIAGNOSTIC_RESULT.txt" "$OUT/natural-verdict.json" <<'PY'
from pathlib import Path
import sys
old='STAGE4_'+'NATURAL_SEASON_PASS'
new='STAGE4_RESUME_DIAGNOSTIC_PASS'
for raw in sys.argv[1:]:
    p=Path(raw)
    if p.exists():
        p.write_text(p.read_text(encoding='utf-8',errors='replace').replace(old,new),encoding='utf-8')
PY
echo 'STAGE4_RESUME_DIAGNOSTIC_COMPLETE' '''


def harden(text: str) -> str:
    if text.count(INSERT_BEFORE) != 1:
        raise SystemExit(f'expected one scoped natural baseline marker, found {text.count(INSERT_BEFORE)}')
    text = text.replace(INSERT_BEFORE, INSERT_AFTER, 1)
    if text.count(TAIL_OLD) != 1:
        raise SystemExit(f'expected one final verifier block, found {text.count(TAIL_OLD)}')
    text = text.replace(TAIL_OLD, TAIL_NEW, 1)
    forbidden = 'STAGE4_' + 'NATURAL_SEASON_PASS'
    if forbidden in text:
        raise SystemExit('diagnostic gate still contains canonical PASS literal')
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_resume_diagnostic.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied DIAGNOSTIC_ONLY natural cycle-9 resume: {dst}')


if __name__ == '__main__':
    main()
