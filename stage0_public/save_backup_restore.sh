#!/usr/bin/env bash
set -euo pipefail
PKG="${NSS_PACKAGE:-com.newstargames.newstarsoccer}"
PREF_REL="shared_prefs/MonkeyGame.xml"
ADB="${ADB:-adb}"
: "${APKSIGNER:?APKSIGNER must be set for the public verification bundle}"
usage(){ echo "usage: $0 backup <directory> | restore <directory>" >&2; exit 2; }
installed_base_apk(){ "$ADB" shell pm path "$PKG" | sed -n 's/^package://p' | head -1 | tr -d '\r'; }
installed_signer_sha256(){ local remote tmp signer; remote="$(installed_base_apk)"; [[ -n "$remote" ]] || return 2; tmp="$(mktemp --suffix=.apk)"; "$ADB" exec-out cat "$remote" > "$tmp"; signer="$("$APKSIGNER" verify --print-certs "$tmp" | sed -n 's/^Signer #1 certificate SHA-256 digest: //p' | head -1 | tr 'A-F' 'a-f' | tr -d '\r')"; rm -f "$tmp"; printf '%s\n' "$signer"; }
backup(){ local out="$1" xml="$1/MonkeyGame.xml" meta="$1/metadata.json" sha signer android; mkdir -p "$out"; "$ADB" wait-for-device; "$ADB" shell run-as "$PKG" test -f "$PREF_REL" || { echo "save preferences missing: $PREF_REL" >&2; exit 3; }; "$ADB" shell am force-stop "$PKG" >/dev/null; "$ADB" exec-out run-as "$PKG" cat "$PREF_REL" > "$xml"; [[ -s "$xml" ]] || exit 4; sha="$(sha256sum "$xml"|awk '{print $1}')"; signer="$(installed_signer_sha256)"; [[ "$signer" =~ ^[0-9a-f]{64}$ ]] || exit 5; android="$($ADB shell getprop ro.build.version.release|tr -d '\r')"; SIGNER_SHA256="$signer" SAVE_SHA256="$sha" ANDROID_VERSION="$android" OUT_META="$meta" PKG="$PKG" python3 - <<'PY'
import json,os
m={'schema':1,'package':os.environ['PKG'],'preferences_file':'MonkeyGame.xml','run_as_path':'shared_prefs/MonkeyGame.xml','save_sha256':os.environ['SAVE_SHA256'],'SIGNER_SHA256':os.environ['SIGNER_SHA256'],'android_version':os.environ['ANDROID_VERSION']}
with open(os.environ['OUT_META'],'w') as f: json.dump(m,f,indent=2,sort_keys=True);f.write('\n')
PY
 echo "BACKUP_OK save_sha256=$sha SIGNER_SHA256=$signer path=$out"; }
restore(){ local src="$1" xml="$1/MonkeyGame.xml" meta="$1/metadata.json" expected_sha expected_signer actual_sha current_signer remote_sha; [[ -f "$xml" && -f "$meta" ]] || exit 6; read -r expected_sha expected_signer < <(python3 - "$meta" "$PKG" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]));assert d['package']==sys.argv[2];assert d['preferences_file']=='MonkeyGame.xml';print(d['save_sha256'],d['SIGNER_SHA256'])
PY
); actual_sha="$(sha256sum "$xml"|awk '{print $1}')"; [[ "$actual_sha" == "$expected_sha" ]] || { echo 'refusing restore: backup SHA-256 mismatch' >&2; exit 7; }; current_signer="$(installed_signer_sha256)"; [[ "$current_signer" == "$expected_signer" ]] || { echo 'refusing restore: installed SIGNER_SHA256 does not match backup signer' >&2; exit 8; }; "$ADB" shell am force-stop "$PKG" >/dev/null; "$ADB" shell run-as "$PKG" mkdir -p shared_prefs; cat "$xml" | "$ADB" shell run-as "$PKG" sh -c "cat > '$PREF_REL.tmp' && chmod 600 '$PREF_REL.tmp' && mv '$PREF_REL.tmp' '$PREF_REL'"; remote_sha="$("$ADB" exec-out run-as "$PKG" cat "$PREF_REL"|sha256sum|awk '{print $1}')"; [[ "$remote_sha" == "$expected_sha" ]] || { echo 'refusing restore: post-write SHA-256 mismatch' >&2; exit 9; }; echo "RESTORE_OK save_sha256=$remote_sha SIGNER_SHA256=$current_signer"; }
[[ $# -eq 2 ]] || usage
case "$1" in backup) backup "$2";; restore) restore "$2";; *) usage;; esac
