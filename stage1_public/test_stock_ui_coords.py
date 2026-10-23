#!/usr/bin/env python3
from stock_ui_coords import compute_coords

c = compute_coords(1080, 2280)
assert c['slot0'] == (550, 804), c['slot0']
assert c['slot1'] == (550, 1098), c['slot1']
assert c['slot2'] == (550, 1391), c['slot2']
assert c['delete1'] == (957, 1096), c['delete1']

# Real run-10 SaveSlot screenshot measured green action bands.
assert 752 <= c['slot0'][1] <= 860
assert 1045 <= c['slot1'][1] <= 1154
assert 1339 <= c['slot2'][1] <= 1448

print('STOCK_UI_COORDS_TEST=PASS')
