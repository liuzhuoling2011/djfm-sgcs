#!/usr/bin/env python3
"""Clean lep decoder (review): H row offsets at 0x30 (relative to 0x30);
each row = repeated (u16 skip_bytes, u16 n_bytes, n_bytes of RGB565) until row filled."""
import struct
import numpy as np
from PIL import Image

def lep_dims(b):
    h = struct.unpack_from('<I', b, 0x10)[0] >> 8
    return h

def decode(b, key=(0xF81F,)):
    if not b.startswith(b'lep\0'):
        return None
    t0 = struct.unpack_from('<I', b, 0x30)[0]
    H = t0 // 4
    if H <= 0 or H > 4096 or t0 % 4:
        return None
    toc = struct.unpack_from('<%dI' % H, b, 0x30)
    rows = []
    W = 0
    for r in range(H):
        p = 0x30 + toc[r]
        end = 0x30 + toc[r + 1] if r + 1 < H else len(b)
        pos = 0
        spans = []
        while p + 2 <= end:
            skip = struct.unpack_from('<H', b, p)[0]; p += 2
            pos += skip
            if p + 2 > end:
                break
            n = struct.unpack_from('<H', b, p)[0]; p += 2
            if n == 0 or p + n > end:
                break
            spans.append((pos // 2, struct.unpack_from('<%dH' % (n // 2), b, p)))
            p += n; pos += n
        W = max(W, pos // 2)
        rows.append(spans)
    a = np.zeros((H, max(W, 1), 4), np.uint8)
    for y, spans in enumerate(rows):
        for x, pix in spans:
            v = np.array(pix, np.uint32)
            r = (v >> 11) & 31; g = (v >> 5) & 63; bb = v & 31
            seg = np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (bb << 3) | (bb >> 2), np.full_like(v, 255)], -1)
            seg[np.isin(v, key)] = 0
            a[y, x:x + len(pix)] = seg[:max(0, a.shape[1] - x)]
    return a
