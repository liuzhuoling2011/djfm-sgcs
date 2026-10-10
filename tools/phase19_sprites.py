#!/usr/bin/env python3
"""Phase 19: export player paper-doll (ResPlayer1 legs+body) and town NPC sheets."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leyilib as L, bld_rle as B

ROOT = Path(__file__).resolve().parents[1]
Z = ROOT / 'extract/Blade And Sword 2 Ancient Legend/zy'
WEB = ROOT / 'web/public/game'

# EventID -> ResNpc3 entry (visual match; Role.graph often paper-doll shadow-only)
NPC_MAP = {
    'sy': 1008, 'zs': 1014, 'cjg': 1007, 'sws': 624, 'tj': 630, 'gbw': 625,
    'td': 618, 'cds': 1109, 'bq': 620, 'zhs': 620, 'xn': None,
}
ROLE_GRAPH = {
    'td': 618, 'cds': 619, 'cjg': 621, 'bq': 622, 'sy': 623, 'sws': 624,
    'tj': 627, 'zhs': 628, 'zs': 629, 'gbw': 630, 'xn': 661,
}

def decode_entry(r, idx):
    out = []
    for _, lep in L.find_nested_leps(r.entry_bytes(idx)):
        try: im = B.decode(lep)
        except Exception: continue
        if im is None: continue
        if (np.array(im)[:, :, 3] > 0).sum() < 40: continue
        out.append(im)
    return out

def foot(im):
    a = np.array(im); ys, xs = np.where(a[:, :, 3] > 0)
    return float(xs[ys == ys.max()].mean()), float(ys.max())

def composite(leg, torso):
    fx, fy = 60.0, 100.0
    lx, ly = foot(leg)
    c = Image.new('RGBA', (120, 120), (0, 0, 0, 0))
    c.paste(leg, (int(fx - lx), int(fy - ly)), leg)
    bb = torso.getbbox() or (0, 0, torso.width, torso.height)
    t_cx = (bb[0] + bb[2]) / 2; t_bottom = bb[3] - 1
    leg_bb = leg.getbbox() or (0, 0, leg.width, leg.height)
    join_y = fy - (ly - leg_bb[1]) * 0.42
    c.alpha_composite(torso, (int(fx - t_cx), int(join_y - t_bottom)))
    return c.crop(c.getbbox())

def export_player():
    r1 = L.LeyiLib.open(Z / 'ResPlayer1.lib')
    legs, body, atk = decode_entry(r1, 0), decode_entry(r1, 256), decode_entry(r1, 260)
    out = WEB / 'player'
    for sub in ('walk', 'idle', 'attack'): (out / sub).mkdir(parents=True, exist_ok=True)
    for d in range(8):
        for f in range(4):
            k = d * 4 + f
            im = composite(legs[k], body[k])
            im.save(out / 'walk' / f'{d}_{f}.png')
            if f == 0: im.save(out / 'idle' / f'{d}_0.png')
        bi = atk[d * 4] if d * 4 < len(atk) else body[d * 4]
        composite(legs[d * 4], bi).save(out / 'attack' / f'{d}_0.png')
    Image.open(out / 'idle' / '0_0.png').save(WEB / 'player.png')
    (out / 'meta.json').write_text(json.dumps({
        'dirs': 8, 'walk_frames': 4, 'layers': {'legs': 0, 'body': 256, 'attack_body': 260},
        'note': 'paper-doll composite; Spr↔full part map still open',
    }, indent=2))
    print('player ok')

def export_npcs():
    r3 = L.LeyiLib.open(Z / 'ResNpc3.lib')
    r2 = L.LeyiLib.open(Z / 'ResNpc2.lib')
    props, npc = WEB / 'map/props', WEB / 'map/npcs'
    props.mkdir(parents=True, exist_ok=True); npc.mkdir(parents=True, exist_ok=True)
    results = {}
    for ev, g in NPC_MAP.items():
        frames = []
        if ev == 'xn':
            for i in range(650, 680):
                for _, lep in L.find_nested_leps(r2.entry_bytes(i)):
                    try: im = B.decode(lep)
                    except Exception: continue
                    if im is None: continue
                    op = (np.array(im)[:, :, 3] > 0).sum()
                    if 80 < op < 900 and 15 <= im.height <= 55:
                        frames.append(im.crop(im.getbbox()))
                if frames: g = i; break
        else:
            frames = [im.crop(im.getbbox()) for im in decode_entry(r3, g) if (np.array(im)[:, :, 3] > 0).sum() >= 400]
        if not frames: print('skip', ev); continue
        primary = frames[0]
        rg = ROLE_GRAPH[ev]
        primary.save(props / f'npc_{rg}.png'); primary.save(npc / f'{ev}.png')
        dirs = []
        step = max(1, len(frames) // 8)
        for di in range(8):
            im = frames[min(di * step, len(frames) - 1)]
            im.save(npc / f'{ev}_{di}.png'); dirs.append(f'{ev}_{di}.png')
        results[ev] = dict(used=g, file=f'npc_{rg}.png', w=primary.width, h=primary.height, dirs=dirs)
        print(ev, results[ev])
    (npc / 'index.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
    meta_path = WEB / 'map/meta.json'
    meta = json.loads(meta_path.read_text())
    for n in meta.get('npcs', []):
        ev = (n.get('EventID') or '').lower()
        if ev in results:
            r = results[ev]; n['file'] = r['file']; n['sw'] = r['w']; n['sh'] = r['h']; n['npc_dirs'] = r['dirs']
    meta['objects'] = meta['npcs']
    meta_path.write_text(json.dumps(meta, ensure_ascii=False))
    print('npcs ok')

if __name__ == '__main__':
    export_player(); export_npcs()
