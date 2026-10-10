# Resource formats — 刀剑封魔录外传：上古传说 (ComeOn / Leyi)

Static analysis only. Never run `ComeOn.exe`.

## leyiLib 2.0 container (`zy/*.lib`)

```
offset  size  field
0x00    11    magic "leyiLib2.0\0"
0x0B    5     padding / checksum
0x10    4     entry_count (u32 LE)
0x100   8*N   TOC: { offset:u32, size:u32 } file-relative
```

Tool: `tools/leyilib.py list|extract [--png] [--nested]`

## `lep` image (RGB565 spans)

```
0x00  "lep\0"
0x0C  u32 width<<8
0x10  u32 height<<8
0x1C  … color keys include 0xF81F
0x30  row TOC → first_off
```

### Color keys (Phase 5)

- Primary: `0xF81F` (RGB565 magenta)
- Secondary chroma (map tip bleed + character): near-primary **blue**  
  `R≤2, G≤4, B≥16` (and dark pure-blue `R=0,G≤2,B≥8`)  
  Implemented as `is_trans_key()` — scrubs bright-blue artifacts.

### Map isometric diamonds

1. Secondary u32 offset table at `first_off` → tip pixel bank near EOF  
2. `yxn` stream tip→equator: `(y*4, x, nbytes, RGB565[nbytes/2])`  
3. Continuation half-spans past equator (`xn` then `yxn`, rebased y)  
4. Sec tip bank as raw rows  

`decode_lep_diamond()` / preferred by `decode_lep_png()`.

### ResPlayer character frames (Phase 6)

`ResPlayer*.lib` entries start with a nested-lep TOC (`u32 count` + offsets). Each nest is a `lep`:

- Same sec-table + row TOC layout as maps; **early slots that land inside the sec TOC are not pixel rows** (skip / clamp start to `sec_end`)
- Primary rows: left-aligned **raw RGB565**; optional trailing exact `(x,nbytes)` or `(npix,x)` span when it consumes the remainder
- Tip bank: raw rows; drop oversized trailing footer entry
- Pure-blue control nibbles (`r=g=0`, `1≤b≤0x38`) are **inpainted** from horizontal neighbors — painting them transparent mid-row caused Venetian-blind striping
- Exact keys only for chroma: `0xF81F`, `0`, `0xFFFF` (near-primary blue chroma key kept for maps via `is_trans_key`, not for sprite paint)
- `decode_lep_sprite()` → walk/idle sheets ~33×42; poses recognizable without heavy stripe holes

`Spr.lib`: non-lep descriptors (hotspots / dims / frame tables) — not a pixel codec; pixels live in Res* packs.

### res00 / leyibld buildings (Phase 12)

`decode_lep_building()` — same row TOC as sprites, plus:

- Mid-row **control triples** `(a<0x40, b∈[0x100,0x200), c<0x80)` stripped (they painted as vertical blue seams)
- No horizontal inpaint of ctrl cells (inpaint looked like smear on walls)
- Structural shear on large fids still unsolved (blit ≠ diamond `yxn`)

## Map packs (`map_*.lib`) — Phase 7

- TOC entries are **per-cell lep diamonds** (ground graphics), not shared-tileset indices.
- Human realm: `map_ren.lib` laid out as **150×123 row-major** (`index = y*150 + x`). Size heatmaps show contiguous bands; ~45% of cells decode as filled diamonds.
- Scene composition tables (`ScnInfo`, `.scn`, `.rmd`) referenced by ComeOn/LeyiMap strings but **not on disk as plaintext**; `.fol` encrypted. Height / layer / object placement still opaque.
- Web export: chunk of cells → `t_XXXX.png` + `meta.json` grid of local tile ids; iso pitch 64×32; outside-diamond black → alpha for Canvas.

## Other assets

| Ext | Notes |
|-----|--------|
| `.sy` | WAV PCM 44.1k mono |
| `.mp3` | BGM |
| `.dhp` | MPEG-1 PS |
| `bdh/*/*.txt` | GBK TSV |


