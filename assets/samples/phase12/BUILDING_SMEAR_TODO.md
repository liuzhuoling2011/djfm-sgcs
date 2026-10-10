# Building lep smear — visual TODO (Phase 12)

Updated: 2026-10-10 Asia/Shanghai (Wine xp_compare ground truth pass)

## What improved this pass
- Added `decode_lep_building()` in `tools/leyilib.py`:
  - Detects embedded control triples `(a<0x40, b∈0x100..0x1FF, c<0x80)` that painted as **vertical blue seams**
  - Strips those triples before row paint; tight pure-blue ctrl skip; **no horizontal inpaint** (inpaint worsened smear)
  - Broader blue fringe scrub in `black_to_alpha`
- Re-exported **112** town `bld_*.png`; mean ctrl-blue **0.0061 → 0.0003**
- Wall pieces (e.g. fid 118/124): blue column largely gone; thin dark seam may remain
- NAS `/volume4/web/djfm/` redeployed (lean ~31MB tgz, HTTP 200)

## Still blocked (structural smear)
Large/complex props still look sheared vs Wine (not just blue key):

| fid | name | issue |
|-----|------|-------|
| 445 | HONGQIANG_G18 | horizontal shear / wavy rows — needs true blit, not scrub |
| 385/386 | QIANG_B28/B29 | shredded / sparse — row x-placement unknown |
| 493 | SHAN_01 | residual fringe |
| 850/690/491/562/448/227 | (prior worst list) | still dirty |

Root cause still unknown without ComeOn.exe blit RE (user forbids ComeOn RE; Wine shots are GT).
Map diamond `yxn` path is **not** the building codec; buildings are raw TOC rows + rare embedded triples.

## Blockers / next
- User may supply **XP ISO** later for in-guest capture / optional deeper validation.
- Do **not** run ComeOn.exe for RE.
- Optional: static PE of ComeOn only if user explicitly allows; until then report smear **partially mitigated, structurally blocked**.
- Secondary deferred: 铁匠 short NPC, dialog flags, HP HUD.
