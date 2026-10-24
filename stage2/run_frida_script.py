#!/usr/bin/env python3
import argparse
import json
import threading
from pathlib import Path

import frida


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--package', default='com.newstargames.newstarsoccer')
    ap.add_argument('--pid', type=int)
    ap.add_argument('--script', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--event-type', default='stage2-smoke')
    ap.add_argument('--timeout', type=float, default=15.0)
    args = ap.parse_args()

    result = {'ok': False, 'event_type': args.event_type, 'events': []}
    done = threading.Event()

    def write_result() -> None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding='utf-8')
        print(json.dumps(result, sort_keys=True))

    def on_message(message, data):
        result['events'].append(message)
        payload = message.get('payload') if message.get('type') == 'send' else None
        if isinstance(payload, dict) and payload.get('type') == args.event_type:
            result.update(payload)
            done.set()

    device = frida.get_usb_device(timeout=10)
    target = args.pid if args.pid else args.package
    result['attach_target'] = target
    try:
        session = device.attach(args.pid if args.pid else args.package)
    except frida.ProcessNotFoundError as exc:
        result['error'] = f'process not found during Frida attach: {exc}'
        write_result()
        raise SystemExit(1)

    script = session.create_script(args.script.read_text(encoding='utf-8'))
    script.on('message', on_message)
    script.load()
    if not done.wait(args.timeout):
        result['error'] = f'timeout waiting for {args.event_type} message'
    try:
        script.unload()
    except Exception:
        pass
    try:
        session.detach()
    except Exception:
        pass

    write_result()
    if not result.get('ok'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
