#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dex_inspect import Dex

MATCH = 'Lcom/newstargames/newstarsoccer/c_TMatch;'
SCREEN = 'Lcom/newstargames/newstarsoccer/c_TScreen_Match;'
TARGETS = {MATCH, SCREEN}
FOCUS = re.compile(
    r'Chance|Minute|Tick|Half|StartMatch|EndMatch|MatchOver|FastForward|Player|Pass|Drib|Shot|Shoot|Goal|Score|'
    r'Keeper|Defend|Attack|Cross|Header|Button|Play|Training|Instruction|Event|Action|Update',
    re.I,
)
DETAIL_METHODS = {'m_CheckFastForward', 'm_ShouldFastForward'}


def inspect_dex(path: Path, label: str):
    d = Dex(path)
    target_methods = {}
    lines = []
    for owner in TARGETS:
        for kind, mid, method, access, code in d.class_methods(owner) or []:
            if not FOCUS.search(method[1]):
                continue
            target_methods[mid] = (owner, method[1], kind, access, code)

    if not target_methods:
        return lines

    lines.append(f'EVENT_LOOP_DEX={label} FOCUS_METHODS={len(target_methods)}')
    for mid, (owner, name, kind, access, code) in sorted(target_methods.items()):
        lines.append(f'FOCUS_METHOD id={mid} owner={owner} name={name} kind={kind} access=0x{access:x} code=0x{code:x}')
        if not code:
            continue
        _regs, _ins, _outs, _tries, _size, items = d.disasm(code)
        if name in DETAIL_METHODS:
            lines.append(f'DETAIL_BEGIN method={owner}->{name} id={mid}')
            for off, op, args, raw in items:
                lines.append(f'DETAIL {off:05x} raw={raw:<28} op={op:<24} args={args}')
            lines.append(f'DETAIL_END method={owner}->{name} id={mid}')
        for off, op, args, raw in items:
            if not op.startswith('invoke-') or '[method@' not in args:
                continue
            m = re.search(r'\[method@(\d+)\]', args)
            if not m:
                continue
            called_id = int(m.group(1))
            if called_id >= len(d.methods):
                continue
            called_owner, called_name, _proto = d.methods[called_id]
            if called_owner.startswith('Lcom/newstargames/newstarsoccer/'):
                lines.append(
                    f'EDGE caller={owner}->{name} caller_id={mid} offset={off:05x} '
                    f'callee={called_owner}->{called_name} callee_id={called_id}'
                )
        for off, op, args, raw in items:
            if op.startswith('const-string') and args and FOCUS.search(args):
                lines.append(f'STRING_REF caller={owner}->{name} id={mid} offset={off:05x} value={args}')

    roots = {
        'm_StartMatch', 'm_IncrementMinute', 'm_UpdateChance', 'm_DoHalfEnds',
        'm_MatchOver', 'm_EndMatch', 'm_ButtonPlay', 'm_PlayerScored', 'm_AddStat',
        'm_CheckFastForward', 'm_ShouldFastForward',
    }
    by_name = {name: mid for mid, (_o, name, _k, _a, _c) in target_methods.items()}
    lines.append('ROOT_METHOD_IDS=' + ','.join(f'{name}:{by_name[name]}' for name in sorted(roots) if name in by_name))
    return lines


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit('usage: audit_stage3_event_loop.py BASE_APK')
    apk = Path(sys.argv[1])
    lines = []
    with zipfile.ZipFile(apk) as z, tempfile.TemporaryDirectory() as td:
        for name in z.namelist():
            if not re.fullmatch(r'classes\d*\.dex', Path(name).name):
                continue
            out = Path(td) / Path(name).name
            out.write_bytes(z.read(name))
            lines.extend(inspect_dex(out, Path(name).name))
    print('STAGE3_EVENT_LOOP_AUDIT')
    text = '\n'.join(lines)
    print(text)
    required = ['m_StartMatch', 'm_IncrementMinute', 'm_UpdateChance', 'm_DoHalfEnds', 'm_MatchOver', 'm_EndMatch', 'm_CheckFastForward', 'm_ShouldFastForward']
    missing = [x for x in required if x not in text]
    if missing:
        raise SystemExit(f'missing event-loop roots: {missing}')
    print('VERDICT=STAGE3_EVENT_LOOP_AUDIT_PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
