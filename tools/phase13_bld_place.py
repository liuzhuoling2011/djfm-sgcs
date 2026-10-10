"""Phase 13: correct BLD→res00 mapping + per-part hotspots.

BLD_*.Mdl record: '03 00' + name[32] + u16 fa + u16 bld_id (what BNT references) + ...
  bbox i32 ox,oy,w,h @ +51 ; parts list at end, each:
  b2 bf bc fe 00 cd cd cd 00 | u16 res00_index | u16 flags | i32 ox | i32 oy
Part draws at iso(cell) + (ox, oy)   (verified vs Wine: PAILOU01C/01D Δcell(4,0) ↔ Δscreen(128,64)).
"""
import json, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import phase10_export_scene as P
import leyilib as L, bld_rle as B

MARK = bytes.fromhex("b2bfbcfe00cdcdcd00")

def parse_records(path):
    d = path.read_bytes()
    recs = P.parse_bld(path)
    out = {}
    for k, rc in enumerate(recs):
        a = rc["off"]; b = recs[k + 1]["off"] if k + 1 < len(recs) else len(d)
        bid = struct.unpack_from("<H", d, a + 36)[0]
        parts = []
        i = d.find(MARK, a)
        while 0 <= i < b:
            rid, fl, ox, oy = struct.unpack_from("<HHii", d, i + 9)
            parts.append(dict(rid=rid, ox=ox, oy=oy))
            i = d.find(MARK, i + 1)
        out.setdefault(bid, dict(bid=bid, name=rc["name"], parts=parts))
    return out

def main():
    root = Path(__file__).resolve().parent.parent
    meta_p = root / "web/public/game/map/meta.json"
    meta = json.loads(meta_p.read_text())
    recs = parse_records(P.EXT / "mb/BLD_Ren.Mdl")
    bld = P.parse_bld(P.EXT / "mb/BLD_Ren.Mdl")
    pl = [p for p in P.parse_bnt(P.EXT / "cj/1-0s.BNT", bld) if p["kind"] == "bld"]
    res00 = L.LeyiLib.open(P.ZY / "res00.Lib")
    props = root / "web/public/game/map/props"
    done = {}
    out = []
    for p in pl:
        r = recs.get(p["bid"])
        if not r or not r["parts"]:
            continue
        parts = []
        for pt in r["parts"]:
            rid = pt["rid"]
            if rid not in done:
                done[rid] = None
                if rid < res00.count:
                    blob = res00.entry_bytes(rid)
                    if blob[:4] == b"lep\x00":
                        try:
                            im = B.decode(blob)
                            if im is not None:
                                im.save(props / f"res_{rid}.png"); done[rid] = im.size
                        except Exception:
                            pass
            if done[rid]:
                parts.append(dict(file=f"res_{rid}.png", ox=pt["ox"], oy=pt["oy"], w=done[rid][0], h=done[rid][1]))
        if parts:
            out.append(dict(x=p["x"], y=p["y"], bid=p["bid"], name=r["name"], parts=parts))
    meta["buildings"] = out
    meta["bld_anchor"] = "part top-left = iso(cell) + (ox,oy); iso step 32x16; z = x+y (Phase 13)"
    meta_p.write_text(json.dumps(meta, ensure_ascii=False))
    print("placements", len(out), "unique images", sum(1 for v in done.values() if v))

if __name__ == "__main__":
    main()
