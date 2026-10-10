"""Phase 17: minimap image = ground_full + all BLD parts, at quarter world pitch (16x8 per cell)."""
import json, sys
from pathlib import Path
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
W = Path('/workspace/djfm-sgcs/web/public/game')
for d in [W / 'map'] + [p for p in (W / 'maps').iterdir() if (p / 'meta.json').exists() and (p / 'ground_full.png').exists()]:
    m = json.loads((d / 'meta.json').read_text()); g = m['ground_full']
    G = Image.open(d / g['file']).convert('RGBA'); s = g['tile_w'] / 64  # ground pitch vs full pitch (0.5)
    for b in sorted(m.get('buildings', []), key=lambda b: b['x'] + b['y']):
        for q in b.get('parts', []):
            try: im = Image.open(d / 'props' / q['file']).convert('RGBA')
            except Exception: continue
            im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
            x = int(((b['x'] - b['y']) * 32 + q['ox']) * s - g['min_sx']); y = int(((b['x'] + b['y']) * 16 + q['oy']) * s - g['min_sy'])
            G.alpha_composite(im, (x, y)) if 0 <= x and 0 <= y and x + im.width <= G.width and y + im.height <= G.height else G.paste(im, (x, y), im)
    M = G.resize((G.width // 2, G.height // 2), Image.BILINEAR); M.save(d / 'minimap.png', optimize=True)
    m['minimap'] = dict(file='minimap.png', scale=0.5, note='ground_full px × 0.5, buildings composited (Phase 17)')
    (d / 'meta.json').write_text(json.dumps(m, ensure_ascii=False)); print(d.name, M.size)
