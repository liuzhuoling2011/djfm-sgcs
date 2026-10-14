# Phase50 — Original-style HD (sharper JM, not new UI)

User direction: **match original layout/style**; only redraw sharper with HD assets.
- Bottom HUD: **canvas JM bar** (`Hud.draw` / jm_1478) — NOT HTML status bar
- Dialog / 行囊 / 买卖 / 镶嵌: **original JM panels**, Real-ESRGAN upscaled → `web/public/game/hud/panels_hd/`
- Player: paper-doll with RH grip nudge + Real-ESRGAN `player_hd`
- Facing unchanged: `(oct+6)%8`

## Proofs for confirmation
| File | What |
|------|------|
| `grip_before_after_strip.png` | Sword grip BEFORE/AFTER (5 dirs) |
| `grip_E_sd_hd.png` | East: SD before / SD after / HD after |
| `live_town.png` / `live_bag.png` / `live_dialog.png` | Live client (re-capture after deploy) |
| `from44_*` | Earlier ESRGAN character/NPC/mon grids |
| `town_overview_hd.png` | Town overview mock |

## Live
https://liuzhuoling2011.github.io/djfm-sgcs/
