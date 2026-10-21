#!/usr/bin/env bash
set -euo pipefail

PKG=com.newstargames.newstarsoccer
NAME="${TEST_NAME:-stage3-public-api29}"
ROOT="$PWD"
OUT="$ROOT/artifacts/$NAME"
WORK="/tmp/nss-reborn-$NAME"
FLOW="$OUT/STAGE3_RUNTIME_FLOW.log"
XAPK_URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
EXPECTED_BASE='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'
mkdir -p "$OUT" "$WORK/xapk" "$WORK/signed"
: > "$FLOW"

capture_failure(){
  local rc=$?
  set +e
  adb logcat -d -v threadtime > "$OUT/failure-logcat.txt" 2>/dev/null
  adb shell dumpsys activity activities > "$OUT/failure-activity.txt" 2>/dev/null
  adb shell dumpsys window windows > "$OUT/failure-window.txt" 2>/dev/null
  adb exec-out screencap -p > "$OUT/failure-screen.png" 2>/dev/null
  echo "failure_rc=$rc" > "$OUT/FAILURE.txt"
  exit "$rc"
}
trap capture_failure ERR

# Download the exact public 4.31 XAPK already independently hash-gated in CI.
curl -fL --retry 3 --retry-delay 2 -A 'Mozilla/5.0 Chrome/141' \
  "$XAPK_URL" -o "$WORK/nss431.xapk"
unzip -tq "$WORK/nss431.xapk" >/dev/null
unzip -q "$WORK/nss431.xapk" -d "$WORK/xapk"
BASE="$WORK/xapk/com.newstargames.newstarsoccer.apk"
[ -f "$BASE" ] || { echo 'base APK missing from XAPK'; exit 10; }
ACTUAL_BASE="$(sha256sum "$BASE" | awk '{print $1}')"
echo "base_sha256=$ACTUAL_BASE" | tee "$OUT/SOURCE_HASH.txt"
[ "$ACTUAL_BASE" = "$EXPECTED_BASE" ] || { echo 'exact NSS 4.31 base hash mismatch'; exit 11; }
[ -f "$WORK/xapk/config.tr.apk" ] || { echo 'config.tr.apk missing'; exit 12; }
[ -f "$WORK/xapk/config.xxhdpi.apk" ] || { echo 'config.xxhdpi.apk missing'; exit 13; }

# Test-only navigation and deterministic match patches. Save/load code stays stock.
python stage3_runtime/tools/patch_cloud_startup_bypass_for_persistence_test.py \
  "$BASE" "$WORK/base-cloud.apk" | tee "$OUT/cloud-patch.txt"
python stage3_runtime/tools/patch_trial_skip_for_persistence_test.py \
  "$WORK/base-cloud.apk" "$WORK/base-nav.apk" | tee "$OUT/trial-patch.txt"
python stage3_runtime/tools/patch_stage3_fast_match_probe.py \
  "$WORK/base-nav.apk" "$WORK/base-stage3-unsigned.apk" | tee "$OUT/stage3-fast-match-patch.txt"

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"
APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt \
  -keystore "$WORK/ci.keystore" -storepass android -keypass android -alias ci \
  -dname 'CN=NSS Reborn Stage3 CI' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1
sign_one(){
  local src="$1" dst="$2" aligned="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$aligned"
  "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci \
    --ks-pass pass:android --key-pass pass:android --out "$dst" "$aligned"
  "$APKSIGNER" verify --verbose "$dst" >/dev/null
}
sign_one "$WORK/base-stage3-unsigned.apk" "$WORK/signed/base.apk"
sign_one "$WORK/xapk/config.tr.apk" "$WORK/signed/config.tr.apk"
sign_one "$WORK/xapk/config.xxhdpi.apk" "$WORK/signed/config.xxhdpi.apk"

adb install-multiple -r \
  "$WORK/signed/base.apk" "$WORK/signed/config.tr.apk" "$WORK/signed/config.xxhdpi.apk" >/dev/null
