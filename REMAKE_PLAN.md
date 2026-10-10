# Remake plan — single-map vertical slice

## Goal
Browser playable slice: walk one early map (瓦当镇 / first outdoor), talk via `Dialog_*.txt`, one combat encounter stub. Stack: **TypeScript + Vite + Canvas 2D** (WebGL later if batching needs it). Node **22** only (`/opt/node22/bin`).

## Asset pipeline
1. `leyilib.py extract zy/map_*.lib --png` → tile PNGs (blocked on codec fidelity).
2. Nested `lep` from `ResPlayer1` → character frames.
3. `sy/*.sy` → `.wav`; `yy/*.mp3` keep; `dhp` → webm via ffmpeg when needed.
4. `bdh/chs/*.txt` GBK → UTF-8 JSON (roles, props, dialogs, quests).

## Slice scope
- Map renderer: isometric/tile from `map_ren` (or first town map once identified).
- Entity: one playable class from `Role.txt` (剑客).
- Input: keyboard move; click NPC → dialog from `Dialog_Public1.txt`.
- Combat stub: collide with one beastie → damage numbers using `Text.txt` strings.
- No full inventory/craft/skill tree in slice.

## Feasibility
- **Logic/data**: strong (existing TSV).
- **Audio/video**: ready.
- **Graphics**: medium–hard until `lep`/`Spr` RE completes; temporary colored placeholders OK for logic bring-up.
