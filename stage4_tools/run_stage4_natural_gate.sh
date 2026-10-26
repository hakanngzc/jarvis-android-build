#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: run_stage4_natural_gate.sh GATE" >&2
  exit 2
fi

GATE="$1"
[ -f "$GATE" ] || { echo "missing Stage4 gate: $GATE" >&2; exit 2; }

stock_source_mismatch(){
  local work="${RUNNER_TEMP:?}/stage4-natural-work"
  local xapk="$work/nss431.xapk"
  local base="$work/xapk/com.newstargames.newstarsoccer.apk"
  local expected_xapk expected_base actual

  expected_xapk="$(sed -n "s/^XAPK_SHA='\([^']*\)'.*/\1/p" "$GATE" | head -1)"
  expected_base="$(sed -n "s/^BASE_SHA='\([^']*\)'.*/\1/p" "$GATE" | head -1)"

  if [ -n "$expected_xapk" ] && [ -f "$xapk" ]; then
    actual="$(sha256sum "$xapk" | awk '{print $1}')"
    if [ "$actual" != "$expected_xapk" ]; then
      echo "stock XAPK sha mismatch: expected=$expected_xapk actual=$actual" >&2
      return 0
    fi
  fi

  if [ -n "$expected_base" ] && [ -f "$base" ]; then
    actual="$(sha256sum "$base" | awk '{print $1}')"
    if [ "$actual" != "$expected_base" ]; then
      echo "stock base APK sha mismatch: expected=$expected_base actual=$actual" >&2
      return 0
    fi
  fi

  return 1
}

rc=0
for setup_attempt in 1 2 3; do
  echo "Stage4 natural gate setup attempt $setup_attempt/3"
  set +e
  bash "$GATE"
  rc=$?
  set -e
  [ "$rc" -eq 0 ] && break

  if [ "$rc" -eq 1 ] && stock_source_mismatch; then
    rc=219
  fi

  case "$rc" in
    218|219)
      mkdir -p "${RUNNER_TEMP:?}/stage4-natural"
      echo "setup-only retry after rc=$rc attempt=$setup_attempt" >> "$RUNNER_TEMP/stage4-natural/setup-retries.log"
      rm -rf "${RUNNER_TEMP:?}/stage4-natural-work"
      ;;
    *) exit "$rc";;
  esac
done

[ "$rc" -eq 0 ] || exit "$rc"
