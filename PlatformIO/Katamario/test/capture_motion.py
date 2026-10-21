"""Capture paired sensor/world gyro samples over USB for ten minutes."""
import collections
import datetime
from pathlib import Path
import time
import sys
import serial

out = Path(__file__).resolve().parents[1] / 'output/tests/motion'
out.mkdir(parents=True, exist_ok=True)
path = out / (datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.log')
with serial.Serial('COM4', 115200, timeout=.2) as port, path.open('w', encoding='utf-8') as log:
    time.sleep(2)
    if '--recalibrate' in sys.argv:
        port.write(b'c\n')
    port.write(b'm\nr\n')
    start = bucket = time.monotonic()
    previous = None
    counts = collections.Counter()
    print('LOG ' + str(path), flush=True)
    try:
        while time.monotonic()-start < 600:
            line = port.readline().decode(errors='replace').strip()
            if not line:
                continue
            log.write(f'{time.monotonic()-start:.3f} {line}\n')
            log.flush()
            if line.startswith('K2,'):
                state = line.split(',')[2]
                counts[state] += 1
                if state != previous:
                    print('STATE ' + state, flush=True)
                    previous = state
            elif line.startswith('#'):
                if not line.startswith('# MOTION,'):
                    print(line, flush=True)
            if time.monotonic()-bucket >= 10:
                print(dict(elapsed=round(time.monotonic()-start), states=dict(counts)), flush=True)
                counts.clear()
                bucket = time.monotonic()
    finally:
        port.write(b'm\nr\n')
        port.flush()
