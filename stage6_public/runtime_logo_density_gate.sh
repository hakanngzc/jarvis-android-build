#!/usr/bin/env bash
set -euo pipefail

CASE="${STAGE6_MATRIX_CASE:?STAGE6_MATRIX_CASE is required}"
API="${STAGE6_MATRIX_API:?STAGE6_MATRIX_API is required}"
DPI="${STAGE6_MATRIX_DPI:?STAGE6_MATRIX_DPI is required}"
DENSITY_SPLIT="${STAGE6_DENSITY_SPLIT:?STAGE6_DENSITY_SPLIT is required}"
LANGUAGE_SPLIT="${STAGE6_LANGUAGE_SPLIT-}"
REAL_XAPK_DIR="${STOCK_XAPK_DIR:?STOCK_XAPK_DIR is required}"
ROOT="$PWD"
OUT="$ROOT/stage6_public_artifacts/runtime"
SHADOW="$RUNNER_TEMP/nss-stage6-density-$CASE-xapk"
mkdir -p "$OUT" "$SHADOW"

python3 stage6_public/density_matrix_contract.py \
  "$CASE" "$API" "$DPI" "$DENSITY_SPLIT" "$LANGUAGE_SPLIT"

test -f "$REAL_XAPK_DIR/$DENSITY_SPLIT"
if [ -n "$LANGUAGE_SPLIT" ]; then test -f "$REAL_XAPK_DIR/$LANGUAGE_SPLIT"; fi

python3 - "$REAL_XAPK_DIR" "$DENSITY_SPLIT" "$LANGUAGE_SPLIT" "$OUT/density-matrix-case.json" "$CASE" "$API" "$DPI" <<'PY'
import hashlib,json,sys,zipfile
from pathlib import Path
root=Path(sys.argv[1]); density=sys.argv[2]; language=sys.argv[3]; out=Path(sys.argv[4])
case=sys.argv[5]; api=int(sys.argv[6]); dpi=int(sys.argv[7])
def inspect(name):
    p=root/name
    raw=p.read_bytes()
    with zipfile.ZipFile(p) as z:
        ng=[n for n in z.namelist() if n.startswith('assets/monkey/NewGUI/')]
    if ng:
        raise SystemExit(f'{name} unexpectedly contains NewGUI assets: {ng[:5]}')
    return {'file':name,'sha256':hashlib.sha256(raw).hexdigest(),'newgui_asset_count':0}
data={'case':case,'api':api,'dpi':dpi,'density_split':inspect(density),'language_split':None}
if language:
    data['language_split']=inspect(language)
out.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print('STAGE6_DENSITY_SELECTED_SPLITS=PASS')
PY

# Reuse the already-proven Stage6 render gate unchanged. Its historical inputs are
# named config.xxhdpi.apk/config.tr.apk, so expose the selected real split APKs under
# those filenames while preserving their internal split manifests.
ln -sf "$REAL_XAPK_DIR/$DENSITY_SPLIT" "$SHADOW/config.xxhdpi.apk"
if [ -n "$LANGUAGE_SPLIT" ]; then
  ln -sf "$REAL_XAPK_DIR/$LANGUAGE_SPLIT" "$SHADOW/config.tr.apk"
fi
export STOCK_XAPK_DIR="$SHADOW"

adb wait-for-device
adb shell wm density "$DPI" > "$OUT/wm-density-set.txt" 2>&1
adb shell wm density > "$OUT/wm-density-before.txt" 2>&1
grep -q "$DPI" "$OUT/wm-density-before.txt"

bash stage6_public/runtime_logo_gate_v2.sh

adb shell wm density > "$OUT/wm-density-after.txt" 2>&1 || true
adb shell dumpsys package com.newstargames.newstarsoccer > "$OUT/density-package.txt" 2>&1 || true
grep -q "$DPI" "$OUT/wm-density-after.txt"

G="$OUT/stage6-logo-gates.txt"
printf 'STAGE6_DENSITY_MATRIX_CASE=PASS\n' >> "$G"
printf 'STAGE6_DENSITY_MATRIX_%s=PASS\n' "${CASE^^}" >> "$G"
printf 'STAGE6_DENSITY_MATRIX_API=%s\n' "$API" >> "$G"
printf 'STAGE6_DENSITY_MATRIX_DPI=%s\n' "$DPI" >> "$G"
printf 'STAGE6_DENSITY_MATRIX_DENSITY_SPLIT=%s\n' "$DENSITY_SPLIT" >> "$G"
printf 'STAGE6_DENSITY_MATRIX_LANGUAGE_SPLIT=%s\n' "${LANGUAGE_SPLIT:-none}" >> "$G"
echo "VERDICT=STAGE6_DENSITY_MATRIX_PASS case=$CASE api=$API dpi=$DPI density=$DENSITY_SPLIT language=${LANGUAGE_SPLIT:-none}"
