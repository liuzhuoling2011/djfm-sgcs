#!/usr/bin/env python3
"""leyiLib 2.0 + lep (RGB565 span) unpacker for 刀剑封魔录外传."""
from __future__ import annotations

import argparse
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore

MAGIC = b"leyiLib2.0"
LEP_MAGIC = b"lep\x00"
COLOR_KEY = 0xF81F
TOC_OFF = 0x100


def is_trans_key(v: int) -> bool:
    """True for magenta key and near-primary blue used as second chroma key."""
    if v in (COLOR_KEY, 0, 0xFFFF):
        return True
    r = (v >> 11) & 0x1F
    g = (v >> 5) & 0x3F
    b = v & 0x1F
    if r <= 2 and g <= 4 and b >= 16:
        return True
    if r == 0 and g <= 2 and b >= 8:
        return True
    return False



@dataclass
class LeyiLib:
    path: Path
    data: bytes
    count: int

    @classmethod
    def open(cls, path: Path) -> "LeyiLib":
        data = path.read_bytes()
        if not data.startswith(MAGIC):
            raise ValueError(f"{path}: not leyiLib2.0")
        count = struct.unpack_from("<I", data, 0x10)[0]
        return cls(path=path, data=data, count=count)

    def entry_meta(self, index: int) -> Tuple[int, int]:
        if not 0 <= index < self.count:
            raise IndexError(index)
        return struct.unpack_from("<II", self.data, TOC_OFF + index * 8)

    def entry_bytes(self, index: int) -> bytes:
        off, size = self.entry_meta(index)
        return self.data[off : off + size]

    def iter_entries(self) -> Iterator[Tuple[int, int, int, bytes]]:
        for i in range(self.count):
            off, size = self.entry_meta(i)
            yield i, off, size, self.data[off : off + size]


def classify(blob: bytes) -> str:
    if not blob:
        return "empty"
    if blob.startswith(LEP_MAGIC):
        return "lep"
    return f"bin:{blob[:4].hex()}"


def _rgba(v: int) -> Tuple[int, int, int, int]:
    if is_trans_key(v):
        return (0, 0, 0, 0)
    r = (v >> 11) & 0x1F
    g = (v >> 5) & 0x3F
    b = v & 0x1F
    return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2), 255)


def parse_lep_header(blob: bytes) -> dict:
    if not blob.startswith(LEP_MAGIC) or len(blob) < 128:
        raise ValueError("not lep")
    u1, a, b, c, flags, z0, keyish, z1 = struct.unpack_from("<8I", blob, 4)
    first = struct.unpack_from("<I", blob, 48)[0]
    nslots = (first - 48) // 4 if first >= 48 and (first - 48) % 4 == 0 else 0
    return {
        "u1": u1,
        "aux": (a >> 8) & 0xFFFF,
        "width": (b >> 8) & 0xFFFF,
        "height_field": (c >> 8) & 0xFFFF,
        "flags": flags,
        "keyish": keyish,
        "b36": blob[36:40].hex(),
        "first_off": first,
        "nslots": nslots,
    }


def _skip_pool(blob: bytes, p: int, end: int) -> int:
    while p + 2 <= end and struct.unpack_from("<H", blob, p)[0] in (0x0080, 0x0000, COLOR_KEY):
        p += 2
    return p


def _parse_xn(blob: bytes, start: int, end: int, w: int) -> List[Tuple[int, List[int]]]:
    p = _skip_pool(blob, start, end)
    out: List[Tuple[int, List[int]]] = []
    while p + 4 <= end:
        x, nbytes = struct.unpack_from("<HH", blob, p)
        if nbytes == 0 or nbytes % 2 or x >= w or nbytes > (w - x) * 2 or p + 4 + nbytes > end:
            break
        npix = nbytes // 2
        pix = list(struct.unpack_from(f"<{npix}H", blob, p + 4))
        out.append((x, pix))
        p += 4 + nbytes
    return out


