#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: run_stage4_natural_gate.sh GATE" >&2
  exit 2
fi

GATE="$1"
[ -f "$GATE" ] || { echo "missing Stage4 gate: $GATE" >&2; exit 2; }

XAPK_SHA='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'
BASE_SHA='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'
XAPK_PATH="${RUNNER_TEMP:?}/stage4-natural-work/nss431.xapk"
BASE_PATH="${RUNNER_TEMP:?}/stage4-natural-work/xapk/com.newstargames.newstarsoccer.apk"

rc=0
for setup_attempt in 1 2 3; do
  echo "Stage4 natural gate setup attempt $setup_attempt/3"
  set +e
  bash "$GATE"
  rc=$?
  set -e
  [ "$rc" -eq 0 ] && break

  # A stock-source SHA mismatch currently surfaces from the gate as generic
  # rc=1. Reinterpret only that proven setup condition; ordinary gameplay
  # rc=1 remains fatal and is never retried.
  if [ "$rc" -eq 1 ]; then
    if [ -f "$XAPK_PATH" ] && ! echo "$XAPK_SHA  $XAPK_PATH" | sha256sum -c - >/dev/null 2>&1; then
      echo "source-integrity XAPK mismatch -> retry rc=214"
      rc=214
    elif [ -f "$BASE_PATH" ] && ! echo "$BASE_SHA  $BASE_PATH" | sha256sum -c - >/dev/null 2>&1; then
      echo "source-integrity base APK mismatch -> retry rc=215"
      rc=215
    fi
  fi

  case "$rc" in
    214|215|218|219)
      mkdir -p "${RUNNER_TEMP:?}/stage4-natural"
      echo "setup-only retry after rc=$rc attempt=$setup_attempt" >> "$RUNNER_TEMP/stage4-natural/setup-retries.log"
      # Attempts generate a fresh CI signing key. Remove any package signed by
      # the previous attempt and clear extracted/signing state before retrying.
      adb uninstall com.newstargames.newstarsoccer >/dev/null 2>&1 || true
      rm -rf "${RUNNER_TEMP:?}/stage4-natural-work"
      ;;
    *) exit "$rc";;
  esac
done

[ "$rc" -eq 0 ] || exit "$rc"
