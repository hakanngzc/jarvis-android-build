#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')

old = r'''# First-time Career match can show a tutorial overlay that consumes the first
# Play press. Use a bounded Play loop and stop as soon as stock MatchStats is
# observed. In the normal path: tutorial -> patched StartMatch/real MatchOver ->
# stock EndMatch -> MatchStats. Extra early presses are harmless here.
MATCHSTATS_REACHED=0
clear_log
for i in $(seq 1 5); do
  press_play 3
  adb logcat -d -v brief > "$WORK/match-ingress.log" 2>/dev/null || true
  capture_log "match ingress Play $i"
  if grep -qiE 'Create Screen:[[:space:]]*matchstats|SETTING ACTIVE:[[:space:]]*matchstats|SetActive:[[:space:]]*matchstats' "$WORK/match-ingress.log"; then
    MATCHSTATS_REACHED=1
    break
  fi
  fatal_check
  shot "stage3-match-ingress-$i"
done
[ "$MATCHSTATS_REACHED" -eq 1 ] || {
  cp "$WORK/match-ingress.log" "$OUT/matchstats-not-reached.log" 2>/dev/null || true
  shot stage3-matchstats-not-reached
  echo 'Did not reach MatchStats after bounded tutorial/StartMatch/EndMatch Play sequence'
  exit 204
}
shot stage3-matchstats
'''

new = r'''# The first Career match shows a tutorial overlay on top of the prematch screen.
# Runtime evidence proves two different controls are involved here:
# - the tutorial overlay is dismissed by the previously proven 1005,400 tap;
# - after StartMatch, the real green >> continuation button is centred at ~984,141
#   on the stock API29 Pixel 4 screenshot. Keep those targets separate.
press_match_tutorial_close(){
  echo 'Match tutorial close target (stock API29 Pixel 4): 1005,400'
  press_physical 1005 400 "${1:-2}"
}
press_match_next(){
  echo 'Match continuation target (stock API29 Pixel 4): 985,165'
  press_physical 985 165 "${1:-2}"
}
matchstats_seen(){
  adb logcat -d -v brief > "$WORK/match-ingress.log" 2>/dev/null || true
  grep -qiE 'Create Screen:[[:space:]]*matchstats|SETTING ACTIVE:[[:space:]]*matchstats|SetActive:[[:space:]]*matchstats' "$WORK/match-ingress.log"
}

MATCHSTATS_REACHED=0
clear_log

# Deterministic fresh-Career tutorial: dismiss the overlay using the target that
# was proven to close it in the previous runtime artifact.
press_match_tutorial_close 2
capture_log 'match tutorial closed'
shot stage3-match-tutorial-closed
fatal_check

# Prematch PLAY now owns input. This invokes the test-only patched m_StartMatch,
# which writes 1-0 to the real selected fixture and calls stock m_MatchOver(true).
clear_log
press_play 3
capture_log 'probe StartMatch -> stock MatchOver'
shot stage3-match-after-probe
if matchstats_seen; then MATCHSTATS_REACHED=1; fi

# After StartMatch the footer is Work Rate / Focus and the green >> button is the
# stock continuation control. A screen can stay active without a fresh SetActive
# line, so advance using the screenshot-backed >> target and keep the loop bounded.
for i in $(seq 1 6); do
  [ "$MATCHSTATS_REACHED" -eq 1 ] && break
  clear_log
  press_match_next 2
  capture_log "match next $i"
  if matchstats_seen; then MATCHSTATS_REACHED=1; break; fi
  fatal_check
  shot "stage3-match-next-$i"
done
[ "$MATCHSTATS_REACHED" -eq 1 ] || {
  cp "$WORK/match-ingress.log" "$OUT/matchstats-not-reached.log" 2>/dev/null || true
  shot stage3-matchstats-not-reached
  echo 'Did not reach MatchStats after tutorial close -> StartMatch -> stock match-next sequence'
  exit 204
}
shot stage3-matchstats
'''

count = s.count(old)
if count != 1:
    raise SystemExit(f'expected exactly one old match-ingress block, found {count}; refusing blind patch')
s = s.replace(old, new, 1)

required = [
    'press_match_tutorial_close(){',
    'press_match_next(){',
    "capture_log 'match tutorial closed'",
    "capture_log 'probe StartMatch -> stock MatchOver'",
    'press_match_next 2',
    'MATCHSTATS_REACHED',
]
if not all(token in s for token in required):
    raise SystemExit('Stage3 match-button-target patch postcondition failed')

p.write_text(s, encoding='utf-8')
print('STAGE3_MATCH_BUTTON_TARGET_PATCH=PASS')
