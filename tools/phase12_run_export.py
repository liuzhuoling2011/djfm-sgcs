#!/usr/bin/env python3
"""Phase 12: fix map diamond decode, rebuild ground+tiles+atlases, NPC pass."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from leyilib import LeyiLib, decode_lep_diamond, decode_lep_sprite, decode_lep_building, find_nested_leps
from phase10_run_export import compose_iso_ground
from phase10_export_scene import (
    black_to_alpha, parse_role_graph, parse_map_grid, export_map_tiles,
)
from phase11_scrub import scrub_sprite_fringe, pick_nested_best
from phase11_run_export import build_chunk_atlases
from PIL import Image

ROOT = Path("/workspace/djfm-sgcs")
ZY = ROOT / "extract/Blade And Sword 2 Ancient Legend/zy"
EXT = ROOT / "assets/samples/phase9/fol_extract"
WEB = ROOT / "web/public/game/map"
OUT = ROOT / "assets/samples/phase12"
OUT.mkdir(parents=True, exist_ok=True)


def rebuild_ground_and_tiles():
    meta = json.loads((WEB / "meta.json").read_text())
    mapren = LeyiLib.open(ZY / "map_ren.lib")
    mw, mh, full_grid, _rest = parse_map_grid(EXT / "cj/1-0s.MAP")
    print(f"MAP {mw}x{mh}")

    print("compose ground_full @0.5 …")
    ground, gorigin, ok, miss, nuc = compose_iso_ground(full_grid, mapren, scale=0.5)
    ground.save(WEB / "ground_full.png", optimize=True)
    ground.save(OUT / "ground_full.png", optimize=True)
    meta["ground_full"] = dict(
        file="ground_full.png", **gorigin, pixel_size=list(ground.size), decode_ok=ok, miss=miss
    )
    print(f"  ground ok={ok} miss={miss} size={ground.size}")

    ox, oy = meta.get("chunk_origin") or [15, 19]
    cw, ch = meta.get("chunk_size") or [96, 80]
    print(f"re-export viewport tiles origin=({ox},{oy}) size={cw}x{ch} …")
    tile_meta = export_map_tiles(full_grid, mapren, WEB, origin=(ox, oy), size=(cw, ch))
    meta.update(tile_meta)
    meta["phase"] = 12
    meta["findings"] = dict(
        meta.get("findings") or {},
        phase12="diamond width0→64 + row-center + blue scrub; no atlas+ground double-draw",
    )
    (WEB / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(
        f"  tiles unique={tile_meta['unique_tiles']} ok={tile_meta['decode_ok']} "
        f"fill={tile_meta['fill_rate']}"
    )

    print("rebuild atlases…")
    build_chunk_atlases(meta, chunk=16)
    # before snapshot: spawn crop
    gf = Image.open(WEB / "ground_full.png")
    gm = meta["ground_full"]
    sw, sh = meta.get("spawn_world") or [63, 59]
    tw, th = gm["tile_w"], gm["tile_h"]
    gx = int((sw - sh) * (tw / 2) - gm["min_sx"])
    gy = int((sw + sh) * (th / 2) - gm["min_sy"])
    gf.crop((gx - 220, gy - 160, gx + 220, gy + 160)).save(OUT / "ground_spawn_after.png")
    return meta


def improve_npcs():
    meta = json.loads((WEB / "meta.json").read_text())
    role = parse_role_graph(EXT / "mb/Role.txt")
    libs = []
    for name in ("ResNpc3.lib", "ResNpc2.lib", "ResNpc.lib", "ResPlayer2.lib", "ResPlayer.lib"):
        p = ZY / name
        if p.exists():
            libs.append((name, LeyiLib.open(p)))
    props = WEB / "props"
    # NPCs listed under meta["npcs"] or objects with file npc_*
    entries = list(meta.get("npcs") or [])
    if not entries:
        entries = [o for o in (meta.get("objects") or []) if (o.get("file") or "").startswith("npc_")]
    for npc in entries:
        rid = npc.get("ModelID")
        graph = npc.get("graph")
        if rid in role:
            graph = role[rid]
        if graph is None and npc.get("file"):
            # npc_627.png → 627
            try:
                graph = int(Path(npc["file"]).stem.split("_")[1])
            except Exception:
                continue
        if graph is None:
            continue
        best = None
        best_src = None
        for lname, lib in libs:
            if graph >= lib.count:
                continue
            blob = lib.entry_bytes(graph)
            img = pick_nested_best(blob, min_h=10, min_area=40)
            cands = []
            if img is not None:
                cands.append(img)
            for _off, lep in find_nested_leps(blob):
                for fn in (decode_lep_sprite, decode_lep_diamond):
                    try:
                        cand = fn(lep)
                    except Exception:
                        cand = None
                    if cand is not None:
                        cands.append(cand)
            for cand in cands:
                cand = scrub_sprite_fringe(black_to_alpha(cand))
                if cand.size[0] < 4 or cand.size[1] < 4:
                    continue
                if best is None or (cand.size[1], cand.size[0] * cand.size[1]) > (
                    best.size[1],
                    best.size[0] * best.size[1],
                ):
                    best, best_src = cand, lname
        if best is None:
            continue
        name = f"npc_{graph}.png"
        prev = props / name
        old = Image.open(prev).size if prev.exists() else (0, 0)
        best.save(props / name)
        best.save(OUT / name)
        print(f"  NPC {name}: {old} → {best.size} via {best_src}")


def main():
    print("=== Phase 12 export ===")
    # Save before ground crop if present
    prev = WEB / "ground_full.png"
    if prev.exists():
        Image.open(prev).save(OUT / "ground_full_before.png")
    rebuild_ground_and_tiles()
    print("NPC pass…")
    improve_npcs()
    print("done")


if __name__ == "__main__":
    main()
