"""Kyuboru bench receiver, no Unity dependency.

USB: python tools/receiver.py --port COM4 --command d --seconds 35
SPP: use the outgoing virtual COM port assigned by Windows after pairing.
Android: connect an RFCOMM/SPP terminal to Kyuboru, not a BLE-only terminal.

Wire protocol: ASCII lines, LF terminated (CRLF accepted).
K2,millis,status,right,forward,qw,qx,qy,qz
millis is ESP32 uptime uint32, wraps at ~49.7 days, NOT wall-clock time.
Axes: X right, Y forward, Z up; quaternion order w,x,y,z. No Unity axis
conversion here. Movement is normalized; only ready/demo enable movement.
Comments/replies begin #. Commands are single bytes d/c/a/h; CR/LF ignored.
d starts/restarts synthetic demo; c exits demo and reconnects/recalibrates;
a confirms ONLY awaiting_alignment; h help. BYPASS_ALIGNMENT remains true.

--timeout is a local reception watchdog, not loss of sensor orientation.
On stale input/disconnect effective movement is zero and orientation invalid.
Fresh valid data restores the receiver; firmware alignment policy is separate.
This bench protocol has no command IDs, retries, authentication layer or
exclusive controller ownership. Use one trusted client; not a final game API.
"""
import argparse
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Packet:
    millis: int
    status: str
    right: float
    forward: float
    q: tuple


def parse(line):
    if not line.startswith('K2,'):
        return None
    fields = line.split(',')
    if len(fields) != 9:
        raise ValueError('field count')
    tick = int(fields[1])
    status = fields[2]
    values = tuple(map(float, fields[3:]))
    if not 0 <= tick <= 0xffffffff or status not in {'waiting', 'awaiting_alignment', 'calibrating', 'ready', 'demo'}:
        raise ValueError('timestamp/status')
    if not all(math.isfinite(v) for v in values):
        raise ValueError('nonfinite')
    if math.hypot(*values[:2]) > 1.001 or abs(sum(v*v for v in values[2:])-1) > .005:
        raise ValueError('movement/quaternion range')
    return Packet(tick, status, *values[:2], values[2:])


class Receiver:
    def __init__(self, timeout=.5):
        if timeout <= 0:
            raise ValueError('timeout must be positive')
        self.timeout = timeout
        self.buffer = bytearray()
        self.dropping = False
        self.packet = None
        self.received = None
        self.count = self.invalid = 0

    def feed(self, data, now):
        for byte in data:
            if byte == 10:
                if not self.dropping:
                    try:
                        packet = parse(self.buffer.decode('ascii').rstrip('\r'))
                        if packet:
                            self.packet, self.received = packet, now
                            self.count += 1
                    except (ValueError, UnicodeError):
                        self.invalid += 1
                self.buffer.clear()
                self.dropping = False
            elif not self.dropping:
                self.buffer.append(byte)
                if len(self.buffer) > 256:
                    self.invalid += 1
                    self.buffer.clear()
                    self.dropping = True

    def snapshot(self, now):
        stale = self.received is None or now-self.received >= self.timeout
        p = self.packet
        active = not stale and p.status in {'ready', 'demo'}
        return dict(state='stale' if stale else p.status,
                    right=p.right if active else 0, forward=p.forward if active else 0,
                    orientation_valid=not stale and p.status in {'ready', 'demo'},
                    q=None if stale else p.q, packets=self.count, invalid=self.invalid)


def main():
    import serial
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--port', required=True)
    parser.add_argument('--command', choices=['d', 'c', 'a', 'h'])
    parser.add_argument('--seconds', type=float, default=35)
    parser.add_argument('--timeout', type=float, default=.5)
    parser.add_argument('--log', type=Path)
    args = parser.parse_args()
    if args.seconds <= 0 or args.timeout <= 0:
        parser.error('seconds and timeout must be positive')
    receiver = Receiver(args.timeout)
    log = None
    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        log = args.log.open('wb')
    try:
        with serial.Serial(args.port, 115200, timeout=.05, write_timeout=1) as port:
            # USB open may reset ESP32. Allow Bluetooth initialization to finish.
            warmup = time.monotonic()+4
            while time.monotonic() < warmup:
                port.read(max(1, min(port.in_waiting, 4096)))
            if args.command:
                port.write((args.command+'\n').encode('ascii'))
            start = last_print = time.monotonic()
            try:
                while time.monotonic()-start < args.seconds:
                    data = port.read(max(1, min(port.in_waiting, 4096)))
                    now = time.monotonic()
                    if log:
                        log.write(data)
                    receiver.feed(data, now)
                    if now-last_print >= .5:
                        print(json.dumps(receiver.snapshot(now)), flush=True)
                        last_print = now
            finally:
                if args.command == 'd' and port.is_open:
                    try:
                        port.write(b'c\n')
                    except serial.SerialException:
                        pass
        return 0 if receiver.count and not receiver.invalid and receiver.snapshot(time.monotonic())['state'] != 'stale' else 1
    except (serial.SerialException, OSError) as error:
        receiver.received = None
        print(json.dumps(dict(error=str(error), **receiver.snapshot(time.monotonic()))))
        return 1
    except KeyboardInterrupt:
        return 130
    finally:
        if log:
            log.close()


if __name__ == '__main__':
    raise SystemExit(main())
