#!/usr/bin/env python3
"""Phase 39: authoritative player paper-doll export (walk/idle/attack).

Root causes fixed
-----------------
1. **Sword backwards:** Init uses **RH_002** (Spr 165, Res 896), not RH_005.
   RH art dir offset: ``rh_dir = (body_dir + 3) % 8`` (E body6 → RH1).
2. **Seven dirs weird:** ``facing = (oct+6)%8`` → screen-E → art 6.
   Body arts: S=0 SW=1 W=2 NW=3 N=4 NE=5 E=6 SE=7.
3. **Walk nests:** Spr walk group when present (d0/d1: subs 1–4; d2/d3: 5–8;
   d6/d7: 1–3 padded). Else first 4 nests. Never ``n/4`` action mix.
4. **ox/oy:** Only from **sole-res** Spr groups; clamp to sane range.
5. **RH under:** body NW/N/NE = {3,4,5}.

Reproduce: ``python3 tools/phase39_player_sprites.py``
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leyilib as L, bld_rle as B
import phase24_paperdoll as P24

ROOT = Path(__file__).resolve().parents[1]
Z = ROOT / 'extract/Blade And Sword 2 Ancient Legend/zy'
WEB = ROOT / 'web/public/game'
SAMPLES = ROOT / 'assets/samples/phase39'

ART_DIR_NAMES = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
HOLD_ORDER = ['E', 'SE', 'S', 'SW', 'W', 'NW', 'N', 'NE']

BODY = {'CA': (34, 0), 'HD': (112, 128), 'TK': (114, 256)}
RH_SID, RH_BASE = 165, 896
RH_DIR_OFF = 3
RH_UNDER_BODY = [3, 4, 5]

CX, CY = 64, 100
CANVAS = (128, 128)
DEFAULT_OXOY = {'CA': (16, 36), 'HD': (4, 67), 'TK': (15, 57), 'RH': (20, 50)}


def nested(r, res):
    out = []
    for _, lep in L.find_nested_leps(r.entry_bytes(res)):
        try:
            im = B.decode(lep)
        except Exception:
            continue
        if im is not None and (np.array(im)[:, :, 3] > 0).sum() > 15:
            out.append(im)
    return out


def sane(ox, oy):
    return -80 <= ox <= 120 and -20 <= oy <= 160


def sole_oxoy_map(sid: int, base: int, d: int) -> dict[int, tuple[int, int]]:
    """1-based sub → (ox,oy) from sole-res Spr groups only."""
    m: dict[int, tuple[int, int]] = {}
    for g in P24.groups(sid):
        fr = g['frames']
        if not fr or set(f['res'] for f in fr) != {base + d}:
            continue
        for f in fr:
            sub = int(f['sub'])
            ox, oy = int(f['ox']), int(f['oy'])
            if sub not in m and sane(ox, oy):
                m[sub] = (ox, oy)
    return m


def lookup_oxoy(m, sub1, default):
    if sub1 in m:
        return m[sub1]
    if not m:
        return default
    return m[min(m.keys(), key=lambda s: abs(s - sub1))]


def walk_subs(sid: int, base: int, d: int, want: int = 4) -> list[int]:
    """1-based nest indices for walk, from best Spr group."""
    sole = [g for g in P24.groups(sid)
            if g['frames'] and set(f['res'] for f in g['frames']) == {base + d}]
    for code, nf in [(10, 4), (8, 5), (6, 6), (8, 3), (10, 3)]:
        for g in sole:
            if g['code'] == code and len(g['frames']) == nf:
                subs = [int(f['sub']) for f in g['frames']]
                # ping-pong (6): take forward 4
                if nf == 6:
                    subs = subs[:4]
                while len(subs) < want:
                    subs.append(subs[-1])
                return subs[:want]
    # Only nf=1 singles (dirs 4–5): continuous walk lives in nests 0..15 —
    # do NOT take every-8th idle keys (9,17,25…). Use first `want` nests.
    if sole and all(len(g['frames']) == 1 for g in sole):
        return list(range(1, want + 1))
    by = {}
    for g in sole:
        for f in g['frames']:
            by.setdefault(int(f['sub']), f)
    if by:
        keys = sorted(by)
        picked = keys[:want]
        while len(picked) < want:
            picked.append(picked[-1])
        return picked
    return list(range(1, want + 1))


def export_player():
    SAMPLES.mkdir(parents=True, exist_ok=True)
    r1 = L.LeyiLib.open(Z / 'ResPlayer1.lib')

    body_frames = {k: {d: nested(r1, base + d) for d in range(8)} for k, (_, base) in BODY.items()}
    rh_frames = {d: nested(r1, RH_BASE + d) for d in range(8)}
    body_oxoy = {k: {d: sole_oxoy_map(sid, base, d) for d in range(8)} for k, (sid, base) in BODY.items()}
    rh_oxoy = {d: sole_oxoy_map(RH_SID, RH_BASE, d) for d in range(8)}

    # Precompute walk sub lists (from CA; sync other parts to same nest indices)
    ca_walk = {d: walk_subs(34, 0, d) for d in range(8)}
    print('CA walk subs', ca_walk)
    print('CA nests', [len(body_frames['CA'][d]) for d in range(8)])
    print('RH nests', [len(rh_frames[d]) for d in range(8)])

    out = WEB / 'player'
    for sub in ('walk', 'idle', 'attack'):
        (out / sub).mkdir(parents=True, exist_ok=True)

    anchors = {k: [] for k in list(BODY) + ['RH']}

    def composite(body_d: int, fi: int) -> Image.Image:
        """fi = walk frame 0..3 using CA walk subs; RH uses same fi on rh_dir strip."""
        subs = ca_walk[body_d]
        sub1 = subs[fi % len(subs)]
        nest_i = max(0, sub1 - 1)
        rh_d = (body_d + RH_DIR_OFF) % 8
        # RH walk subs for rh_d (may differ); use same fi index into RH walk list
        rh_subs = walk_subs(RH_SID, RH_BASE, rh_d)
        rh_sub1 = rh_subs[fi % len(rh_subs)]
        rh_nest = max(0, rh_sub1 - 1)

        c = Image.new('RGBA', CANVAS, (0, 0, 0, 0))
        under = body_d in RH_UNDER_BODY
        order = ['RH', 'CA', 'TK', 'HD'] if under else ['CA', 'TK', 'HD', 'RH']
        for k in order:
            if k == 'RH':
                ims = rh_frames[rh_d]
                ni, s1 = rh_nest, rh_sub1
                ox, oy = lookup_oxoy(rh_oxoy[rh_d], s1, DEFAULT_OXOY['RH'])
            else:
                ims = body_frames[k][body_d]
                ni, s1 = nest_i, sub1
                ox, oy = lookup_oxoy(body_oxoy[k][body_d], s1, DEFAULT_OXOY[k])
            if ni >= len(ims) or ims[ni] is None:
                continue
            c.alpha_composite(ims[ni], (CX - ox, CY - oy))
        return c

    for d in range(8):
        for fi in range(4):
            im = composite(d, fi)
            im.save(out / 'walk' / f'{d}_{fi}.png')
            if fi == 0:
                im.save(out / 'idle' / f'{d}_0.png')
                rh_d = (d + RH_DIR_OFF) % 8
                sub1 = ca_walk[d][0]
                for k in BODY:
                    anchors[k].append(list(lookup_oxoy(body_oxoy[k][d], sub1, DEFAULT_OXOY[k])))
                rh_s = walk_subs(RH_SID, RH_BASE, rh_d)[0]
                anchors['RH'].append(list(lookup_oxoy(rh_oxoy[rh_d], rh_s, DEFAULT_OXOY['RH'])))
        # attack: mid nest of CA strip
        n_ca = max(1, len(body_frames['CA'][d]))
        # temporarily compose with forced nest via walk_subs hack: use last walk-like
        ai_sub = min(n_ca, max(ca_walk[d][-1] + 4, n_ca // 2))
        # build attack by overriding — simple: use nest ai_sub-1 with oxoy lookup
        rh_d = (d + RH_DIR_OFF) % 8
        c = Image.new('RGBA', CANVAS, (0, 0, 0, 0))
        under = d in RH_UNDER_BODY
        order = ['RH', 'CA', 'TK', 'HD'] if under else ['CA', 'TK', 'HD', 'RH']
        ni = min(n_ca - 1, ai_sub - 1)
        for k in order:
            if k == 'RH':
                ims = rh_frames[rh_d]
                rni = min(len(ims) - 1, ni) if ims else 0
                ox, oy = lookup_oxoy(rh_oxoy[rh_d], rni + 1, DEFAULT_OXOY['RH'])
                if ims:
                    c.alpha_composite(ims[rni], (CX - ox, CY - oy))
            else:
                ims = body_frames[k][d]
                ox, oy = lookup_oxoy(body_oxoy[k][d], ni + 1, DEFAULT_OXOY[k])
                if ims and ni < len(ims):
                    c.alpha_composite(ims[ni], (CX - ox, CY - oy))
        c.save(out / 'attack' / f'{d}_0.png')

    Image.open(out / 'idle' / '6_0.png').save(WEB / 'player.png')

    meta = {
        'dirs': 8,
        'walk_frames': 4,
        'hotspot': [CX, CY],
        'canvas': list(CANVAS),
        'frame_order': 'spr_walk_subs_else_first4',
        'ca_walk_subs': ca_walk,
        'dir_convention': 'E→6 SE→7 S→0 SW→1 W→2 NW→3 N→4 NE→5; facing=(oct+6)%8',
        'art_dir_names': ART_DIR_NAMES,
        'rh_index': f'(body+{RH_DIR_OFF})%8',
        'rh_under_dirs': RH_UNDER_BODY,
        'rh_part': 'RH_002',
        'rh_spr': RH_SID,
        'rh_base': RH_BASE,
        'source': 'Phase39: RH_002 +(body+3)%8; Spr walk subs; sole-res ox/oy; RH under NW/N/NE; facing (oct+6)%8',
        'spr_parts': {**{k: v[0] for k, v in BODY.items()}, 'RH': RH_SID},
        'res_bases': {**{k: v[1] for k, v in BODY.items()}, 'RH': RH_BASE},
        'anchors': anchors,
    }
    (out / 'meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print('exported', out)
    # sanity anchors
    for k, rows in anchors.items():
        for d, (ox, oy) in enumerate(rows):
            if not sane(ox, oy):
                print('BAD ANCHOR', k, d, ox, oy)
    return composite


def make_samples(composite):
    SAMPLES.mkdir(parents=True, exist_ok=True)
    wine_root = ROOT / 'assets/samples/phase37/wine_walk'

    grid = Image.new('RGBA', (8 * 100, 4 * 110 + 28), (22, 22, 32, 255))
    D = ImageDraw.Draw(grid)
    D.text((6, 4), 'P39 walk 8×4  hold cols  facing=(oct+6)%8  RH=(b+3)%8', fill=(255, 220, 80))
    for oct, name in enumerate(HOLD_ORDER):
        art = (oct + 6) % 8
        rh = (art + RH_DIR_OFF) % 8
        D.text((oct * 100 + 18, 18), f'{name}\na{art} R{rh}', fill=(180, 220, 255))
        for fi in range(4):
            grid.paste(composite(art, fi), (oct * 100, 40 + fi * 110), composite(art, fi))
    grid.save(SAMPLES / 'walk_8dir_grid.png')

    strip = Image.new('RGBA', (8 * 110, 150), (22, 22, 32, 255))
    D = ImageDraw.Draw(strip)
    D.text((6, 4), 'P39 hold→art  facing=(oct+6)%8', fill=(255, 220, 80))
    for oct, name in enumerate(HOLD_ORDER):
        art = (oct + 6) % 8
        im = composite(art, 0)
        strip.paste(im, (oct * 110 + 5, 36), im)
        D.text((oct * 110 + 18, 20), f'{name}→a{art}', fill=(180, 255, 180))
    strip.save(SAMPLES / 'map_hold_to_art.png')

    for wd in ('E', 'W', 'N', 'S'):
        wp = wine_root / f'walk_{wd}_f0.png'
        if not wp.exists():
            continue
        wine = Image.open(wp).convert('RGBA')
        wcrop = wine.crop((412 - 55, 227 - 85, 412 + 55, 227 + 45)).resize((110, 110))
        art = (HOLD_ORDER.index(wd) + 6) % 8
        web = composite(art, 0).resize((110, 110), Image.NEAREST)
        panel = Image.new('RGBA', (240, 150), (22, 22, 32, 255))
        D = ImageDraw.Draw(panel)
        D.text((8, 4), f'Wine {wd} vs Web a{art}={ART_DIR_NAMES[art]}', fill=(255, 220, 80))
        panel.paste(wcrop, (10, 28))
        panel.paste(web, (125, 28), web)
        panel.save(SAMPLES / f'wine_vs_web_{wd}.png')

    board = Image.new('RGBA', (500, 320), (18, 18, 28, 255))
    D = ImageDraw.Draw(board)
    D.text((8, 4), 'P39 Wine vs Web EWNS', fill=(255, 220, 80))
    for i, wd in enumerate(('E', 'W', 'N', 'S')):
        p = SAMPLES / f'wine_vs_web_{wd}.png'
        if p.exists():
            board.paste(Image.open(p), ((i % 2) * 250, 24 + (i // 2) * 148))
    board.save(SAMPLES / 'wine_vs_web_EWNS.png')

    pe = Image.new('RGBA', (280, 160), (10, 10, 16, 255))
    D = ImageDraw.Draw(pe)
    D.text((8, 4), 'P39: E body6 + RH1 OVER vs Wine walk_E', fill=(255, 220, 80))
    pe.paste(composite(6, 0), (10, 28), composite(6, 0))
    wp = wine_root / 'walk_E_f0.png'
    if wp.exists():
        wine = Image.open(wp).convert('RGBA')
        pe.paste(wine.crop((412 - 55, 227 - 85, 412 + 55, 227 + 45)).resize((128, 128)), (145, 28))
    pe.save(SAMPLES / 'proof_east_p39.png')

    proof = Image.new('RGBA', (8 * 100, 220), (40, 30, 24, 255))
    D = ImageDraw.Draw(proof)
    D.text((6, 4), 'P39 RH=(b+3)%8 over except NW/N/NE under | facing (oct+6)%8', fill=(255, 220, 80))
    for oct, name in enumerate(HOLD_ORDER):
        art = (oct + 6) % 8
        rh = (art + RH_DIR_OFF) % 8
        proof.paste(composite(art, 0), (oct * 100, 24), composite(art, 0))
        D.text((oct * 100 + 15, 20), f'{name} R{rh}', fill=(255, 230, 120))
    D.text((6, 160), 'Wine phase37 below', fill=(200, 200, 200))
    for oct, name in enumerate(HOLD_ORDER):
        wp = wine_root / f'walk_{name}_f0.png'
        if wp.exists():
            wine = Image.open(wp).convert('RGBA')
            crop = wine.crop((412 - 40, 227 - 60, 412 + 40, 227 + 30)).resize((90, 50))
            proof.paste(crop, (oct * 100 + 5, 165))
    proof.save(SAMPLES / 'proof_8dir_p39.png')

    # RH flip/offset board
    flip = Image.new('RGBA', (4 * 130, 150), (22, 22, 32, 255))
    D = ImageDraw.Draw(flip)
    D.text((6, 4), 'E=a6: final RH002+(b+3) | RH005 same body no-off | idle SE=a7', fill=(255, 220, 80))
    flip.paste(composite(6, 0), (5, 28), composite(6, 0))
    flip.paste(composite(7, 0), (135, 28), composite(7, 0))
    flip.paste(composite(0, 0), (265, 28), composite(0, 0))
    D.text((20, 130), 'E a6', fill=(180, 255, 180))
    D.text((150, 130), 'SE a7', fill=(180, 220, 255))
    D.text((280, 130), 'S a0', fill=(255, 200, 120))
    flip.save(SAMPLES / 'rh_hold_samples.png')

    print('samples →', SAMPLES)


if __name__ == '__main__':
    composite = export_player()
    make_samples(composite)
