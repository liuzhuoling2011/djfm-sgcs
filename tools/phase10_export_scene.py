#!/usr/bin/env python3
"""Phase 10: export 1-0s full/large map + BNT buildings + ONT NPC sprites."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from leyilib import LeyiLib, decode_lep_sprite, decode_lep_png, decode_lep_building  # noqa: E402
from PIL import Image
import numpy as np

ROOT = Path("/workspace/djfm-sgcs")
ZY = ROOT / "extract/Blade And Sword 2 Ancient Legend/zy"
EXT = ROOT / "assets/samples/phase9/fol_extract"
OUT = ROOT / "assets/samples/phase10"
WEB = ROOT / "web/public/game/map"
PROPS = WEB / "props"


def black_to_alpha(img: Image.Image) -> Image.Image:
    a = np.array(img.convert("RGBA"))
    rgb = a[:, :, :3]
    # near-black + pure black → transparent (map/building convention)
    mask = (rgb[:, :, 0] < 8) & (rgb[:, :, 1] < 8) & (rgb[:, :, 2] < 8)
    a[:, :, 3] = np.where(mask, 0, a[:, :, 3])
    # scrub leftover blue key fringe
    blue = (rgb[:, :, 2] >= 14) & (rgb[:, :, 0] <= 40) & (rgb[:, :, 1] <= 55) & (rgb[:, :, 2] > rgb[:, :, 0] + 40) & (a[:, :, 3] > 0)
    a[:, :, 3] = np.where(blue, 0, a[:, :, 3])
    return Image.fromarray(a)


def decode_sprite(blob: bytes) -> Image.Image | None:
    # Buildings: prefer decode_lep_building (strips vertical blue control triples).
    try:
        import bld_rle
        (sc, W, rows, _p), s, e = bld_rle.best_parse(blob)
        if rows and sc >= 0.98 * (e - s):
            return bld_rle.decode(blob)
    except Exception:
        pass
    for fn in (decode_lep_building, decode_lep_sprite, decode_lep_png):
        try:
            img = fn(blob)
            if img is None:
                continue
            if img.size[0] < 2 or img.size[1] < 2:
                continue
            return black_to_alpha(img)
        except Exception:
            continue
    return None


def parse_bld(path: Path) -> list[dict]:
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 0x20)[0]
    recs: list[dict] = []
    i = 0x40
    while i < len(data) - 50 and len(recs) < count + 50:
        typ = struct.unpack_from("<H", data, i)[0]
        if typ != 3:
            i += 1
            continue
        name_raw = data[i + 2 : i + 2 + 32]
        z = name_raw.find(b"\x00")
        if not (1 <= z <= 30):
            i += 1
            continue
        pad = name_raw[z + 1 :]
        if sum(1 for b in pad if b not in (0xCD, 0)) > 3:
            i += 1
            continue
        try:
            name = name_raw[:z].decode("gbk")
        except Exception:
            i += 1
            continue
        body = i + 34
        fa, fid = struct.unpack_from("<HH", data, body)
        ox_q8, oy_q8 = struct.unpack_from("<ii", data, body + 16)
        w_q8, h_q8 = struct.unpack_from("<II", data, body + 24)
        # Q8-ish hotspot; clamp nonsense
        ox = ox_q8 >> 8 if abs(ox_q8) < 500_000 else 0
        oy = oy_q8 >> 8 if abs(oy_q8) < 500_000 else 0
        w = w_q8 >> 8 if 0 < w_q8 < 500_000 else 0
        h = h_q8 >> 8 if 0 < h_q8 < 500_000 else 0
        recs.append(
            dict(idx=len(recs), off=i, name=name, fa=fa, fid=fid, ox=ox, oy=oy, w=w, h=h)
        )
        j = body + 40
        found = False
        while j < min(i + 3000, len(data) - 50):
            if struct.unpack_from("<H", data, j)[0] == 3:
                nr = data[j + 2 : j + 2 + 32]
                zz = nr.find(b"\x00")
                if 1 <= zz <= 30 and sum(1 for b in nr[zz + 1 :] if b not in (0xCD, 0)) <= 3:
                    try:
                        nr[:zz].decode("gbk")
                        i = j
                        found = True
                        break
                    except Exception:
                        pass
            j += 1
        if not found:
            break
    return recs


def parse_bnt(path: Path, bld: list[dict]) -> list[dict]:
    raw = path.read_bytes()
    data = raw[0xC4:]
    out: list[dict] = []
    off = 0
    while off + 20 <= len(data):
        typ, bid = struct.unpack_from("<HH", data, off)
        if typ == 3:
            x, y = struct.unpack_from("<II", data, off + 4)
            if x <= 128 and y <= 128:
                info = bld[bid] if bid < len(bld) else {}
                out.append(
                    dict(
                        kind="bld",
                        bid=bid,
                        x=x,
                        y=y,
                        name=info.get("name", ""),
                        fid=info.get("fid"),
                        ox=info.get("ox", 0),
                        oy=info.get("oy", 0),
                        w=info.get("w", 0),
                        h=info.get("h", 0),
                    )
                )
                off += 20
                continue
        if typ == 4:
            x, y = struct.unpack_from("<II", data, off + 4)
            # capture short script ascii
            chunk = data[off + 20 : off + 120]
            asc = "".join(chr(b) if 32 <= b < 127 else " " for b in chunk).strip()
            out.append(dict(kind="trigger", bid=bid, x=x, y=y, script=asc[:80], fid=None))
            found = False
            for j in range(off + 20, min(off + 600, len(data) - 20)):
                t2 = struct.unpack_from("<H", data, j)[0]
                if t2 in (3, 4):
                    x2, y2 = struct.unpack_from("<II", data, j + 4)
                    if x2 <= 128 and y2 <= 128:
                        off = j
                        found = True
                        break
            if not found:
                off += 1
            continue
        off += 1
    return out


def parse_ont(path: Path) -> list[dict]:
    text = path.read_text(encoding="gbk", errors="replace")
    objs: list[dict] = []
    cur: dict = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip()
        if k == "Type" and cur.get("Type") is not None:
            objs.append(cur)
            cur = {}
        if k in (
            "Type",
            "ModelID",
            "MapX",
            "MapY",
            "Logic",
            "MoveLevel",
            "Logic_x",
            "Logic_y",
            "Logic_cx",
            "Logic_cy",
            "Logic_Dir",
        ):
            try:
                cur[k] = int(v)
            except ValueError:
                cur[k] = v
        elif k == "EventID":
            cur[k] = v
    if cur.get("Type") is not None:
        objs.append(cur)
    return objs


def parse_role_graph(path: Path) -> dict[int, int]:
    """角色ID → 图形ID"""
    text = path.read_text(encoding="gbk", errors="replace")
    lines = text.splitlines()
    if not lines:
        return {}
    headers = lines[0].split("\t")
    try:
        i_role = headers.index("角色ID")
        i_graph = headers.index("图形ID")
    except ValueError:
        # fallback: scan
        i_role, i_graph = 0, 1
        for i, h in enumerate(headers):
            if "角色" in h and "ID" in h:
                i_role = i
            if "图形" in h:
                i_graph = i
    m: dict[int, int] = {}
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) <= max(i_role, i_graph):
            continue
        try:
            m[int(parts[i_role])] = int(parts[i_graph])
        except ValueError:
            continue
    return m


def nested_first_frame(blob: bytes) -> Image.Image | None:
    if len(blob) < 8:
        return None
    count = struct.unpack_from("<I", blob, 0)[0]
    if count == 0 or count > 512:
        return None
    offs = []
    for i in range(count):
        if 4 + 4 * i + 4 > len(blob):
            break
        offs.append(struct.unpack_from("<I", blob, 4 + 4 * i)[0])
    for i, o in enumerate(offs):
        if o >= len(blob) or blob[o : o + 4] != b"lep\x00":
            continue
        end = offs[i + 1] if i + 1 < len(offs) else len(blob)
        if end <= o:
            end = len(blob)
        img = decode_sprite(blob[o:end])
        if img and img.size[1] >= 20:  # prefer tall character frames
            return img
        if img and img.size[0] >= 16:
            return img
    return None


def parse_map_grid(map_path: Path) -> tuple[int, int, list[list[int]], bytes]:
    """Parse LeyiMap1.50 ground grid (ComeOn/LeyiMap load @ 0x4ef7e0).

    File layout (verified against ComeOn.exe static disassembly):
      0x00  magic ``LeyiMap1.50``
      0x10  u16 width, u16 height
      0x44  Debug name (16) + Map_*.lib name (256)
      0x154 8-byte pack header + u16 remap table (lib preload, NOT the grid)
      EOF - w*h*10: per-cell records (fread size 0xA):
          u16 ground_tid, u16 overlay_tid, u8 flag, u8, u16 height, u16 pad
    Ground ``0xFFFF`` = empty hole. ``ground_tid`` indexes map_*.lib directly.
    Projection is diamond iso: screen=( (x-y)*32, (x+y)*16 ), tile 64x32
    (occupancy of valid cells forms a diamond in index space).
    """
    data = map_path.read_bytes()
    if not data.startswith(b"LeyiMap1.50"):
        raise RuntimeError(f"{map_path}: not LeyiMap1.50")
    w, h = struct.unpack_from("<HH", data, 0x10)
    rec_size = 10
    need = w * h * rec_size
    if need > len(data):
        raise RuntimeError(f"grid OOB need={need} len={len(data)}")
    rec_off = len(data) - need
    grid: list[list[int]] = []
    overlay: list[list[int]] = []
    flags: list[list[int]] = []
    for y in range(h):
        grow, orow, frow = [], [], []
        for x in range(w):
            o = rec_off + (y * w + x) * rec_size
            g, ov, fl, _ff, ht, _pad = struct.unpack_from("<HHBBHH", data, o)
            grow.append(g)
            orow.append(ov)
            frow.append(fl | (ht << 8))
        grid.append(grow)
        overlay.append(orow)
        flags.append(frow)
    # rest = remap table region (for debugging); pack as overlay+flags sidecar tip
    rest = data[0x154:rec_off]
    # stash overlays on function attribute for exporters that want them
    parse_map_grid.last_overlay = overlay  # type: ignore[attr-defined]
    parse_map_grid.last_flags = flags  # type: ignore[attr-defined]
    parse_map_grid.last_rec_off = rec_off  # type: ignore[attr-defined]
    return w, h, grid, rest


def export_map_tiles(
    grid: list[list[int]],
    map_lib: LeyiLib,
    out_dir: Path,
    origin: tuple[int, int] | None = None,
    size: tuple[int, int] | None = None,
) -> dict:
    mh, mw = len(grid), len(grid[0])
    ox, oy = origin or (0, 0)
    cw, ch = size or (mw, mh)
    cw = min(cw, mw - ox)
    ch = min(ch, mh - oy)
    # unique tile ids in window
    tile_map: dict[int, int] = {}  # lib_idx -> local
    tiles: list[Image.Image | None] = []
    local_grid: list[list[int]] = []
    decode_ok = 0
    miss = 0
    for y in range(ch):
        row = []
        for x in range(cw):
            tid = grid[oy + y][ox + x]
            if tid == 0xFFFF or tid >= map_lib.count:
                row.append(-1)
                miss += 1
                continue
            if tid not in tile_map:
                blob = map_lib.entry_bytes(tid)
                img = None
                try:
                    from leyilib import decode_lep_diamond

                    img = decode_lep_diamond(blob)
                except Exception:
                    img = None
                if img is None:
                    img = decode_sprite(blob)
                if img is not None:
                    img = black_to_alpha(img)
                    decode_ok += 1
                else:
                    miss += 1
                tile_map[tid] = len(tiles)
                tiles.append(img)
            row.append(tile_map[tid])
        local_grid.append(row)
    out_dir.mkdir(parents=True, exist_ok=True)
    # wipe old tiles
    for p in out_dir.glob("t_*.png"):
        p.unlink()
    for i, img in enumerate(tiles):
        path = out_dir / f"t_{i:04d}.png"
        if img is None:
            Image.new("RGBA", (64, 32), (0, 0, 0, 0)).save(path)
        else:
            img.save(path)
    fill = sum(1 for row in local_grid for v in row if v >= 0 and tiles[v] is not None)
    total = cw * ch
    return dict(
        chunk_origin=[ox, oy],
        chunk_size=[cw, ch],
        map_dims=[mw, mh],
        unique_tiles=len(tiles),
        grid=local_grid,
        decode_ok=decode_ok,
        miss_holes=miss,
        fill_rate=round(fill / total, 4) if total else 0,
        tile_pixel=[64, 32],
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PROPS.mkdir(parents=True, exist_ok=True)

    print("=== BLD ===")
    bld = parse_bld(EXT / "mb/BLD_Ren.Mdl")
    print(f"  buildings: {len(bld)}")
    (OUT / "bld_ren_index.json").write_text(
        json.dumps(bld[:50] + ([{"_truncated": True}] if len(bld) > 50 else []), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== BNT ===")
    placements = parse_bnt(EXT / "cj/1-0s.BNT", bld)
    bld_place = [p for p in placements if p.get("kind") == "bld" and p.get("fid")]
    print(f"  placements: {len(placements)} bld_with_fid={len(bld_place)}")

    print("=== ONT + Role ===")
    ont = parse_ont(EXT / "cj/1-0s.ONT")
    role_graph = parse_role_graph(EXT / "mb/Role.txt")
    print(f"  objects: {len(ont)} role_graphs: {len(role_graph)}")

    res00 = LeyiLib.open(ZY / "res00.Lib")
    resnpc3 = LeyiLib.open(ZY / "ResNpc3.lib")
    resnpc2 = LeyiLib.open(ZY / "ResNpc2.lib")
    mapren = LeyiLib.open(ZY / "map_ren.lib")

    # Export unique building fids
    print("=== building sprites ===")
    fid_set = sorted({p["fid"] for p in bld_place if p.get("fid")})
    fid_ok = {}
    for fid in fid_set:
        if fid >= res00.count:
            continue
        img = decode_sprite(res00.entry_bytes(fid))
        if img is None:
            print(f"  fid {fid}: FAIL")
            continue
        name = f"bld_{fid}.png"
        img.save(PROPS / name)
        img.save(OUT / name)
        fid_ok[fid] = dict(file=name, w=img.size[0], h=img.size[1])
        print(f"  fid {fid}: {img.size}")

    # Export NPC sprites by graph id
    print("=== NPC sprites ===")
    npc_ok = {}
    for o in ont:
        mid = o.get("ModelID")
        if mid is None:
            continue
        gid = role_graph.get(int(mid), int(mid))
        if gid in npc_ok:
            continue
        img = None
        for L in (resnpc3, resnpc2):
            if gid < L.count:
                img = nested_first_frame(L.entry_bytes(gid))
                if img:
                    break
        if img is None and gid < res00.count:
            img = decode_sprite(res00.entry_bytes(gid))
        if img is None:
            print(f"  model {mid} graph {gid}: FAIL")
            continue
        name = f"npc_{gid}.png"
        img.save(PROPS / name)
        img.save(OUT / name)
        npc_ok[gid] = dict(file=name, w=img.size[0], h=img.size[1], model=mid)
        print(f"  model {mid} graph {gid}: {img.size}")

    # Full 128×128 map export (streaming-friendly: all tiles, client culls)
    print("=== MAP 128×128 ===")
    mw, mh, grid, rest = parse_map_grid(EXT / "cj/1-0s.MAP")
    print(f"  dims {mw}x{mh} rest_plane_bytes={len(rest)}")
    # height/aux probe
    aux_note = "second plane looks like 0xFFFF/0xCDCD padding; height channel unclear"
    if len(rest) >= mw * mh * 2:
        plane2 = rest[: mw * mh * 2]
        vals = [struct.unpack_from("<H", plane2, i)[0] for i in range(0, min(2000, len(plane2)), 2)]
        from collections import Counter

        c = Counter(vals)
        aux_note = f"plane2 top values {c.most_common(5)}; deferred as height"
        print(" ", aux_note)

    meta_tiles = export_map_tiles(grid, mapren, WEB, origin=(0, 0), size=(mw, mh))
    print(
        f"  tiles unique={meta_tiles['unique_tiles']} fill={meta_tiles['fill_rate']} ok={meta_tiles['decode_ok']}"
    )

    # Collision: empty MAP cells + ONT Logic_* boxes
    blocked = []
    for y in range(mh):
        for x in range(mw):
            if grid[y][x] == 0xFFFF:
                blocked.append([x, y])
    logic_boxes = []
    for o in ont:
        if "Logic_x" in o and "Logic_cx" in o:
            logic_boxes.append(
                dict(
                    x=o["Logic_x"],
                    y=o["Logic_y"],
                    cx=o["Logic_cx"],
                    cy=o["Logic_cy"],
                    model=o.get("ModelID"),
                    event=o.get("EventID"),
                )
            )
            # mark box cells blocked for solid NPCs (Logic==1)
            if o.get("Logic") == 1:
                for ly in range(o["Logic_y"], o["Logic_y"] + o["Logic_cy"]):
                    for lx in range(o["Logic_x"], o["Logic_x"] + o["Logic_cx"]):
                        if 0 <= lx < mw and 0 <= ly < mh:
                            blocked.append([lx, ly])

    # Dedup blocked
    blocked_u = sorted({(x, y) for x, y in blocked})
    blocked = [list(p) for p in blocked_u]

    buildings_out = []
    for p in bld_place:
        fid = p["fid"]
        if fid not in fid_ok:
            continue
        buildings_out.append(
            dict(
                x=p["x"],
                y=p["y"],
                bid=p["bid"],
                name=p["name"],
                fid=fid,
                file=fid_ok[fid]["file"],
                sw=fid_ok[fid]["w"],
                sh=fid_ok[fid]["h"],
                ox=p.get("ox", 0),
                oy=p.get("oy", 0),
            )
        )

    npcs_out = []
    for o in ont:
        mid = o.get("ModelID")
        if mid is None:
            continue
        gid = role_graph.get(int(mid), int(mid))
        if gid not in npc_ok:
            continue
        npcs_out.append(
            dict(
                x=o.get("MapX", 0),
                y=o.get("MapY", 0),
                ModelID=mid,
                Type=o.get("Type"),
                EventID=o.get("EventID"),
                graph=gid,
                file=npc_ok[gid]["file"],
                sw=npc_ok[gid]["w"],
                sh=npc_ok[gid]["h"],
                Logic=o.get("Logic"),
                MoveLevel=o.get("MoveLevel"),
            )
        )

    triggers = [p for p in placements if p.get("kind") == "trigger"]

    meta = dict(
        source="cj/1-0s.MAP + Map_Ren.lib + BLD_Ren.Mdl + 1-0s.BNT/ONT (Phase 10)",
        scene="1-0s",
        scene_id=0,
        scene_name="瓦当镇",
        pack_id="ren",
        spawn=[63, 59],  # ActMdl act0
        objects=npcs_out,  # keep compat key for markers; now with sprites
        buildings=buildings_out,
        npcs=npcs_out,
        triggers=[{"x": t["x"], "y": t["y"], "bid": t["bid"], "script": t.get("script", "")} for t in triggers],
        blocked_sample=blocked[:5000],
        blocked_count=len(blocked),
        logic_boxes=logic_boxes,
        aux_planes=aux_note,
        iso={"tileW": 64, "tileH": 32},
        findings={
            "fol": "CRACKED",
            "begin_scn": "0 -> 1-0s / Map_Ren.lib",
            "bld": "leyibld1.50 → fid indexes res00.Lib lep sprites",
            "ont": "ModelID=Role角色ID → 图形ID → ResNpc3 nested lep",
            "collision": "MAP 0xFFFF holes + ONT Logic_* boxes when Logic=1",
        },
        **meta_tiles,
    )
    # Absolute coords already — chunk is full map
    meta["chunk_origin"] = [0, 0]
    (WEB / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    (OUT / "scene_1-0s_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    props_index = dict(buildings=buildings_out, npcs=npcs_out, fids=fid_ok, graphs=npc_ok)
    (PROPS / "index.json").write_text(json.dumps(props_index, ensure_ascii=False, indent=2), encoding="utf-8")

    # Update maps index
    idx_path = ROOT / "web/public/game/maps/index.json"
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    idx["begin_scn_mapping"] = (
        "Phase10: BeginScn=0 → 1-0s 瓦当镇 128×128; BNT buildings + ONT NPCs blitted; "
        "ActMdl spawn (63,59); Logic_* collision."
    )
    idx_path.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"DONE buildings={len(buildings_out)} npcs={len(npcs_out)} "
        f"blocked={len(blocked)} triggers={len(triggers)}"
    )


if __name__ == "__main__":
    main()
