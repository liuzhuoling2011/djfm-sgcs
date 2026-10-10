#!/usr/bin/env python3
"""Phase 19b: SprRole.h paper-doll for player + town NPC SprRole TK → Res* frames.

Player (role 901 / 剑客):
  SprRole.h SPR_ROLE_901_{CA,HD,TK,RH_005}_001_001 → Spr.lib indices 34/112/114/116
  Each Spr entry: 512 slots, res = ResPlayer1 base+dir (CA:0-7, HD:128-135, TK:256-263, RH:384-391)
  ox/oy = foot hotspot in each part sprite; composite at shared (CX,CY).

Town NPCs:
  SPR_ROLE_{graph}_TK_001_001 → Spr index (e.g. 623→1619); ResExNpc/ResNpc frames with size filter.
  Civilian fallbacks when SprRole hits combat/partial art (sy→1008, etc.).
"""
from __future__ import annotations
# Re-run logic lives in this module; invoke: python3 tools/phase19b_sprites.py
import json, re, struct, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leyilib as L, bld_rle as B

ROOT = Path(__file__).resolve().parents[1]
Z = ROOT / 'extract/Blade And Sword 2 Ancient Legend/zy'
WEB = ROOT / 'web/public/game'
SPRROLE = ROOT / 'assets/samples/phase9/fol_extract/slr/SprRole.h'

def parse_spr(s, gid):
    if gid >= s.count: return []
    b = s.entry_bytes(gid); v = list(struct.unpack_from('<%di' % (len(b)//4), b))
    frames = []; i = 1
    while i + 9 < len(v):
        if v[i+1]==4 and v[i+2]==7 and v[i+3]==0 and 0 < v[i+4] < 64:
            packed = v[i+5] & 0xffffffff
            frames.append(dict(n=v[i+4], res=packed & 0xffff, ox=v[i+8], oy=v[i+9]))
            i += 10
        else: i += 1
    return frames

def nested(r, res):
    out = []
    for _, lep in L.find_nested_leps(r.entry_bytes(res)):
        try: im = B.decode(lep)
        except Exception: continue
        if im is not None and (np.array(im)[:,:,3]>0).sum() > 15:
            out.append(im)
    return out

def export_player():
    s = L.LeyiLib.open(Z/'Spr.lib'); r1 = L.LeyiLib.open(Z/'ResPlayer1.lib')
    parts = {'CA': (34, 0), 'HD': (112, 128), 'TK': (114, 256), 'RH': (116, 384)}
    parsed = {k: parse_spr(s, sid) for k,(sid,_) in parts.items()}
    anc = {}
    for k,(_,base) in parts.items():
        a = []
        for d in range(8):
            slots = [f for f in parsed[k] if f['res']==base+d]
            if not slots: a.append((20,40)); continue
            a.append((int(round(sum(f['ox'] for f in slots)/len(slots))),
                      int(round(sum(f['oy'] for f in slots)/len(slots)))))
        anc[k] = a
    frames = {k: {d: nested(r1, base+d) for d in range(8)} for k,(_,base) in parts.items()}
    CX,CY = 64,100
    out = WEB/'player'
    for sub in ('walk','idle','attack'): (out/sub).mkdir(parents=True, exist_ok=True)
    def composite(d, fi):
        c = Image.new('RGBA',(128,128),(0,0,0,0))
        for k in ('CA','TK','HD','RH'):
            fr = frames[k][d]
            if not fr: continue
            im = fr[fi % len(fr)]; ox,oy = anc[k][d]
            c.alpha_composite(im, (CX-ox, CY-oy))
        bb = c.getbbox(); return c.crop(bb) if bb else c
    for d in range(8):
        n = max(1, len(frames['CA'][d]))
        for fi,src in enumerate([0, n//4, n//2, (3*n)//4]):
            im = composite(d, src); im.save(out/'walk'/f'{d}_{fi}.png')
            if fi==0: im.save(out/'idle'/f'{d}_0.png')
        composite(d, min(n-1, n//2+2)).save(out/'attack'/f'{d}_0.png')
    Image.open(out/'idle'/'0_0.png').save(WEB/'player.png')
    (out/'meta.json').write_text(json.dumps({
        'dirs':8,'walk_frames':4,'spr_parts':{k:v[0] for k,v in parts.items()},
        'res_bases':{k:v[1] for k,v in parts.items()},'anchors':anc,'hotspot':[CX,CY],
    }, indent=2))
    print('player ok')

if __name__ == '__main__':
    export_player()
