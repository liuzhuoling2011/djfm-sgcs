#!/usr/bin/env python3
"""Phase 10 runner: props + full-map composed ground + large tile viewport."""
from __future__ import annotations
import json, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase10_export_scene import (
    ROOT, ZY, EXT, OUT, WEB, PROPS,
    parse_bld, parse_bnt, parse_ont, parse_role_graph, parse_map_grid,
    decode_sprite, nested_first_frame, black_to_alpha, export_map_tiles,
)
from leyilib import LeyiLib, decode_lep_diamond
from PIL import Image
import numpy as np

def compose_iso_ground(grid, map_lib, tile_w=64, tile_h=32, scale=1.0):
    mh, mw = len(grid), len(grid[0])
    tw, th = int(tile_w*scale), int(tile_h*scale)
    # iso bounds
    # screen x = (x-y)*(tw/2); y = (x+y)*(th/2)
    # x range: -(mh-1)*tw/2 .. (mw-1)*tw/2
    pad = max(tw, th)
    min_sx = int(-(mh) * (tw/2)) - pad
    max_sx = int((mw) * (tw/2)) + pad
    min_sy = -pad
    max_sy = int((mw+mh) * (th/2)) + pad
    W = max_sx - min_sx
    H = max_sy - min_sy
    print(f"  compose canvas {W}x{H} scale={scale} cells={mw}x{mh}")
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cache = {}
    ok = miss = 0
    for y in range(mh):
        if y % 16 == 0:
            print(f"  row {y}/{mh} ok={ok} miss={miss}")
        for x in range(mw):
            tid = grid[y][x]
            if tid == 0xFFFF or tid >= map_lib.count:
                miss += 1
                continue
            if tid not in cache:
                blob = map_lib.entry_bytes(tid)
                img = None
                try:
                    img = decode_lep_diamond(blob)
                except Exception:
                    img = None
                if img is None:
                    img = decode_sprite(blob)
                if img is not None:
                    img = black_to_alpha(img)
                    if scale != 1.0:
                        img = img.resize((tw, th), Image.Resampling.NEAREST)
                    elif img.size != (tw, th):
                        # keep native; blit centered on diamond footprint
                        pass
                cache[tid] = img
            img = cache[tid]
            if img is None:
                miss += 1
                continue
            ok += 1
            sx = int((x - y) * (tw / 2) - min_sx - img.size[0] / 2)
            sy = int((x + y) * (th / 2) - min_sy - img.size[1] / 2)
            canvas.alpha_composite(img, (sx, sy))
    origin = dict(min_sx=min_sx, min_sy=min_sy, tile_w=tw, tile_h=th, scale=scale)
    return canvas, origin, ok, miss, len(cache)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PROPS.mkdir(parents=True, exist_ok=True)

    bld = parse_bld(EXT / "mb/BLD_Ren.Mdl")
    placements = parse_bnt(EXT / "cj/1-0s.BNT", bld)
    bld_place = [p for p in placements if p.get("kind") == "bld" and p.get("fid")]
    ont = parse_ont(EXT / "cj/1-0s.ONT")
    role_graph = parse_role_graph(EXT / "mb/Role.txt")
    print(f"bld={len(bld)} place={len(bld_place)} ont={len(ont)} roles={len(role_graph)}")

    res00 = LeyiLib.open(ZY / "res00.Lib")
    resnpc3 = LeyiLib.open(ZY / "ResNpc3.lib")
    resnpc2 = LeyiLib.open(ZY / "ResNpc2.lib")
    mapren = LeyiLib.open(ZY / "map_ren.lib")

    fid_ok = {}
    for fid in sorted({p["fid"] for p in bld_place}):
        if fid >= res00.count: continue
        img = decode_sprite(res00.entry_bytes(fid))
        if not img: continue
        name = f"bld_{fid}.png"
        img.save(PROPS / name); img.save(OUT / name)
        fid_ok[fid] = dict(file=name, w=img.size[0], h=img.size[1])
    print(f"building sprites: {len(fid_ok)}")

    npc_ok = {}
    for o in ont:
        mid = o.get("ModelID")
        if mid is None: continue
        gid = role_graph.get(int(mid), int(mid))
        if gid in npc_ok: continue
        img = None
        for L in (resnpc3, resnpc2):
            if gid < L.count:
                img = nested_first_frame(L.entry_bytes(gid))
                if img: break
        if img is None and gid < res00.count:
            img = decode_sprite(res00.entry_bytes(gid))
        if not img: continue
        name = f"npc_{gid}.png"
        img.save(PROPS / name); img.save(OUT / name)
        npc_ok[gid] = dict(file=name, w=img.size[0], h=img.size[1], model=mid)
    print(f"npc sprites: {len(npc_ok)}")

    mw, mh, grid, rest = parse_map_grid(EXT / "cj/1-0s.MAP")
    # fix grid offset: skip u32 after \x12HR*
    data = (EXT / "cj/1-0s.MAP").read_bytes()
    marker = data.find(b"\x12HR")
    grid_off = marker + 8  # * + u32
    need = mw * mh * 2
    grid = []
    for y in range(mh):
        row = []
        for x in range(mw):
            row.append(struct.unpack_from("<H", data, grid_off + (y * mw + x) * 2)[0])
        grid.append(row)
    rest = data[grid_off + need :]
    print(f"MAP {mw}x{mh} rest={len(rest)}")

    # Large tile viewport covering town + props (full 128 if feasible via compose)
    # 1) Tile chunk 96x80 around spawn for interactive tile layer fallback
    spawn = (63, 59)
    vw, vh = 96, 80
    ox = max(0, min(mw - vw, spawn[0] - vw // 2))
    oy = max(0, min(mh - vh, spawn[1] - vh // 2))
    print(f"tile viewport origin=({ox},{oy}) size={vw}x{vh}")
    meta_tiles = export_map_tiles(grid, mapren, WEB, origin=(ox, oy), size=(vw, vh))
    print(f"tiles unique={meta_tiles['unique_tiles']} fill={meta_tiles['fill_rate']}")

    # 2) Full-map composed ground at 0.5 scale for overview/streaming base
    print("composing full ground...")
    ground, gorigin, ok, miss, nuc = compose_iso_ground(grid, mapren, scale=0.5)
    ground_path = WEB / "ground_full.png"
    ground.save(ground_path, optimize=True)
    ground.save(OUT / "ground_full.png", optimize=True)
    print(f"ground {ground.size} ok={ok} miss={miss} unique={nuc} -> {ground_path}")

    buildings_out = []
    for p in bld_place:
        fid = p["fid"]
        if fid not in fid_ok: continue
        buildings_out.append(dict(
            x=p["x"], y=p["y"], bid=p["bid"], name=p["name"], fid=fid,
            file=fid_ok[fid]["file"], sw=fid_ok[fid]["w"], sh=fid_ok[fid]["h"],
            ox=p.get("ox", 0), oy=p.get("oy", 0),
        ))
    npcs_out = []
    for o in ont:
        mid = o.get("ModelID")
        if mid is None: continue
        gid = role_graph.get(int(mid), int(mid))
        if gid not in npc_ok: continue
        npcs_out.append(dict(
            x=o.get("MapX", 0), y=o.get("MapY", 0), ModelID=mid, Type=o.get("Type"),
            EventID=o.get("EventID"), graph=gid, file=npc_ok[gid]["file"],
            sw=npc_ok[gid]["w"], sh=npc_ok[gid]["h"],
            Logic=o.get("Logic"), MoveLevel=o.get("MoveLevel"),
            # local to tile viewport
            lx=o.get("MapX", 0) - ox, ly=o.get("MapY", 0) - oy,
        ))

    blocked = []
    for y in range(oy, oy + meta_tiles["chunk_size"][1]):
        for x in range(ox, ox + meta_tiles["chunk_size"][0]):
            if grid[y][x] == 0xFFFF or grid[y][x] >= mapren.count:
                blocked.append([x - ox, y - oy])
    logic_boxes = []
    for o in ont:
        if "Logic_x" in o and "Logic_cx" in o:
            logic_boxes.append(dict(
                x=o["Logic_x"], y=o["Logic_y"], cx=o["Logic_cx"], cy=o["Logic_cy"],
                model=o.get("ModelID"), event=o.get("EventID"),
            ))
            if o.get("Logic") == 1:
                for ly in range(o["Logic_y"], o["Logic_y"] + o["Logic_cy"]):
                    for lx in range(o["Logic_x"], o["Logic_x"] + o["Logic_cx"]):
                        if ox <= lx < ox + meta_tiles["chunk_size"][0] and oy <= ly < oy + meta_tiles["chunk_size"][1]:
                            blocked.append([lx - ox, ly - oy])
    blocked = [list(p) for p in sorted({(a, b) for a, b in blocked})]

    triggers = [p for p in placements if p.get("kind") == "trigger"]

    meta = dict(
        source="cj/1-0s.MAP + Map_Ren.lib + BLD_Ren.Mdl + BNT/ONT (Phase 10)",
        scene="1-0s", scene_id=0, scene_name="瓦当镇", pack_id="ren",
        spawn=[spawn[0] - ox, spawn[1] - oy],
        spawn_world=list(spawn),
        world_dims=[mw, mh],
        objects=npcs_out,
        buildings=buildings_out,
        npcs=npcs_out,
        triggers=[{"x": t["x"], "y": t["y"], "bid": t["bid"], "script": t.get("script", "")[:60]} for t in triggers],
        blocked_sample=blocked[:8000],
        blocked_count=len(blocked),
        logic_boxes=logic_boxes,
        ground_full=dict(file="ground_full.png", **gorigin, pixel_size=list(ground.size), decode_ok=ok, miss=miss),
        aux_planes="plane2 after u16 grid: mostly 0xFFFF/0xCDCD — height channel unclear",
        iso={"tileW": 64, "tileH": 32},
        findings={
            "fol": "CRACKED",
            "bld": "leyibld1.50 fid → res00.Lib lep",
            "ont": "ModelID=Role角色ID → 图形ID → ResNpc3",
            "collision": "MAP holes + Logic_* boxes (Logic=1)",
            "viewport": f"{vw}x{vh} tiles + full ground compose @0.5",
        },
        **meta_tiles,
    )
    (WEB / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    (OUT / "scene_1-0s_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (PROPS / "index.json").write_text(json.dumps(dict(buildings=buildings_out, npcs=npcs_out, fids=fid_ok, graphs=npc_ok), ensure_ascii=False, indent=2), encoding="utf-8")

    idx_path = ROOT / "web/public/game/maps/index.json"
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    idx["begin_scn_mapping"] = (
        "Phase10: BeginScn=0 → 1-0s 瓦当镇; BNT buildings (res00) + ONT NPCs (ResNpc3); "
        f"viewport {vw}×{vh} + ground_full; ActMdl spawn (63,59); Logic_* collision."
    )
    idx_path.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DONE buildings={len(buildings_out)} npcs={len(npcs_out)} blocked={len(blocked)}")

if __name__ == "__main__":
    main()
