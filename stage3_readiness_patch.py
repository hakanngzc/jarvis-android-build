#!/usr/bin/env python3
from pathlib import Path

path = Path('stage3_minimal_gate.sh')
text = path.read_text(encoding='utf-8')
old = '''start_game(){
  local tag="$1"
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  clear_log
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
  wait_log 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 60 "$tag-mainmenu"
  sleep 3
  test -n "$(adb shell pidof "$PKG" | tr -d '\\r' || true)"
  capture_log "$tag mainmenu"
  shot "$tag-mainmenu"
}
'''
new = '''wait_game_ready(){
  local tag="$1" timeout_s="${2:-75}" i pid activity window log
  for i in $(seq 0 "$timeout_s"); do
    fatal_check || return 1
    pid="$(adb shell pidof "$PKG" 2>/dev/null | tr -d '\\r' || true)"
    activity="$(timeout 5 adb shell dumpsys activity activities 2>/dev/null || true)"
    window="$(timeout 5 adb shell dumpsys window windows 2>/dev/null || true)"
    adb logcat -d -v brief > "$WORK/game-ready-logcat.txt" 2>/dev/null || true
    log="$(cat "$WORK/game-ready-logcat.txt")"
    if [ -n "$pid" ] \
      && { grep -q "$PKG/.MonkeyGame" <<<"$activity" || grep -q "$PKG/.MonkeyGame" <<<"$window"; } \
      && grep -qE 'EGL_emulation.*eglMakeCurrent|libEGL.*loaded|HostConnection.*New Host Connection' <<<"$log"; then
      sleep 4
      pid="$(adb shell pidof "$PKG" 2>/dev/null | tr -d '\\r' || true)"
      activity="$(timeout 5 adb shell dumpsys activity activities 2>/dev/null || true)"
      window="$(timeout 5 adb shell dumpsys window windows 2>/dev/null || true)"
      if [ -n "$pid" ] && { grep -q "$PKG/.MonkeyGame" <<<"$activity" || grep -q "$PKG/.MonkeyGame" <<<"$window"; }; then
        echo "Game foreground/render ready for $tag after ${i}s"
        printf '%s\n' "$activity" > "$OUT/$tag-activity-ready.txt"
        printf '%s\n' "$window" > "$OUT/$tag-window-ready.txt"
        return 0
      fi
    fi
    sleep 1
  done
  timeout 5 adb shell dumpsys activity activities > "$OUT/$tag-activity-timeout.txt" 2>/dev/null || true
  timeout 5 adb shell dumpsys window windows > "$OUT/$tag-window-timeout.txt" 2>/dev/null || true
  cp "$WORK/game-ready-logcat.txt" "$OUT/timeout-$tag-game-ready.txt" 2>/dev/null || true
  shot "$tag-game-ready-timeout"
  echo "Timed out waiting for real game readiness: $tag"
  return 1
}

start_game(){
  local tag="$1"
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  clear_log
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
  wait_game_ready "$tag" 75
  capture_log "$tag foreground ready"
  shot "$tag-mainmenu"
}
'''
if old not in text:
    raise SystemExit('expected start_game block not found; refusing blind patch')
text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
print('STAGE3_READINESS_PATCH=PASS')
