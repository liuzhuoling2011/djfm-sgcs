#!/usr/bin/env python3
"""Phase 11: scrub props, fix NPCs, tile chunks/lazy meta, BGM+dialog+skill stubs."""
from __future__ import annotations
import json, struct, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from leyilib import LeyiLib, decode_lep_sprite, decode_lep_diamond
from phase10_export_scene import (
    ROOT, ZY, EXT, WEB, PROPS,
    parse_bld, parse_bnt, parse_ont, parse_role_graph, black_to_alpha,
)
from phase11_scrub import scrub_sprite_fringe, pick_nested_best, spr_first_large_res00, parse_bld_hotspot
from PIL import Image
import numpy as np

OUT = ROOT / "assets/samples/phase11"
OUT.mkdir(parents=True, exist_ok=True)


def decode_building(blob: bytes):
    img = None
    try:
        img = decode_lep_sprite(blob)
    except Exception:
        img = None
    if img is None:
        return None
    img = black_to_alpha(img)
    return scrub_sprite_fringe(img)


def export_props():
    bld = parse_bld(EXT / "mb/BLD_Ren.Mdl")
    # patch hotspots with improved parser
    raw = (EXT / "mb/BLD_Ren.Mdl").read_bytes()
    for rec in bld:
        body = rec["off"] + 34
        if body + 32 < len(raw):
            ox, oy, w, h = parse_bld_hotspot(raw, body)
            rec["ox"], rec["oy"], rec["w"], rec["h"] = ox, oy, w, h

    placements = parse_bnt(EXT / "cj/1-0s.BNT", bld)
    bld_place = [p for p in placements if p.get("kind") == "bld" and p.get("fid")]
    # refresh placement hotspots from bld
    for p in bld_place:
        info = bld[p["bid"]] if p["bid"] < len(bld) else {}
        p["ox"] = info.get("ox", 0)
        p["oy"] = info.get("oy", 0)

    ont = parse_ont(EXT / "cj/1-0s.ONT")
    role_graph = parse_role_graph(EXT / "mb/Role.txt")
    res00 = LeyiLib.open(ZY / "res00.Lib")
    resnpc3 = LeyiLib.open(ZY / "ResNpc3.lib")
    resnpc2 = LeyiLib.open(ZY / "ResNpc2.lib")
    spr = LeyiLib.open(ZY / "Spr.lib")

    PROPS.mkdir(parents=True, exist_ok=True)
    fid_ok = {}
    for fid in sorted({p["fid"] for p in bld_place if p.get("fid")}):
        if fid >= res00.count:
            continue
        img = decode_building(res00.entry_bytes(fid))
        if not img:
            continue
        name = f"bld_{fid}.png"
        img.save(PROPS / name)
        img.save(OUT / name)
        fid_ok[fid] = dict(file=name, w=img.size[0], h=img.size[1])
    print(f"buildings scrubbed: {len(fid_ok)}")

    npc_ok = {}
    for o in ont:
        mid = o.get("ModelID")
        if mid is None:
            continue
        gid = role_graph.get(int(mid), int(mid))
        if gid in npc_ok:
            continue
        img = None
        # 1) best nested frame from ResNpc*
        for L in (resnpc3, resnpc2):
            if gid < L.count:
                img = pick_nested_best(L.entry_bytes(gid), min_h=18)
                if img and img.size[1] >= 18:
                    break
                img = None
        # 2) Spr → large res00 (行囊 etc.)
        if (img is None or img.size[1] < 18) and gid < spr.count:
            alt = spr_first_large_res00(spr.entry_bytes(gid), res00, min_side=40)
            if alt is not None:
                img = alt
        # 3) weak nested fallback
        if img is None:
            for L in (resnpc3, resnpc2):
                if gid < L.count:
                    img = pick_nested_best(L.entry_bytes(gid), min_h=8, min_area=50)
                    if img:
                        break
        if img is None:
            print(f"  npc graph {gid} FAIL")
            continue
        img = scrub_sprite_fringe(black_to_alpha(img))
        # bag sprites can be huge — downscale for map prop
        if max(img.size) > 120:
            scale = 120 / max(img.size)
            img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.Resampling.NEAREST)
        name = f"npc_{gid}.png"
        img.save(PROPS / name)
        img.save(OUT / name)
        npc_ok[gid] = dict(file=name, w=img.size[0], h=img.size[1], model=mid)
        print(f"  npc {mid} graph {gid}: {img.size}")

    buildings_out = []
    for p in bld_place:
        fid = p["fid"]
        if fid not in fid_ok:
            continue
        ox, oy = p.get("ox", 0), p.get("oy", 0)
        if abs(ox) > 80:
            ox = 0
        if abs(oy) > 200:
            oy = 0
        buildings_out.append(dict(
            x=p["x"], y=p["y"], bid=p["bid"], name=p["name"], fid=fid,
            file=fid_ok[fid]["file"], sw=fid_ok[fid]["w"], sh=fid_ok[fid]["h"],
            ox=ox, oy=oy,
        ))
    npcs_out = []
    meta = json.loads((WEB / "meta.json").read_text(encoding="utf-8"))
    ox0, oy0 = meta["chunk_origin"]
    for o in ont:
        mid = o.get("ModelID")
        if mid is None:
            continue
        gid = role_graph.get(int(mid), int(mid))
        if gid not in npc_ok:
            continue
        npcs_out.append(dict(
            x=o.get("MapX", 0), y=o.get("MapY", 0), ModelID=mid, Type=o.get("Type"),
            EventID=o.get("EventID"), graph=gid, file=npc_ok[gid]["file"],
            sw=npc_ok[gid]["w"], sh=npc_ok[gid]["h"],
            Logic=o.get("Logic"), MoveLevel=o.get("MoveLevel"),
            lx=o.get("MapX", 0) - ox0, ly=o.get("MapY", 0) - oy0,
        ))

    meta["buildings"] = buildings_out
    meta["npcs"] = npcs_out
    meta["objects"] = npcs_out
    meta["phase"] = 11
    meta["findings"] = dict(meta.get("findings") or {}, phase11="scrub fringe; best NPC frames; Spr→res00 bag; lazy tiles; BGM+interact")
    (WEB / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    (PROPS / "index.json").write_text(json.dumps(dict(buildings=buildings_out, npcs=npcs_out, fids=fid_ok, graphs=npc_ok), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"props done bld={len(buildings_out)} npc={len(npcs_out)}")
    return meta


def build_chunk_atlases(meta: dict, chunk: int = 16):
    """Pack tiles into chunk×chunk atlases; write chunks/meta and update meta.lazy."""
    mapW, mapH = meta["chunk_size"]
    tileW, tileH = meta["tile_pixel"]
    grid = meta["grid"]
    # load unique tile images once
    tiles: list[Image.Image | None] = []
    for i in range(meta["unique_tiles"]):
        p = WEB / f"t_{i:04d}.png"
        if p.exists():
            tiles.append(Image.open(p).convert("RGBA"))
        else:
            tiles.append(None)
    cdir = WEB / "chunks"
    if cdir.exists():
        shutil.rmtree(cdir)
    cdir.mkdir(parents=True)
    atlas_list = []
    cy = 0
    while cy < mapH:
        cx = 0
        ch = min(chunk, mapH - cy)
        while cx < mapW:
            cw = min(chunk, mapW - cx)
            # atlas: each cell as tileW x tileH in row-major
            aw, ah = cw * tileW, ch * tileH
            atlas = Image.new("RGBA", (aw, ah), (0, 0, 0, 0))
            local = []
            for ly in range(ch):
                row = []
                for lx in range(cw):
                    tid = grid[cy + ly][cx + lx]
                    row.append(tid)
                    if tid >= 0 and tid < len(tiles) and tiles[tid] is not None:
                        im = tiles[tid]
                        # center in cell
                        px = lx * tileW + (tileW - im.size[0]) // 2
                        py = ly * tileH + (tileH - im.size[1]) // 2
                        atlas.alpha_composite(im, (px, py))
                local.append(row)
            name = f"c_{cx}_{cy}.png"
            atlas.save(cdir / name, optimize=True)
            atlas_list.append(dict(x=cx, y=cy, w=cw, h=ch, file=name))
            cx += chunk
        cy += chunk
    lazy = dict(chunk=chunk, atlases=atlas_list, mode="atlas")
    meta["lazy"] = lazy
    (cdir / "index.json").write_text(json.dumps(lazy, ensure_ascii=False), encoding="utf-8")
    (WEB / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    # Drop per-tile PNGs from dist path later; keep in public for fallback but mark preferred atlas
    print(f"atlases: {len(atlas_list)} chunks of {chunk}")
    return lazy


def export_game_data():
    data_dir = ROOT / "web/public/game/data"
    data_dir.mkdir(parents=True, exist_ok=True)
    # BGM: ScnInfo sound col for 1-0s = 4 → 04_AMAZINGWATER
    bgm_src = ROOT / "extract/Blade And Sword 2 Ancient Legend/yy/04_AMAZINGWATER.mp3"
    bgm_dir = ROOT / "web/public/game/bgm"
    bgm_dir.mkdir(parents=True, exist_ok=True)
    if bgm_src.exists():
        shutil.copy2(bgm_src, bgm_dir / "town.mp3")
        # also keep a couple extras
        for extra in ["01_IHAVETOGO.mp3", "18_CHINESE_KONGFU.mp3"]:
            p = bgm_src.parent / extra
            if p.exists():
                shutil.copy2(p, bgm_dir / extra)
    bgm = dict(scene="1-0s", file="game/bgm/town.mp3", sound_id=4, name="04_AMAZINGWATER")

    # Dialogs: Dialog_Public1 + talk stubs keyed by EventID
    dialogs = {}
    pub = (EXT / "mb/Dialog_Public1.txt").read_text(encoding="gbk", errors="replace").splitlines()
    pub_map = {}
    for line in pub[1:]:
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].isdigit():
            # split //// into lines
            text = parts[1].replace("%5%", "少侠").replace("%7%", "少侠").replace("%1%", "少侠").replace("%12%", "英雄")
            pub_map[int(parts[0])] = [s for s in text.split("////") if s.strip()]
    talk_dir = EXT / "mb/trigger/talk"
    for o in json.loads((PROPS / "index.json").read_text())["npcs"]:
        eid = o.get("EventID")
        if not eid:
            continue
        tp = talk_dir / f"{eid}.txt"
        lines_out = []
        if tp.exists():
            for line in tp.read_text(encoding="gbk", errors="replace").splitlines()[1:]:
                parts = line.split("\t")
                if len(parts) < 5:
                    continue
                # 跳转数据 often dialog id when 跳转类型==1
                try:
                    jump_type = int(parts[4]) if parts[4] else 0
                    jump_data = int(parts[5]) if len(parts) > 5 and parts[5] else 0
                except ValueError:
                    continue
                if jump_type == 1 and jump_data in pub_map:
                    lines_out.extend(pub_map[jump_data])
                    if len(lines_out) >= 4:
                        break
        if not lines_out and pub_map:
            # fallback first few public lines by remark match later
            lines_out = pub_map.get(122, list(pub_map.values())[0])[:3]
        dialogs[eid] = dict(name=eid, model=o.get("ModelID"), lines=lines_out[:6])

    # Skills stub: 剑客_普通攻击*
    skills = []
    for line in (EXT / "mb/Skill.ini").read_text(encoding="gbk", errors="replace").splitlines():
        if "剑客_普通攻击" in line:
            parts = line.split("\t")
            skills.append(dict(name=parts[1] if len(parts) > 1 else "attack", raw=parts[:12]))
            if len(skills) >= 4:
                break
    attack = dict(name="剑客_普通攻击", skills=skills, key="Space", range=1.5, cooldown_ms=450)

    game = dict(bgm=bgm, dialogs=dialogs, attack=attack, interact_key="e", interact_range=2.0)
    (data_dir / "game.json").write_text(json.dumps(game, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"game data: dialogs={len(dialogs)} skills={len(skills)} bgm={bgm['file']}")
    return game


def main():
    meta = export_props()
    build_chunk_atlases(meta, chunk=16)
    export_game_data()
    # update maps index blurb
    idx_path = ROOT / "web/public/game/maps/index.json"
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    idx["begin_scn_mapping"] = (
        "Phase11: 瓦当镇 props scrubbed; NPC frames fixed; tile atlases+lazy; "
        "BGM 04_AMAZINGWATER; E=talk Space=attack stub; spawn (63,59)."
    )
    idx_path.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Phase 11 export OK")


if __name__ == "__main__":
    main()
