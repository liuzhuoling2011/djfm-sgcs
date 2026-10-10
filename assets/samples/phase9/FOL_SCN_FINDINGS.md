# Phase 9 — CombineLib `.fol` CRACKED

ComeOn.exe never executed. Capstone static RE only.

## Status: **CRACKED**

### Crypto

| Stage | Formula (all `u32` mod 2³²) |
|-------|------------------------------|
| Header | `count_raw` bit31 = encrypted flag; `count = count_raw & 0x7FFFFFFF` |
| TOC entry | 0x88 bytes = 34 dwords; `plain[j] = enc[j] - 9·j³ - key[i]` for `j=0..33` |
| Payload | `plain[j] = enc[j] - key[i] - 99·j²` for dword `j` of file blob |
| Key store | trailer at `EOF - 4·(97 + count)`; `count` little-endian `u32` keys |

Entry layout after TOC decrypt: name C-string at +0; **offset `u32` @ +0x80**; **size `u32` @ +0x84**.

Tool: `tools/fol.py <file.fol> -o outdir`

### Packs

| File | Role | Highlights |
|------|------|------------|
| `cj.fol` | Scenes | `*.Scn` / `*.MAP` / `*.BNT` / `*.ONT` (255) |
| `mb.fol` | Design tables | **ScnInfo.txt**, ActMdl, Role, triggers, BLD_*.Mdl, Skill.ini… |
| `slr.fol` | Slr sprites | `NNN\NNN_001.PLI` |

### BeginScn → map

`ComeOn.ini BeginScn=0` → `ScnInfo.txt` row **1-0s** (scene_id 0).

`1-0s.Scn`:
```
MapFile=1-0s.MAP
BldFile=1-0s.BNT
ObjFile=1-0s.ONT
```
`1-0s.MAP` = `LeyiMap1.50`, lib **`Map_Ren.lib`**, dims **128×128**, tile u16 grid after `\x12HR*` marker.
`ActMdl.txt` act0 spawn **(63,59)** in 1-0s.
`1-0s.ONT` plaintext object list (ModelID/MapX/MapY/EventID/Logic_*).

### Height / layers

MAP files contain additional planes after the ground u16 grid; second plane on 1-0s still looks like padding/sentinel (`0xFFFF` / `0xCDCD`) — full height channel RE deferred. Building layer is `*.BNT` (`LeyiInit1.00`). Objects in `*.ONT`.

### Extract location

`assets/samples/phase9/fol_extract/{cj,mb,slr}/`