adb shell pm clear "$PKG" >/dev/null || true

nss_runtime_failure(){
  local log="$1"
  grep -qE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$log"
}
fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  if nss_runtime_failure "$WORK/live-logcat.txt"; then
    cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" || true
    echo 'NSS-owned crash/ANR detected'
    return 1
  fi
}
wait_log(){
  local pattern="$1" timeout_s="${2:-30}" label="${3:-$1}" i
  for i in $(seq 0 "$timeout_s"); do
    fatal_check || return 1
    adb logcat -d -v brief > "$WORK/wait-logcat.txt" 2>/dev/null || true
    if grep -qiE "$pattern" "$WORK/wait-logcat.txt"; then
      echo "Reached $label after ${i}s"
      return 0
    fi
    sleep 1
  done
  cp "$WORK/wait-logcat.txt" "$OUT/timeout-${label//[^A-Za-z0-9_-]/_}.txt" 2>/dev/null || true
  echo "Timed out waiting for $label"
  return 1
}
shot(){ adb exec-out screencap -p > "$OUT/$1.png"; }
logical_xy(){
python - "$1" "$2" <<'PY'
import re,subprocess,sys
x,y=map(float,sys.argv[1:])
s=subprocess.check_output(['adb','shell','wm','size'],text=True)
w,h=map(int,re.search(r'(\d+)x(\d+)',s).groups())
scale=w/640.0; top=(h-960*scale)/2.0
print(round(x*scale),round(top+y*scale))
PY
}
press_logical(){
  local x y px py delay="${3:-2}"
  x="$1"; y="$2"
  read -r px py < <(logical_xy "$x" "$y")
  adb shell input touchscreen swipe "$px" "$py" "$px" "$py" 220 </dev/null || true
  sleep "$delay"
}
press_footer_ok(){ press_logical 536 880 "${1:-2}"; }
press_message_accept(){ press_logical 477 880 "${1:-2}"; }
press_play(){ press_logical 553 829 "${1:-2}"; }

start_game(){
  local tag="$1" i menu=0 resumed=0
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb logcat -c >/dev/null 2>&1 || true
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
  for i in $(seq 1 90); do
    sleep 1
    fatal_check || return 1
    adb logcat -d -v brief > "$WORK/${tag}-start.log" 2>/dev/null || true
    grep -qE 'Create Screen:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu' "$WORK/${tag}-start.log" && menu=1 || true
    adb shell dumpsys activity activities > "$WORK/${tag}-activity.txt" 2>/dev/null || true
    grep -qE 'ResumedActivity.*com\.newstargames\.newstarsoccer.*MonkeyGame|mResumedActivity.*com\.newstargames\.newstarsoccer.*MonkeyGame|topResumedActivity=.*com\.newstargames\.newstarsoccer.*MonkeyGame' "$WORK/${tag}-activity.txt" && resumed=1 || true
    if [ "$menu" -eq 1 ] && [ "$resumed" -eq 1 ]; then
      shot "${tag}-mainmenu"
      echo "MainMenu ready after ${i}s"
      return 0
    fi
  done
  echo "MainMenu startup failed menu=$menu resumed=$resumed"
  return 1
}

open_slot0(){
  local tag="$1"
  # Stock 4.31 mainmenu.uis: CareerButton center ~= (471,541) logical.
  adb logcat -c >/dev/null 2>&1 || true
  press_logical 471 541 2
  wait_log 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' 30 'saveslot'
  shot "${tag}-saveslot"
  # Stock saveslot.uis slot0 Load Career button center ~= (332,324) logical.
  press_logical 332 324 3
  fatal_check
}
load_slot0_after_open(){
  local tag="$1"
  sleep 2
  adb logcat -d -v brief > "$WORK/${tag}-load.txt" 2>/dev/null || true
  if ! grep -q 'LoadCareer saveslot: 0' "$WORK/${tag}-load.txt"; then
    press_message_accept 3
  fi
  adb logcat -d -v threadtime > "$OUT/${tag}-load-logcat.txt" 2>/dev/null || true
  grep -q 'LoadCareer saveslot: 0' "$OUT/${tag}-load-logcat.txt" || { echo "LoadCareer slot0 not observed ($tag)"; return 1; }
  fatal_check
}

