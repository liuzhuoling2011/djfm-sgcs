"""Phase 24: SprRole.h part → Spr.lib groups → Res* nested lep, composited per frame.
Spr frame record: packed=(sub<<24)|(libnib<<20)|res ; ox,oy foot offsets. libnib: 2 ResPrior 3 ResPlayer1 4 ResBoss 5 ResNpc2 10 ResExNpc1."""
import re, struct, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leyilib as L, bld_rle as B
ROOT = Path('/workspace/djfm-sgcs'); Z = ROOT/'extract/Blade And Sword 2 Ancient Legend/zy'
H = (ROOT/'assets/samples/phase9/fol_extract/slr/SprRole.h').read_text(errors='replace')
LIBF = {2:'ResPrior.lib',3:'ResPlayer1.lib',4:'ResBoss.lib',5:'ResNpc2.lib',9:'ResNpc3.lib',10:'ResExNpc1.lib'}
_libs = {}; _cache = {}
def lib(n):
    if n not in _libs: _libs[n] = L.LeyiLib.open(Z/LIBF[n])
    return _libs[n]
SPR = L.LeyiLib.open(Z/'Spr.lib')

def parts(graph, var='001'):
    out = {}
    for m in re.finditer(rf'SPR_ROLE_{graph}_([A-Z]+)_(\d+)_001\s+(\d+)', H):
        p, v, sid = m.group(1), m.group(2), int(m.group(3))
        if p.endswith('S') and len(p) == 3: continue  # shadow layers
        if v == var or p not in out: out[p] = sid
    return out

def groups(sid):
    b = SPR.entry_bytes(sid); v = struct.unpack_from('<%di' % (len(b)//4), b)
    gs = []; i = 1
    while i < len(v) - 5:
        if v[i+1] == 4 and v[i+2] == 7 and v[i+3] == 0 and 0 < v[i+4] < 64:
            n = v[i+4]; fr = []; j = i + 5
            for _ in range(n):
                if j + 7 > len(v): break
                p = v[j] & 0xffffffff
                fr.append(dict(sub=p >> 24, lib=(p >> 20) & 0xf, res=p & 0xffff, ox=v[j+3], oy=v[j+4])); j += 7
            gs.append(dict(code=v[i], frames=fr)); i = j
        else: i += 1
    return gs

def lep(libn, res, sub):
    k = (libn, res)
    if k not in _cache:
        ims = []
        if libn in LIBF and res < lib(libn).count:
            for _, l in L.find_nested_leps(lib(libn).entry_bytes(res)):
                try: im = B.decode(l)
                except Exception: im = None
                ims.append(im)
        _cache[k] = ims
    ims = _cache[k]
    if not ims: return None
    s = sub - 1 if sub >= 1 else 0
    return ims[s] if s < len(ims) else None


def pli_orders(graph):
    """Per-frame part draw order from PLI (indices into parts() key list)."""
    import re
    slr = ROOT/'assets/samples/phase9/fol_extract/slr'/graph
    files = list(slr.glob('*.PLI')) if slr.exists() else []
    if not files: return None
    b = files[0].read_bytes()
    # part tags in header order
    tags = [m.group(1).decode() for m in re.finditer(rb'([A-Z]{2})\x00\x00\x00[0-9]{3}\x00', b[:300])]
    if not tags:
        tags = [m.group(1).decode() for m in re.finditer(rb'([A-Z]{2})\x00', b[:120])]
    n = len(tags) or 5
    i = b.find(b'\x80\x00')
    if i < 0: i = 120
    else: i += 2
    # skip leading u16 pairs that look like counts
    while i + 4 < len(b) and b[i+1] == 0 and b[i+3] == 0 and b[i] < 64 and b[i+2] < 64:
        i += 4
    orders = []
    while i + n <= len(b) and len(orders) < 400:
        chunk = list(b[i:i+n])
        if all(c < n for c in chunk):
            orders.append([tags[c] if c < len(tags) else tags[0] for c in chunk])
            i += n
        else:
            i += 1
            if i > len(b) - n: break
    return orders if orders else None

ORDER = ['CA','LE','LA','LH','TK','RA','RH','HD','RE']
def composite(pmap, gi, fi, C=(160, 200), orders=None):
    can = Image.new('RGBA', (320, 260), (0,0,0,0)); any_ = False
    if orders and gi < len(orders):
        seq = [p for p in orders[gi] if p in pmap] + [p for p in pmap if p not in (orders[gi] if gi < len(orders) else [])]
    else:
        seq = sorted(pmap, key=lambda q: ORDER.index(q) if q in ORDER else 5)
    for p in seq:
        gs = pmap[p]
        if gi >= len(gs) or not gs[gi]['frames']: continue
        f = gs[gi]['frames'][min(fi, len(gs[gi]['frames'])-1)]
        if f['lib'] in (0, 15): continue
        im = lep(f['lib'], f['res'], f['sub'])
        if im is None or im.height <= 2: continue
        can.alpha_composite(im, (C[0] - f['ox'], C[1] - f['oy'])); any_ = True
    return can if any_ else None

def load(graph):
    pm = {p: groups(sid) for p, sid in parts(graph).items()}
    return pm, pli_orders(graph)

if __name__ == '__main__':
    g = sys.argv[1]; pm, ords = load(g)
    ref = next(iter(pm.values()))
    print('pli orders', len(ords) if ords else 0)
    print(g, {p: len(v) for p, v in pm.items()})
    print('codes', [(i, x['code'], len(x['frames'])) for i, x in enumerate(ref)][:60])
    tiles = []
    for gi in range(len(ref)):
        im = composite(pm, gi, 0, orders=ords)
        if im: bb = im.getbbox(); tiles.append((gi, ref[gi]['code'], im.crop(bb) if bb else im))
    W = 12; sheet = Image.new('RGBA', (W*110, ((len(tiles)+W-1)//W)*130), (20,20,30,255))
    from PIL import ImageDraw; d = ImageDraw.Draw(sheet)
    for k, (gi, c, im) in enumerate(tiles):
        im.thumbnail((104, 112)); x, y = (k%W)*110, (k//W)*130
        sheet.paste(im, (x+3, y+16), im); d.text((x+2, y+2), f'{gi}:c{c}', fill=(255,220,90))
    sheet.save(ROOT/f'assets/samples/phase24/pd_{g}.png'); print('sheet', len(tiles))
