"""Phase 16: generic scene exporter → web/public/game/maps/<scene>/ (meta.json, ground_full.png, props/, mon/).
Usage: python3 tools/scene_export.py 1-2s
Ground = MAP col0 diamonds + col1 overlay decals (Phase 14 rule); buildings = BLD part lists (Phase 13);
walk = MAP flag byte (1 = walkable); NPCs = ONT Role graph first frame; monsters = ONT roles that have
RolePrivate stats + a RoleQuest bestiary entry, with ResNpc3 action sets (see MONSTER_SETS)."""
import json, re, struct, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leyilib as L, bld_rle as B
import phase10_export_scene as P
from phase10_run_export import compose_iso_ground
from phase13_bld_place import parse_records

ROOT = Path('/workspace/djfm-sgcs'); EXT = P.EXT; ZY = P.ZY
# ResNpc3 action-set start per role (12 entries: 0 walk(8×10) 1 idle(8×2) 2 hurt(8×1) 3 (8×2) 4-7 attacks(8×8) 8 (8×7) 9 death(8×2) 10 (8×5)).
# 594 = complete spear ghost-soldier body (matched visually); the saber variant is a multi-layer paper-doll
# (sets 522/546/570) we cannot composite yet → both use 594.
MONSTER_SETS = {190: 594, 191: 594}
ACTIONS = {'walk': (0, 10), 'idle': (1, 2), 'hurt': (2, 1), 'attack': (4, 8), 'death': (9, 2)}

def tsv(name):
    rows = open(EXT / 'mb' / name, encoding='gbk', errors='replace').read().splitlines()
    hdr = rows[0].split('\t'); return hdr, [r.split('\t') for r in rows[1:] if r.strip()]

def role_tables():
    _, rows = tsv('Role.txt'); role = {}
    for p in rows:
        if len(p) > 4 and p[1].strip().isdigit(): role[int(p[1])] = dict(name=p[0], graph=p[4].strip())
    hdr, rows = tsv('RolePrivate.txt'); stats = {}
    for p in rows:
        if len(p) > 16 and p[1].strip().isdigit():
            g = lambda i: int(p[i]) if p[i].strip().lstrip('-').isdigit() else 0
            stats.setdefault(int(p[1]), []).append(dict(lv=g(2), spd=g(3), run=g(4), sight=g(5), hp=g(9), at=g(10), df=g(11), hit=g(13), eva=g(14), exp=g(16)))
    _, rows = tsv('RoleQuest.txt'); best = {int(p[1]) for p in rows if len(p) > 1 and p[1].isdigit()}
    return role, stats, best

def export_monster_frames(setstart, outdir):
    r = L.LeyiLib.open(ZY / 'ResNpc3.lib'); out = {}
    for act, (k, per) in ACTIONS.items():
        leps = L.find_nested_leps(r.entry_bytes(setstart + k)); frames = []
        for i, (_, lep) in enumerate(leps):
            try: im = B.decode(lep)
            except Exception: im = None
            if im is None: frames.append(None); continue
            bb = im.getbbox() or (0, 0, 1, 1); im = im.crop(bb)
            fn = f'{setstart}_{act}_{i}.png'; im.save(outdir / fn); frames.append([fn, im.width, im.height])
        out[act] = dict(per_dir=per, frames=frames)
    return out

