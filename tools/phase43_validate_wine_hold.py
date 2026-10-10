#!/usr/bin/env python3
"""Validate Wine hold GIFs show real gait (player-crop MAD + unique poses)."""
from __future__ import annotations
import json, sys
from pathlib import Path
from PIL import Image, ImageSequence
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HOLD = ROOT / 'assets/samples/phase43/wine_hold'
KEYS = ['W', 'A', 'S', 'D', 'WA', 'WD', 'SA', 'SD']
REQUIRED = [f'hold_{k}.gif' for k in KEYS] + [f'run_hold_{k}.gif' for k in KEYS]


def score(path: Path, uniq_thresh=5.0):
    frs = [np.asarray(f.convert('RGB'), dtype=np.float32)
           for f in ImageSequence.Iterator(Image.open(path))]
    if len(frs) < 4:
        return dict(ok=False, mad=0.0, uniq=0, n=len(frs), reason='too_few_frames')
    h, w = frs[0].shape[:2]
    y0, y1 = h // 2 - 25, h // 2 + 75
    x0, x1 = w // 2 - 40, w // 2 + 40
    crops = [f[y0:y1, x0:x1] for f in frs]
    diffs = [float(np.abs(a - b).mean()) for a, b in zip(crops, crops[1:])]
    mad = sum(diffs) / max(1, len(diffs))
    reps = [crops[0]]
    for c in crops[1:]:
        if min(float(np.abs(c - r).mean()) for r in reps) > uniq_thresh:
            reps.append(c)
    ok = mad >= 4.0 and len(reps) >= 3 and path.stat().st_size > 20000
    reason = None
    if not ok:
        if mad < 1.5:
            reason = 'idle_or_static'
        elif len(reps) < 3:
            reason = 'weak_gait_uniq'
        else:
            reason = 'weak_mad_or_small'
    return dict(ok=ok, mad=round(mad, 3), uniq=len(reps), n=len(frs), reason=reason)


def main():
    hold = Path(sys.argv[1]) if len(sys.argv) > 1 else HOLD
    missing, bad, good = [], [], []
    report = {}
    for name in REQUIRED:
        p = hold / name
        if not p.exists():
            missing.append(name)
            report[name] = dict(ok=False, reason='missing')
            continue
        st = score(p)
        report[name] = st
        (good if st['ok'] else bad).append(name)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f'OK {len(good)}/16  BAD {len(bad)}  MISSING {len(missing)}', file=sys.stderr)
    return 0 if not missing and not bad else 1


if __name__ == '__main__':
    raise SystemExit(main())