# Fresh Career through stock setup and stock save path.
start_game fresh
open_slot0 fresh
wait_log 'Create Screen:[[:space:]]*chooseclub|SetActive:[[:space:]]*chooseclub|SETTING ACTIVE:[[:space:]]*chooseclub' 30 'chooseclub'
for _ in 1 2 3 4; do
  adb logcat -d -v brief > "$WORK/setup.txt" 2>/dev/null || true
  grep -qiE 'Create Screen:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation' "$WORK/setup.txt" && break
  press_footer_ok 2
  fatal_check
done
wait_log 'Create Screen:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation' 30 'choosenation'
adb logcat -c >/dev/null 2>&1 || true
press_footer_ok 2
wait_log 'LoadDataAndStartTrial|TrialDone|SetActive:[[:space:]]*message|SETTING ACTIVE:[[:space:]]*messagedefault|Create Screen:[[:space:]]*message' 30 'career message'
for _ in 1 2 3 4; do
  press_message_accept 2
  fatal_check
  adb logcat -d -v threadtime > "$WORK/save-progress.txt" 2>/dev/null || true
  grep -qE 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$WORK/save-progress.txt" && break
done
sleep 2
adb logcat -d -v threadtime > "$OUT/create-save-logcat.txt" 2>/dev/null || true
grep -qE 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$OUT/create-save-logcat.txt" || { echo 'fresh Career stock save not observed'; exit 101; }
wait_log 'Create Screen:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu' 30 'fresh gamemenu'
shot fresh-career-gamemenu

# Prove stock reload before starting the Stage3 lifecycle.
start_game pre-match-restart
open_slot0 pre-match-restart
load_slot0_after_open pre-match-restart
wait_log 'Create Screen:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu' 40 'loaded gamemenu'

# Root only for evidence reads from private prefs on the emulator.
adb root >/dev/null 2>&1 || true
adb wait-for-device
sleep 2

capture_log(){
  local label="$1"
  { echo; echo "===== $label ====="; adb logcat -d -v brief 2>/dev/null || true; } >> "$FLOW"
}
clear_log(){ adb logcat -c >/dev/null 2>&1 || true; }
current_state(){
  adb logcat -d -v brief > "$WORK/state.log" 2>/dev/null || true
  local line="$(grep -Ei 'SETTING ACTIVE:|SetActive:|Create Screen:' "$WORK/state.log" | tail -1 || true)"
  case "${line,,}" in
    *matchstats*) echo matchstats;; *matchreview*) echo matchreview;; *leaguefixtures*) echo leaguefixtures;; *gamemenu*) echo gamemenu;; *message*) echo message;;
    *" active: match"*|*"setactive: match"*|*"screen: match"*) echo match;;
    *" active: league"*|*"setactive: league"*|*"screen: league"*) echo league;;
    *) echo unknown;;
  esac
}
wait_state(){
  local wanted="$1" timeout_s="${2:-30}" i state
  for i in $(seq 0 "$timeout_s"); do
    fatal_check || return 1
    state="$(current_state)"
    if [[ " $wanted " == *" $state "* ]]; then echo "$state"; return 0; fi
    sleep 1
  done
  capture_log "timeout waiting state: $wanted"; echo unknown; return 1
}
dump_save(){
  local tag="$1" xml="$OUT/${tag}-MonkeyGame.xml" json="$OUT/${tag}-checkpoint.json"
  local remote="/data/data/$PKG/shared_prefs/MonkeyGame.xml"
  adb shell cat "$remote" > "$xml" 2>/dev/null || adb exec-out run-as "$PKG" cat "$remote" > "$xml" 2>/dev/null
  grep -q 'monkeystate' "$xml" || { echo "Career prefs unreadable ($tag)"; return 1; }
  python - "$xml" "$json" <<'PY'
import hashlib,json,sys,xml.etree.ElementTree as ET
xml,out=sys.argv[1:]
root=ET.parse(xml).getroot(); vals={n.attrib.get('name'):(n.text or '') for n in root.findall('string')}
state=vals.get('.monkeystate') or vals.get('gxtkAppState')
if state.startswith('#TWEAKS'):
 m='#ENDTWEAKS'; state=state[state.index(m)+len(m):].lstrip('\r\n')
r=state.split(';'); p=r[1].rstrip('\r\n').split(',')
def h(s):return hashlib.sha256(s.encode()).hexdigest()
obj={'sdate':int(p[0]),'clubid':int(p[2]),'careerapps':int(p[13]),'playerrecordsha256':h(r[1]),'clubrecordsha256':h(r[2]),'competitionrecordsha256':h(r[3]),'additionalclubrecordsha256':h(r[4])}
open(out,'w').write(json.dumps(obj,indent=2,sort_keys=True))
PY
}

