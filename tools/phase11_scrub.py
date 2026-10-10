"""Phase 11 sprite scrub + NPC frame pick helpers."""
from __future__ import annotations
import struct
from typing import Optional, Tuple
import numpy as np
from PIL import Image

def strip_blue_columns(img: Image.Image, max_cols: int = 12) -> Image.Image:
    a = np.array(img.convert("RGBA"))
    W = a.shape[1]
    for xs in (range(min(max_cols, W)), range(W - 1, max(W - max_cols, 0) - 1, -1)):
        for x in xs:
            col = a[:, x]
            op = col[:, 3] > 0
            if op.sum() < 2:
                continue
            b, r = col[op, 2], col[op, 0]
            if (b.astype(int) > r.astype(int) + 18).mean() > 0.45 and float(b.mean()) > 24:
                a[:, x, 3] = 0
    out = Image.fromarray(a)
    bbox = out.split()[-1].getbbox()
    return out.crop(bbox) if bbox else out


def scrub_sprite_fringe(img: Image.Image) -> Image.Image:
    """Remove chroma-blue fringe, opaque black, and 1px edge speckles."""
    a = np.array(img.convert("RGBA"), dtype=np.uint8)
    rgb, alpha = a[:, :, :3], a[:, :, 3]
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    # near-black → clear
    near_black = (r < 10) & (g < 10) & (b < 10)
    # near-primary blue / control blue (maps + building fringe)
    near_blue = (b >= 14) & (r <= 6) & (g <= 10) & (b > r + 8) & (b > g + 6)
    # very saturated blue leftover
    sat_blue = (b >= 40) & (r <= 12) & (g <= 16) & (b >= r * 2) & (b >= g * 2)
    alpha = np.where(near_black | near_blue | sat_blue, 0, alpha)
    a[:, :, 3] = alpha
    # kill isolated opaque pixels (fringe dots)
    op = alpha > 0
    # 4-neighbor count
    n = np.zeros_like(op, dtype=np.uint8)
    n[1:, :] += op[:-1, :]
    n[:-1, :] += op[1:, :]
    n[:, 1:] += op[:, :-1]
    n[:, :-1] += op[:, 1:]
    isolated = op & (n == 0)
    a[:, :, 3] = np.where(isolated, 0, a[:, :, 3])
    out = Image.fromarray(a)
    bbox = out.split()[-1].getbbox()
    out = out.crop(bbox) if bbox else out
    return strip_blue_columns(out)


def pick_nested_best(blob: bytes, min_h: int = 18, min_area: int = 200):
    """Return best (tallest/area) nested lep frame from ResNpc-style TOC."""
    from leyilib import decode_lep_sprite, decode_lep_png
    if len(blob) < 8:
        return None
    count = struct.unpack_from("<I", blob, 0)[0]
    if count == 0 or count > 512:
        return None
    offs = []
    for i in range(count):
        if 4 + 4 * (i + 1) > len(blob):
            break
        offs.append(struct.unpack_from("<I", blob, 4 + 4 * i)[0])
    best = None
    for i, o in enumerate(offs):
        if o >= len(blob) or blob[o : o + 4] != b"lep\x00":
            continue
        end = offs[i + 1] if i + 1 < len(offs) else len(blob)
        nest = blob[o:end]
        img = None
        for fn in (decode_lep_sprite, decode_lep_png):
            try:
                img = fn(nest)
                if img is not None:
                    break
            except Exception:
                continue
        if img is None:
            continue
        area = img.size[0] * img.size[1]
        h = img.size[1]
        score = (h >= min_h, area, h)
        if best is None or score > best[0]:
            best = (score, img)
    if best and (best[0][0] or best[0][1] >= min_area):
        return best[1]
    return best[1] if best else None


def spr_first_large_res00(spr_blob: bytes, res00, min_side: int = 40):
    """Scan Spr descriptor for res00 entries; return largest decoded sprite."""
    from leyilib import decode_lep_sprite
    best = None
    seen = set()
    for off in range(0, len(spr_blob) - 4, 4):
        packed = struct.unpack_from("<I", spr_blob, off)[0]
        entry = packed & 0xFFFF
        hi = (packed >> 16) & 0xFFFF
        if entry in seen or entry >= res00.count:
            continue
        # accept common hi flags or any large referenced entry
        if hi not in (0x10, 0x150, 0x170, 368) and not (0x100 <= hi <= 0x200):
            continue
        seen.add(entry)
        blob = res00.entry_bytes(entry)
        if len(blob) < 200:
            continue
        try:
            img = decode_lep_sprite(blob)
        except Exception:
            img = None
        if img is None:
            continue
        if max(img.size) < min_side:
            continue
        area = img.size[0] * img.size[1]
        if best is None or area > best[0]:
            best = (area, img)
    return best[1] if best else None


def parse_bld_hotspot(data: bytes, body: int) -> Tuple[int, int, int, int]:
    """Return ox, oy, w, h with best-effort Q8 / unaligned fallback."""
    # standard layout
    ox_q, oy_q = struct.unpack_from("<ii", data, body + 16)
    w_q, h_q = struct.unpack_from("<II", data, body + 24)
    def q8(v, signed=True):
        if abs(v) > 500_000:
            return 0
        return v >> 8
    ox, oy = q8(ox_q), q8(oy_q)
    w, h = q8(w_q, False), q8(h_q, False)
    # unaligned +1 byte often yields sensible small hotspots
    if abs(ox) > 80 or abs(oy) > 200 or w > 800 or h > 800:
        try:
            ox2, oy2 = struct.unpack_from("<ii", data, body + 17)
            w2, h2 = struct.unpack_from("<II", data, body + 25)
            if abs(ox2) < 200 and abs(oy2) < 400 and 0 < w2 < 600 and 0 < h2 < 600:
                return ox2, oy2, w2, h2
        except Exception:
            pass
    if abs(ox) > 80:
        ox = 0
    if abs(oy) > 200:
        oy = 0
    if w > 800:
        w = 0
    if h > 800:
        h = 0
    return ox, oy, w, h
