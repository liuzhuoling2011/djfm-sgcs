"""Phase 24: export SprRole paper-doll composites as monster_sets ('pd<graph>') into every map using those roles."""
import json, sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase24_paperdoll as P
import phase23_fix_sprites as F
WEB = Path('/workspace/djfm-sgcs/web/public/game/maps')
# graph → action → first group of its 8-direction block (picked from assets/samples/phase24/pd_<g>.png)
BLOCKS = {
  '602': dict(walk=0, idle=8, hurt=24, attack=32, death=62),
  '603': dict(walk=0, idle=8, hurt=24, attack=32, death=82),
  '601': dict(walk=0, idle=24, hurt=8, attack=32, death=56),
  '006': dict(walk=4, idle=84, hurt=32, attack=40, death=24),
  '009': dict(walk=0, idle=8, hurt=46, attack=24, death=54),
  '003': dict(walk=0, idle=37, hurt=53, attack=21, death=61),
  '113': dict(walk=0, idle=8, hurt=54, attack=62, death=16),
  '008': dict(walk=0, idle=8, hurt=58, attack=66, death=42),
}
ROLE_G = {190:'602',191:'603',189:'601',10:'006',11:'006',75:'006',158:'009',170:'009',46:'008',12:'003',55:'113'}
_built = {}
def build(g):
    if g in _built: return _built[g]
    pm = P.load(g); ref = next(iter(pm.values())); acts = {}
    for act, g0 in BLOCKS[g].items():
        per = max(len(ref[g0+d]['frames']) for d in range(8) if g0+d < len(ref))
        acts[act] = (per, [[P.composite(pm, g0+d, k) for k in range(per)] for d in range(8)])
    bb = None
    for per, dirs in acts.values():
        for fr in dirs:
            for im in fr:
                if im is None: continue
                b = im.getbbox()
                if b: bb = b if bb is None else (min(bb[0],b[0]),min(bb[1],b[1]),max(bb[2],b[2]),max(bb[3],b[3]))
    _built[g] = (acts, bb); return _built[g]

def write(g, mon):
    acts, bb = build(g); meta = {}
    for act, (per, dirs) in acts.items():
        frames = []
        for d, fr in enumerate(dirs):
            last = None
            for k in range(per):
                im = fr[k] if k < len(fr) and fr[k] is not None else last
                if im is None: frames.append(None); continue
                last = im; c = im.crop(bb); fn = f'pd{g}_{act}_{d}_{k}.png'
                if not (mon/fn).exists(): c.save(mon/fn, optimize=True)
                frames.append([fn, c.width, c.height])
        meta[act] = dict(per_dir=per, frames=frames)
    return meta

role, stats = F.role_stats()
for mp in sorted(WEB.glob('*/meta.json')):
    m = json.loads(mp.read_text()); ch = False
    keep = []
    for n in m.get('npcs') or []:
        mid = int(n.get('ModelID') or 0)
        if mid in ROLE_G and str(n.get('EventID','')).lower() == 'auto':
            st = sorted(stats.get(mid, [dict(lv=1,spd=8,run=8,sight=6,hp=300,at=60,df=30,hit=30,eva=0,exp=50)]), key=lambda s: s['lv'])[0]
            m.setdefault('monsters', []).append(dict(x=n['x'], y=n['y'], role=mid, name=role.get(mid, '?'), set=0, **st, range=[n['x'], n['y'], 0, 0], event='auto'))
            ch = True; continue
        if mid in ROLE_G and n.get('EventID'):
            g = ROLE_G[mid]; (mp.parent/'mon').mkdir(exist_ok=True)
            m.setdefault('monster_sets', {})[f'pd{g}'] = write(g, mp.parent/'mon')
            fr = m['monster_sets'][f'pd{g}']['idle']['frames'][5] or m['monster_sets'][f'pd{g}']['walk']['frames'][0]
            (mp.parent/'props').mkdir(exist_ok=True)
            Image.open(mp.parent/'mon'/fr[0]).save(mp.parent/'props'/f'npc_pd{g}.png')
            n.update(file=f'npc_pd{g}.png', sw=fr[1], sh=fr[2], ox=fr[1]/2, oy=fr[2]-4, npc_dirs=[]); ch = True
        keep.append(n)
    if ch: m['npcs'] = m['objects'] = keep
    for mo in m.get('monsters') or []:
        g = ROLE_G.get(int(mo.get('role') or 0))
        if not g: continue
        (mp.parent/'mon').mkdir(exist_ok=True)
        if f'pd{g}' not in (m.get('monster_sets') or {}):
            m.setdefault('monster_sets', {})[f'pd{g}'] = write(g, mp.parent/'mon')
        mo['set'] = f'pd{g}'; ch = True
    if ch:
        # drop stale interim sets
        for k in ['r348','boss564','rex72','10']:
            if k in m['monster_sets'] and not any(str(x.get('set'))==k for x in m['monsters']): m['monster_sets'].pop(k)
        mp.write_text(json.dumps(m, ensure_ascii=False)); print(mp.parent.name, sorted(m['monster_sets']), len(m['monsters']))
