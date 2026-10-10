# 刀剑封魔录外传：上古传说 — Web remake (act 1)

Vite + TypeScript Canvas client for act-1 of *Blade & Sword 2: Ancient Legend*.  
Working tree: `/workspace/djfm-sgcs`. Pages: `https://liuzhuoling2011.github.io/djfm-sgcs/`.

## Controls

| Key | Action |
|-----|--------|
| **W A S D** / arrows | Move (iso). **Shift** sprint (stamina) |
| **E** / Enter | Talk / advance dialog / interact |
| **Space** | Melee attack |
| **F1 / F2** | Skills (扫叶 / 疾电) |
| **Q** | Special (Q slot) |
| **1–4** | Potions (1–2 HP, 3–4 MP). Shared cooldown ~1.1s |
| **5** | 飞蝗石 (throw) |
| **6** | 指南珠 (return to scene spawn) |
| **I** | Inventory (行囊 JM panel) |
| **G** | Pick ground loot |
| **M** | Mute BGM + SFX |
| **Esc** | Close dialog / panels |

Query flags: `?softdf=1` soft DF; `?sfx=0` disable SFX; `?tint=0` / `?rain=0` disable scene FX.

## Act-1 quest outline (瓦当镇 → bq2=100)

1. **瓦当镇 (`ren` / 1-0s)** — Talk **沈云 (sy)** until `sy1=100`. Shop via **铁匠 (tj)** ShowJM. Leave north when exit unlocks.
2. **郊外 1-1s → 1-2s** — Clear trash; boss **魔豕兽** on 1-2s path.
3. **1-3s / 1-4s** — Meet **水英雄 / 号角** chain; continue toward冰池.
4. **1-5s → 1-6s** — Pick **蜀水** (trigger `shushui`) for blacksmith quench / embed.
5. **1-7s → 1-8s** — 九天池: avoid **天冰** hazards; talk / flags for **玲珑心** (bq tumble → wake, then 水英雄 + 天芝).
6. **1-9s** — **张珊 / 战象**; remake thins trash density for WASD clears.
7. **1-10\* / 1-11s** — Machines / **天机** dual fight; push flags to **bq2=100**.

Growth uses `mb/player/Init.txt` 男主角 (AT40+4/lv …). Foe RolePrivate stats are **scene-tier capped** (see `game.json` `combat`). Late-map trash/leash is **remake tuning** (`combat.remake`), not original table data.

## Dev

```bash
cd web && npm run build
# static: web/dist → GitHub Pages `main` / NAS `/volume4/web/djfm/`
```

Progress log: [`PROGRESS.md`](./PROGRESS.md).
