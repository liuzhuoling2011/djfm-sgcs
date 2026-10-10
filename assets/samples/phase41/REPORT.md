# Phase41 报告 — 走/跑 gait + 叠层

## 1. 根因

### Gait
1. Client 用顺序循环 `0,1,2,3,0`，而 Spr 多向（尤其 code=6）是半周期 + ping-pong `0,1,2,3,2,1`；3→0 腿相硬切，姿势「跳」。
2. Run 误用 walk 同一套 nest；Spr 第二组 loco（code 8/6，如 S 的 nests 8–11、W 的 12–15）才是跑姿，Wine run 明显更探身/迈步。
3. E/SE 的 Spr walk 只有 3 帧，旧导出 pad 成 `[1,2,3,3]` 末帧粘滞。

### 叠层
1. RH under 仅 `{3,4,5}`（NW/N/NE）；Wine 上 S/SW/W 刀在身后，应变 under。
2. CA/TK/HD/RH 已同 fi；问题主要在 under 范围与 run nest，不是部位不同步。

## 2. 改动

| 文件 | 前后 |
|------|------|
| **新建** `tools/phase41_player_sprites.py` | 权威导出：walk + **run**；`loco_subs(which=0/1)`；RH under `{0,1,2,3,4,5}`；3 帧 pad `1,2,3,2` |
| `tools/phase39_player_sprites.py` | 注明 gait/run/under 以 phase41 为准；保留 RH_002/facing |
| `web/public/game/player/{walk,run,idle,attack}/` + `meta.json` | 重导出；新增 `run/`；gait=`pingpong_012321` |
| `web/src/main.ts` | 加载 `playerRun`；`GAIT_PP=[0,1,2,3,2,1]`；Shift 用 run 图集；`animT += moved*2.4`；跑速 6.5 |

未改 facing / RH_002 / (body+3)%8。未开第二幕。未 git commit。

## 3. 成果路径（`assets/samples/phase41/`）

- `walk_{E,SE,S,SW,W,NW,N,NE}.gif`、`run_{...}.gif`
- `walk_8dir.gif`、`run_8dir.gif`
- `wine_vs_web_walk_8dir.gif|.png`、`wine_vs_web_run_8dir.gif|.png`
- `proof_rh_under_8dir.png`、`walk_8dir_grid.png`、`run_8dir_grid.png`
- `README.md`（本目录说明）

## 4. 请「重温老游戏」硬刷新后试

1. **WASD** 八向走：腿是否还 3→0 抽一下；S/W 刀是否到身后。
2. **Shift+WASD** 八向跑：是否换跑姿（比走更迈），不是单纯加速走。
3. 只按 **D / D+S**：刀仍应在身前（E/SE = RH over）。

## 5. 剩余风险

- SW 等仅一组 Spr loco 的向：run 用 nest+8 启发式，未必完美贴 Wine。
- E/SE 仍 3 帧源，ping-pong 后略重复。
- Wine `wine_walk_*` 全屏截图角色坐标漂移，分帧对照不如 strip；以 strip + 实机为准。
- S/SW/W 的 RH under 若实机觉得刀「吃进身体」，可再收窄 under 集合。
