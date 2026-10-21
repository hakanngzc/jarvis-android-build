#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')

start_anchor = "clear_log; press_play 3; capture_log 'probe StartMatch -> stock MatchOver'; shot stage3-match-after-probe\n"
end_anchor = "# Restart, reload the same Career, then prove match state persisted.\n"

start = s.find(start_anchor)
end = s.find(end_anchor, start + 1 if start >= 0 else 0)
if start < 0 or end < 0 or end <= start:
    raise SystemExit('Stage3 match-flow anchors not found; refusing blind patch')

replacement = r'''# First-time Career match can show a tutorial overlay that consumes the first
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

# MatchStats has staged animation. Advance only until the stock Career writer is
# actually observed; this proves the result is being handed back to Career.
MY_MATCH_PLAYED=0
clear_log
for i in $(seq 1 24); do
  press_play 2
  adb logcat -d -v brief > "$WORK/matchstats-progress.log" 2>/dev/null || true
  if grep -qiE 'MyMatchPlayed|CallFunc:[[:space:]]*PlayToDate|SetActive:[[:space:]]*message|SETTING ACTIVE:[[:space:]]*message' "$WORK/matchstats-progress.log"; then
    MY_MATCH_PLAYED=1
    break
  fi
  fatal_check
done
capture_log 'MatchStats -> MyMatchPlayed'
[ "$MY_MATCH_PLAYED" -eq 1 ] || {
  cp "$WORK/matchstats-progress.log" "$OUT/mymatchplayed-not-observed.log" 2>/dev/null || true
  echo 'MyMatchPlayed was not observed'
  exit 205
}

# Continue the stock PlayToDate/results chain. Do not require a newly-created
# Message screen because the message layer can already be active.
PLAY_TO_DATE=0
state="$(current_state)"
for i in $(seq 1 10); do
  adb logcat -d -v brief > "$WORK/playtodate-progress.log" 2>/dev/null || true
  if grep -qiE 'CallFunc:[[:space:]]*PlayToDate|PlayToDate' "$WORK/playtodate-progress.log"; then
    PLAY_TO_DATE=1
  fi
  state="$(current_state)"
  if [[ " leaguefixtures league gamemenu matchreview dilemma ad " == *" $state "* ]]; then
    break
  fi
  clear_log
  press_message_accept 3
  fatal_check
done
capture_log 'MyMatchPlayed -> PlayToDate -> results'
[ "$PLAY_TO_DATE" -eq 1 ] || {
  cp "$WORK/playtodate-progress.log" "$OUT/playtodate-not-observed.log" 2>/dev/null || true
  echo 'PlayToDate continuation was not observed'
  exit 206
}

# Results -> League/Continue -> optional MatchReview/Dilemma -> GameMenu.
# Stock 4.31 can launch an AdMob interstitial immediately after GameMenu has
# already saved the Career. Treat that Activity as a temporary overlay, dismiss
# it with Android Back, then re-read the underlying Monkey state.
#
# A stock Dilemma can also appear in this chain. dilemma.uis proves TopOption is
# PushOrigin(55,165+[@T*0.3]) with a 528x368 pressable rectangle. Logical point
# (320,400) is safely inside that stock relationship1 option. The internal
# splashmessage may consume the first attempt. Preserve the parent Dilemma log
# across that retry so current_state() can still classify the parent and the next
# bounded iteration can press the same verified stock option again.
state="$(current_state)"
if [[ " leaguefixtures league gamemenu matchreview dilemma message ad " != *" $state "* ]]; then
  state="$(wait_state 'leaguefixtures league gamemenu matchreview dilemma message ad' 30 || true)"
fi
for step in $(seq 1 16); do
  [ "$state" = gamemenu ] && break
  case "$state" in
    ad)
      shot "post-match-ad-$step"
      echo 'Closing stock AdMob interstitial with Android Back'
      adb shell input keyevent 4 </dev/null || true
      sleep 2
      ;;
    leaguefixtures|league|matchreview)
      clear_log
      press_play 3
      ;;
    dilemma)
      press_logical 320 400 3
      ;;
    message)
      clear_log
      press_message_accept 3
      ;;
    *)
      clear_log
      # One bounded neutral wait for transitions that have not emitted their
      # next screen line yet. Never fall into the old 24x20s unknown loop.
      sleep 2
      ;;
  esac
  state="$(wait_state 'league matchreview gamemenu dilemma message leaguefixtures ad' 25 || true)"
  capture_log "post-match state machine step $step -> $state"
  if [ "$state" = unknown ]; then
    shot "post-match-unknown-$step"
    echo "Post-match state became unknown at bounded step $step"
    exit 207
  fi
done
[ "$state" = gamemenu ] || { echo "Did not return to GameMenu; state=$state"; exit 207; }
shot stage3-gamemenu-postmatch
sleep 2
dump_save post-match

'''

s = s[:start] + replacement + s[end:]

required = [
    'MATCHSTATS_REACHED=0',
    "capture_log 'MatchStats -> MyMatchPlayed'",
    "capture_log 'MyMatchPlayed -> PlayToDate -> results'",
    ' dilemma ',
    'dilemma)',
    'press_logical 320 400',
    ' ad ',
    'ad)',
    'input keyevent 4',
    'dump_save post-match',
]
if not all(x in s for x in required):
    raise SystemExit('Stage3 match-flow replacement postcondition failed')

p.write_text(s, encoding='utf-8')
print('STAGE3_MATCH_FLOW_PATCH=PASS')
