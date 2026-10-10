#!/usr/bin/env python3
"""Phase 40: remape act-1 monsters to full-body ResNpc/ResEx/ResBoss sets (keep lists)."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase23_fix_sprites as P23

WEB = Path(__file__).resolve().parents[1] / 'web/public/game/maps'
REMAP = {
  189: ('rex', 72, 'rex72'),
  10: ('r3', 48, 'r348'),
  11: ('r3', 48, 'r348'),
  75: ('r3', 48, 'r348'),
  190: ('r3', 594, 'r3594'),
  191: ('r3', 594, 'r3594'),
  158: ('boss', 564, 'boss564'),
  196: ('boss', 196, 'boss196'),
}
SCENES = ['1-2s','1-3as','1-9s','1-10s','1-10a4s','1-10a5s','1-10a6s','1-11s']

def ok(meta_act):
  fr = (meta_act or {}).get('frames') or []
  hs = [f[2] for f in fr if f]
  return len(fr) >= 4 and hs and 40 <= max(hs) < 400

def main():
  scenes = sys.argv[1:] or SCENES
  for scene in scenes:
    mp = WEB / scene / 'meta.json'
    if not mp.exists(): continue
    meta = json.loads(mp.read_text())
    mon_dir = WEB / scene / 'mon'; mon_dir.mkdir(exist_ok=True)
    monsets = dict(meta.get('monster_sets') or {})
    mons = list(meta.get('monsters') or [])
    roles = {int(m.get('role') or 0) for m in mons}
    n = 0
    for rid in sorted(roles):
      if rid not in REMAP: continue
      libk, ss, tag = REMAP[rid]
      exported = P23.export_set(libk, ss, mon_dir, tag)
      if not ok(exported.get('walk') or exported.get('idle')):
        print(scene, rid, tag, 'skip bad'); continue
      monsets[tag] = exported
      for m in mons:
        if int(m.get('role') or 0) == rid and str(m.get('set')) != tag:
          m['set'] = tag; n += 1
      print(scene, 'role', rid, '→', tag)
    meta['monsters'] = mons
    meta['monster_sets'] = monsets
    mp.write_text(json.dumps(meta, ensure_ascii=False))
    print(scene, 'remapped', n)
if __name__ == '__main__':
  main()
