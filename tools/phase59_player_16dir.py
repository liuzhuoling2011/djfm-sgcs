"""Phase59: player paper-doll from graph 901 (CA/HD/TK/LA/RA/LE/RE/JQ/RH=167) using Spr groups.
Actions are res pairs × 16 dirs. Mac recording 2 template match: walk = res6 (8 fr), run = res10 (7 fr, forward lean);
16-dir index: E=0, NE=2, N=4, NW=6, W=8, SW=10, S=12, SE=14. Frames past the listed Spr frames reuse the last offset.
Reproduce: python3 tools/phase59_player_16dir.py"""
import sys, json
sys.path.insert(0, '/workspace/djfm-sgcs/tools')
from phase59_act16 import frame16
from pathlib import Path
OUT = Path('/workspace/djfm-sgcs/web/public/game/player')
ART16 = {0: 12, 1: 10, 2: 8, 3: 6, 4: 4, 5: 2, 6: 0, 7: 14}  # web art S,SW,W,NW,N,NE,E,SE
ACT = {'walk': (6, 8), 'run': (10, 7)}
for a in ('walk', 'run', 'idle'):
    (OUT / a).mkdir(parents=True, exist_ok=True)
    for p in (OUT / a).glob('*.png'): p.unlink()
for art, d16 in ART16.items():
    for name, (res, n) in ACT.items():
        for f in range(n):
            frame16(res, d16, f).crop((16, 20, 144, 148)).save(OUT / name / f'{art}_{f}.png')
    frame16(6, d16, 0).crop((16, 20, 144, 148)).save(OUT / 'idle' / f'{art}_0.png')
m = json.load(open(OUT / 'meta.json'))
m.update({'walk_frames': 8, 'run_frames': 7, 'gait': 'sequential', 'source': 'Phase59 graph901 res6 walk / res10 run, 16-dir idx E0 N4 W8 S12', 'art16': ART16})
json.dump(m, open(OUT / 'meta.json', 'w'), indent=1, ensure_ascii=False)
print('ok')
