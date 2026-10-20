"""Record one manually positioned pose from sensor-diagnostic firmware.

Usage: python test/capture_sensor_pose.py z_up --seconds 8
Records observations only; does not apply any calibration correction.
"""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import statistics
import time
import serial

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('pose', choices=['z_up', 'z_down', 'x_up', 'x_down', 'y_up', 'y_down'])
parser.add_argument('--seconds', type=float, default=8)
parser.add_argument('--port', default='COM4')
args = parser.parse_args()
directory = Path(__file__).resolve().parents[1] / 'output/tests/sensor-poses'
directory.mkdir(parents=True, exist_ok=True)
stem = directory / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + args.pose)
rows = []
with serial.Serial(args.port, 115200, timeout=.2) as port, stem.with_suffix('.log').open('w', encoding='utf-8') as log:
    # Opening USB may reset the ESP32. Discard startup and settling interval.
    warmup = time.monotonic() + 2
    while time.monotonic() < warmup:
        port.readline()
    end = time.monotonic() + args.seconds
    while time.monotonic() < end:
        line = port.readline().decode('ascii', errors='replace').strip()
        if not line:
            continue
        log.write(line + '\n')
        if line.startswith('RAW,'):
            try:
                row = list(map(float, line.split(',')[1:]))
                if len(row) == 17 and all(math.isfinite(v) for v in row):
                    rows.append(row)
            except ValueError:
                pass
valid = [r for r in rows if not (int(r[14]) & (32 | 64))]
report = dict(pose=args.pose, samples=len(rows), valid_samples=len(valid),
              bad_i2c=sum(bool(int(r[14]) & 64) for r in rows))
if valid:
    report['accel_g'] = {axis: dict(mean=statistics.mean(r[i] for r in valid),
                                  stdev=statistics.pstdev(r[i] for r in valid),
                                  min=min(r[i] for r in valid), max=max(r[i] for r in valid))
                         for axis, i in [('x', 7), ('y', 8), ('z', 9)]}
    report['gyro_dps_mean'] = [statistics.mean(r[i] for r in valid) for i in (10, 11, 12)]
    report['blocking_counts'] = {str(bit): sum(bool(int(r[14]) & bit) for r in valid) for bit in (1, 2, 4, 8, 16)}
stem.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
print('Saved:', stem.with_suffix('.json'))
raise SystemExit(0 if len(valid) >= 30 else 1)
