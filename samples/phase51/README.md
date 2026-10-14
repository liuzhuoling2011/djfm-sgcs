# Phase51 — HD world wiring + sword grip (part-compose)

## Sword grip (priority)
Whole-frame ESRGAN separates sword from fist. **Fix:** upscale CA/TK/HD/RH parts individually, then paper-doll compose (`tools/phase44_player_hd_compose.py`) with `rh_grip_nudges`.

| File | What |
|------|------|
| `grip_before_after_strip.png` | BEFORE / AFTER HD (E S W N SE) |
| `grip_E_sd_hd.png` | East SD vs HD + fist zoom |
| `rh_grip_zoom_E.png` | Phase44 HD E grip zoom |
| `rh_align_8dir.png` | 8-dir HD align |

Facing unchanged: `(oct+6)%8`. Canvas JM HUD unchanged.

## Also this phase
- `props_hd/` top-48 town props ×2
- `ground_hd/ground_full.png` ×2 (8320×4224)
- NPC/mon draw scaled for HD sheets
- Live: https://liuzhuoling2011.github.io/djfm-sgcs/
