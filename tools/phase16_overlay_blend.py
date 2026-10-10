"""Phase 16c: test MAP overlay (col1) blend modes against Wine pixels at full 64x32 pitch.
Camera calibration from Phase 13: 01_gate_rain cell (70,55) → screen (560,156); 10_pavilion cell (84,78) → (258,500).
Tile top-left = iso(cell) - (32, 0)?  We search the tile offset too."""
import sys, json
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).parent))
import leyilib as L, phase10_export_scene as P
mw, mh, grid, _ = P.parse_map_grid(P.EXT / 'cj/1-0s.MAP'); ov = P.parse_map_grid.last_overlay
lib = L.LeyiLib.open(P.ZY / 'map_ren.lib'); cache = {}
def tile(v):
    if v not in cache:
        try: cache[v] = np.array(L.decode_lep_diamond(lib.entry_bytes(v))).astype(float)
        except Exception: cache[v] = None
    return cache[v]
def layer(g, cell, anchor, off):
    can = np.zeros((600, 800, 4)); (cx, cy), (ax, ay) = cell, anchor
    for y in range(max(0, cy - 30), min(mh, cy + 30)):
        for x in range(max(0, cx - 30), min(mw, cx + 30)):
            v = g[y][x]
            if v == 0xFFFF: continue
            t = tile(v)
            if t is None: continue
            sx = ax + ((x - y) - (cx - cy)) * 32 + off[0]; sy = ay + ((x + y) - (cx + cy)) * 16 + off[1]
            h, w = t.shape[:2]
            x0, y0, x1, y1 = max(0, sx), max(0, sy), min(800, sx + w), min(600, sy + h)
            if x0 >= x1 or y0 >= y1: continue
            s = t[y0 - sy:y1 - sy, x0 - sx:x1 - sx]; a = s[:, :, 3:4] / 255
            can[y0:y1, x0:x1, :3] = can[y0:y1, x0:x1, :3] * (1 - a) + s[:, :, :3] * a
            can[y0:y1, x0:x1, 3:4] = np.maximum(can[y0:y1, x0:x1, 3:4], a)
    return can
tint = lambda c: c * np.array([0.63, 0.63, 0.80]) + np.array([8, 9, 10])
def run(shot, cell, anchor):
    W = np.array(Image.open(shot).convert('RGB'))[:600, :800].astype(float)
    # pick ground tile offset by best fit of col0 alone
    best = None
    for off in [(-32, 0), (-32, -16), (0, 0), (-32, -8), (-64, -16)]:
        g = layer(grid, cell, anchor, off); m = g[:, :, 3] > 0.99
        e = np.abs(tint(g[:, :, :3]) - W)[m].mean()
        if best is None or e < best[0]: best = (e, off, g)
    e0, off, g = best
    o = layer(ov, cell, anchor, off); m = (o[:, :, 3] > 0.5) & (g[:, :, 3] > 0.99) & (np.arange(600)[:, None] < 480)
    G, O, a = g[:, :, :3], o[:, :, :3], o[:, :, 3:4]
    modes = {'ground only': G, 'alpha over': G * (1 - a) + O * a, '50% over': G * (1 - a / 2) + O * a / 2,
             'additive': np.minimum(255, G + O * a), 'multiply': G * (1 - a) + G * O / 255 * a,
             'black-key over (drop <48)': np.where((a > 0) & (O.sum(2, keepdims=True) / 3 >= 48), O, G),
             'darken': np.where(a > 0, np.minimum(G, O), G), 'lighten': np.where(a > 0, np.maximum(G, O), G)}
    res = {k: round(float(np.median(np.abs(tint(v) - W)[m])), 2) for k, v in modes.items()}
    return dict(shot=Path(shot).name, ground_offset=off, ground_err=round(e0, 2), overlay_px=int(m.sum()), median_abs_err=res), modes, W, m
if __name__ == '__main__':
    out = []
    for shot, cell, anc in [('assets/samples/xp_compare/orig_wadang/01_gate_rain.png', (70, 55), (560, 156)),
                            ('assets/samples/xp_compare/orig_wadang/10_pavilion_tower.png', (84, 78), (258, 500))]:
        r, modes, W, m = run(shot, cell, anc); out.append(r); print(json.dumps(r, ensure_ascii=False))
        bestk = min((k for k in r['median_abs_err'] if k != 'ground only'), key=lambda k: r['median_abs_err'][k])
        vis = np.concatenate([W, tint(modes['ground only']), tint(modes[bestk])], 1).clip(0, 255).astype(np.uint8)
        Image.fromarray(vis).save(f"assets/samples/phase16/overlay_blend_{Path(shot).stem}.png")
    json.dump(out, open('assets/samples/phase16/overlay_blend.json', 'w'), ensure_ascii=False, indent=1)
