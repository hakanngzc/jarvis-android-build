#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = 'dump_save natural-baseline; checkpoint natural-baseline'

REPLACEMENT = r'''# DIAGNOSTIC ONLY: replace the disposable fresh slot with the exact slot0
# naturally reached at cycle 9 in run #262 (sdate=99). This branch is only for
# blocker discovery; impossible verifier floors in its workflow prevent it from
# ever being accepted as the final from-fresh Stage4 proof.
: "${STAGE4_DIAGNOSTIC_ARTIFACT_ID:?missing diagnostic artifact id}"
: "${GH_TOKEN:?missing GitHub token}"
seed_zip="$WORK/diagnostic-cycle9-artifact.zip"
seed_xml="$WORK/diagnostic-cycle9-MonkeyGame.xml"
seed_url="https://api.github.com/repos/hakanngzc/jarvis-android-build/actions/artifacts/${STAGE4_DIAGNOSTIC_ARTIFACT_ID}/zip"
curl -fsSL --retry 3 \
  -H "Authorization: Bearer ${GH_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "$seed_url" -o "$seed_zip"
unzip -p "$seed_zip" cycle-9-MonkeyGame.xml > "$seed_xml"
test -s "$seed_xml"
grep -q monkeystate "$seed_xml"

prefs="/data/data/$PKG/shared_prefs/MonkeyGame.xml"
app_uid="$(adb shell dumpsys package "$PKG" 2>/dev/null | sed -n 's/.*userId=\([0-9][0-9]*\).*/\1/p' | head -1 | tr -d '\r')"
[[ "$app_uid" =~ ^[0-9]+$ ]] || { echo 'diagnostic seed could not resolve app uid' >> "$FLOW"; exit 219; }
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
adb push "$seed_xml" /data/local/tmp/stage4-cycle9-MonkeyGame.xml >/dev/null
adb shell "cp /data/local/tmp/stage4-cycle9-MonkeyGame.xml '$prefs' && chown '$app_uid:$app_uid' '$prefs' && chmod 660 '$prefs'" >/dev/null
adb shell rm -f /data/local/tmp/stage4-cycle9-MonkeyGame.xml >/dev/null 2>&1 || true

clear_log
adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
seed_loaded=0
seed_mainmenu=0
for _ in $(seq 1 30); do
  fatal_check || exit 220
  adb logcat -d -v brief > "$WORK/diagnostic-seed-load.txt" 2>/dev/null || true
  if grep -qiE 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' "$WORK/diagnostic-seed-load.txt"; then
    seed_loaded=1
    break
  fi
  if grep -qiE 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' "$WORK/diagnostic-seed-load.txt"; then
    seed_mainmenu=1
  fi
  sleep 1
done

if [ "$seed_loaded" -ne 1 ]; then
  [ "$seed_mainmenu" -eq 1 ] || { capture_log 'diagnostic cycle9 seed reload unresolved'; exit 219; }
  open_slot0 diagnostic-cycle9
  load_existing diagnostic-cycle9
fi
capture_log 'diagnostic cycle9 seed loaded'
echo 'STAGE4_DIAGNOSTIC_BASELINE=cycle9' | tee "$OUT/diagnostic-cycle9.txt" >> "$FLOW"
dump_save natural-baseline; checkpoint natural-baseline'''


def harden(text: str) -> str:
    count = text.count(ANCHOR)
    if count != 1:
        raise SystemExit(f'expected one natural baseline anchor, found {count}')
    return text.replace(ANCHOR, REPLACEMENT, 1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_cycle9_diagnostic.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied diagnostic natural cycle9 seed continuation: {dst}')


if __name__ == '__main__':
    main()