def _parse_yxn(blob: bytes, start: int, end: int, w: int, max_h: int = 512) -> Tuple[List[Tuple[int, int, List[int]]], int]:
    p = _skip_pool(blob, start, end)
    out: List[Tuple[int, int, List[int]]] = []
    while p + 6 <= end:
        y4, x, nbytes = struct.unpack_from("<HHH", blob, p)
        if (
            nbytes == 0
            or nbytes % 2
            or y4 % 4
            or y4 // 4 >= max_h
            or x >= w
            or nbytes > (w - x) * 2
            or p + 6 + nbytes > end
        ):
            break
        y = y4 // 4
        npix = nbytes // 2
        pix = list(struct.unpack_from(f"<{npix}H", blob, p + 6))
        out.append((y, x, pix))
        p += 6 + nbytes
    return out, p


def _get_sec_table(blob: bytes, first: int) -> Tuple[List[int], int]:
    """Ascending u32 file offsets after first_off → secondary row bank (bottom tip)."""
    sec: List[int] = []
    p = first
    while p + 4 <= len(blob):
        v = struct.unpack_from("<I", blob, p)[0]
        if not (p < v <= len(blob)):
            break
        if sec and v <= sec[-1]:
            break
        sec.append(v)
        p += 4
    return sec, p


def _paint(spans: List[Tuple[int, int, List[int]]], w: int, h: int) -> "Image.Image":
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for y, x, pix in spans:
        if not (0 <= y < h):
            continue
        for i, v in enumerate(pix):
            if v == COLOR_KEY:
                continue
            if 0 <= x + i < w:
                px[x + i, y] = _rgba(v)
    bbox = img.split()[-1].getbbox()
    return img.crop(bbox) if bbox else img