def main(scene):
    out = ROOT / 'web/public/game/maps' / scene; (out / 'props').mkdir(parents=True, exist_ok=True); (out / 'mon').mkdir(exist_ok=True)
    cj = {p.name.lower(): p for p in (EXT / 'cj').iterdir()}
    mp, bnt, ont = cj[f'{scene}.map'], cj[f'{scene}.bnt'], cj[f'{scene}.ont']
    mw, mh, grid, _ = P.parse_map_grid(mp); overlay = P.parse_map_grid.last_overlay
    data = mp.read_bytes(); rec = len(data) - mw * mh * 10
    walk = [''.join('1' if data[rec + (y * mw + x) * 10 + 4] == 1 else '0' for x in range(mw)) for y in range(mh)]
    libname = data[0x44 + 16:0x44 + 16 + 256].split(b'\0')[0].decode('latin1') or 'Map_Ren.lib'
    mlib = L.LeyiLib.open(next(p for p in ZY.iterdir() if p.name.lower() == libname.lower()))
    g, orig, ok, miss, _ = compose_iso_ground(grid, mlib, scale=0.5)
    cov = {}
    for v in {v for row in overlay for v in row}:
        if v == 0xFFFF or v >= mlib.count: continue
        im = L.decode_lep_diamond(mlib.entry_bytes(v)); cov[v] = (np.array(im)[:, :, 3] > 0).mean() if im is not None else 1
    deco = overlay  # Phase 16c: all overlay tiles alpha-over (Wine-verified)
    d, dorig, *_ = compose_iso_ground(deco, mlib, scale=0.5)
    g.alpha_composite(d)
    g.save(out / 'ground_full.png', optimize=True)
    # buildings
    mdl = re.search(rb'BLD_\w+\.M[Dd][Ll]', bnt.read_bytes()[:0xC4]).group().decode()
    mdlp = next(p for p in (EXT / 'mb').iterdir() if p.name.lower() == mdl.lower())
    recs = parse_records(mdlp); bld = P.parse_bld(mdlp); res00 = L.LeyiLib.open(ZY / 'res00.Lib')
    md = mdlp.read_bytes(); fp = {}
    for rc in bld:
        a = rc['off']; fp.setdefault(struct.unpack_from('<H', md, a + 36)[0], struct.unpack_from('<HH', md, a + 79))
    done = {}; blds = []
    trig = []
    for p in P.parse_bnt(bnt, bld):
        if p['kind'] == 'trigger': trig.append(dict(x=p['x'], y=p['y'], bid=p['bid'], script=p.get('script', '')))
        if p['kind'] != 'bld' or p['bid'] not in recs: continue
        parts = []
        for pt in recs[p['bid']]['parts']:
            rid = pt['rid']
            if rid not in done:
                done[rid] = None
                try:
                    blob = res00.entry_bytes(rid)
                    if blob[:4] == b'lep\x00':
                        im = B.decode(blob)
                        if im is not None: im.save(out / 'props' / f'res_{rid}.png'); done[rid] = im.size
                except Exception: pass
            if done[rid]: parts.append(dict(file=f'res_{rid}.png', ox=pt['ox'], oy=pt['oy'], w=done[rid][0], h=done[rid][1]))
        if parts:
            fw, fh = fp.get(p['bid'], (1, 1)); blds.append(dict(x=p['x'], y=p['y'], bid=p['bid'], name=recs[p['bid']]['name'], parts=parts, fw=fw, fh=fh))
    # ONT
    role, stats, best = role_tables(); objs = P.parse_ont(ont); npcs = []; mons = []; monsets = {}
    for o in objs:
        mid = int(o.get('ModelID', 0) or 0); x, y = o.get('MapX'), o.get('MapY')
        if x is None or mid >= 20000: continue
        if mid in best and mid in stats and mid in MONSTER_SETS:
            st = sorted(stats[mid], key=lambda s: s['lv'])[0]; s0 = MONSTER_SETS[mid]
            if s0 not in monsets: monsets[s0] = export_monster_frames(s0, out / 'mon')
            mons.append(dict(x=x, y=y, role=mid, name=role.get(mid, {}).get('name', '?'), set=s0, **st,
                             range=[o.get('MoveRangeX', x), o.get('MoveRangeY', y), o.get('MoveRangeCx', 0), o.get('MoveRangeCy', 0)]))
        else:
            gid = role.get(mid, {}).get('graph', '')
            try: gid = int(gid) if str(gid).isdigit() else mid
            except Exception: gid = mid
            npcs.append(dict(x=x, y=y, ModelID=mid, Type=o.get('Type'), EventID=o.get('EventID'),
                             name=role.get(mid, {}).get('name', ''), graph=gid))
    _, act = tsv('ActMdl.txt')
    spawn = None
    for p in act:
        if len(p) > 4 and p[2].lower() == scene: spawn = [int(p[3]), int(p[4])]
    if spawn is None:  # first walkable cell nearest the map centre
        cand = [(abs(x - mw // 2) + abs(y - mh // 2), x, y) for y in range(mh) for x in range(mw) if walk[y][x] == '1' and grid[y][x] != 0xFFFF]
        if mons: cand = [(abs(x - mons[0]['x']) + abs(y - mons[0]['y']) + (100 if abs(x - mons[0]['x']) + abs(y - mons[0]['y']) < 8 else 0), x, y) for _, x, y in cand]
        _, sx, sy = min(cand); spawn = [sx, sy]
    meta = dict(scene=scene, scene_name=scene, pack_id=scene, chunk_origin=[0, 0], chunk_size=[mw, mh], map_dims=[mw, mh],
                tile_pixel=[64, 32], spawn=spawn, grid=[], buildings=blds, npcs=npcs, objects=npcs, monsters=mons, monster_sets=monsets, triggers=trig,
                walk_grid=walk, ground_full=dict(file='ground_full.png', **orig, pixel_size=list(g.size)),
                source=f'Phase16 scene_export {scene}: {mp.name}+{libname}+{mdl}')
    (out / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False))
    print(scene, mw, mh, 'bld', len(blds), 'mons', len(mons), 'npcs', len(npcs), 'spawn', spawn, 'lib', libname, 'ground', g.size)

if __name__ == '__main__':
    main(sys.argv[1].lower())
