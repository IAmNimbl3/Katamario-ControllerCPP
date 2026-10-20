"""Bench check of the existing synthetic demo on an ESP32, no sensor required."""
import json
import math
from pathlib import Path
import statistics
import time
import serial
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1] / 'output' / 'tests' / '2026-10-14-demo')
out = parser.parse_args().out
out.mkdir(parents=True, exist_ok=True)
records = []
checks = {}
with (out / 'serial.log').open('w', encoding='utf-8') as log:
    with serial.Serial('COM4', 115200, timeout=0.2) as port:
        def capture(seconds, stage):
            rows = []
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                line = port.readline().decode('utf-8', errors='replace').strip()
                if not line:
                    continue
                log.write(f'{stage}: {line}\n')
                log.flush()
                if line.startswith('K2,'):
                    fields = line.split(',')
                    if len(fields) != 9:
                        raise ValueError(f'Malformed packet: {line}')
                    row = (int(fields[1]), fields[2], *map(float, fields[3:]))
                    rows.append(row)
                    records.append((stage, line))
            return rows

        try:
            initial = capture(3, 'initial')
            checks['waiting_without_sensor'] = bool(initial) and all(r[1] == 'waiting' and r[2:4] == (0.0, 0.0) for r in initial[-30:])
            port.write(b'h\n')
            capture(1, 'help')
            port.write(b'd\n')
            demo = [r for r in capture(33, 'demo') if r[1] == 'demo']
            if not demo:
                raise RuntimeError('No demo packets received')
            start = demo[0][0]
            expected = [(0, 0), (0, .2463), (0, .7935), (0, 0), (.4716, 0), (0, -.4716), (-.4716, 0), (0, 0)]
            phases = []
            for cycle in range(2):
                for phase, target in enumerate(expected):
                    # Ignore 150 ms at boundaries; first packet follows command by <=20 ms.
                    rows = [r for r in demo if cycle*16000+phase*2000+150 <= r[0]-start < cycle*16000+(phase+1)*2000-150]
                    error = max((max(abs(r[2]-target[0]), abs(r[3]-target[1])) for r in rows), default=999)
                    passed = len(rows) >= 70 and error < .002
                    checks[f'cycle_{cycle+1}_phase_{phase}'] = passed
                    phases.append(dict(cycle=cycle+1, phase=phase, samples=len(rows), expected=target, max_error=error))
            checks['finite_values'] = all(math.isfinite(v) for r in demo for v in r[2:])
            norm_error = max(abs(math.sqrt(sum(v*v for v in r[4:]))-1) for r in demo)
            checks['unit_quaternions'] = norm_error < .00001
            gaps = [b[0]-a[0] for a,b in zip(demo,demo[1:])]
            checks['monotonic_timestamps'] = min(gaps) > 0
            checks['stream_cadence'] = max(gaps) <= 60
            checks['bounded_movement'] = all(math.hypot(r[2],r[3]) <= 1.0001 for r in demo)
            port.write(b'd\n')
            restarted = capture(1, 'restart')
            checks['restart_at_rest'] = bool(restarted) and all(r[1]=='demo' and r[2:4] == (0.0,0.0) for r in restarted[-20:])
        finally:
            port.write(b'c\n')
            stopped = capture(2, 'stop')
            checks['return_to_waiting'] = bool(stopped) and all(r[1]=='waiting' and r[2:4] == (0.0,0.0) for r in stopped[-30:])

report = dict(checks=checks, passed=all(checks.values()), demo_packets=len(demo),
              cadence_ms=dict(min=min(gaps), median=statistics.median(gaps), max=max(gaps)),
              max_quaternion_norm_error=norm_error, phases=phases)
(out / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
raise SystemExit(0 if report['passed'] else 1)
