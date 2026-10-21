#!/usr/bin/env python3
from pathlib import Path

path = Path('stage3_minimal_gate.sh')
text = path.read_text(encoding='utf-8')

helper = r'''wait_game_ready(){
  local tag="$1" timeout_s="${2:-75}" i pid activity window log frame bytes
  frame="$WORK/$tag-render-probe.png"
  for i in $(seq 0 "$timeout_s"); do
    fatal_check || return 1
    pid="$(adb shell pidof "$PKG" 2>/dev/null | tr -d '\r' || true)"
    activity="$(timeout 5 adb shell dumpsys activity activities 2>/dev/null || true)"
    window="$(timeout 5 adb shell dumpsys window windows 2>/dev/null || true)"
    adb logcat -d -v brief > "$WORK/game-ready-logcat.txt" 2>/dev/null || true
    log="$(cat "$WORK/game-ready-logcat.txt")"
    adb exec-out screencap -p > "$frame" 2>/dev/null || true
    bytes="$(wc -c < "$frame" 2>/dev/null || echo 0)"
    if [ -n "$pid" ] \
      && { grep -q "$PKG/.MonkeyGame" <<<"$activity" || grep -q "$PKG/.MonkeyGame" <<<"$window"; } \
      && grep -qE 'EGL_emulation.*eglMakeCurrent|libEGL.*loaded|HostConnection.*New Host Connection' <<<"$log" \
      && [ "${bytes:-0}" -gt 30000 ]; then
      sleep 4
      pid="$(adb shell pidof "$PKG" 2>/dev/null | tr -d '\r' || true)"
      activity="$(timeout 5 adb shell dumpsys activity activities 2>/dev/null || true)"
      window="$(timeout 5 adb shell dumpsys window windows 2>/dev/null || true)"
      adb exec-out screencap -p > "$frame" 2>/dev/null || true
      bytes="$(wc -c < "$frame" 2>/dev/null || echo 0)"
      if [ -n "$pid" ] \
        && { grep -q "$PKG/.MonkeyGame" <<<"$activity" || grep -q "$PKG/.MonkeyGame" <<<"$window"; } \
        && [ "${bytes:-0}" -gt 30000 ]; then
        cp "$frame" "$OUT/$tag-render-ready.png" || true
        echo "Game foreground/render ready for $tag after ${i}s (${bytes} bytes)"
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
  cp "$frame" "$OUT/$tag-render-timeout.png" 2>/dev/null || true
  shot "$tag-game-ready-timeout"
  echo "Timed out waiting for real game readiness: $tag"
  return 1
}
'''

if 'wait_game_ready(){' not in text:
    anchor = 'start_game(){\n'
    if anchor not in text:
        raise SystemExit('start_game anchor not found; refusing blind patch')
    text = text.replace(anchor, helper + '\n' + anchor, 1)

gate = '''  wait_log 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 60 "$tag-mainmenu"\n'''
if gate in text:
    start = text.index(gate)
    end_anchor = '  capture_log "$tag mainmenu"\n'
    end = text.find(end_anchor, start)
    if end < 0:
        raise SystemExit('start_game capture anchor not found; refusing blind patch')
    # Runtime hotfix may insert a screenshot render loop between the old mainmenu
    # log wait and this capture point. Replace that whole readiness section only.
    text = text[:start] + '  wait_game_ready "$tag" 75\n' + text[end:]
elif '  wait_game_ready "$tag" 75\n' not in text:
    raise SystemExit('mainmenu readiness gate not found; refusing blind patch')

path.write_text(text, encoding='utf-8')
print('STAGE3_READINESS_PATCH=PASS')