dump_save pre-match
shot stage3-pre-match-gamemenu

# GameMenu -> LeagueFixtures.
clear_log; press_play 3
state="$(wait_state 'leaguefixtures message' 30 || true)"; capture_log 'GameMenu Play'
if [ "$state" = message ]; then clear_log; press_message_accept 3; state="$(wait_state 'leaguefixtures gamemenu' 30 || true)"; capture_log 'GameMenu message accepted'; fi
if [ "$state" = gamemenu ]; then clear_log; press_play 3; state="$(wait_state 'leaguefixtures message' 30 || true)"; capture_log 'second GameMenu Play'; fi
[ "$state" = leaguefixtures ] || { echo "Did not reach LeagueFixtures; state=$state"; exit 202; }
shot stage3-leaguefixtures-before-match

MATCH_REACHED=0
state=leaguefixtures
for step in $(seq 1 24); do
  clear_log
  case "$state" in leaguefixtures|gamemenu|league) press_play 3;; message) press_message_accept 3;; *) sleep 2;; esac
  state="$(wait_state 'match message leaguefixtures league gamemenu' 20 || true)"
  capture_log "pre-match state machine step $step -> $state"
  if [ "$state" = match ]; then MATCH_REACHED=1; break; fi
done
[ "$MATCH_REACHED" -eq 1 ] || { echo 'No playable Career match reached'; exit 203; }
shot stage3-match-prematch

clear_log; press_play 3; capture_log 'match Play -> probe StartMatch -> real MatchOver'; shot stage3-match-after-probe
clear_log; press_play 3
state="$(wait_state 'matchstats match' 30 || true)"; capture_log "match full-time Play -> $state"
if [ "$state" = match ]; then clear_log; press_play 3; state="$(wait_state 'matchstats match' 30 || true)"; capture_log "match full-time retry -> $state"; fi
[ "$state" = matchstats ] || { echo "Did not reach MatchStats; state=$state"; exit 204; }
shot stage3-matchstats

MY_MATCH_PLAYED=0; clear_log
for i in $(seq 1 24); do
  press_play 2
  adb logcat -d -v brief > "$WORK/matchstats-progress.log" 2>/dev/null || true
  if grep -qiE 'MyMatchPlayed|CallFunc:[[:space:]]*PlayToDate|SetActive:[[:space:]]*message' "$WORK/matchstats-progress.log"; then MY_MATCH_PLAYED=1; break; fi
done
capture_log 'MatchStats -> MyMatchPlayed'
[ "$MY_MATCH_PLAYED" -eq 1 ] || { echo 'MyMatchPlayed was not observed'; exit 205; }

