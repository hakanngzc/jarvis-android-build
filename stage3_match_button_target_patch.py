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

new = r'''# First Career match has a tutorial overlay. Dismiss it with the already proven
# overlay target, then let the patched StartMatch reproduce stock full-time.
# The probe now calls stock TScreen_Match.m_DoHalfEnd(), which restores the normal
# navigation panel. Stock TScreen_Match.m_ButtonPlay handles matchstate=5 by
# calling TMatch.m_EndMatch(), so the NEXT input must be the footer Play/Continue
# button, not the in-match upper-right fast-forward control.
press_match_tutorial_close(){
  echo 'Match tutorial close target (stock API29 Pixel 4): 1005,400'
  press_physical 1005 400 "${1:-2}"
}
matchstats_seen(){
  adb logcat -d -v brief > "$WORK/match-ingress.log" 2>/dev/null || true
  grep -qiE 'Create Screen:[[:space:]]*matchstats|SETTING ACTIVE:[[:space:]]*matchstats|SetActive:[[:space:]]*matchstats' "$WORK/match-ingress.log"
}

MATCHSTATS_REACHED=0
clear_log
press_match_tutorial_close 2
capture_log 'match tutorial closed'
shot stage3-match-tutorial-closed
fatal_check

# First footer press invokes the TEST-ONLY StartMatch probe. The probe writes the
# real selected fixture 1-0, calls stock MatchOver(true), sets state5, runs the GS
# match-over hook, and finally executes stock m_DoHalfEnd() to restore footer nav.
clear_log
press_play 3
capture_log 'probe StartMatch -> stock MatchOver -> DoHalfEnd'
shot stage3-match-after-probe
if matchstats_seen; then MATCHSTATS_REACHED=1; fi

# With state5 + stock half-end UI active, footer Play/Continue is the stock exit
# path: TScreen_Match.m_ButtonPlay -> TMatch.m_EndMatch -> g_GSEndMatch -> MatchStats.
for i in $(seq 1 3); do
  [ "$MATCHSTATS_REACHED" -eq 1 ] && break
  clear_log
  echo "Stock full-time footer continuation attempt $i/3"
  press_play 3
  capture_log "stock state5 footer continuation $i"
  if matchstats_seen; then MATCHSTATS_REACHED=1; break; fi
  fatal_check
  shot "stage3-fulltime-footer-$i"
done
[ "$MATCHSTATS_REACHED" -eq 1 ] || {
  cp "$WORK/match-ingress.log" "$OUT/matchstats-not-reached.log" 2>/dev/null || true
  shot stage3-matchstats-not-reached
  echo 'Did not reach MatchStats after stock DoHalfEnd -> state5 footer EndMatch sequence'
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
    "capture_log 'probe StartMatch -> stock MatchOver -> DoHalfEnd'",
    'Stock full-time footer continuation attempt',
    'press_play 3',
    'MATCHSTATS_REACHED',
]
if not all(token in s for token in required):
    raise SystemExit('Stage3 match-button-target patch postcondition failed')

p.write_text(s, encoding='utf-8')
print('STAGE3_MATCH_BUTTON_TARGET_PATCH=PASS')
