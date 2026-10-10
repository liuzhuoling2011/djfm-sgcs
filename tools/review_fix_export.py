#!/usr/bin/env python3
"""Review fix: correct MAP 10-byte grid + lep TOC decoder; rebuild ground/atlases."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from leyilib import LeyiLib, decode_lep_diamond
from phase10_export_scene import parse_map_grid, export_map_tiles, black_to_alpha
from phase10_run_export import compose_iso_ground
from phase11_run_export import build_chunk_atlases
from PIL import Image

ROOT = Path("/workspace/djfm-sgcs")
ZY = ROOT / "extract/Blade And Sword 2 Ancient Legend/zy"
EXT = ROOT / "assets/samples/phase9/fol_extract"
WEB = ROOT / "web/public/game/map"
REV = ROOT / "assets/samples/review"
REV.mkdir(parents=True, exist_ok=True)

def main():
    meta = json.loads((WEB / "meta.json").read_text())
    mapren = LeyiLib.open(ZY / "map_ren.lib")
    mw, mh, full_grid, rest = parse_map_grid(EXT / "cj/1-0s.MAP")
    filled = sum(1 for row in full_grid for v in row if v != 0xFFFF)
    print(f"MAP {mw}x{mh} filled={filled} rec_off={getattr(parse_map_grid,'last_rec_off',None)}")

    # BEFORE snapshot already saved; compose AFTER
    print("compose ground_full @0.5 …")
    ground, gorigin, ok, miss, nuc = compose_iso_ground(full_grid, mapren, scale=0.5)
    ground.save(WEB / "ground_full.png", optimize=True)
    ground.save(REV / "ground_after_full.png", optimize=True)
    meta["ground_full"] = dict(
        file="ground_full.png", **gorigin, pixel_size=list(ground.size), decode_ok=ok, miss=miss
    )
    print(f"  ground ok={ok} miss={miss} size={ground.size} origin={gorigin}")

    ox, oy = meta.get("chunk_origin") or [15, 19]
    cw, ch = meta.get("chunk_size") or [96, 80]
    # clamp origin into filled diamond roughly
    print(f"viewport tiles origin=({ox},{oy}) size={cw}x{ch}")
    tile_meta = export_map_tiles(full_grid, mapren, WEB, origin=(ox, oy), size=(cw, ch))
    meta.update(tile_meta)
    meta["tile_pixel"] = [64, 32]
    meta["phase"] = "review-map-fix"
    meta["iso"] = {"mode": "diamond", "step": [32, 16], "tile": [64, 32]}
    meta["findings"] = dict(
        meta.get("findings") or {},
        review_map_fix=(
            "Root cause: parse_map_grid read the u16 remap table (identity 1..N) "
            "instead of the EOF w*h*10 cell records. ComeOn fread size 0xA per cell: "
            "u16 ground, u16 overlay, u8 flag, u8, u16 height, u16 pad. "
            "Projection remains diamond iso (x-y)*32,(x+y)*16; occupancy is diamond-shaped. "
            "lep tiles decode via TOC row spans → 64x32."
        ),
    )
    (WEB / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"  tiles unique={tile_meta['unique_tiles']} ok={tile_meta['decode_ok']} fill={tile_meta['fill_rate']}")

    print("rebuild atlases…")
    build_chunk_atlases(meta, chunk=16)

    # crops for review
    gf = Image.open(WEB / "ground_full.png")
    gm = meta["ground_full"]
    sw, sh = meta.get("spawn_world") or [63, 59]
    tw, th = gm["tile_w"], gm["tile_h"]
    gx = int((sw - sh) * (tw / 2) - gm["min_sx"])
    gy = int((sw + sh) * (th / 2) - gm["min_sy"])
    gf.crop((gx - 280, gy - 200, gx + 280, gy + 200)).save(REV / "ground_after.png")
    # also save a town overview
    gf.resize((gf.size[0]//2, gf.size[1]//2), Image.LANCZOS).save(REV / "ground_after_overview.png")
    print("done", REV)

if __name__ == "__main__":
    main()
