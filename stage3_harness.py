#!/usr/bin/env python3
import argparse
import json
import re
import sys

SCREEN_RE = re.compile(r'(?:SETTING ACTIVE:|SetActive:|Create Screen:)\s*([A-Za-z0-9_]+)', re.I)

SCREEN_STATES = {
    'matchstats': ('matchstats', 'matchstats'),
    'matchreview': ('matchreview', 'matchreview'),
    'leaguefixtures': ('leaguefixtures', 'prematch'),
    'gamemenu': ('gamemenu', 'career'),
    'choosenation': ('choosenation', 'setup'),
    'chooseclub': ('chooseclub', 'setup'),
    'message': ('message', 'message'),
    'messagedefault': ('message', 'message'),
    'match': ('match', 'match'),
    'league': ('league', 'postmatch'),
}

GAMEPLAY_SIGNALS = (
    (re.compile(r'USE\s+player\.matchReviewBuxAwarded', re.I), 'weeklyreport', 'weeklyreport'),
    (re.compile(r'Award\s+Currency', re.I), 'weeklyreport', 'weeklyreport'),
    (re.compile(r'\bMatchOver\b', re.I), 'fulltime', 'fulltime'),
)

NSS_FAULT_RE = re.compile(
    r'ANR in com\.newstargames\.newstarsoccer|'
    r'Process:\s*com\.newstargames\.newstarsoccer,\s*PID:|'
    r'FATAL EXCEPTION.*com\.newstargames\.newstarsoccer',
    re.I | re.S,
)

EMULATOR_FAULT_RE = re.compile(
    r'ANR in (?:com\.android\.systemui|com\.google\.android\.apps\.nexuslauncher|com\.android\.launcher\w*)|'
    r'(?:SystemUI|Launcher).*ANR|'
    r'OutOfMemoryError|lowmemorykiller|lmkd.*kill|'
    r'emulator.*(?:crash|fatal)',
    re.I | re.S,
)


def _event(state, phase, signal, line_no):
    return {'state': state, 'phase': phase, 'signal': signal.strip(), 'line': line_no}


def detect_state(log_text):
    latest = _event('unknown', 'unknown', '', -1)
    for line_no, line in enumerate(log_text.splitlines(), 1):
        screen = SCREEN_RE.search(line)
        if screen:
            name = screen.group(1).lower()
            if name in SCREEN_STATES:
                state, phase = SCREEN_STATES[name]
                latest = _event(state, phase, line, line_no)
        for pattern, state, phase in GAMEPLAY_SIGNALS:
            if pattern.search(line):
                latest = _event(state, phase, line, line_no)
                break
    return latest


def classify_failure(log_text, process_alive):
    if NSS_FAULT_RE.search(log_text):
        return 'nss'
    if EMULATOR_FAULT_RE.search(log_text):
        return 'emulator'
    if process_alive:
        return 'harness'
    return 'unknown'


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    state_parser = sub.add_parser('state')
    state_parser.add_argument('--json', action='store_true')
    classify_parser = sub.add_parser('classify')
    classify_parser.add_argument('--process-alive', action='store_true')
    args = parser.parse_args(argv)
    text = sys.stdin.read()
    if args.command == 'state':
        result = detect_state(text)
        print(json.dumps(result) if args.json else result['state'])
        return 0
    print(classify_failure(text, args.process_alive))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
