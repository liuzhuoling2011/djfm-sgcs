# Phase 43 Wine hold — CAPTURE BLOCKED (2026-10-10)

## Why re-record
Phase42 `wine_hold/*.gif` fail player-crop gait validation (MAD≈0, uniq≈1). Prior cropMAD scores were rain/noise, not leg swap.
See `../PHASE42_IDLE_REJECT.md`, `../phase42_gait_scores.json`, `../reject_hold_D_idle_crops.png`.

## Target
- 16 GIFs under this dir: `hold_*` + `run_hold_*`
- Continuous keydown WASD / Shift+WASD in 瓦当镇
- Accept only via `tools/phase43_validate_wine_hold.py` (mad≥4, uniq≥3)

## Blockers this session
1. In-town keys went to chat overlay; after Esc still no stride.
2. After X/Wine restart: DirectDraw Present frozen (ComeOn ~170% CPU, identical frames). Menu hover works; click/Enter do not activate 载入.
3. Cannot re-enter 瓦当镇; no new GIFs; no web walk change; no Pages deploy.
