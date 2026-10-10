# Phase 41 — 主角走/跑 gait + 叠层

对照 Wine（`assets/samples/phase37/wine_walk/` + `wine_*_8dir_strip.png`），修网页主角走/跑姿势。

## 权威脚本
- `tools/phase41_player_sprites.py` — 导出 `web/public/game/player/{walk,run,idle,attack}/`
- Phase39 的 RH_002 / facing=(oct+6)%8 / rh=(body+3)%8 **保持不变**；gait、run 图集、RH under 以本阶段为准。

## 文件说明（按键方向 = hold，非 art index）

### 分向短 GIF（推荐试看）
- `walk_{E,SE,S,SW,W,NW,N,NE}.gif` — 走，ping-pong 0,1,2,3,2,1
- `run_{E,SE,S,SW,W,NW,N,NE}.gif` — 跑（独立 nest）
- `walk_8dir.gif` / `run_8dir.gif` — 八向拼盘

### Wine 对照
- `wine_vs_web_walk_8dir.png` / `.gif` — Wine strip / 帧 vs Web walk
- `wine_vs_web_run_8dir.png` / `.gif` — 同上（run）
- `proof_rh_under_8dir.png` — RH under={0..5}（S..NE），over=E/SE
- `walk_8dir_grid.png` / `run_8dir_grid.png` — 8×4 帧网格

### 诊断过程图（可忽略）
`diag_*`、`nest_cmp_*`、`ca_nests_*`、`under_*`、`group_pick_*`、`run_nest_candidates.png` 等。

## Client
`web/src/main.ts`：ping-pong；Shift 跑用 `player/run/`；`animT += moved * 2.4`。

## 请硬刷新后试
WASD 八向走、Shift+WASD 八向跑；看腿相是否还跳、刀是否在 S/W 等到身后、跑是否比走更「迈」。
