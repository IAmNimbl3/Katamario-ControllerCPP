"""Observe production calibration with USB diagnostics; never activates demo."""
import json
from pathlib import Path
import statistics
import time
import serial

out = Path(__file__).resolve().parents[1] / 'output/tests/2026-10-20-sensor'
out.mkdir(parents=True, exist_ok=True)
rows, notes, ready = [], [], []
states = {}
with serial.Serial('COM4', 115200, timeout=.2) as port, (out/'production-calibration.log').open('w', encoding='utf-8') as log:
    warmup = time.monotonic()+3
    while time.monotonic() < warmup:
        line = port.readline().decode('utf-8', errors='replace').strip()
        if line:
            log.write(line+'\n')
            if line.startswith('#'):
                notes.append(line)
    port.write(b'r\nc\n')
    try:
        end = time.monotonic()+20
        while time.monotonic() < end:
            line = port.readline().decode('utf-8', errors='replace').strip()
            if not line:
                continue
            log.write(line+'\n')
            if line.startswith('# CALRAW,'):
                rows.append(list(map(float, line.split(',')[1:])))
            elif line.startswith('K2,'):
                f = line.split(',')
                if len(f)==9:
                    states[f[2]]=states.get(f[2],0)+1
                    if f[2]=='ready':
                        ready.append(list(map(float, f[3:])))
            elif line.startswith('#') and len(notes)<40:
                notes.append(line)
    finally:
        port.write(b'r\n')
        # Drain until diagnostics have explicitly been disabled.
        end = time.monotonic()+1
        while time.monotonic()<end:
            line = port.readline().decode('utf-8', errors='replace').strip()
            if line:
                log.write(line+'\n')
            if line=='# CALRAW_OFF':
                notes.append(line)
                break
report = dict(states=states, notes=notes, diagnostic_rows=len(rows))
if rows:
    report['sampled_accel_g_mean']=[statistics.mean(r[i] for r in rows) for i in range(3)]
    report['sampled_gyro_rad_s_mean']=[statistics.mean(r[i] for r in rows) for i in range(3,6)]
    report['best_consecutive_good']=max(r[9] for r in rows)
    report['observed_samples']=sum(int(r[10]) for r in rows)
    report['rejections']={name:sum(int(r[i]) for r in rows) for name,i in [('gyro',11),('x',12),('y',13),('z',14),('sample_gap',15)]}
if ready:
    report['ready_packets']=len(ready)
    report['max_ready_movement']=max((r[0]**2+r[1]**2)**.5 for r in ready)
(out/'production-calibration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