PLAY_TO_DATE=0
for i in $(seq 1 8); do
  adb logcat -d -v brief > "$WORK/playtodate-progress.log" 2>/dev/null || true
  grep -qiE 'CallFunc:[[:space:]]*PlayToDate|PlayToDate' "$WORK/playtodate-progress.log" && PLAY_TO_DATE=1 || true
  state="$(current_state)"; [ "$state" = leaguefixtures ] && break
  press_message_accept 3
done
capture_log 'MyMatchPlayed -> PlayToDate -> results'
state="$(current_state)"; [ "$state" = leaguefixtures ] || state="$(wait_state 'leaguefixtures league gamemenu matchreview' 30 || true)"
[ "$PLAY_TO_DATE" -eq 1 ] || { echo 'PlayToDate continuation was not observed'; exit 206; }

for step in $(seq 1 16); do
  case "$state" in leaguefixtures|league) clear_log; press_play 3;; matchreview) clear_log; press_play 3;; gamemenu) break;; message) clear_log; press_message_accept 3;; *) sleep 2;; esac
  state="$(wait_state 'league matchreview gamemenu message leaguefixtures' 25 || true)"
  capture_log "post-match state machine step $step -> $state"
done
[ "$state" = gamemenu ] || { echo "Did not return to GameMenu; state=$state"; exit 207; }
shot stage3-post-match-gamemenu; sleep 2; capture_log 'post-match GameMenu final'; dump_save post-match

start_game stage3-restart
open_slot0 stage3-restart
load_slot0_after_open stage3-restart
wait_log 'Create Screen:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu' 40 'stage3 restart gamemenu'
capture_log 'restart -> LoadCareer -> GameMenu'; dump_save post-restart; shot stage3-post-restart-gamemenu

python - "$OUT/pre-match-MonkeyGame.xml" "$OUT/post-match-MonkeyGame.xml" "$OUT/post-restart-MonkeyGame.xml" "$FLOW" "$OUT/pre-match-checkpoint.json" "$OUT/post-match-checkpoint.json" "$OUT/post-restart-checkpoint.json" "$OUT/STAGE3_RUNTIME_VERIFICATION.txt" "$OUT/STAGE3_FIXTURE_RESULT_VERIFICATION.txt" <<'PY'
import hashlib,json,re,sys,xml.etree.ElementTree as ET
before_xml,after_xml,restart_xml,flow_path,bj,aj,rj,report,fixture_report=sys.argv[1:]
b=json.load(open(bj)); a=json.load(open(aj)); r=json.load(open(rj)); flow=open(flow_path,errors='replace').read()
checks=[
 (b['competitionrecordsha256']!=a['competitionrecordsha256'],'pre-match -> post-match competition block changed'),
 (a['competitionrecordsha256']==r['competitionrecordsha256'],'post-match competition block survives restart'),
 (a['clubrecordsha256']==r['clubrecordsha256'],'post-match club block survives restart'),
 (a['playerrecordsha256']==r['playerrecordsha256'],'post-match player block survives restart'),
 (a['sdate']==r['sdate'],'post-match Career date survives restart')]

def state(path):
 root=ET.parse(path).getroot(); vals={n.attrib.get('name'):(n.text or '') for n in root.findall('string')}; s=vals.get('.monkeystate') or vals.get('gxtkAppState')
 if s.startswith('#TWEAKS'):
  m='#ENDTWEAKS'; s=s[s.index(m)+len(m):].lstrip('\r\n')
 return s

def comp(path):return state(path).split(';')[3]
fields=('sdate','matchtype','round','groupno','leg','home','away','result','resulttype','score1','score2','penscore1','penscore2','level','compid','randno')
rx=re.compile(r'(?<![0-9/])(-?\d+(?:/-?\d+){14,15})\?')
def fixtures(s):
 out=[]
 for m in rx.finditer(s):
  v=[int(x) for x in m.group(1).split('/')]
  if len(v)==15:v.append(None)
  if len(v)==16:out.append(dict(zip(fields,v)))
 return out
