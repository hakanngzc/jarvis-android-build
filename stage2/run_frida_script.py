#!/usr/bin/env python3
import argparse
import json
import threading
from pathlib import Path

import frida


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--package', default='com.newstargames.newstarsoccer')
    ap.add_argument('--script', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--timeout', type=float, default=15.0)
    args = ap.parse_args()

    result = {'ok': False, 'events': []}
    done = threading.Event()

    def on_message(message, data):
        result['events'].append(message)
        payload = message.get('payload') if message.get('type') == 'send' else None
        if isinstance(payload, dict) and payload.get('type') == 'stage2-smoke':
            result.update(payload)
            done.set()

    device = frida.get_usb_device(timeout=10)
    session = device.attach(args.package)
    script = session.create_script(args.script.read_text(encoding='utf-8'))
    script.on('message', on_message)
    script.load()
    if not done.wait(args.timeout):
        result['error'] = 'timeout waiting for stage2-smoke message'
    try:
        script.unload()
    except Exception:
        pass
    try:
        session.detach()
    except Exception:
        pass

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding='utf-8')
    print(json.dumps(result, sort_keys=True))
    if not result.get('ok'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
