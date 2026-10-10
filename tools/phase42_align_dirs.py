#!/usr/bin/env python3
"""Phase42: key-hold Wine vs Web alignment boards.

Uses assets/samples/phase42/wine_hold/{hold,run_hold}_*.gif (real key-held
captures) and web_hold/* — never strip column crops.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageSequence

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/samples/phase42'
WINE = OUT / 'wine_hold'
WEB = OUT / 'web_hold'

# Column order = key tags (same keys Wine & Web held)
KEY_ORDER = ['W', 'A', 'S', 'D', 'WA', 'WD', 'SA', 'SD']
ART = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
# Client facing with (oct+6)%8
KEY_TO_ART = {'W': 4, 'A': 2, 'S': 0, 'D': 6, 'WA': 3, 'WD': 5, 'SA': 1, 'SD': 7}

REQUIRED = [f'hold_{t}.gif' for t in KEY_ORDER] + [f'run_hold_{t}.gif' for t in KEY_ORDER]


def mean_frame_diff(path: Path) -> float:
    """Center-crop MAD — camera-locked town keeps most pixels still."""
    import numpy as np
    frames = load_gif_frames(path, max_frames=8)
    if len(frames) < 2:
        return 0.0
    diffs = []
    for a, b in zip(frames, frames[1:]):
        aa = np.asarray(a.convert('RGB'), dtype=np.float32)
        bb = np.asarray(b.convert('RGB'), dtype=np.float32)
        if aa.shape != bb.shape:
            continue
        h, w = aa.shape[:2]
        # player lives near center under locked cam
        y0, y1 = max(0, h // 2 - 90), min(h, h // 2 + 50)
        x0, x1 = max(0, w // 2 - 80), min(w, w // 2 + 80)
        diffs.append(float(np.abs(aa[y0:y1, x0:x1] - bb[y0:y1, x0:x1]).mean()))
    return sum(diffs) / max(1, len(diffs))


def wine_ready() -> list[str]:
    missing = []
    for f in REQUIRED:
        p = WINE / f
        if not p.exists() or p.stat().st_size < 20000:
            missing.append(f + ' (missing/small)')
            continue
        d = mean_frame_diff(p)
        # Char-create UI barely moves; real walk GIFs usually >> 1
        if d < 0.8:
            missing.append(f + f' (static UI? diff={d:.3f})')
    return missing


def load_gif_frames(path: Path, max_frames=8) -> list[Image.Image]:
    im = Image.open(path)
    frames = []
    for i, fr in enumerate(ImageSequence.Iterator(im)):
        frames.append(fr.convert('RGBA'))
        if i + 1 >= max_frames:
            break
    return frames or [Image.new('RGBA', (128, 128), (40, 40, 50, 255))]


def crop_char(im: Image.Image, size=100) -> Image.Image:
    """Center crop — Wine full-window GIFs need center; web already cropped."""
    w, h = im.size
    if w <= size + 40 and h <= size + 60:
        return im.resize((size, size), Image.NEAREST)
    # Prefer center-lower (player under camera)
    cx, cy = w // 2, h // 2 + 8
    half = max(size // 2, min(w, h) // 5)
    # If looks like full game window, tighter crop around center
    if w >= 400:
        half = 80
        cy = h // 2 + 10
    box = (cx - half, cy - half - 15, cx + half, cy + half - 15)
    return im.crop(box).resize((size, size), Image.NEAREST)


def save_gif(path: Path, frames: list[Image.Image], duration=100):
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=duration, loop=0, disposal=2)


def build_board(mode: str):
    """mode: walk -> hold_*.gif ; run -> run_hold_*.gif"""
    prefix = 'hold_' if mode == 'walk' else 'run_hold_'
    # Static PNG: mid frame
    board = Image.new('RGBA', (8 * 120, 280), (16, 16, 24, 255))
    D = ImageDraw.Draw(board)
    D.text((6, 4), f'P42 Wine vs Web {mode}  cols=KEY held  (not strip cols)', fill=(255, 220, 80))
    D.text((6, 130), 'Wine', fill=(200, 200, 200))
    D.text((6, 250), 'Web', fill=(200, 200, 200))

    anim_frames = []
    for step in range(6):
        row = Image.new('RGBA', (8 * 110, 240), (16, 16, 24, 255))
        Rd = ImageDraw.Draw(row)
        Rd.text((4, 2), f'P42 {mode} step{step}  Wine|Web  key cols', fill=(255, 220, 80))
        anim_frames.append(row)

    for i, tag in enumerate(KEY_ORDER):
        art = KEY_TO_ART[tag]
        wp = WINE / f'{prefix}{tag}.gif'
        vb = WEB / f'{prefix}{tag}.gif'
        wframes = load_gif_frames(wp) if wp.exists() else []
        vframes = load_gif_frames(vb) if vb.exists() else []
        # static mid
        wmid = crop_char(wframes[min(2, len(wframes)-1)]) if wframes else Image.new('RGBA', (100, 100), (60, 40, 40, 255))
        vmid = crop_char(vframes[min(2, len(vframes)-1)]) if vframes else Image.new('RGBA', (100, 100), (40, 40, 60, 255))
        board.paste(wmid, (i * 120 + 10, 28))
        board.paste(vmid, (i * 120 + 10, 150), vmid)
        D.text((i * 120 + 30, 22), f'{tag}', fill=(180, 255, 180))
        D.text((i * 120 + 20, 128), f'a{art}={ART[art]}', fill=(180, 200, 255))

        # per-key side-by-side GIF
        sbs = []
        n = max(len(wframes), len(vframes), 4)
        for fi in range(min(8, n)):
            canvas = Image.new('RGBA', (220, 140), (16, 16, 24, 255))
            Cd = ImageDraw.Draw(canvas)
            Cd.text((6, 2), f'{mode} key {tag}  Wine|Web  art{art}', fill=(255, 220, 80))
            wi = crop_char(wframes[fi % len(wframes)], 100) if wframes else Image.new('RGBA', (100, 100), (60, 40, 40))
            vi = crop_char(vframes[fi % len(vframes)], 100) if vframes else Image.new('RGBA', (100, 100), (40, 40, 60))
            canvas.paste(wi, (8, 24))
            canvas.paste(vi, (112, 24), vi)
            sbs.append(canvas)
        save_gif(OUT / f'key_{tag}_{"run_" if mode=="run" else ""}wine_vs_web.gif', sbs, 100)

        for step in range(6):
            wi = crop_char(wframes[step % len(wframes)], 90) if wframes else Image.new('RGBA', (90, 90), (60, 40, 40))
            vi = crop_char(vframes[step % len(vframes)], 90) if vframes else Image.new('RGBA', (90, 90), (40, 40, 60))
            anim_frames[step].paste(wi, (i * 110 + 8, 24))
            anim_frames[step].paste(vi, (i * 110 + 8, 130), vi)
            if step == 0:
                ImageDraw.Draw(anim_frames[step]).text((i * 110 + 35, 220), tag, fill=(180, 255, 180))

    board.save(OUT / f'wine_vs_web_{mode}_8dir.png')
    save_gif(OUT / f'wine_vs_web_{mode}_8dir.gif', anim_frames, 110)
    print('wrote', OUT / f'wine_vs_web_{mode}_8dir.png')


def main():
    miss = wine_ready()
    if miss:
        print('WINE_NOT_READY missing:', ', '.join(miss))
        sys.exit(2)
    print('Wine hold set complete — building boards')
    build_board('walk')
    build_board('run')
    # Refresh root hold_*.gif: prefer wine if we want key_*; keep web copies as web_hold_*
    # Deliverable hold_*.gif = web recordings already at OUT; also copy wine to wine_hold_* names at root
    for tag in KEY_ORDER:
        for prefix in ('hold_', 'run_hold_'):
            src = WINE / f'{prefix}{tag}.gif'
            if src.exists():
                (OUT / f'wine_{prefix}{tag}.gif').write_bytes(src.read_bytes())
    print('done')


if __name__ == '__main__':
    main()