## ScnInfo fields (Phase 8)

MapFile, BldFile, ObjFile, PreScn, PortalNum, MapX, MapY, ModelID, Type, RadarID, Dir, Logic_* pathing. LeyiMap1.50 + leyibld1.50. BeginScn=0 → map_ren heuristic until ScnInfo recovered.


## CombineLib `.fol` (Phase 9 — CRACKED)

Header u32 bit31 = encrypted flag; count = value & 0x7FFFFFFF.
TOC entry size 0x88 (34 dwords). Per-entry key from trailer at EOF - 4*(97+count).

- TOC dword j: plain = enc - 9*j^3 - key
- Payload dword j: plain = enc - key - 99*j^2
- Entry fields: name at 0; offset u32 at 0x80; size u32 at 0x84

Tool: `tools/fol.py <file.fol> -o outdir`

### LeyiMap `*.MAP` (cj.fol) — reviewed 2026-10-09

Magic `LeyiMap1.50`; u16 width/height @0x10; Debug name @0x44 (16); `Map_*.lib` name @0x54 (256).

After the name block (@0x154): 8-byte pack header + **u16 remap table** (preload list into the lib — often `1..libcount-1`). **This is NOT the ground grid.**

Ground/overlay cells are **`w*h` records of 10 bytes at EOF** (ComeOn `fread` size `0xA` @ `0x4efa51`):

| off | type | field |
|-----|------|--------|
| 0 | u16 | ground tile id → `map_*.lib` (0xFFFF = hole) |
| 2 | u16 | overlay tile id (optional second plane) |
| 4 | u8 | flag |
| 5 | u8 | (often 0xFF) |
| 6 | u16 | height / aux |
| 8 | u16 | pad (0xCDCD) |

Valid cells form a **diamond** in index space. Screen projection is **diamond iso**:
`sx=(x-y)*32`, `sy=(x+y)*16`, tile bitmap **64×32**.

`lep` map tiles: row TOC at 0x30 (offsets relative to 0x30); each row = repeated `(u16 skip_bytes, u16 n_bytes, RGB565…)`.

Scn wires MapFile/BldFile/ObjFile. Prior bug: treating the remap table as the grid (identity `y*w+x+1`) scrambled 瓦当镇.

## Missing tables

Recovered from mb.fol (Phase 9): ActMdl, ScnInfo, Skill.ini, trigger_*, Role, etc.

## Buildings `leyibld1.50` + `LeyiInit1.00` BNT (Phase 10)

`BLD_*.Mdl` (mb.fol): magic `leyibld1.50`; u32 count @0x20; records from 0x40:
`u16 type(=3)` + 32-byte name (GBK/ASCII, null + `0xCD` pad) + body.
Body: `u16 fa`, **`u16 fid` → `res00.Lib` lep sprite**, then unk/flags; ox/oy/w/h look shifted/Q8 — treat as soft.

`*.BNT` (cj.fol): magic `LeyiInit1.00`; u16 count @0x10; mdl name; placements @0xC4:
20-byte `{u16 type=3, u16 bid, u32 x, u32 y, u32, u32}` indexing BLD record `bid`.
type=4 = portal/trigger with trailing script text (`go …`, `SetFlag…`).

## ONT ModelID → sprite (Phase 10)

`ModelID` = `Role.txt` 角色ID → 图形ID → `ResNpc3.lib` (else `ResNpc2`) nested-lep TOC (same idea as ResPlayer). `Spr.lib` graph entries often point at tiny `res00` radar icons (hi=0x10), not full bodies.

## Phase 11 notes

- Building/NPC post: `scrub_sprite_fringe` + `strip_blue_columns` after `decode_lep_sprite`.
- Map streaming: 16×16 RGBA atlases in `chunks/c_X_Y.png`; meta.lazy lists them. Per-cell `t_*.png` optional fallback, omitted on NAS.
- Scene BGM: `ScnInfo` 声音 column → `ScnSoundMdl` → `yy/*.mp3`.
