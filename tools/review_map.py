#!/usr/bin/env python3
"""Review: correct LeyiMap1.50 parse + ground render + seam metric."""
import struct, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).parent))
import lep2

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'extract/Blade And Sword 2 Ancient Legend'

def parse_map(path):
    d = Path(path).read_bytes()
    assert d.startswith(b'LeyiMap1.50')
    w, h = struct.unpack_from('<HH', d, 0x10)
    lib = d[0x54:0x154].split(b'\0')[0].decode()
    # 0x154: u32 tag, u32 n, then remap table of (libcount-1) u16 -> fixed 36906-byte block
    tail = len(d) - w * h * 10
    recs = np.frombuffer(d, dtype=np.dtype([('g', '<u2'), ('o', '<u2'), ('f', 'u1'), ('ff', 'u1'), ('h', '<u2'), ('pad', '<u2')]), count=w * h, offset=tail).reshape(h, w)
    remap = np.frombuffer(d, '<u2', count=(tail - 0x15c) // 2, offset=0x15c)
    return dict(w=w, h=h, lib=lib, recs=recs, remap=remap, rec_off=tail)

class TileCache:
    def __init__(self, lib):
        from leyilib import LeyiLib
        self.L = LeyiLib.open(lib)
        self.c = {}
    def get(self, i):
        if i not in self.c:
            a = lep2.decode(self.L.entry_bytes(i)) if 0 <= i < self.L.count else None
            self.c[i] = a
        return self.c[i]

def pos(layout, x, y):
    if layout == 'diamond':   return (x - y) * 32, (x + y) * 16
    if layout == 'diamondT':  return (y - x) * 32, (x + y) * 16
    if layout == 'stagger':   return x * 64 + (y & 1) * 32, y * 16
    if layout == 'stagger2':  return x * 64 + ((y + 1) & 1) * 32, y * 16
    if layout == 'staggerT':  return y * 64 + (x & 1) * 32, x * 16
    raise ValueError(layout)

def render(m, tc, layout='diamond', field='g', idx_off=0, region=None, overlay=False):
    x0, y0, x1, y1 = region or (0, 0, m['w'], m['h'])
    cells = [(x, y) for y in range(y0, y1) for x in range(x0, x1)]
    ps = [pos(layout, x, y) for x, y in cells]
    minx = min(p[0] for p in ps); miny = min(p[1] for p in ps)
    W = max(p[0] for p in ps) - minx + 64; H = max(p[1] for p in ps) - miny + 32
    img = np.zeros((H, W, 4), np.uint8); cid = np.full((H, W), -1, np.int32)
    layers = [field] + (['o'] if overlay else [])
    for L_ in layers:
        for (x, y), (px, py) in zip(cells, ps):
            v = int(m['recs'][y, x][L_])
            if v == 0xFFFF: continue
            t = tc.get(v + idx_off)
            if t is None: continue
            sx, sy = px - minx, py - miny
            a = t[:, :, 3] > 0
            img[sy:sy + 32, sx:sx + 64][a] = t[a]
            if L_ == field:
                cid[sy:sy + 32, sx:sx + 64][a] = y * m['w'] + x
    return img, cid, (minx, miny)

def seam_ratio(img, cid):
    g = img[:, :, :3].astype(np.int32); op = img[:, :, 3] > 0
    out = {}
    tot_s = tot_i = 0; ns = ni = 0
    for dy, dx in ((0, 1), (1, 0)):
        A = g[:g.shape[0] - dy, :g.shape[1] - dx]; B = g[dy:, dx:]
        oa = op[:op.shape[0] - dy, :op.shape[1] - dx] & op[dy:, dx:]
        ca = cid[:cid.shape[0] - dy, :cid.shape[1] - dx]; cb = cid[dy:, dx:]
        diff = np.abs(A - B).sum(-1)
        s = oa & (ca != cb) & (ca >= 0) & (cb >= 0); i = oa & (ca == cb)
        tot_s += diff[s].sum(); ns += s.sum(); tot_i += diff[i].sum(); ni += i.sum()
    seam = tot_s / max(ns, 1); inner = tot_i / max(ni, 1)
    return seam, inner, seam / max(inner, 1e-9)

if __name__ == '__main__':
    m = parse_map(ROOT / 'assets/samples/phase9/fol_extract/cj/1-0s.MAP')
    tc = TileCache(GAME / 'zy' / m['lib'].lower())
    reg = (40, 40, 90, 90)
    for layout in ['diamond', 'diamondT', 'stagger', 'stagger2', 'staggerT']:
        for off in (-1, 0, 1):
            img, cid, _ = render(m, tc, layout, 'g', off, reg)
            s, i, r = seam_ratio(img, cid)
            print(f'{layout:9s} off={off:+d} seam={s:6.1f} inner={i:6.1f} ratio={r:5.2f}')
