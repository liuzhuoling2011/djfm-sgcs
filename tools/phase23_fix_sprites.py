#!/usr/bin/env python3
"""Phase 23: remap wrong monster/NPC sprites; re-export act-1 combat casts.

MONSTER_SETS uses (lib, setstart):
  r3=ResNpc3, rex=ResExNpc1, boss=ResBoss
Exact Spr/PLI paper-doll compositing for graph 006/009 still open — these are
best full-body visual matches (filter out h<=2 / w>500 strip junk).
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leyilib as L, bld_rle as B

ROOT = Path('/workspace/djfm-sgcs')
ZY = ROOT / 'extract/Blade And Sword 2 Ancient Legend/zy'
WEB = ROOT / 'web/public/game/maps'
ACTIONS = {'walk': (0, 10), 'idle': (1, 2), 'hurt': (2, 1), 'attack': (4, 8), 'death': (9, 2)}
LIBS = {
    'r3': ZY / 'ResNpc3.lib',
    'rex': ZY / 'ResExNpc1.lib',
    'boss': ZY / 'ResBoss.lib',
}
# role → (lib_key, setstart, note)
MONSTER_SETS = {
    190: ('r3', 594, '鬼兵 spear body'),
    191: ('r3', 594, '鬼兵 spear body'),
    189: ('rex', 72, '狐猴 — ResEx full-body (graph 601 was paper-doll idle strip)'),
    10: ('r3', 48, '魔豕兽战士 — ResNpc3 set48 full actions (was set0 human + 1712×1 death)'),
    11: ('r3', 48, '魔豕兽'),
    158: ('boss', 564, '战象 interim full-body (graph 009 nests are 1px strips)'),
    75: ('r3', 48, '野猪王 shares graph 006'),
}
# scenes that need Auto 狐猴 / bossdaxiang remapped
AFFECTED = ['1-2s', '1-9s', '1-10s', '1-10a4s', '1-10a5s', '1-10a6s']

_lib_cache = {}
def open_lib(key):
    if key not in _lib_cache:
        _lib_cache[key] = L.LeyiLib.open(LIBS[key])
    return _lib_cache[key]

def good_frame(im):
    if im is None: return False
    if im.height <= 3 or im.width > 500: return False
    op = int((np.array(im)[:, :, 3] > 0).sum())
    return op >= 80

def export_set(lib_key, setstart, outdir, tag):
    lib = open_lib(lib_key)
    outdir.mkdir(parents=True, exist_ok=True)
    meta = {}
    for act, (k, per) in ACTIONS.items():
        frames = []
        if setstart + k >= lib.count:
            meta[act] = dict(per_dir=1, frames=[])
            continue
        for i, (_, lep) in enumerate(L.find_nested_leps(lib.entry_bytes(setstart + k))):
            try: im = B.decode(lep)
            except Exception: im = None
            if not good_frame(im):
                continue
            im = im.crop(im.getbbox() or (0, 0, 1, 1))
            fn = f'{tag}_{act}_{len(frames)}.png'
            im.save(outdir / fn)
            frames.append([fn, im.width, im.height])
        if frames and len(frames) % 8 == 0:
            per = max(1, len(frames) // 8)
        elif frames:
            per = max(1, (len(frames) + 7) // 8)
        # fallback: reuse walk for missing hurt/death/attack
        meta[act] = dict(per_dir=per, frames=frames)
        print(f'  {tag} {act}: {len(frames)} frames per_dir={per}')
    for act in ('hurt', 'attack', 'death', 'idle'):
        if not meta.get(act, {}).get('frames') and meta.get('walk', {}).get('frames'):
            meta[act] = dict(per_dir=meta['walk']['per_dir'], frames=list(meta['walk']['frames']))
            print(f'  {tag} {act}: fallback→walk')
    return meta

def role_stats():
    EXT = ROOT / 'assets/samples/phase9/fol_extract'
    def tsv(name):
        rows = open(EXT / 'mb' / name, encoding='gbk', errors='replace').read().splitlines()
        return [r.split('\t') for r in rows[1:] if r.strip()]
    stats = {}
    for p in tsv('RolePrivate.txt'):
        if len(p) > 16 and p[1].strip().isdigit():
            g = lambda i: int(p[i]) if p[i].strip().lstrip('-').isdigit() else 0
            stats.setdefault(int(p[1]), []).append(dict(
                lv=g(2), spd=g(3), run=g(4), sight=g(5), hp=g(9), at=g(10), df=g(11),
                hit=g(13), eva=g(14), exp=g(16)))
    role = {}
    for p in tsv('Role.txt'):
        if len(p) > 4 and p[1].strip().isdigit():
            role[int(p[1])] = p[0]
    return role, stats

def patch_scene(scene):
    meta_path = WEB / scene / 'meta.json'
    if not meta_path.exists():
        print('skip missing', scene); return
    meta = json.loads(meta_path.read_text())
    mon_dir = WEB / scene / 'mon'
    role, stats = role_stats()
    # export needed sets into this map's mon/
    monsets = dict(meta.get('monster_sets') or {})
    # drop broken set 10 yezhu strip
    for bad in list(monsets.keys()):
        if bad in ('10',) or str(bad) == '10':
            del monsets[bad]
    set_key_for_role = {}
    for rid, (libk, ss, note) in MONSTER_SETS.items():
        tag = f'{libk}{ss}'
        key = tag  # monster_sets key = set id string used by client
        if key not in monsets:
            print(f'{scene}: export {rid} {note} → {key}')
            monsets[key] = export_set(libk, ss, mon_dir, tag)
        set_key_for_role[rid] = key

    # Convert Auto/bossdaxiang NPCs that map to MONSTER_SETS into monsters
    npcs = meta.get('npcs') or meta.get('objects') or []
    keep_npcs = []
    mons = list(meta.get('monsters') or [])
    # drop old placeholder 魔豕 with set 10
    mons = [m for m in mons if m.get('set') != 10 and m.get('role') not in MONSTER_SETS]
    added = 0
    for n in npcs:
        mid = int(n.get('ModelID') or 0)
        eid = str(n.get('EventID') or '')
        if mid in MONSTER_SETS and (eid.lower() in ('auto', 'bossdaxiang', 'bossyezhu') or n.get('Type') == 13):
            st = sorted(stats.get(mid, [dict(lv=1, spd=8, run=8, sight=6, hp=200, at=40, df=20, hit=30, eva=0, exp=40)]), key=lambda s: s['lv'])[0]
            sk = set_key_for_role[mid]
            # numeric set for client: encode as hash? Client uses f.set as monSets key.
            # Store set as string key via set field — main uses String(f.set). Use tag string.
            mons.append(dict(
                x=n['x'], y=n['y'], role=mid, name=role.get(mid, n.get('name', '?')),
                set=sk, **st,
                range=[n['x'], n['y'], 0, 0], event=eid.lower()))
            added += 1
            continue
        # drop bossdaxiang / Auto with wrong graph even if not converted
        if eid.lower() in ('auto',) and mid == 189:
            continue
        if eid.lower() == 'bossdaxiang':
            continue
        # strip bad npc_dirs that point at graph-601 strip for autos already skipped
        keep_npcs.append(n)

    # Also ensure bossyezhu combat uses set r348 — update any leftover
    for m in mons:
        if m.get('role') in MONSTER_SETS:
            m['set'] = set_key_for_role[m['role']]
        # ghosts keep 594
        if m.get('role') in (190, 191):
            m['set'] = set_key_for_role.get(m['role'], 594)
            if '594' not in monsets and 'r3594' not in monsets:
                monsets['594'] = export_set('r3', 594, mon_dir, '594')
                # also alias
            if '594' not in monsets and 'r3594' in monsets:
                monsets['594'] = monsets['r3594']
            m['set'] = 594 if '594' in monsets else 'r3594'

    # Ensure 594 present for ghosts already on map
    if any(m.get('role') in (190, 191) for m in mons) or any(m.get('set') == 594 for m in meta.get('monsters') or []):
        if '594' not in monsets:
            monsets['594'] = export_set('r3', 594, mon_dir, '594')

    # Re-add original non-remapped monsters (ghosts etc.) that we filtered
    for m in meta.get('monsters') or []:
        if m.get('role') in (190, 191) and m.get('set') in (594, '594'):
            if not any(x.get('x') == m['x'] and x.get('y') == m['y'] and x.get('role') == m['role'] for x in mons):
                mm = dict(m); mm['set'] = 594; mons.append(mm)

    meta['npcs'] = keep_npcs
    meta['objects'] = keep_npcs
    meta['monsters'] = mons
    meta['monster_sets'] = monsets
    meta['phase23'] = {str(k): v[2] for k, v in MONSTER_SETS.items()}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False))
    print(f'{scene}: npcs {len(keep_npcs)} mons {len(mons)} (+{added} from Auto) sets {list(monsets.keys())}')

def main():
    scenes = sys.argv[1:] or AFFECTED
    for sc in scenes:
        patch_scene(sc.lower())

if __name__ == '__main__':
    main()
