# Map assembly review (瓦当镇 1-0s)

## Root cause
`parse_map_grid` read the **u16 remap table** after the 0x154 pack header (values `1,2,3,…`) and treated it as the ground grid. ComeOn.exe loads that table only as a lib preload list. The real grid is **`w*h` × 10-byte records at EOF**.

Evidence from ComeOn.exe (static, never executed):
- `0x4efa0c..0x4efa59`: allocate `count*10`, `fread` with element size `0xA`
- Runtime cell expands to 19 bytes; file fields copy ground/overlay words directly
- Occupancy of non-`0xFFFF` cells is diamond-shaped → diamond iso, not row-stagger for MAP indices
- Stagger helpers at `0x4f2640` are for a different coord path (after `0x43d010` convert)

## Seam metrics (region 40..100, diamond layout)
| | seam Δ | inner Δ | seam/inner |
|--|--|--|--|
| before (identity remap) | 58.9 | 22.8 | **2.59** |
| after (EOF 10-byte grid) | 35.3 | 30.0 | **1.18** |

Alternatives (stagger / transpose / mirrors) were worse than diamond+EOF grid on seam ratio.

## What changed
- `tools/phase10_export_scene.py` `parse_map_grid`
- `tools/leyilib.py` TOC row lep decoder (`decode_lep_diamond_v2`) → 64×32
- Rebuilt `web/public/game/map/ground_full.png`, tiles, 30 atlases, `meta.json`
- NAS `/volume4/web/djfm/` redeployed (HTTP 200)

## Screenshots
- `ground_before.png` / `ground_after.png` / `ground_after_full.png`
- `web_view_after.png` / `web_view_after_ground.png` / `web_view_after_moved.png`

## Still wrong
- Building `res00` lep **vertical smear** (pre-existing; not a MAP pitch bug)
- Overlay plane (`o` field) not fully wired (some ids are not map diamonds)
- Height plane / collision from MAP flags still soft
- Image-level road edges can still look slightly stepped because transition tiles are discrete; much improved vs identity grid
