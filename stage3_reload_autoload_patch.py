#!/usr/bin/env python3
from pathlib import Path

OLD = '''# Restart, reload the same Career, then prove match state persisted.
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
start_game reload
open_slot0 reload
load_existing reload
sleep 2; dump_save post-restart
capture_log 'Stage3 after restart/load'
'''

NEW = '''# Restart and prove the same Career state persisted. NSS 4.31 can automatically
# invoke LoadCareer and switch from MainMenu to GameMenu after process restart.
# Accept that stock path when observed; otherwise retain the proven manual
# MainMenu -> SaveSlot -> LoadCareer fallback.
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
start_game reload
RELOAD_AUTO=0
for reload_i in $(seq 0 8); do
  adb logcat -d -v brief > "$WORK/reload-autoload.log" 2>/dev/null || true
  if grep -qiE 'CallFunc:[[:space:]]*LoadCareer|LoadCareer saveslot:[[:space:]]*0' "$WORK/reload-autoload.log" \
     && grep -qiE 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' "$WORK/reload-autoload.log"; then
    RELOAD_AUTO=1
    echo "Auto-loaded Career detected after restart at ${reload_i}s"
    capture_log 'reload-auto-gamemenu'
    shot reload-auto-gamemenu
    break
  fi
  sleep 1
done
if [ "$RELOAD_AUTO" -ne 1 ]; then
  echo 'No automatic Career reload observed; using manual SaveSlot fallback'
  open_slot0 reload
  load_existing reload
fi
sleep 2; dump_save post-restart
capture_log 'Stage3 after restart/load'
'''


def patch_text(s: str) -> str:
    count = s.count(OLD)
    if count != 1:
        raise ValueError(f'expected exactly one restart/load block, found {count}; refusing blind patch')
    out = s.replace(OLD, NEW, 1)
    required = [
        'RELOAD_AUTO=0',
        'reload-auto-gamemenu',
        'Auto-loaded Career detected after restart',
        'open_slot0 reload',
        'load_existing reload',
        'dump_save post-restart',
    ]
    if not all(token in out for token in required):
        raise ValueError('reload auto-load patch postcondition failed')
    return out


def main() -> None:
    p = Path('stage3_minimal_gate.sh')
    p.write_text(patch_text(p.read_text(encoding='utf-8')), encoding='utf-8')
    print('STAGE3_RELOAD_AUTOLOAD_PATCH=PASS')


if __name__ == '__main__':
    main()
