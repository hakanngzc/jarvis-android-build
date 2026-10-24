#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
text = src.read_text(encoding='utf-8')
old = '''sign_one(){ local src="$1" dst="$2" tmp="$WORK/aligned-$(basename "$dst")"; "$ZIPALIGN" -f 4 "$src" "$tmp"; "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$tmp"; "$APKSIGNER" verify --verbose "$dst" >/dev/null; }'''
new = '''sign_one(){
  local src="$1" dst="$2" tmp
  tmp="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$tmp"
  "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$tmp"
  "$APKSIGNER" verify --verbose "$dst" >/dev/null
}'''
if text.count(old) != 1:
    raise SystemExit(f'expected one nounset-unsafe sign_one helper, found {text.count(old)}')
text = text.replace(old, new)
dst.write_text(text, encoding='utf-8')
print(f'Prepared nounset-safe Stage2 gate: {dst}')
