#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')

old_sign = 'sign_one(){ local src="$1" dst="$2" tmp="$WORK/aligned-$(basename "$dst")";'
new_sign = 'sign_one(){ local src="$1" dst="$2"; local tmp="$WORK/aligned-$(basename "$dst")";'
if old_sign in s:
    s = s.replace(old_sign, new_sign, 1)

trial_line = 'PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_trial_skip_for_persistence_test.py "$BASE" "$WORK/base-career-unsigned.apk" | tee "$OUT/career-trial-patch.txt"'
overlay_block = trial_line + '''\npython3 stage3_tools/patch_first_run_overlays.py "$WORK/base-career-unsigned.apk" "$WORK/base-career-overlay-unsigned.apk" | tee "$OUT/first-run-overlay-patch.txt"\nmv "$WORK/base-career-overlay-unsigned.apk" "$WORK/base-career-unsigned.apk"'''
if 'first-run-overlay-patch.txt' not in s:
    if trial_line not in s:
        raise SystemExit('trial-patch anchor not found')
    s = s.replace(trial_line, overlay_block, 1)

old_career = 'press_career(){ press_logical 471 541 "${1:-3}"; }'
new_career = '''press_career(){
  local size
  size="$(adb shell wm size 2>/dev/null | tr -d '\\r')"
  case "$size" in
    *1080x2280*)
      # Stock mainmenu.uis: CareerButton press rect is X=339..603 and
      # Y=(505-0.8*@T)..(577-0.8*@T). On the API29 Pixel 4 app viewport
      # @T=-160, so the verified physical centre is approximately 795,1399.
      echo 'Career target (stock API29 Pixel 4): 795,1399'
      press_physical 795 1399 "${1:-3}"
      ;;
    *)
      echo "Unsupported Stage3 MainMenu geometry: $size" >&2
      return 1
      ;;
  esac
}'''
if old_career in s:
    s = s.replace(old_career, new_career, 1)
elif 'Career target (stock API29 Pixel 4)' not in s:
    raise SystemExit('press_career anchor not found')

old_start = '''  wait_log 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 60 "$tag-mainmenu"\n  sleep 3\n  test -n "$(adb shell pidof "$PKG" | tr -d '\\r' || true)"'''
new_start = '''  wait_log 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 60 "$tag-mainmenu"\n  local rendered=0 ready_i bytes\n  for ready_i in $(seq 1 45); do\n    adb exec-out screencap -p > "$WORK/render-probe.png" 2>/dev/null || true\n    bytes="$(wc -c < "$WORK/render-probe.png" 2>/dev/null || echo 0)"\n    if [ "${bytes:-0}" -gt 30000 ]; then\n      cp "$WORK/render-probe.png" "$OUT/${tag}-render-ready.png" || true\n      echo "Rendered frame ready after ${ready_i}s (${bytes} bytes)"\n      rendered=1\n      break\n    fi\n    sleep 1\n  done\n  [ "$rendered" -eq 1 ] || { cp "$WORK/render-probe.png" "$OUT/${tag}-render-timeout.png" 2>/dev/null || true; echo 'Rendered frame did not become ready'; return 1; }\n  test -n "$(adb shell pidof "$PKG" | tr -d '\\r' || true)"'''
if old_start in s:
    s = s.replace(old_start, new_start, 1)
elif 'Rendered frame ready after' not in s:
    raise SystemExit('start_game render-gate anchor not found')

old_boot = '''install_base "$WORK/signed/base-career.apk"\nadb shell pm clear "$PKG" >/dev/null || true\nadb root >/dev/null 2>&1 || true; adb wait-for-device; sleep 2\n\n# Fresh stock Career creation.'''
new_boot = '''install_base "$WORK/signed/base-career.apk"\nadb shell pm clear "$PKG" >/dev/null || true\n# Make first launch deterministic: finish package compilation before starting the game.\nadb shell cmd package compile -m speed -f "$PKG" >/dev/null 2>&1 || true\nsleep 2\n\n# Fresh stock Career creation.'''
if old_boot in s:
    s = s.replace(old_boot, new_boot, 1)
elif 'Make first launch deterministic' not in s:
    raise SystemExit('initial install/root anchor not found')

root_anchor = '''shot fresh-after-save\n\n# Same-signature Stage3 fast-match update.'''
root_replacement = '''shot fresh-after-save\n\n# Root is required only for direct save-file evidence; defer adbd restart until after the first stable Career save.\nadb root >/dev/null 2>&1 || true\nadb wait-for-device\nsleep 2\n\n# Same-signature Stage3 fast-match update.'''
if root_anchor in s:
    s = s.replace(root_anchor, root_replacement, 1)
elif 'Root is required only for direct save-file evidence' not in s:
    raise SystemExit('deferred-root anchor not found')

p.write_text(s, encoding='utf-8')
print('Applied Stage3 runtime hotfixes: sign scope + overlay removal + verified Career target + render gate + deterministic first launch + deferred root')