def decode_lep_diamond_v2(blob: bytes, cell: Tuple[int, int] = (64, 32)) -> Optional["Image.Image"]:
    """Map tile via row TOC at 0x30 (offsets relative to 0x30).

    ComeOn lep rows: repeated (u16 skip_bytes, u16 n_bytes, RGB565[n/2]).
    TOC length = first_u32/4. Header width/height fields are often 0 / wrong.
    """
    if Image is None:
        raise RuntimeError("Pillow required")
    if not blob.startswith(LEP_MAGIC) or len(blob) < 0x34:
        return None
    import numpy as np
    t0 = struct.unpack_from("<I", blob, 0x30)[0]
    if t0 % 4 or t0 < 4:
        return None
    H = t0 // 4
    if H > 4096 or 0x30 + H * 4 > len(blob):
        return None
    toc = struct.unpack_from(f"<{H}I", blob, 0x30)
    rows = []
    W = 0
    for r in range(H):
        p = 0x30 + toc[r]
        end = 0x30 + toc[r + 1] if r + 1 < H else len(blob)
        pos = 0
        spans = []
        while p + 4 <= end:
            skip, n = struct.unpack_from("<HH", blob, p)
            p += 4
            pos += skip
            if n == 0 or n % 2 or p + n > end:
                break
            npix = n // 2
            pix = list(struct.unpack_from(f"<{npix}H", blob, p))
            spans.append((pos // 2, pix))
            p += n
            pos += n
        W = max(W, pos // 2)
        rows.append(spans)
    cell_w, cell_h = cell
    if W <= 0:
        return None
    # Prefer native diamond width when it matches common 64
    out_w = cell_w if W <= cell_w else W
    out_h = cell_h if H >= cell_h - 2 else max(H, cell_h)
    a = np.zeros((out_h, out_w, 4), np.uint8)
    for y, spans in enumerate(rows):
        if y >= out_h:
            break
        for x, pix in spans:
            for i, v in enumerate(pix):
                xx = x + i
                if not (0 <= xx < out_w):
                    continue
                if v == COLOR_KEY or is_trans_key(v):
                    continue
                r = (v >> 11) & 0x1F
                g = (v >> 5) & 0x3F
                b = v & 0x1F
                a[y, xx] = ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2), 255)
    # If content is shorter than cell, keep bottom padding transparent (tessellation uses 16px step)
    img = Image.fromarray(a)
    if img.size != (cell_w, cell_h):
        canvas = Image.new("RGBA", (cell_w, cell_h), (0, 0, 0, 0))
        # center horizontally; top-align vertically (tip at y=0)
        ox = max(0, (cell_w - img.size[0]) // 2)
        canvas.paste(img, (ox, 0), img)
        img = canvas
    return img

def decode_lep_diamond(blob: bytes, cell: Tuple[int, int] = (64, 32)) -> Optional["Image.Image"]:
    """Map-tile isometric diamond. Prefer TOC row decoder; fall back to stream parser.
    """
    v2 = decode_lep_diamond_v2(blob, cell=cell)
    if v2 is not None and v2.split()[-1].getbbox():
        return v2
    return _decode_lep_diamond_stream(blob, cell=cell)


def _decode_lep_diamond_stream(blob: bytes, cell: Tuple[int, int] = (64, 32)) -> Optional["Image.Image"]:
    """Map-tile isometric diamond: yxn half + continuation + sec tip.

    Header width==0 (common on map_ren town tiles) is treated as 64.
    Spans are right-anchored in the file; we re-center each row into a
    fixed cell so diamonds tessellate under standard iso placement.
    """
    if Image is None:
        raise RuntimeError("Pillow required")
    if not blob.startswith(LEP_MAGIC) or len(blob) < 128:
        return None
    hdr = parse_lep_header(blob)
    w = hdr["width"]
    # Town / map_ren often stores width=0; spans still target a 64px diamond.
    if w == 0:
        w = 64
    sec, sec_end = _get_sec_table(blob, hdr["first_off"])
    if len(sec) < 4:
        return None
    end_mid = sec[0]
    p = sec_end
    if p + 4 <= end_mid:
        x0, n0 = struct.unpack_from("<HH", blob, p)
        if 0 < n0 <= 32 and n0 % 2 == 0 and x0 < w and n0 <= (w - x0) * 2:
            p += 4 + n0
    tri, be = _parse_yxn(blob, p, end_mid, w)
    if len(tri) < 8:
        best: List[Tuple[int, int, List[int]]] = []
        be = p
        for s in range(sec_end, min(sec_end + 100, end_mid)):
            stream, endp = _parse_yxn(blob, s, end_mid, w)
            if len(stream) > len(best):
                best, be = stream, endp
        tri = best
    if len(tri) < 8:
        return None
    max_y = max(y for y, _, _ in tri)
    max_w = max(len(pix) for _, _, pix in tri)
    if max_w < 16:
        return None
    # Tip→equator stored tip-first; reorder so tip is at image y=0
    spans: List[Tuple[int, int, List[int]]] = [(max_y - y, x, pix) for y, x, pix in tri]
    y = max_y
    expect_x = 4
    expect_w = max_w - 4
    p = be
    while expect_w >= 4:
        got = None
        pix = None
        if p + 6 <= end_mid:
            y4, x, nbytes = struct.unpack_from("<HHH", blob, p)
            if (
                nbytes == expect_w * 2
                and x == expect_x
                and y4 % 4 == 0
                and p + 6 + nbytes <= end_mid
            ):
                pix = list(struct.unpack_from(f"<{expect_w}H", blob, p + 6))
                got = p + 6 + nbytes
        if got is None and p + 4 <= end_mid:
            x, nbytes = struct.unpack_from("<HH", blob, p)
            if nbytes == expect_w * 2 and x == expect_x and p + 4 + nbytes <= end_mid:
                pix = list(struct.unpack_from(f"<{expect_w}H", blob, p + 4))
                got = p + 4 + nbytes
        if got is None:
            break
        spans.append((y, expect_x, pix))
        p = got
        y += 1
        expect_x += 4
        expect_w -= 4
    for i, o in enumerate(sec):
        if expect_w < 4:
            break
        e = sec[i + 1] if i + 1 < len(sec) else len(blob)
        chunk = blob[o:e]
        npix = len(chunk) // 2
        if npix < 2:
            break
        take = min(npix, expect_w)
        pix = list(struct.unpack_from(f"<{take}H", chunk, 0))
        spans.append((y, expect_x, pix))
        y += 1
        expect_x += 4
        expect_w -= 4
    # Re-center each row into a fixed cell so right-anchored spans tessellate.
    cell_w, cell_h = cell
    cell_w = max(cell_w, max_w, 8)
    centered: List[Tuple[int, int, List[int]]] = []
    for yy, _x, pix in spans:
        if not pix:
            continue
        x2 = max(0, (cell_w - len(pix)) // 2)
        if x2 + len(pix) > cell_w:
            pix = pix[: cell_w - x2]
        centered.append((yy, x2, pix))
    if not centered:
        return None
    H = max(yy for yy, _, _ in centered) + 1
    # Paint into full cell without bbox-crop (crop would undo centering)
    img = Image.new("RGBA", (cell_w, H), (0, 0, 0, 0))
    px = img.load()
    for yy, xx, pix in centered:
        if not (0 <= yy < H):
            continue
        for i, v in enumerate(pix):
            if v == COLOR_KEY or is_trans_key(v):
                continue
            if 0 <= xx + i < cell_w:
                px[xx + i, yy] = _rgba(v)
    if img.size != (cell_w, cell_h):
        img = img.resize((cell_w, cell_h), Image.Resampling.NEAREST)
    import numpy as np
    a = np.array(img.convert("RGBA"))
    r, g, b, al = a[:, :, 0], a[:, :, 1], a[:, :, 2], a[:, :, 3]
    pure = (r < 16) & (g < 16) & (b > 160) & (al > 0)
    a[pure, 3] = 0
    # 1px dilate opaque region to close iso tessellation hairline gaps
    op = a[:, :, 3] > 128
    dil = op.copy()
    dil[1:, :] |= op[:-1, :]
    dil[:-1, :] |= op[1:, :]
    dil[:, 1:] |= op[:, :-1]
    dil[:, :-1] |= op[:, 1:]
    # fill newly opaque from nearest neighbor
    newpx = dil & ~op
    if newpx.any():
        # copy color from a shifted neighbor that was opaque
        filled = a.copy()
        for dy, dx in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            src = np.roll(np.roll(a, dy, axis=0), dx, axis=1)
            src_op = np.roll(np.roll(op, dy, axis=0), dx, axis=1)
            take = newpx & src_op & (filled[:, :, 3] == 0)
            filled[take] = src[take]
        a = filled
    return Image.fromarray(a)


def decode_lep_generic(blob: bytes) -> Optional["Image.Image"]:
    """Fallback: row TOC xn + best yxn stream (sprites / odd tiles)."""
    if Image is None:
        raise RuntimeError("Pillow required")
    if not blob.startswith(LEP_MAGIC) or len(blob) < 64:
        return None
    hdr = parse_lep_header(blob) if len(blob) >= 128 else None
    if hdr is None:
        return None
    w = hdr["width"]
    hf = hdr["height_field"]
    nslots = hdr["nslots"]
    first = hdr["first_off"]
    if w == 0:
        ww = hf if hf else 1
        col = struct.unpack_from("<H", blob, min(0xB0, len(blob) - 2))[0] if len(blob) > 0xB0 else COLOR_KEY
        return Image.new("RGBA", (ww, 1), _rgba(col))
    if nslots <= 0:
        return None
    slots = [struct.unpack_from("<I", blob, 48 + i * 4)[0] for i in range(nslots)]
    best: List[Tuple[int, int, List[int]]] = []
    for s in range(first, min(len(blob) - 6, first + 500)):
        stream, _ = _parse_yxn(blob, s, len(blob), w, 512)
        if len(stream) > len(best):
            best = stream
    for yi in range(nslots):
        start = slots[yi]
        end = slots[yi + 1] if yi + 1 < nslots else len(blob)
        if end - start > 6:
            stream, _ = _parse_yxn(blob, start, end, w, 512)
            if len(stream) > len(best):
                best = stream
    H = max(hf or 1, nslots, (max(y for y, _, _ in best) + 1 if best else 1))
    spans: List[Tuple[int, int, List[int]]] = []
    for yi in range(nslots):
        start = slots[yi]
        end = slots[yi + 1] if yi + 1 < nslots else len(blob)
        if end - start <= 2:
            continue
        for x, pix in _parse_xn(blob, start, end, w):
            spans.append((yi, x, pix))
    spans.extend(best)
    if not spans:
        return None
    return _paint(spans, w, H)



def _is_sprite_ctrl_blue(v: int) -> bool:
    """Pure-blue u16s used as xn/npix headers inside ResPlayer rows."""
    if v in (COLOR_KEY, 0, 0xFFFF):
        return False
    r = (v >> 11) & 0x1F
    g = (v >> 5) & 0x3F
    b = v & 0x1F
    return r == 0 and g == 0 and 1 <= b <= 0x38


def _sprite_rgba_exact(v: int) -> Tuple[int, int, int, int]:
    if v in (COLOR_KEY, 0, 0xFFFF):
        return (0, 0, 0, 0)
    r = (v >> 11) & 0x1F
    g = (v >> 5) & 0x3F
    b = v & 0x1F
    return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2), 255)


def _parse_sprite_row(pix: List[int]) -> List[Tuple[Optional[int], List[int]]]:
    """Prefer trailing exact (x,nbytes)/(npix,x); else whole row as left-aligned raw."""
    n = len(pix)
    for i in range(n - 1):
        a, b = pix[i], pix[i + 1]
        rem = n - (i + 2)
        if rem < 2:
            continue
        x = sp = None
        if a < 48 and b % 2 == 0 and 2 <= b <= 160 and b // 2 == rem and a <= i + 2:
            x, sp = a, pix[i + 2 :]
        elif 2 <= a <= 100 and b < 48 and a == rem and b <= i + 2:
            x, sp = b, pix[i + 2 :]
        if x is None:
            continue
        solid = sum(1 for v in sp if v not in (COLOR_KEY, 0, 0xFFFF) and not _is_sprite_ctrl_blue(v) and v >= 0x40)
        if solid < max(1, len(sp) // 4):
            continue
        out: List[Tuple[Optional[int], List[int]]] = []
        if i:
            out.append((None, pix[:i]))
        out.append((x, sp))
        return out
    return [(None, pix)]


def decode_lep_sprite(blob: bytes) -> Optional["Image.Image"]:
    """ResPlayer nested lep → character frame.

    Phase 6 fixes vs earlier hybrid decoder:
    - Skip slots that land inside the secondary TOC (not pixel rows)
    - Primary + tip as left-aligned raw RGB565; trailing exact xn when present
    - Drop oversized tip footer
    - Pure-blue control nibbles are inpainted from horizontal neighbors (not left
      as transparent holes — that was the Venetian-blind striping)
    """
    if Image is None:
        raise RuntimeError("Pillow required")
    if not blob.startswith(LEP_MAGIC) or len(blob) < 128:
        return None
    hdr = parse_lep_header(blob)
    nslots, first = hdr["nslots"], hdr["first_off"]
    if nslots <= 0:
        return None
    slots = [struct.unpack_from("<I", blob, 48 + i * 4)[0] for i in range(nslots)]
    sec, sec_end = _get_sec_table(blob, first)
    end = sec[0] if sec else len(blob)

    row_spans: List[List[Tuple[Optional[int], List[int]]]] = []
    for yi in range(nslots):
        s = slots[yi]
        e = slots[yi + 1] if yi + 1 < nslots else end
        if s < sec_end:
            s = sec_end
        if e <= s:
            continue
        chunk = blob[s:e]
        if len(chunk) % 2:
            chunk = chunk[:-1]
        if len(chunk) < 2:
            continue
        pix = list(struct.unpack_from(f"<{len(chunk) // 2}H", chunk, 0))
        spans = _parse_sprite_row(pix)
        if any(v not in (COLOR_KEY, 0, 0xFFFF) for _, p in spans for v in p):
            row_spans.append(spans)

    tip_rows: List[List[int]] = []
    if sec:
        for i, o in enumerate(sec):
            e = sec[i + 1] if i + 1 < len(sec) else len(blob)
            chunk = blob[o:e]
            if len(chunk) % 2:
                chunk = chunk[:-1]
            if len(chunk) < 4:
                continue
            tip_rows.append(list(struct.unpack_from(f"<{len(chunk) // 2}H", chunk, 0)))
        if len(tip_rows) >= 2 and len(tip_rows[-1]) > len(tip_rows[-2]) + 4:
            tip_rows = tip_rows[:-1]
        for pix in tip_rows:
            spans = _parse_sprite_row(pix)
            if sum(1 for _, p in spans for v in p if v not in (COLOR_KEY, 0, 0xFFFF)) >= 3:
                row_spans.append(spans)

    if not row_spans:
        return None
    maxw = 1
    for spans in row_spans:
        for x, pix in spans:
            maxw = max(maxw, len(pix) if x is None else x + len(pix))
    H = len(row_spans)
    W = maxw
    # RGBA buffer + control mask for inpaint
    buf = bytearray(W * H * 4)
    ctrl = [False] * (W * H)

    def put(x: int, y: int, rgba: Tuple[int, int, int, int]) -> None:
        if not (0 <= x < W and 0 <= y < H):
            return
        i = (y * W + x) * 4
        buf[i : i + 4] = bytes(rgba)

    for y, spans in enumerate(row_spans):
        for x, pix in spans:
            x0 = 0 if x is None else x
            for j, v in enumerate(pix):
                xx = x0 + j
                if not (0 <= xx < W):
                    continue
                if v in (COLOR_KEY, 0, 0xFFFF):
                    continue
                if _is_sprite_ctrl_blue(v):
                    ctrl[y * W + xx] = True
                    continue
                put(xx, y, _sprite_rgba_exact(v))

    # Horizontal inpaint of control cells
    for y in range(H):
        for x in range(W):
            idx = y * W + x
            if not ctrl[idx]:
                continue
            left = right = None
            for lx in range(x - 1, -1, -1):
                li = (y * W + lx) * 4
                if buf[li + 3] and not ctrl[y * W + lx]:
                    left = buf[li : li + 4]
                    break
            for rx in range(x + 1, W):
                ri = (y * W + rx) * 4
                if buf[ri + 3] and not ctrl[y * W + rx]:
                    right = buf[ri : ri + 4]
                    break
            if left and right:
                put(x, y, tuple((left[k] + right[k]) // 2 for k in range(4)))  # type: ignore
            elif left:
                put(x, y, tuple(left))  # type: ignore
            elif right:
                put(x, y, tuple(right))  # type: ignore

    img = Image.frombytes("RGBA", (W, H), bytes(buf))
    bbox = img.split()[-1].getbbox()
    return img.crop(bbox) if bbox else img




def _find_building_ctrl_triples(pix: List[int]) -> List[Tuple[int, int, int, int]]:
    """Detect embedded (a, b, c) control triples that paint as blue vertical seams.

    Pattern seen across res00 building rows: a < 0x40, b in 0x100..0x1FF (near-blue
    RGB565), c < 0x80. When left as pixels these form a 1–3px vertical blue column.
    """
    out: List[Tuple[int, int, int, int]] = []
    i = 0
    n = len(pix)
    while i < n - 2:
        a, b, c = pix[i], pix[i + 1], pix[i + 2]
        if a < 0x40 and 0x100 <= b < 0x200 and c < 0x80:
            out.append((i, a, b, c))
            i += 3
        else:
            i += 1
    return out


def _is_building_ctrl(v: int) -> bool:
    """Control / chroma words inside building rows.

    Keep this tight: dark stone shadows are often low-R RGB565 and must not be
    dropped. Only pure-blue markers + tiny command words are treated as control.
    """
    if v in (COLOR_KEY, 0, 0xFFFF):
        return True
    if v < 0x40:
        return True
    r = (v >> 11) & 0x1F
    g = (v >> 5) & 0x3F
    b = v & 0x1F
    # pure blue control nibbles (same family as sprite ctrl-blue)
    if r == 0 and g == 0 and 1 <= b <= 0x38:
        return True
    # 0x01xx near-blue markers used inside control triples / seams
    if 0x100 <= v < 0x200 and r == 0 and g <= 2:
        return True
    return False


def decode_lep_building(blob: bytes) -> Optional["Image.Image"]:
    """res00 / leyibld building & prop leps.

    Same row-TOC layout as decode_lep_sprite, but:
    - Strip embedded control triples that become vertical blue seams
    - Drop remaining ctrl/near-blue words as transparent (no horizontal inpaint —
      inpaint was pulling neighbor colors into the seam and looking like smear)
    - Still append tip-bank rows when present
    """
    if Image is None:
        raise RuntimeError("Pillow required")
    if not blob.startswith(LEP_MAGIC) or len(blob) < 128:
        return None
    hdr = parse_lep_header(blob)
    nslots, first = hdr["nslots"], hdr["first_off"]
    if nslots <= 0:
        return None
    slots = [struct.unpack_from("<I", blob, 48 + i * 4)[0] for i in range(nslots)]
    sec, sec_end = _get_sec_table(blob, first)
    end = sec[0] if sec else len(blob)

    def row_spans_from_chunk(chunk: bytes) -> List[Tuple[Optional[int], List[int]]]:
        if len(chunk) % 2:
            chunk = chunk[:-1]
        if len(chunk) < 2:
            return []
        pix = list(struct.unpack_from(f"<{len(chunk) // 2}H", chunk, 0))
        skip = set()
        for ti, _a, _b, _c in _find_building_ctrl_triples(pix):
            skip.update((ti, ti + 1, ti + 2))
        if skip:
            pix = [v for i, v in enumerate(pix) if i not in skip]
        if not pix:
            return []
        return _parse_sprite_row(pix)

    row_spans: List[List[Tuple[Optional[int], List[int]]]] = []
    for yi in range(nslots):
        s = slots[yi]
        e = slots[yi + 1] if yi + 1 < nslots else end
        if s < sec_end:
            s = sec_end
        if e <= s:
            continue
        spans = row_spans_from_chunk(blob[s:e])
        if any(not _is_building_ctrl(v) for _, p in spans for v in p):
            row_spans.append(spans)

    if sec:
        for i, o in enumerate(sec):
            e = sec[i + 1] if i + 1 < len(sec) else len(blob)
            spans = row_spans_from_chunk(blob[o:e])
            if sum(1 for _, p in spans for v in p if not _is_building_ctrl(v)) >= 3:
                row_spans.append(spans)

    if not row_spans:
        return None
    maxw = 1
    for spans in row_spans:
        for x, pix in spans:
            maxw = max(maxw, len(pix) if x is None else x + len(pix))
    H = len(row_spans)
    W = maxw
    buf = bytearray(W * H * 4)

    def put(x: int, y: int, rgba: Tuple[int, int, int, int]) -> None:
        if not (0 <= x < W and 0 <= y < H):
            return
        i = (y * W + x) * 4
        buf[i : i + 4] = bytes(rgba)

    for y, spans in enumerate(row_spans):
        for x, pix in spans:
            x0 = 0 if x is None else x
            for j, v in enumerate(pix):
                xx = x0 + j
                if not (0 <= xx < W):
                    continue
                if _is_building_ctrl(v):
                    continue
                put(xx, y, _sprite_rgba_exact(v))

    img = Image.frombytes("RGBA", (W, H), bytes(buf))
    # Final scrub of residual near-primary blue
    try:
        import numpy as np

        a = np.array(img)
        r, g, b, al = a[:, :, 0], a[:, :, 1], a[:, :, 2], a[:, :, 3]
        pure = (r < 25) & (g < 50) & (b > 130) & (al > 0)
        a[:, :, 3] = np.where(pure, 0, al)
        img = Image.fromarray(a)
    except Exception:
        pass
    bbox = img.split()[-1].getbbox()
    return img.crop(bbox) if bbox else img


def decode_lep_png(blob: bytes) -> Optional["Image.Image"]:
    """Decode lep → RGBA. Prefers full iso diamond for map tiles."""
    img = decode_lep_diamond(blob)
    if img is not None and img.size[0] >= 24 and img.size[1] >= 16:
        return img
    return decode_lep_generic(blob)


def find_nested_leps(blob: bytes) -> List[Tuple[int, bytes]]:
    out = []
    pos = 0
    while True:
        i = blob.find(LEP_MAGIC, pos)
        if i < 0:
            break
        j = blob.find(LEP_MAGIC, i + 4)
        chunk = blob[i : j if j > 0 else len(blob)]
        out.append((i, chunk))
        pos = i + 4
    return out


def cmd_list(args: argparse.Namespace) -> None:
    lib = LeyiLib.open(Path(args.lib))
    rows = []
    for i, off, size, blob in lib.iter_entries():
        kind = classify(blob)
        rec = {"index": i, "offset": off, "size": size, "kind": kind}
        if kind == "lep" and size >= 128:
            try:
                rec.update(parse_lep_header(blob))
            except Exception as e:  # noqa: BLE001
                rec["lep_error"] = str(e)
        rows.append(rec)
    if args.json:
        print(json.dumps({"path": str(lib.path), "count": lib.count, "entries": rows}, indent=2))
    else:
        print(f"{lib.path}: {lib.count} entries")
        for r in rows[: args.limit]:
            extra = ""
            if r["kind"] == "lep":
                extra = f" w={r.get('width')} hf={r.get('height_field')} slots={r.get('nslots')}"
            print(f"  [{r['index']:5d}] off=0x{r['offset']:08x} size={r['size']:8d} {r['kind']}{extra}")


def cmd_extract(args: argparse.Namespace) -> None:
    lib = LeyiLib.open(Path(args.lib))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    indices = range(lib.count) if args.all else [int(x) for x in args.index]
    manifest = []
    for i in indices:
        blob = lib.entry_bytes(i)
        kind = classify(blob)
        raw_path = out / f"{i:05d}_{kind.split(':')[0]}.bin"
        raw_path.write_bytes(blob)
        item = {"index": i, "kind": kind, "raw": str(raw_path), "size": len(blob)}
        if args.png and Image is not None:
            if kind == "lep":
                img = decode_lep_png(blob)
                if img is not None:
                    png = out / f"{i:05d}_lep.png"
                    img.save(png)
                    item["png"] = str(png)
                    item["png_size"] = list(img.size)
            elif args.nested:
                for ni, lep in find_nested_leps(blob):
                    img = decode_lep_sprite(lep) or decode_lep_png(lep)
                    if img is None:
                        continue
                    png = out / f"{i:05d}_nest{ni:04d}.png"
                    img.save(png)
                    item.setdefault("nested_pngs", []).append(str(png))
        manifest.append(item)
        print(f"wrote {raw_path}")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p_list = sp.add_parser("list")
    p_list.add_argument("lib")
    p_list.add_argument("--json", action="store_true")
    p_list.add_argument("--limit", type=int, default=40)
    p_list.set_defaults(func=cmd_list)
    p_ex = sp.add_parser("extract")
    p_ex.add_argument("lib")
    p_ex.add_argument("-o", "--out", required=True)
    p_ex.add_argument("--index", nargs="*", default=[])
    p_ex.add_argument("--all", action="store_true")
    p_ex.add_argument("--png", action="store_true")
    p_ex.add_argument("--nested", action="store_true", help="Also decode nested lep in bin entries")
    p_ex.set_defaults(func=cmd_extract)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
