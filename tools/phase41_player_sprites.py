#!/usr/bin/env python3
"""Phase 41: walk/run gait + RH layering fix on top of Phase39.

Keeps Phase39 facing / RH_002 / (body+3)%8. Changes:
1. **Ping-pong pad** for 3-frame Spr walks (1,2,3,2) — client also ping-pongs.
2. **Separate run atlas** from 2nd Spr locomotion group (code 6/8/10).
3. **RH under** expanded to body dirs {0,1,2,3,4,5} (S/SW/W/NW/N/NE);
   E=6 and SE=7 stay RH over (Wine strip).
4. CA/TK/HD/RH share the same frame index into their loco sub lists.

Authority: this script (phase39 still valid for RH_002/facing; gait/run → here).
Reproduce: ``python3 tools/phase41_player_sprites.py``
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
SAMPLES = ROOT / 'assets/samples/phase41'

ART_DIR_NAMES = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
HOLD_ORDER = ['E', 'SE', 'S', 'SW', 'W', 'NW', 'N', 'NE']

BODY = {'CA': (34, 0), 'HD': (112, 128), 'TK': (114, 256)}
RH_SID, RH_BASE = 165, 896
RH_DIR_OFF = 0  # Phase58: Mac recording S/N/E sword = RH same dir as body (was +3 for all)
# Phase58 per-body override: W keeps raised up-right blade (+3) as in the recording
RH_DIR_OFF_BY_BODY = {2: 3}
def rh_dir(body_d: int) -> int:
    return (body_d + RH_DIR_OFF_BY_BODY.get(body_d, RH_DIR_OFF)) % 8
# Phase41: Wine strips — sword behind for S/SW/W/NW/N/NE; over for E/SE
RH_UNDER_BODY = [2, 3]  # Phase58: right hand on far side only when facing W/NW

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


def _pad_subs(subs: list[int], want: int) -> list[int]:
    """Pad short lists with ping-pong mirror (1,2,3 → 1,2,3,2)."""
    while len(subs) < want:
        if len(subs) >= 2:
            nxt = subs[-2]
            if len(subs) >= 3 and nxt == subs[-1]:
                nxt = subs[0]
            subs.append(nxt)
        else:
            subs.append(subs[-1])
    return subs[:want]


def loco_subs(sid: int, base: int, d: int, which: int = 0, want: int = 4) -> list[int]:
    """1-based nest indices for walk (which=0) or run (which=1) from Spr loco groups.

    Prefers sole-res groups with code in {6,8,10} and nf>=3.
    Code 6 nf=6 is already ping-pong in Spr — take forward 4.
    Dirs with only nf=1 singles: continuous nests starting at which*8.
    """
    sole = [g for g in P24.groups(sid)
            if g['frames'] and set(f['res'] for f in g['frames']) == {base + d}]
    candidates: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    for g in sole:
        nf = len(g['frames'])
        code = g['code']
        if nf < 3 or code not in (6, 8, 10):
            continue
        subs = [int(f['sub']) for f in g['frames']]
        key = tuple(subs)
        if key in seen:
            continue
        seen.add(key)
        if nf == 6:
            subs = subs[:4]
        candidates.append(subs)

    if which < len(candidates):
        return _pad_subs(list(candidates[which]), want)

    # Only one multi-frame loco group (e.g. SW): walk = that group; run = nests +8
    if which > 0 and candidates:
        base_subs = candidates[0]
        bumped = [s + 8 for s in base_subs]
        return _pad_subs(bumped, want)

    # nf=1-only dirs (N/NE): walk = nests 1..4, run = nests 9..12 (0-based 8..)
    if sole and all(len(g['frames']) == 1 for g in sole):
        start = 1 + which * 8
        return list(range(start, start + want))

    # fallback: gather sorted unique subs
    by: dict[int, object] = {}
    for g in sole:
        for f in g['frames']:
            by.setdefault(int(f['sub']), f)
    if by:
        keys = sorted(by)
        offset = which * want
        picked = keys[offset:offset + want]
        if len(picked) < want and keys:
            picked = keys[:want]
        return _pad_subs(list(picked) if picked else list(range(1, want + 1)), want)
    start = 1 + which * 8
    return list(range(start, start + want))


def export_player():
    SAMPLES.mkdir(parents=True, exist_ok=True)
    r1 = L.LeyiLib.open(Z / 'ResPlayer1.lib')

    body_frames = {k: {d: nested(r1, base + d) for d in range(8)} for k, (_, base) in BODY.items()}
    rh_frames = {d: nested(r1, RH_BASE + d) for d in range(8)}
    body_oxoy = {k: {d: sole_oxoy_map(sid, base, d) for d in range(8)} for k, (sid, base) in BODY.items()}
    rh_oxoy = {d: sole_oxoy_map(RH_SID, RH_BASE, d) for d in range(8)}

    ca_walk = {d: loco_subs(34, 0, d, which=0) for d in range(8)}
    ca_run = {d: loco_subs(34, 0, d, which=1) for d in range(8)}
    print('CA walk subs', ca_walk)
    print('CA run  subs', ca_run)
    print('CA nests', [len(body_frames['CA'][d]) for d in range(8)])
    print('RH nests', [len(rh_frames[d]) for d in range(8)])

    out = WEB / 'player'
    for sub in ('walk', 'run', 'idle', 'attack'):
        (out / sub).mkdir(parents=True, exist_ok=True)

    anchors = {k: [] for k in list(BODY) + ['RH']}

    def composite(body_d: int, fi: int, mode: str = 'walk') -> Image.Image:
        subs = ca_run[body_d] if mode == 'run' else ca_walk[body_d]
        sub1 = subs[fi % len(subs)]
        nest_i = max(0, sub1 - 1)
        rh_d = rh_dir(body_d)
        rh_subs = loco_subs(RH_SID, RH_BASE, rh_d, which=(1 if mode == 'run' else 0))
        rh_sub1 = rh_subs[fi % len(rh_subs)]
        rh_nest = max(0, rh_sub1 - 1)

        c = Image.new('RGBA', CANVAS, (0, 0, 0, 0))
        under = body_d in RH_UNDER_BODY
        order = ['RH', 'CA', 'TK', 'HD'] if under else ['CA', 'TK', 'HD', 'RH']
        for k in order:
            if k == 'RH':
                ims = rh_frames[rh_d]
                ni, s1 = rh_nest, rh_sub1
                # Phase58: run blade nest empty → reuse walk blade of the same step (recording: blade always visible)
                if mode == 'run' and (ni >= len(ims) or ims[ni] is None):
                    ws = loco_subs(RH_SID, RH_BASE, rh_d, which=0)
                    s1 = ws[fi % len(ws)]; ni = max(0, s1 - 1)
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
            composite(d, fi, 'walk').save(out / 'walk' / f'{d}_{fi}.png')
            composite(d, fi, 'run').save(out / 'run' / f'{d}_{fi}.png')
            if fi == 0:
                composite(d, 0, 'walk').save(out / 'idle' / f'{d}_0.png')
                sub1 = ca_walk[d][0]
                for k in BODY:
                    anchors[k].append(list(lookup_oxoy(body_oxoy[k][d], sub1, DEFAULT_OXOY[k])))
                rh_d = rh_dir(d)
                rh_s = loco_subs(RH_SID, RH_BASE, rh_d, which=0)[0]
                anchors['RH'].append(list(lookup_oxoy(rh_oxoy[rh_d], rh_s, DEFAULT_OXOY['RH'])))
        # attack: mid nest of CA strip (unchanged spirit from P39)
        n_ca = max(1, len(body_frames['CA'][d]))
        ai_sub = min(n_ca, max(ca_walk[d][-1] + 4, n_ca // 2))
        rh_d = rh_dir(d)
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
        'run_frames': 4,
        'gait': 'pingpong_012321',
        'hotspot': [CX, CY],
        'canvas': list(CANVAS),
        'frame_order': 'spr_loco_subs_walk0_run1',
        'ca_walk_subs': ca_walk,
        'ca_run_subs': ca_run,
        'dir_convention': 'E→6 SE→7 S→0 SW→1 W→2 NW→3 N→4 NE→5; facing=(oct+6)%8',
        'art_dir_names': ART_DIR_NAMES,
        'rh_index': f'(body+{RH_DIR_OFF})%8',
        'rh_under_dirs': RH_UNDER_BODY,
        'rh_part': 'RH_002',
        'rh_spr': RH_SID,
        'rh_base': RH_BASE,
        'source': 'Phase41: RH_002 +(body+3)%8; walk/run Spr loco groups; ping-pong pad; RH under S/SW/W/NW/N/NE; facing (oct+6)%8',
        'spr_parts': {**{k: v[0] for k, v in BODY.items()}, 'RH': RH_SID},
        'res_bases': {**{k: v[1] for k, v in BODY.items()}, 'RH': RH_BASE},
        'anchors': anchors,
        'phase39_note': 'facing/RH_002 unchanged; gait+run+RH_under superseded by phase41',
    }
    (out / 'meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print('exported', out)
    return composite, ca_walk, ca_run


def make_samples(composite, ca_walk, ca_run):
    SAMPLES.mkdir(parents=True, exist_ok=True)
    wine_root = ROOT / 'assets/samples/phase37/wine_walk'
    strip_w = ROOT / 'assets/samples/phase37/wine_walk_8dir_strip.png'
    strip_r = ROOT / 'assets/samples/phase37/wine_run_8dir_strip.png'

    def hold_art(name):
        return (HOLD_ORDER.index(name) + 6) % 8

    # 8×4 walk / run grids (hold columns)
    for mode in ('walk', 'run'):
        grid = Image.new('RGBA', (8 * 100, 4 * 110 + 28), (22, 22, 32, 255))
        D = ImageDraw.Draw(grid)
        D.text((6, 4), f'P41 {mode} 8×4  hold cols  RH under={RH_UNDER_BODY}', fill=(255, 220, 80))
        for oct, name in enumerate(HOLD_ORDER):
            art = hold_art(name)
            D.text((oct * 100 + 18, 18), f'{name}\na{art}', fill=(180, 220, 255))
            for fi in range(4):
                im = composite(art, fi, mode)
                grid.paste(im, (oct * 100, 40 + fi * 110), im)
        grid.save(SAMPLES / f'{mode}_8dir_grid.png')

    # GIFs per hold direction
    def save_gif(path, frames, duration=120):
        frames[0].save(path, save_all=True, append_images=frames[1:],
                       duration=duration, loop=0, disposal=2)

    # Ping-pong cycle for GIF preview (matches client)
    PP = [0, 1, 2, 3, 2, 1]
    for mode in ('walk', 'run'):
        mosaic_frames = []
        for step in range(6):
            fi = PP[step]
            row = Image.new('RGBA', (8 * 96, 110), (18, 18, 26, 255))
            D = ImageDraw.Draw(row)
            D.text((4, 2), f'{mode} pp fi={fi}', fill=(255, 220, 80))
            for oct, name in enumerate(HOLD_ORDER):
                art = hold_art(name)
                im = composite(art, fi, mode).resize((90, 90), Image.NEAREST)
                row.paste(im, (oct * 96 + 3, 18), im)
                if step == 0:
                    D.text((oct * 96 + 35, 95), name, fill=(180, 255, 180))
            mosaic_frames.append(row)
        save_gif(SAMPLES / f'{mode}_8dir.gif', mosaic_frames, duration=100)

        for name in HOLD_ORDER:
            art = hold_art(name)
            frames = []
            for step in range(6):
                fi = PP[step]
                canvas = Image.new('RGBA', (140, 150), (18, 18, 26, 255))
                D = ImageDraw.Draw(canvas)
                D.text((8, 4), f'{mode} {name} (hold)', fill=(255, 220, 80))
                im = composite(art, fi, mode)
                canvas.paste(im, (6, 20), im)
                frames.append(canvas)
            save_gif(SAMPLES / f'{mode}_{name}.gif', frames, duration=110)

    # Wine vs web comparison strips
    def wine_tile(strip_path, oct, size=100):
        if not strip_path.exists():
            return Image.new('RGBA', (size, size), (40, 40, 50, 255))
        im = Image.open(strip_path).convert('RGBA')
        tw = im.width // 8
        tile = im.crop((oct * tw, 18, (oct + 1) * tw, min(im.height, 130)))
        return tile.resize((size, size), Image.NEAREST)

    for mode, strip in (('walk', strip_w), ('run', strip_r)):
        board = Image.new('RGBA', (8 * 110, 250), (16, 16, 24, 255))
        D = ImageDraw.Draw(board)
        D.text((6, 4), f'P41 Wine strip vs Web {mode} f0  (hold cols)', fill=(255, 220, 80))
        for oct, name in enumerate(HOLD_ORDER):
            art = hold_art(name)
            board.paste(wine_tile(strip, oct, 100), (oct * 110 + 5, 28))
            web = composite(art, 0, mode).resize((100, 100), Image.NEAREST)
            board.paste(web, (oct * 110 + 5, 140), web)
            D.text((oct * 110 + 40, 22), name, fill=(180, 255, 180))
        D.text((6, 130), 'Web', fill=(200, 200, 200))
        board.save(SAMPLES / f'wine_vs_web_{mode}_8dir.png')

        # Animated side-by-side GIF (web ping-pong; wine uses f0..3 if available)
        frames = []
        for step in range(6):
            fi = PP[step]
            wine_fi = min(3, fi if fi < 4 else 5 - fi)  # map pp back to 0..3
            row = Image.new('RGBA', (8 * 100, 220), (16, 16, 24, 255))
            D = ImageDraw.Draw(row)
            D.text((4, 2), f'Wine {mode} f{wine_fi} | Web {mode} pp={fi}', fill=(255, 220, 80))
            for oct, name in enumerate(HOLD_ORDER):
                art = hold_art(name)
                wp = wine_root / f'{mode}_{name}_f{wine_fi}.png'
                if wp.exists():
                    # per-dir crop using strip coords defaults; E@377,263 as baseline
                    # Use center of motion: crop around 400,280 as compromise
                    wim = Image.open(wp).convert('RGBA')
                    crop = wim.crop((377 - 48, 263 - 72, 377 + 48, 263 + 36)).resize((90, 90))
                    row.paste(crop, (oct * 100 + 5, 24))
                else:
                    row.paste(wine_tile(strip, oct, 90), (oct * 100 + 5, 24))
                web = composite(art, fi, mode).resize((90, 90), Image.NEAREST)
                row.paste(web, (oct * 100 + 5, 120), web)
            frames.append(row)
        save_gif(SAMPLES / f'wine_vs_web_{mode}_8dir.gif', frames, duration=120)

    # RH under proof
    proof = Image.new('RGBA', (8 * 100, 200), (40, 30, 24, 255))
    D = ImageDraw.Draw(proof)
    D.text((6, 4), 'P41 RH under {0,1,2,3,4,5}=S..NE; over E/SE | facing (oct+6)%8', fill=(255, 220, 80))
    for oct, name in enumerate(HOLD_ORDER):
        art = hold_art(name)
        proof.paste(composite(art, 0, 'walk'), (oct * 100, 24), composite(art, 0, 'walk'))
        under = 'U' if art in RH_UNDER_BODY else 'O'
        D.text((oct * 100 + 15, 20), f'{name} {under}', fill=(255, 230, 120))
    proof.save(SAMPLES / 'proof_rh_under_8dir.png')

    print('samples →', SAMPLES)


if __name__ == '__main__':
    composite, ca_walk, ca_run = export_player()
    make_samples(composite, ca_walk, ca_run)
