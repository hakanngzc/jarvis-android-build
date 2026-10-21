#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')

old_sign = 'sign_one(){ local src="$1" dst="$2" tmp="$WORK/aligned-$(basename "$dst")";'
new_sign = 'sign_one(){ local src="$1" dst="$2"; local tmp="$WORK/aligned-$(basename "$dst")";'
if old_sign in s:
    s = s.replace(old_sign, new_sign, 1)

old_start = '''  wait_log 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 60 "$tag-mainmenu"\n  sleep 3\n  test -n "$(adb shell pidof "$PKG" | tr -d '\\r' || true)"'''
new_start = '''  wait_log 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 60 "$tag-mainmenu"\n  local rendered=0 ready_i bytes\n  for ready_i in $(seq 1 45); do\n    adb exec-out screencap -p > "$WORK/render-probe.png" 2>/dev/null || true\n    bytes="$(wc -c < "$WORK/render-probe.png" 2>/dev/null || echo 0)"\n    if [ "${bytes:-0}" -gt 30000 ]; then\n      cp "$WORK/render-probe.png" "$OUT/${tag}-render-ready.png" || true\n      echo "Rendered frame ready after ${ready_i}s (${bytes} bytes)"\n      rendered=1\n      break\n    fi\n    sleep 1\n  done\n  [ "$rendered" -eq 1 ] || { cp "$WORK/render-probe.png" "$OUT/${tag}-render-timeout.png" 2>/dev/null || true; echo 'Rendered frame did not become ready'; return 1; }\n  test -n "$(adb shell pidof "$PKG" | tr -d '\\r' || true)"'''

if old_start not in s:
    raise SystemExit('start_game render-gate anchor not found')
s = s.replace(old_start, new_start, 1)
p.write_text(s, encoding='utf-8')
print('Applied Stage3 runtime hotfixes: sign_one scope + rendered-frame gate')