dates={int(x) for x in re.findall(r'SetUpFixture:\s*(-?\d+)',flow,re.I)}
if len(dates)!=1:raise SystemExit(f'fixture gate: expected one SetUpFixture date, got {sorted(dates)}')
date=next(iter(dates)); club=b['clubid']
identity_fields=('sdate','matchtype','round','groupno','leg','home','away','level','compid','randno')
pre=[f for f in fixtures(comp(before_xml)) if f['sdate']==date and f['result']==0 and club in (f['home'],f['away'])]
if len(pre)!=1:raise SystemExit(f'fixture gate: unresolved selected fixture count={len(pre)}')
idt=tuple(pre[0][x] for x in identity_fields)
def find(path,label):
 hits=[f for f in fixtures(comp(path)) if tuple(f[x] for x in identity_fields)==idt]
 if len(hits)!=1:raise SystemExit(f'fixture gate: {label} identity count={len(hits)}')
 return hits[0]
after=find(after_xml,'post-match'); restart=find(restart_xml,'post-restart')
if [after['score1'],after['score2']]!=[1,0] or after['result']==0:raise SystemExit(f"fixture gate: expected resolved 1-0, got {after['score1']}-{after['score2']} result={after['result']}")
for k in ('result','resulttype','score1','score2','penscore1','penscore2'):
 if after[k]!=restart[k]:raise SystemExit(f'fixture gate: restart mismatch {k}')
lines=['NSS REBORN — ETAP 3 RUNTIME PERSISTENCE VERIFICATION']
for i,(ok,label) in enumerate(checks,1):lines.append(f"{'PASS' if ok else 'FAIL'} {i}/{len(checks)} {label}")
if not all(x[0] for x in checks):
 open(report,'w').write('\n'.join(lines)+'\nVERDICT=STAGE3_CHECKPOINT_GATE_FAIL\n');raise SystemExit('checkpoint gate failed')
lines+=['PASS runtime selected Career fixture reached Match screen','PASS TEST-ONLY StartMatch probe executed selected fixture 1-0 -> stock MatchOver path','PASS stock EndMatch boundary reached MatchStats','PASS stock MyMatchPlayed observed','PASS stock PlayToDate observed','PASS force-stop/restart stock LoadCareer slot 0 observed','VERDICT=STAGE3_CHECKPOINT_GATE_PASS']
open(report,'w').write('\n'.join(lines)+'\n')
flines=['NSS REBORN — ETAP 3 SELECTED FIXTURE VERIFICATION',f"PASS selected fixture date={date} club={club} home={after['home']} away={after['away']}",f"PASS selected fixture persisted score=1-0 result={after['result']} resulttype={after['resulttype']}",'VERDICT=STAGE3_SELECTED_FIXTURE_GATE_PASS']
open(fixture_report,'w').write('\n'.join(flines)+'\n')
print('\n'.join(lines));print('\n'.join(flines))
PY

for pattern in \
  'SETTING ACTIVE:.*match|SetActive:.*match|Create Screen:.*match' \
  'SETTING ACTIVE:.*matchstats|SetActive:.*matchstats|Create Screen:.*matchstats' \
  'MyMatchPlayed' 'PlayToDate' 'LoadCareer saveslot: 0' \
  'SETTING ACTIVE:.*gamemenu|SetActive:.*gamemenu|Create Screen:.*gamemenu'
do
  grep -qiE "$pattern" "$FLOW" || { echo "Missing runtime evidence: $pattern"; exit 208; }
done
if grep -qiE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$FLOW"; then
  echo 'NSS-owned crash/ANR found in Stage3 flow'; exit 209
fi
cat "$OUT/STAGE3_RUNTIME_VERIFICATION.txt"
cat "$OUT/STAGE3_FIXTURE_RESULT_VERIFICATION.txt"
echo 'STAGE3_PUBLIC_KVM_GATE=PASS'
