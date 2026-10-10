# 刀剑封魔录外传：上古传说 — Phase 1 Progress

**Working dir:** `/workspace/djfm-sgcs/`  
**Date:** 2026-10-09 (Asia/Shanghai)  
**Constraint:** static analysis only — EXE never executed.

## Source file

| Field | Value |
|--------|--------|
| NAS path | `/volume4/Share10T/liuzhuoling/Share4T/Public/我的游戏/Blade And Sword 2 Ancient Legend.exe` |
| Box path | `/workspace/djfm-sgcs/Blade And Sword 2 Ancient Legend.exe` |
| Size | **1 133 687 733** bytes (~1.06 GiB) |
| SHA256 | `32aac48e93ba539a1e2df6fc3aeb2acf8b0c026cd1e672094b7a9b34f6b5b8c2` |
| `file` | PE32+ x86-64 GUI (WinRAR **sfxrar64** stub) |

## Packaging

- **Format:** WinRAR5 self-extracting archive (`Rar!\x1a\x07\x01` at overlay offset ~485 376).
- **SFX metadata:** `Setup=` points at `https://www.x6k.com/` (adware/repack launcher URLs). **Do not run the SFX.**
- **Extracted with:** rarlab `unrar` 7.12 (`tools/rar/unrar`). System `7z` failed with “Unsupported Method” on RAR5 solid streams.
- **Unpacked tree:** `/workspace/djfm-sgcs/extract/Blade And Sword 2 Ancient Legend/` (~**2.3 GiB**, 632 archive entries).
- **Repack extras (ignore for remake core):** `launcher.exe`, `steam_api.dll`, `tenoke.ini` (Steam appid **2924510**), `XDGAME*.url`, `游戏启动说明.txt`, dgVoodoo/`ddraw.dll` wrappers, `ComeOn.dll` (likely wrapper).

## Game identity

- **Title (chs):** 刀剑封魔录外传：上古传说  
- **Title (eng):** BladeSword DLC / Blade & Sword 2: Ancient Legend  
- **Config:** `ComeOn.ini` → `Version=1.02`, `current_language=chs`  
- **Main binary:** `ComeOn.exe` — PE32 i386 GUI, VC++/MFC, **PE timestamp 2003-07-29**, DirectDraw + DirectSound.  
- **Engine strings:** `LeyiInit1.00`, **`LeyiMap1.50`**, `leyiLib2.0`, `comeon begin/end`, paths `Zy\…`, `%sdhp\%s.dhp`, `%syy\%s.mp3`.

**Engine guess:** Custom early-2000s Chinese ARPG engine branded **ComeOn / Leyi (乐易) Lib 2.0 + LeyiMap 1.50** — **not** Unity/Unreal. Same lineage as classic 《刀剑封魔录》 PC releases (isometric/ARPG, DirectDraw).

## Directory inventory

| Path | Role | Notes |
|------|------|--------|
| `ComeOn.exe` | Game executable | Core logic; static RE target |
| `bdh/{chs,cht,eng,jpn}/` | Localized tables + intro video | Tab-separated **GBK** `.txt`; `begin.dhp` ~68 MB MPEG |
| `dhp/*.dhp` | Cutscenes / in-game video | **MPEG-1 Program Stream** (playable conceptually as video) — 33 files, ~84 MB |
| `yy/*.mp3` | BGM | 25 tracks, standard MP3 — **web-ready** |
| `sy/*.sy` | SFX | **WAV PCM** 16-bit mono 44.1 kHz renamed `.sy` — 486 files — **web-ready** (rename/copy) |
| `zy/*.lib` | Resource packs | Magic **`leyiLib2.0`**; TOC at `0x100` (u32 offset+size pairs); ~1.8 GiB |
| `zy/idx.lib` | Pack index | Plain text list of 14 lib names |
| `th/*.bmp` | Tiny effect textures | Standard BMP |
| `*.fol` (`cj`/`mb`/`slr`) | Unknown packed blobs | High entropy; likely encrypted/compressed fonts or data — needs RE |
| `Save/`, `ScreenShot/` | Runtime dirs | Empty in package |

### `zy/` leyiLib packs (entry counts)

| File | Entries | ~Size | Likely content |
|------|---------|-------|----------------|
| `Spr.lib` | 1790 | 39 MB | UI / sprites |
| `res00.Lib` | 14341 | 268 MB | General resources (`lep\0` records) |
| `ResPrior.lib` | 1090 | 58 MB | Priority / early-load art |
| `ResPlayer{1,2,3}.lib` | 5k–6k each | ~46–60 MB | Playable characters |
| `ResExPlayer{1,2}.lib` | — | — | Extra player assets |
| `ResBoss.lib` | 1202 | 137 MB | Bosses |
| `ResNpc{2,3}.lib`, `ResExNpc1.lib` | — | large | NPCs |
| `ResJM.Lib.{chs,cht,eng,jpn}` | — | ~90 MB each | Language-specific graphics/UI |
| `ResEx01.Lib` | — | — | Extra pack |
| `map_{ren,diyu,snow,nanfang,grave,Icecave}.lib` | 2.7k–18k | 5–33 MB | Maps (`lep\0` tiles/chunks) |
| `PixelGame.lib` | — | 1 byte (`1`) | Flag file |

Entry payloads are **proprietary** (not raw BMP/DDS at entry start). Some packs contain JPEG markers inside frames; full decode needs format RE (dimensions + palette/pixels or embedded JPEG streams).

### Readable data tables (`bdh/chs/`, GBK TSV)

Already human-readable — strong remake foundation:

- `Role.txt` — characters/monsters (IDs, anim frame lists, speeds, AI hooks)
- `PropMdl.txt` — items (potions, gems, craft formulas in description text)
- `Text.txt` — UI strings
- `Dialog_Public{1,2,3}.txt`, `Dialog_private.txt` — dialogue
- `RoleQuest.txt` — bestiary-style lore
- `TriggerQuest.txt` — quest flags / chapter flow

**Referenced by `ComeOn.exe` but not present as loose files** (likely packed inside libs or generated paths):  
`ActMdl.txt`, `BeastieMdl.txt`, `Font.txt`, `JMMDL.txt`, `MethodPoint.txt`, `ScnInfo.txt`, `ScnSoundMdl.txt`, `RoleEffectMdl.txt`, `PropGemFunc.txt`, `PropUpgrade.txt`, `Player\Skill.txt`, `player\init.txt`, `randprop.txt`, `trigger\scene\*.txt`, `trigger\talk\*.txt`, `EquipStr901–905.txt`.  
→ Need CombineLib / loader RE to extract.

## Remake feasibility (Canvas / WebGL, 老夫子-style)

### Easy / already web-friendly

- MP3 BGM (`yy/`)
- WAV SFX (`sy/` → `.wav`)
- MPEG cutscenes (`dhp/` → transcode to WebM/MP4 once)
- Localization & design data in `bdh/*/…txt` (quests, items, roles, UI copy)
- Small BMPs in `th/`

### Medium (pipeline work)

- **leyiLib2.0** unpacker: parse TOC, classify record types (`lep` maps vs sprite frames), dump images to PNG/WebP
- Map reconstruction from `map_*.lib` + `LeyiMap1.50` semantics (tile size, layers, collision)
- Animation wiring from `Role.txt` frame ID lists → sprite sheets
- Dialogue / quest state machine from Trigger/Dialog tables

### Hard (needs deeper RE of `ComeOn.exe`)

- Combat, skills, AI, crafting (聚宝盆), inventory rules not fully spelled out in loose txt
- Missing mdl/skill/trigger tables inside packs
- `.fol` formats
- Exact rendering (z-order, shadows, skill VFX) and input feel
- Save format

### Not in scope / blockers

- **Never run** packaged crack/Steam emu / adware SFX Setup URLs.
- Full parity ARPG remake is **much larger** than 老夫子大富翁 (board game): expect multi-phase asset RE + systems rewrite.
- Legal/source: user-supplied NAS copy used for personal remake experiment; keep cracked wrappers out of any public deploy.

## Suggested remake shape

1. **Asset pipeline (Phase 2):** Python leyiLib extractor → PNG sheets + JSON manifests; convert `sy`→wav; ffmpeg `dhp`→webm; parse `bdh` TSV → JSON UTF-8.  
2. **Playable vertical slice:** one map + one playable class + basic attack/move + dialog overlay (Canvas 2D or Pixi/WebGL).  
3. **Systems:** combat → inventory/craft → quests → remaining maps.  
4. **Stack:** TypeScript + Vite (Node 22 at `/opt/node22/bin`), static hosting like 老夫子.

## Tools on box

- `tools/rar/unrar` — RAR5 extract  
- `sha256.txt` — hash record  
- Extracted clean tree under `extract/`

## Next steps

1. Reverse **leyiLib2.0** entry formats (sprite + `lep` map) with static analysis / REA on `ComeOn.exe` loaders — dump sample PNGs.  
2. Locate and extract missing `*Mdl.txt` / skill / scene trigger tables from libs.  
3. Document combat & map object model from RE + table cross-refs.  
4. Only then scaffold `web/` remake for a single-map prototype.

## Phase 1 status

**Done:** copy, hash, safe extract, inventory, engine ID, feasibility note.  
**Not started:** full web remake, asset dump pipeline, Ghidra deep dive (queued for Phase 2).


## Phase 2 status (2026-10-09)

**Done**
- Documented `leyiLib2.0` TOC + partial `lep` format in `tools/FORMATS.md`.
- Unpacker `tools/leyilib.py` (`list` / `extract [--png]`).
- Sample dumps under `assets/samples/` (map_ren leps, Spr/ResPlayer raw, nested player leps).
- Searched libs for missing mdl/skill/trigger tables — **not present as plaintext**.
- Remake plan + optional web proof under `web/` (see below).

**Blockers for art-perfect remake**
- `lep` row codec still incomplete (PNGs are RE probes).
- `Spr.lib` / player anim wrappers not fully decoded.
- Missing design tables not recovered yet.

**Next (Phase 3)**
1. Finish `lep` decoder via deeper ComeOn blit RE (Ghidra/REA on row unpack).
2. Decode `Spr` + player frame wrappers → sprite sheets.
3. Recover missing tables from loader or infer from `bdh` + binary.
4. Single-map Canvas vertical slice using real tiles once PNGs are correct.


## Phase 3 status (2026-10-09 18:24 CST)

**lep codec**
- Span layout confirmed: `(y*4, x, nbytes, RGB565[nbytes/2])`, color key `0xF81F`; `nbytes` is **byte** length (not pixel count).
- Map tiles (`map_ren.lib`): decode into **terrain-colored isometric wedges** — continuous texture, no stripes after bbox crop. Height uses max of header hf / nslots / yxn. Still may miss some half-spans → full diamonds incomplete.
- Player nested `lep` / `Spr.lib`: **not** clean walk cycles (wrong canvas / sparse). `Spr` remains a non-lep anim descriptor (hotspots + frame counts) — not fully decoded.
- Tools: `tools/leyilib.py` (`list` / `extract --png --nested`); docs in `tools/FORMATS.md`.

**Samples (attachable PNGs)**
| Path | Notes |
|------|--------|
| `assets/samples/clean/tile_*.png` (+ `_x6`) | Dense bbox wedges from map_ren |
| `assets/samples/clean/final_500.png` / `final_6.png` | Best probe tiles |
| `assets/samples/tileset/` | Contact sheet + more tile probes |
| `assets/samples/game/tile_00..15.png` | 128×64 crops for web slice |
| `assets/samples/game/player.png` | Sparse nested lep (placeholder) |
| `assets/samples/player_sheet/` | Nested ResPlayer frames (walk still poor) |
| `assets/samples/map_ren/` | Earlier map dumps |

**Web vertical slice**
- `web/` — Vite+TS Canvas iso stub, WASD/arrows, Node 22 (`/opt/node22/bin`).
- Loads 16 dumped map tiles + player (fallback stick if needed).
- Built: `web/dist/`.

**NAS deploy**
- **Yes** — `/volume4/web/djfm/` live (HTTP 200 on `index.html` + `game/tile_00.png`). Swap deploy via tar|ssh (same pattern as lfz).

**Blockers**
1. lep still incomplete for full iso diamonds / UI text (half-spans).
2. ResPlayer nested lep + Spr wrappers → no usable walking character sheet yet.
3. Missing design tables (`ActMdl`, `Skill`, `trigger/*`) still unrecovered from libs.
4. ComeOn.exe never run (static RE only); REA MCP schema timeouts → fell back to capstone/hex for blit path.

**Next (Phase 4 candidates)**
1. Deeper ComeOn blit RE for remaining span variants + solid stubs.
2. Spr frame TOC → assemble walk sheet from correct nested leps.
3. Wire Role.txt anim IDs once sheets exist; expand map beyond stub grid.

## Phase 4 status (2026-10-09 18:45 CST)

**lep map diamonds**
- Half-span completion implemented: yxn tip→equator + continuation xn/yxn + sec tip bank.
- Output ~**64×30 full isometric diamonds** (ASCII silhouette verified), dens≈0.53.
- `tools/leyilib.py`: `decode_lep_diamond` + generic fallback; `tools/FORMATS.md` updated.

**Samples that look correct (attachable PNGs)**
| Path | Notes |
|------|--------|
| `assets/samples/phase4/diamond_final.png` (+ `_x4`) | Reference full diamond |
| `assets/samples/tileset/t21.png`, `t36.png`, `t50.png`, … (+ `_x4`) | Re-dumped map diamonds |
| `assets/samples/tileset/contact.png` | 8×4 contact of diamonds |
| `assets/samples/game/tile_00..15.png` | 128×64 centered diamonds for web |
| `assets/samples/player_sheet/walk_sheet_v2.png` | ResPlayer nests — still sparse |
| `assets/samples/game/player.png` | Drawn swordsperson stub (lep player not clean yet) |

**Web vertical slice**
- Larger map 24×18, camera follow, edge + interior collision stubs, WASD/arrows.
- Vite + Node 22 build; diamond tiles loaded on Canvas.

**NAS deploy**
- **Yes** — `/volume4/web/djfm/` live (HTTP 200 on index, tile_00, diamond_final_x4).

**Blockers**
1. ResPlayer/Spr walk cycles still not art-correct (sparse spans); web uses stub character.
2. Sec tip 1px short on some tiles; rare blue edge artifacts.
3. No real collision/map layout data yet (stub blocked cells only).
4. Missing design tables still unrecovered.

## Phase 5 status (2026-10-09 18:55 CST)

**Player / NPC sprites**
- `decode_lep_sprite()` for ResPlayer nested leps: hybrid row xn + raw fallback, empty-row collapse, dual color-key scrub (0xF81F + near-primary blue).
- Exported walk/idle sheets from `ResPlayer1.lib` entry 0 (~26–32 direction frames).
- Still some horizontal striping / incomplete limbs — better than Phase 4 stub, not art-perfect.
- `Spr.lib` remains descriptor-only (no pixel stream).

**Map diamond blue scrub**
- Near-primary blue chroma keyed out in `is_trans_key()`; tileset re-dumped.

**Web**
- Replaced stub with ResPlayer frame + `game/walk/*.png` anim (dir × frame when 8-way).
- Camera follow + collision stubs retained.

**NAS**
- **Yes** — `/volume4/web/djfm/` live (HTTP 200 on index, player, walk frames, walk_sheet).

**Attachable PNGs**
| Path | Notes |
|------|--------|
| `assets/samples/phase5/walk_sheet.png` (+ `_x3`) | Walk contact |
| `assets/samples/phase5/idle.png` (+ `_x4`) | Idle frame |
| `assets/samples/phase5/v3_00.png` … | Per-frame exports |
| `assets/samples/player_sheet/walk_sheet.png` | Same sheet |
| `assets/samples/game/player.png` | Web player frame |
| `assets/samples/tileset/t21.png` etc. | Scrubbed diamonds |

**Blockers**
1. Character lep still not fully RE’d (striping) — need deeper blit loop RE.
2. Spr.lib wiring to ResPlayer frame IDs incomplete.
3. No real map collision data.


## Phase 6 — ResPlayer stripe fix (2026-10-09 Asia/Shanghai)

**Goal:** Eliminate horizontal striping in `decode_lep_sprite`; clear walk/idle poses; re-export; web; NAS; docs. ComeOn.exe never run (static hex/capstone only).

**Root cause found**
- Sec TOC overlaps early slot indices — treating those as pixel rows injected garbage at the top.
- Mid-row pure-blue u16s are span headers (`x`/`nbytes`/`npix`), not chroma. Keying them transparent left **horizontal holes** through the body (Venetian blind). Painting them raw left blue speckles.
- Tip bank last entry is often a non-row footer.

**Fix (`tools/leyilib.py`)**
- Skip/clamp TOC slots; tip without footer.
- Left-aligned raw RGB565 + trailing exact xn when present.
- Inpaint control blues from horizontal neighbors.
- Exact color key for sprite paint (`0xF81F`/`0`/`0xFFFF`).

**Exports**
- `assets/samples/phase6/walk_sheet.png` (+ `_x3`), `idle_sheet.png`, `player_preview_magenta_x5.png`
- `assets/samples/player_sheet/walk_sheet_v6.png`, `idle_sheet_v6.png`, per-frame `walk_XX.png`
- `web/public/game/walk/{00..31}.png`, `{dir}_{frame}.png`, `meta.json` (32 = 8×4)
- `web/public/game/player.png`

**Web / NAS**
- Vite rebuild; deployed `/volume4/web/djfm/` (HTTP 200 on index). Walk frames + sheets updated.

**Attachable PNGs**
- `assets/samples/phase6/walk_sheet_x3.png`
- `assets/samples/phase6/player_preview_magenta_x5.png`
- `assets/samples/phase6/idle_sheet_x3.png`

**Open**
1. Full blit RE still incomplete (some rows may keep minor shear); Spr↔ResPlayer ID wiring open.
2. Near-blue `is_trans_key` remains for map diamonds — do not reuse for sprite paint.

## Phase 7 — authentic map chunk + polish (2026-10-09 Asia/Shanghai)

**Goal:** Compose real scenes from `map_*.lib` (tile indices / layering / height) via ComeOn/LeyiMap static RE + leftover tables; export starting-town-ish chunk; polish remaining blue key dots; redeploy NAS; docs. ComeOn.exe never run.

**Map findings**
- Each `map_*.lib` entry is a full ground-cell **lep diamond**, not an index into a shared tileset. Scene = placing consecutive lib slots on a grid.
- Best layout for human-realm pack: **`map_ren.lib` = 150×123 row-major** cells (~18 450 slots; ~8.3k decode as solid diamonds; adjacent size banding visible on size heatmaps).
- `ComeOn.ini` `BeginScn=0` points at first scene; **ScnInfo.txt / `*.scn` / `*.rmd` are referenced by the exe but not present as loose files** (likely packed via CombineLib / runtime). `.fol` remains encrypted — height/layer tables not recovered yet.
- Composition for the web client: treat lib index `y*150+x` as the tile at grid `(x,y)`. No separate height channel found in the lib TOC; vertical stacking would need Scn/rmd.
- Web PNG export: outside-diamond **black keyed to alpha** so Canvas iso draw does not shutter with opaque rects.
- Exported chunk: origin **(100,40)**, size **20×16**, tile pixels **64×32**. Unique cells 240 decode_ok / 80 miss filled with opaque fallback. Files: `web/public/game/map/t_XXXX.png` + `meta.json`; overview `assets/samples/phase7/map_ren_chunk_iso*.png`.

**Player polish**
- Remaining pure-blue control dots (`r=g=0`, `1≤b≤0x38`) zeroed on walk frames after neighbor inpaint pass; `player_after_polish_x5.png` / walk `00..` show **0 blue_dots**.

**Web**
- `main.ts` loads `game/map/meta.json` + `t_*.png` grid; iso draw 64×32; walk anim + camera retained. Title Phase 7.

**NAS**
- **Yes** — `/volume4/web/djfm/` redeployed (HTTP 200 index + `game/map/meta.json` + walk frames).

**Screenshots / attachable**
| Path | Notes |
|------|--------|
| `assets/samples/phase7/map_ren_chunk_iso.png` (+ `_x2`, `_crop`) | Iso overview of exported chunk |
| `assets/samples/phase7/map_chunk_tileset.png` | Unique cell atlas |
| `assets/samples/phase7/web_view.png` / `web_canvas.png` | Playwright local dist |
| `assets/samples/phase7/player_polished_x5.png` | Blue-dot polish |

**Open**
1. ScnInfo / `.scn` / `.rmd` / fol height+layer still unrecovered — no authentic multi-layer or collision yet.
2. Miss-rate tiles in chunk (empty/undecodeable leps) still stub-filled.
3. Spr↔ResPlayer frame ID wiring still open.

## Phase 8 — fol/ScnInfo RE + expanded map (2026-10-09 Asia/Shanghai)

**Goal:** Static-RE `.fol` / ScnInfo / layers / height; expand web map; wire map packs; Playwright shots; NAS; docs. ComeOn.exe never run.

**fol / ScnInfo findings**
- CombineLib init registers packs `cj` / `slr` / `mb` + ext `fol` (`InitGameFileProperty` string table). Path prefixes `cj\`, `Slr\`, `mb\` sit beside `%s%s.lib` / `leyiLib2.0`.
- On-disk fols: high entropy (~7.94), header `xx000080` — encrypted container. No recovered plaintext ScnInfo / `.scn` / `.rmd` / MapFile inside (XOR probes). Decrypt key not found static-only.
- ScnInfo schema from exe strings: **MapFile, BldFile, ObjFile, PreScn, PortalNum, MapX/Y, ModelID, Type, RadarID, Dir, Logic_***. LeyiMap1.50 + leyibld1.50. Height/object layers still blocked on fol decrypt.
- `BeginScn=0` → heuristic **map_ren** (starting human-realm / 瓦当镇 arc). Full index awaits ScnInfo.
- Detail write-up: `assets/samples/phase8/FOL_SCN_FINDINGS.md`

**Expanded map**
- `map_ren` densest 48×36 band at origin **(61,76)** — decode fill **65.7%** (1136 ok / 592 holes). Miss cells omitted (no green stubs).
- Web default loads this chunk; canvas 1100×640.

**Multi-pack wiring**
- `game/maps/index.json` + previews 24×16 for diyu / snow / nanfang / grave / icecave (nanfang/grave/icecave 100% fill at origin). Toolbar pack switcher in `main.ts`.

**NAS / screenshots**
- Redeploy `/volume4/web/djfm/`.
- Playwright:
  - `assets/samples/phase8/web_view.png` / `web_canvas.png` (ren 48×36)
  - `web_view_nanfang.png` / `web_canvas_nanfang.png`
  - `web_view_icecave.png` / `web_canvas_icecave.png`
  - `map_ren_48x36_iso.png`, `map_ren_filled_150x123.png`, `FOL_SCN_FINDINGS.md`

**Open**
1. fol decrypt / extract ScnInfo still blocked.
2. True height + object layers need ObjFile/BldFile/.rmd.
3. BeginScn↔MapFile mapping still heuristic.

## Phase 9 — fol decrypt CRACKED + scene 1-0s (2026-10-09 Asia/Shanghai)

**Goal:** Recover `.fol` decrypt via static RE; dump ScnInfo/MAP/ONT; wire starting scene; NAS. ComeOn.exe never run.

### fol: **CRACKED**
- TOC: plain[j] = enc[j] - 9*j^3 - key[i] (34 dwords / entry 0x88)
- Payload: plain[j] = enc[j] - key[i] - 99*j^2
- Keys at EOF - 4*(97+count)
- Tool `tools/fol.py`; extract `assets/samples/phase9/fol_extract/`
- Details: `assets/samples/phase9/FOL_SCN_FINDINGS.md`

### Scene wiring
- BeginScn=0 -> ScnInfo **1-0s** -> 1-0s.MAP (Map_Ren.lib 128x128) + 1-0s.ONT objects
- ActMdl spawn (63,59); web chunk 48x36 with object markers
- Multi-pack switcher retained

### NAS / screenshots
- Redeploy `/volume4/web/djfm/`
- Playwright: `assets/samples/phase9/web_view.png`, `web_canvas.png`, `scene_1-0s_iso*.png`

### Open
1. MAP height/aux planes beyond ground u16 grid
2. BNT building blit + ONT ModelID -> Res* sprite link
3. Full-map walk + collision from MAP flags

## Phase 10 — BNT buildings + ONT NPCs on 瓦当镇 (2026-10-09 CST)

**Goal:** Decode BNT/BLD + ONT→Res* sprites; blit onto 1-0s; MAP height/collision; large viewport + culling; ActMdl spawn (63,59); NAS; Playwright; docs. ComeOn.exe never run.

### BLD / BNT
- `leyibld1.50` (`BLD_Ren.Mdl`): record = `u16 type=3` + 32-byte name (null+`0xCD`) + body; **`fid` u16 @ body+2** indexes **`res00.Lib` lep** sprites.
- Hotspot/`w`/`h` fields look Q8-ish / partially opaque — web uses foot-anchor (ignore bad ox/oy).
- `1-0s.BNT` (`LeyiInit1.00`): count u16@0x10 (=362); after name pad @0xC4: **20-byte type=3 placements** `(bid,x,y,…)` + type=4 portal/script records (`go 1-9s`, `SetFlag…`).
- Export: **325** buildings with decoded sprites (`web/public/game/map/props/bld_*.png`, 112 unique fids).

### ONT → sprites
- `ModelID` = Role **角色ID** → **图形ID** → `ResNpc3` (fallback `ResNpc2`) nested-lep first tall frame.
- Town NPCs blitted with EventID labels (铁蛋 `td`, 蔡大婶 `cds`, 张珊 `zs`, …). **11** NPC sprites.

### MAP / collision / viewport
- `1-0s.MAP` 128×128; grid after `\x12HR*` + u32; second plane still `0xFFFF`/`0xCDCD` — **height deferred**.
- Collision: MAP holes + ONT `Logic_*` boxes when `Logic=1`.
- Web: **96×80** tile viewport origin `(15,19)` (~92% fill) + camera culling; `ground_full.png` 4160×2112 @0.5 scale (press **G**); spawn **world (63,59)** / local (48,40).

### Tools / assets
- `tools/phase10_export_scene.py`, `tools/phase10_run_export.py`
- Samples: `assets/samples/phase10/{web_view,web_view_moved,web_view_ground,web_town_spawn,web_town_overview,bld_*,npc_*}.png`

### Web / NAS / screenshots
- Vite Phase 10 client; Playwright/Chrome shots of preview.
- **NAS** `/volume4/web/djfm/` redeployed (HTTP 200 index, meta, ground, props).

### Visual progress
- Town no longer ground+yellow dots only: large wall/rock/house props + labeled NPC sprites at ActMdl spawn.
- Blockers: sprite decode fringe (blue verticals / smear); BLD ox/oy Q8 not fully trusted; BLD index 998/1013 slight drift; height plane unknown; 7.6k tile HTTP load is heavy (culling helps; ground_full fallback).

## Phase 11 — Prop scrub, lazy atlases, BGM + interact (2026-10-09 CST)

**Goal:** Reduce building fringe; fix short NPCs; BGM + attack/talk stub; mitigate 7680-tile load; NAS; shots; docs. ComeOn.exe never run.

### Sprite scrub
- `tools/phase11_scrub.py`: near-black / near-blue chroma → alpha, isolated-pixel kill, **blue-column strip** on L/R edges.
- Re-exported 112 building props under `game/map/props/bld_*.png`.
- BLD hotspots: Q8 + unaligned+1 fallback; clamp bad ox/oy.

### NPC frames
- Pick **best nested** frame (max height/area) from ResNpc*.
- **行囊** graph 661: `ResPlayer2` nested → **24×28** (was broken/short; Spr→res00 wrongly pulled roof art).
- **铁匠** graph 627: best ResNpc3 frame **26×17** (was ~26×3) — still short (lep decode limit on that bank).

### Tile load
- Built **30 atlases** (16×16) in `game/map/chunks/`; client **lazy-loads** in-view chunks only.
- Default ground layer = `ground_full.png`; NAS deploy **drops** `t_*.png` → **~42 MB** (was ~55 MB+ with 7.6k tiles).

### BGM / combat-talk stub
- BGM: ScnInfo sound id **4** → `yy/04_AMAZINGWATER.mp3` → `game/bgm/town.mp3` (loop; **M** mute).
- `game/data/game.json`: Dialog_Public1 lines wired via `trigger/talk/{EventID}.txt`; **E** talk, **Space** slash stub from Skill.ini `剑客_普通攻击*`.

### Web / NAS / shots
- Phase 11 Vite client; Playwright: `assets/samples/phase11/web_{view,dialog,attack,tiles}.png`.
- NAS `/volume4/web/djfm/` HTTP 200 (index, meta, chunks, bgm, data).

### Blockers
- Some building leps still smear internally (codec, not just fringe).
- 铁匠 / a few NPCs remain short frames after best-pick.
- Dialog stub ignores full flag conditions (first matching Public1 lines).
- Attack is VFX-only (no hitbox damage yet).

## Phase 12 — Map diamond blue strips + building smear status (2026-10-09 CST)

**Goal:** Fix residual blue vertical strips on ground (atlas/diamond); dig building lep smear; improve short NPCs; NAS; shots; docs. ComeOn.exe never run.

### Map diamonds (FIXED enough for playable ground)
- Root cause: many `map_ren` leps store **header width=0**; decoder returned `None` → fell back to `decode_lep_sprite` → **(66×29) wedges with pure-blue seams**. Atlases + `ground_full` baked those; client also **double-drew** ground_full + atlases.
- Fix in `tools/leyilib.py` `decode_lep_diamond`:
  - `width==0` → treat as **64**
  - re-center right-anchored spans into fixed **64×32** cell (no bbox crop)
  - scrub pure control-blue; 1px alpha dilate for hairline seams
- Client (`web/src/main.ts`): skip atlas tile draw when `ground_full` is on (**G** still toggles).
- Rebuild: `ground_full.png`, viewport `t_*.png`, 30 atlases via `tools/phase12_run_export.py`.
- Metrics: tile diamond decode **~7056/7680** in viewport (was mostly sprite fallback); screenshot pure-blue **613→45**; regular blue strips **~25→~8** (leftover mostly on building props).

### Building lep smear — UNFIXED
- Static probes (xn / raw / yxn / 部件 / Spr alt) change heuristics but visuals stay shredded for dirty fids.
- ComeOn building blit path not recovered (REA open blocked as “run”; Capstone around `lep` only hits constructor / F81F inits).
- Visual TODO: `assets/samples/phase12/BUILDING_SMEAR_TODO.md` (worst fids e.g. 850, 690, 491, 562, 448, 227…).
- Before/after props copied under `assets/samples/phase12/bld_*_{before,after}.png` (same decode — no visual win).

### NPCs
- Re-picked nested frames across ResNpc*/ResPlayer2.
- Slight height gains on several (e.g. 618, 619, 630, 629).
- **铁匠 `npc_627` still 26×17** — ResNpc3 bank limit; needs deeper RE.

### Web / NAS / shots
- Phase 12 Vite client; Playwright: `assets/samples/phase12/web_view{,_before,_moved,_atlases}.png`, `web_dialog.png`, `ground_spawn_after.png`.
- NAS `/volume4/web/djfm/` lean redeploy (~**42 MB**, no `t_*.png`) HTTP 200 (index, meta, ground, chunks).



### Map assembly fix (同日续) — 地图格子读偏了
**根因（给用户）：** `1-0s.MAP` 在 `\x12HR*` 标记后还有 **4 字节 u32**，真正的地砖索引表从 **标记+8** 才开始。旧解析从 +4 起读，把 u32 当成了两格地砖，整张 128×128 图的 `map_ren` 索引整体错位约 2 格。建筑/NPC 用 BNT 真实坐标，地面却错位，所以路和墙对不上 —— **不是轴翻转，是格子读偏了。**

**公式校验：** 修正后 `grid[y][x] == y*128 + x + 1`（16384/16384 命中）；`map_ren` 是「每格一颗 lep 钻石」，不是共享图块集。

**其它：** iso 步距改为原生钻石 **64×30**（高曾误用 32 造成细缝）。建筑 lep 内部糊仍未解（见 `BUILDING_SMEAR_TODO.md`）。

**产物：** 重导 `ground_full` + tiles + atlases；截图 `web_view_assembly_before.png` / `web_view_assembly_after.png` / `web_view_town_walls.png`；NAS 42MB 已更。

### Blockers / next
1. Building res00 blit codec (true ComeOn static RE of row unpack for type 06/08 tags).
2. 铁匠 / short ResNpc frames.
3. Dialog flag graph + HP HUD (deferred this pass — ground regression was priority).
4. Remaining iso hairline dashes on ground (minor vs prior blue columns).


## Phase XP-compare (2026-10-10)
See assets/samples/xp_compare/COMPARE_NOTES.md — Wine original 瓦当镇 shots captured; ReactOS 0.4.16 Live up; no XP ISO. Web map: building smear remains main gap vs original.


## Phase 12 — building smear vs Wine xp_compare (2026-10-10 CST)

**Priority:** match Wine 瓦当镇 shots in `assets/samples/xp_compare/`.

### Done
- Ground-truth pack already present (`orig_wadang/*`, `COMPARE_NOTES.md`).
- New `decode_lep_building`: strip mid-row control triples that became vertical **blue** seams; re-export 112 town buildings; blue ratio ~**0.006 → 0.0003**.
- Before/after: `assets/samples/phase12/before_bld_*.png`, `after3_bld_*.png`, `ba3_bld_*.png`, `COMPARE_wine_vs_bld_fix.png`.
- NAS lean redeploy `/volume4/web/djfm/` (HTTP 200).

### Still blocked
- **Structural** vertical/horizontal smear on large buildings (esp. fid **445**, **385**) — scrubbing blue does not restore Wine-clean roofs/walls. Building blit ≠ map diamond `yxn`; ComeOn.exe RE forbidden; XP ISO not yet provided.
- See `assets/samples/phase12/BUILDING_SMEAR_TODO.md`.


## Phase 12b — res00 building lep codec CRACKED (2026-10-10 CST)

- Building/prop leps are a **row RLE**, not raw rows / diamond yxn: after the sec table, each row is
  `skip_bytes ( count_bytes  RGB565[count/2]  skip_bytes )*`, row ends when x == W (px). W is not in the header;
  found by searching W such that the stream is consumed **exactly** (112/112 town fids parse 100% of bytes).
- The old "control triples" / blue seams were just skip/count words mis-painted as pixels → smear.
- `tools/bld_rle.py` (`best_parse`, `decode`), used first by `phase10_export_scene.decode_sprite` (falls back to old decoders).
- Re-exported all 112 `bld_*.png`, meta sw/sh updated, NAS redeployed.
- Compare: `assets/samples/phase12/COMPARE_wine_before_after_rle.png` (Wine | before | after), `rle_*.png`.
- Remaining: building **anchor/placement & layering** (some props, e.g. big cliff/walls, sit offset vs Wine); per-sprite hotspot likely in header/Spr.lib — TODO. Weather/HUD still absent.

## Phase 13 — 瓦当镇 building placement / hotspots / layering (2026-10-10)

**Root cause found:** buildings were drawn with the wrong *images* and wrong anchors.
- `BLD_*.Mdl` record = `03 00` + name[32] + u16 `fa` + **u16 bld_id** (this is what BNT type-3 `bid` references — all 352/352 placements resolve) + … + bbox `i32 ox,oy,w,h` (plain pixels, *not* Q8) + footprint/block grid + **parts list**.
- Each part: marker `b2 bf bc fe 00 cd cd cd 00` | **u16 res00 index** | u16 flags | **i32 ox | i32 oy**. 1432 parts in BLD_Ren. The old exporter used the u16 after `fa` as the res00 index → wrong pictures (e.g. "PAILOU" showed a grass tuft; real arch is res00 532; pavilion TEXIAOWU_16A is res00 4845).
- Hotspot: **part top-left = iso(cell) + (ox, oy)**, iso step 32×16 (64×32 diamond). Verified vs Wine: PAILOU01C (70,55) / 01D (74,55) Δcell (4,0) ↔ Δscreen (128,64) in `01_gate_rain.png`; pavilion/tower/tree/statue/corpses all land on Wine pixels in fresh shot `10_pavilion_tower.png`.
- Ground `ground_full.png` is exported at half pitch (32×16); client now scales it ×2 (nearest) so ground and buildings share the same 64×32 grid (it was drawn 1:1 → half-size ground under full-size buildings).
- Draw order: z = cell x+y of the placement anchor (parts in record order), same key as player/NPCs.

**Code:** `tools/phase13_bld_place.py` (re-exports `props/res_<rid>.png` via bld_rle, rewrites `meta.buildings[] = {x,y,bid,name,parts[{file,ox,oy,w,h}]}`), `tools/phase13_compare.py` (offline compose at a Wine camera), `web/src/main.ts` (parts draw, ground ×2, `?at=x,y` world-cell start). 327 placements / 144 images. NAS `/volume4/web/djfm/` redeployed (HTTP 200).

**Compare images** (`assets/samples/phase13/`): `wine_vs_model_arch.png`, `wine_vs_model_pavilion_ground.png`, `wine_vs_model_pavilion.png` (left Wine, right web model at same camera); live client `web_spawn.png`, `web_arch.png`, `web_pavilion.png`.

**Still off:** shadow parts (e.g. under the pavilion) are drawn opaque/light instead of darkened-translucent (flag field likely marks shadow/blend — not decoded); Wine global night/rain tint not applied; some small rubble/rocks seen in Wine are not BNT buildings (likely ONT/other layer) and are missing; depth sort is by anchor cell only — large multi-cell buildings vs player may mis-layer at edges (footprint grid in record not used yet). Old fids 445/385/386 were mis-mapped ids; they are no longer meaningful.

## Phase 14 — shadows / tint+rain / debris layer / footprint layering (2026-10-10 11:57 UTC+8, logged)

- **Shadow parts:** per-part u16 flags are only 0x10 / 0xD0 (1270 / 162). Neither one marks shadows. The "shadow" under the pavilion (res00 4849) is pre-darkened grass art drawn opaque, as in Wine. It looked too light only because the global scene tint was missing (below). There is no separate translucent shadow pass.
- **Night/rain tint:** a per-channel linear fit of Wine vs our render over building pixels gives approximately rgb·(0.63,0.63,0.80)+(8,9,10) (pavilion and arch shots agree within ±0.06). The client applies it as a multiply+lighter full-screen pass after the world draw. Rain streaks follow ScnInfo 1-0s BigRain=15/SmallRain=20. Toggle with `?tint=0` / `?rain=0`.
- **Debris layer:** found in the MAP file, not the ONT. The cell record is 5×u16 {ground_tid, overlay_tid, flags FF00/FF01, level 0–3, CDCD}. overlay_tid (1372 cells) indexes map_ren decals (pebbles/rubble/grass). `tools/phase14_ground_deco.py` composes them onto `review/ground_after_full.png` → `ground_full.png`. Full-diamond overlays and their dark (<48 luma) pixels are dropped because drawn opaque they showed up as dark stripes that Wine does not show; how Wine blends them is still unknown. The ONT Type-13 "zs/zhs" objects decode empty (old npc_628/629) and are not the debris.
- **Walk grid:** the cell flag is FF01 = walkable, FF00 = blocked (the arch pillars at x=70/74 are blocked and the gap between them is walkable). Exported as `meta.walk_grid`; the client now uses it instead of blocked_sample.
- **Footprint layering:** each BLD record has a footprint grid (u16 gw,gh @+79, e.g. pavilion 12×12, PAILOU 1×4). Buildings still sort by anchor cell (x+y), with one extra rule for the player: inside the footprint rectangle [x−gw..x]×[y−gh..y] the building draws over the player; past the anchor on either axis the player draws on top. Not verified against Wine with the player behind a big building.
- Compare images: `assets/samples/phase14/wine_vs_web_arch.png`, `wine_vs_web_pavilion.png` (left Wine, right web model with tint).
- **NAS deploy FAILED** at this milestone: the ssh SOCKS proxy to 100.100.214.12 returns "socks fail" (tried 3×). NAS still serves the Phase 13 build.

## Phase 15 — original HUD, HP/MP orbs, combat (2026-10-10 11:57 UTC+8, logged)

- HUD art comes from `ResJM.Lib.chs` (2183 RLE leps, decoded with bld_rle). Entries matched pixel-exact (score 1.0) against Wine: bar `1478` (800×110, top y=490), HP orb `417` at (11,+20), MP orb `415` at (41,+18), weapon icon `1910` at (156,+61), and right menu buttons `515–520`. Saved as `web/public/game/hud/jm_*.png`.
- `web/src/hud.ts`: draws the bar centred at the bottom; the orbs drain from the top by HP/MP ratio; there is an EXP strip and an HP/MP/Lv text line.
- Combat (our own placeholder model, not decoded from the original game): melee arc on Space (range 1.8, ±70°, 14–22 dmg), foes chase within 7 cells, hit 6–10 every 1.3 s, die and respawn after 8 s, +25 EXP per kill, level-up adds +20 maxHP. Player HP and MP regenerate; at 0 HP the player respawns at spawn. 瓦当镇 has no hostile ONT entries, so foes appear only with `?foe=N` (placeholder ellipse sprites).
- Compare images: `assets/samples/phase15/wine_vs_web_hud.png` (top Wine, bottom web), `web_combat.png`, `web_hud_pavilion.png`.
- Missing: potion and skill slot icons, the orange stamina bar, the Q skill icon, the minimap, real enemy sprites and stats (Role.txt / ResNpc), and damage formulas from the original game.
- **NAS deploy FAILED** (same SOCKS proxy failure). Build is ready in `web/dist`.

## Phase 16a — real monsters + first field map 1-2s (2026-10-10 14:10 UTC+8)

- **Monster IDs:** the Type-13 `200xx` entries in ONT are beasties and moving props (BeastieMdl: 20006 = 蜻蜓 dragonfly, 20009 = 老鼠 rat, 20032–37 = SPR_BLD_MOVEBLD_*), not enemies. Real monsters are ONT entries whose ModelID is a Role.txt id that also has a RoleQuest bestiary entry. In ScnInfo order: 1-1s has one (拾遗小妖), and **1-2s is the first field map with combat monsters**: 持刀鬼兵 (190) and 2× 持枪鬼兵 (191). After that, 1-9s/1-10s have 24–32 each.
- **Stats:** from RolePrivate.txt (lowest level row): 鬼兵 lv3 HP300/250, AT140, DF37, EXP50, speed 8, sight 6. Player = 男主角 (role 4) lv1: HP70, AT40, DF30.
- **Sprites:** ResNpc3 holds monsters as 12-entry action sets (8 directions × n frames, decoded with bld_rle). An entry flagged `0505` in the lep header is a shadow layer (all pixels 0). Sets 522–606 have the same frame-count pattern; 594 is a complete spear ghost-soldier body, while 522/546/570 are paper-doll layers (body, head/arm, weapon). Spr.lib descriptors (`tools/spr.py`) list per-action, per-direction frames as `(frame_no<<24)|(lib 0x50<<16)|res` plus ox/oy, but the res→ResNpc3 offset is not constant (603→+34 fits, 602 does not). So **both 鬼兵 types use set 594** until the paper-doll layers can be composited.
- **Damage:** placeholder formula `AT·100/(100+DF)/4 ±10%`; the original formula is not decoded.
- **Exporter:** `tools/scene_export.py <scene>` → `web/public/game/maps/<scene>/` with ground + overlay decals, BLD parts, walk grid, monsters and frame sheets. 1-2s: 256×256, 458 buildings, 3 monsters, spawn (115,230). ActMdl has no entry for 1-2s, so spawn is computed next to the monsters.
- **Client:** `?pack=1-2s` (also a toolbar button). Monsters animate idle/walk/attack/hurt/death by direction, show name and HP bar, chase within sight, and respawn 12 s after death.
- **Shots:** `assets/samples/phase16/web_1-2s_monsters.png`, `web_1-2s_combat.png`. Not yet compared with Wine (1-2s not reached in Wine).
- **Deploy:** GitHub Pages commit ced17c6 → https://liuzhuoling2011.github.io/djfm-sgcs/ (1-2s meta HTTP 200). NAS deploy OK.

## Phase 16b — HUD: stamina, potions, skills, Q, minimap (2026-10-10 14:14 UTC+8)

- Matched against the Wine HUD (`/tmp/w7.png` 800×600) using masked pixel search over ResJM.Lib.chs:
  - **Potions:** JM 92 (red) is pixel-exact at (258,572), error 0.1. JM 90 (blue) is exact at (306,572)/(330,572). Slot pitch is 24 px, with yellow key digits 1–4.
  - **Q skill icon:** JM 63 at (606,551), error 3.7 (the leftover error is the 'Q' text overlay).
  - **Minimap frame:** JM 1549 (137×133) at (663,0), error 4.7. The scene-name strip sits underneath.
  - **Orange stamina bar:** spans x255–388, y555–561. No ResJM entry matched (best error 45), so the bar strip is **cropped from Wine** as `hud/stamina_wine.png` and drains from the right. Shift = run (speed 8), which costs stamina.
- **Gameplay:** keys 1–4 drink potions (red +40 HP, blue +30 MP; counts 5/5/3/3). Q = whirl attack costing 10 MP that hits everything within 2.5 cells. F1/F2 labels are shown; the skills are not implemented.
- **Minimap:** renders ground_full at 1/8 world scale around the player, with dots: green = player, red = monsters, blue = NPCs. **It does not draw buildings yet**, so it looks plainer than Wine's, and the Wine zoom level is estimated.
- **Compare images:** `assets/samples/phase16/wine_vs_web_hud.png`, `wine_vs_web_hud_zoom.png` (top: Wine bar; middle: web bar; bottom: minimaps), `web_hud_800.png`, `web_1-2s_hud.png`.
- **Deploy:** Pages 087ef0a; NAS OK.

## Phase 16c — MAP overlay (col1) blending (2026-10-10 14:16 UTC+8)

- **Method:** `tools/phase16_overlay_blend.py` renders col0 (ground) and col1 (overlay) at full 64×32 pitch at the calibrated Wine cameras (01_gate_rain, 10_pavilion_tower), applies the measured night tint, and scores each blend mode by median absolute error against Wine over the ~105k pixels covered by overlays (HUD excluded). Results are in `assets/samples/phase16/overlay_blend.json`.
  | mode | gate | pavilion |
  |---|---|---|
  | ground only | 15.7 | 14.6 |
  | **alpha-over (colour key 0xF81F → transparent)** | **6.45** | **6.45** |
  | Phase 14 black-key (drop <48) | 7.49 | 6.59 |
  | 50 % | 11.6 | 10.6 |
  | darken / lighten | 11.4 / 10.5 | 10.4 / 12.5 |
  | multiply | 37.8 | 30.0 |
  | additive | 52.8 | 61.8 |
- Split by tile coverage: full-diamond overlays improve from 14.6→7.5 and 11.2→4.8 when drawn opaque, so **the Phase 14 rule that skipped coverage ≥45 % tiles was wrong**.
- **Conclusion:** overlay tiles are a plain colour-keyed opaque blit over the ground diamond, with no translucency or special blend mode and no per-tile flag needed. phase14_ground_deco.py and scene_export.py now draw every col1 tile that way. 瓦当镇 now shows Wine's dirt paths and worn patches.
- **Compare images:** `assets/samples/phase16/wine_vs_model_pavilion_overlay.png`, `wine_vs_model_gate_overlay.png`, `overlay_blend_01_gate_rain.png`, `overlay_blend_10_pavilion_tower.png` (Wine | ground only | best mode).

## Phase 17a — git repo + map transitions 1-0s ↔ 1-1s ↔ 1-2s (2026-10-10 14:23 UTC+8)

- **git:** `git init` in /workspace/djfm-sgcs. `.gitignore` excludes extract/, *.exe, *.lib/*.Lib/*.fol, fol_extract/, node_modules, web/dist and t_*.png. First commit 15c1b48.
- **Exits:** taken from the real BNT trigger records (`go <scene>` scripts), now exported by scene_export.py:
  - 1-0s (71,6)/(72,12) → 1-1s
  - 1-1s (128,241–248) → 1-0s; (213,90–97) → 1-2s
  - 1-2s (123–129,239–246) → 1-1s; (125–133,8–15) → 1-3s (not exported yet)
- **Arrival rule:** you arrive at the centroid of the destination map's own `go <previous scene>` triggers, stepped toward the map centre to the first walkable cell. The trigger radius is 3.2 cells. A trigger only re-arms after you leave every trigger, which stops bounce-back loops.
- **Fixes:** 1-0s was cropped to a 96×80 window starting at (15,19), which made the north exit unreachable; it is now the full 128×128. Fixed a spawn-search bug where `break` only left the inner loop and teleported the player far away (for example `?at=75,9` → (52,111)).
- **Tested** (headless; `window.__djfm` shows the scene and position):
  - 1-0s → 1-1s (arrive at 128,241)
  - 1-1s → 1-2s (127,238)
  - 1-2s → 1-1s (209,95)
- **Shots:** `assets/samples/phase17/warp_*.png`.

## Phase 17b — minimap with buildings (2026-10-10 14:25 UTC+8)

- `tools/phase17_minimap.py`: for each map, draws ground_full plus every BLD part at half pitch, in depth order, then halves the result (16×8 px per cell). Output is `minimap.png` and `meta.minimap`. Sizes: 1-0s 2080×1056, 1-1s/1-2s 4128×2080.
- The HUD minimap now samples this image at 0.75 (about 1/5.3 world scale, eyeballed to match Wine's zoom), with dots for the player, monsters and NPCs.
- **Compare:** `assets/samples/phase17/wine_vs_web_minimap.png` (left Wine, right web).

## Phase 17c — real player stats, quest gate, walking town→1-1s, Wine attempt (2026-10-10 14:55 UTC+8)

- **Damage formula:** not present in any data table. I searched every mb/*.txt and *.ini file plus mb/player/* for 伤害/公式/攻击/防御/命中. define.ini only defines poison/fire DoT (MaxHp/90 per second and MaxMp/80 per second). The formula is compiled into ComeOn.exe and is **not decoded**. The client now uses AT − DF/2 ±10% (an assumption, labelled in hud.ts).
- **Real data now used:**
  - mb/player/Init.txt 男主角: AT40 (+4/lv), DF30 (+4), HP800 (+80), HP regen 1.4/s, MP36, MP regen 1.2/s, Stamina 80 (regen 3/s, drain 10/s while running).
  - Starting items 4×2, 8×2, 63×5, 62×2. PropMdl: 小血瓶 id4 "Atb HP 400", 小气瓶 id8 "Atb MP 18". The potion slots now use these values.
  - Init.txt also has DF4..DF0 = 100/100/80/70/60, meaning not yet known.
- **Quest gate:** 瓦当镇's walk flags block all of row y=24 between the town and the north exit (71,6). A `Quest` trigger sits at (71,24), so in the original the gate opens through story progress. The web build opens x70–72 of that row (`meta.quest_gate`). A headless keyboard walk following a BFS path now goes from the act spawn (71,62) to 1-1s, arriving at (128,241): `assets/samples/phase17/walk_town_to_1-1s.png`. 1-1s→1-2s is connected in the walk grid (BFS verified).
- **Wine 1-2s capture: blocked.**
  - Save edits don't work: loading 剑客/大刀客 always replays the act-1 intro and respawns at (71,62). Patching the save's scene/position u32s at +264/+268 had no effect (the game autosaves back to 0/(71,62)).
  - Walking to the exit in Wine is also impossible, because the north gate is still story-locked (`wine_north_blocked.png`). Reaching 1-2s needs the act-1 quest chain played in Wine.
  - Original saves were restored from `assets/samples/phase17/save_backup_*.001`.
- **Save format notes:** `.001` holds the player paper-doll string `CA_001_001_031*HD_…*TK_…` (layers CA/HD/JQ/LA/LE/RA/RE/RH/TK), float stats AT/DF/HP/MP/Stamina at +188.., and position i32 at +268.

## Phase 17d — stamina asset search, saber ghost-soldier (2026-10-10 15:04 UTC+8)

- **Stamina bar: not found in any library.** I texture-matched a 38×4 interior strip of the Wine bar against every entry of ResJM.Lib.chs/.cht, ResPrior.lib and ResEx01.Lib, using both bld_rle and the sprite decoder, at every offset. I also matched vertical colour profiles against all ResJM entries 5–9 px tall. The best mean error was 29 (an exact match is under 1), and PixelGame.lib is not leyiLib2.0. The bar is most likely drawn in code (a gradient or palette fill), so the Wine-sampled strip stays (`hud/stamina_wine.png`).
- **Saber ghost-soldier (持刀鬼兵): still not assembled.**
  - Layers identified: ResNpc3 sets 522 (body+legs), 546 (arm), 570 (curved saber), each 12 actions × 8 directions. The shadow sets 534/558 are all-zero 0505 leps.
  - The per-frame lep header after `b8` holds two (u32, u32) pairs. When the first value is 0, the second equals the decoded W (or H), e.g. 546 f10: (0,17),(0,24) = 17×24. Otherwise the pair seems to be a packed offset plus size that I haven't cracked (594 f0: (1326,6),(667,22) for a 108×51 frame), so the layer registration offsets are unknown.
  - bld_rle also guesses the wrong width on some tiny layer frames (570 f0 → 24×1).
  - Without those offsets, any composite would be a guess, so 190 still uses the spear body (set 594). Next step: decode the header pair (likely x/y origin relative to the role foot) or use the Spr.lib ox/oy tables (`tools/spr.py`) once their res→ResNpc3 mapping is known.

## Phase 18a — act-1 map chain 1-3s / 1-3as (2026-10-10 15:11 UTC+8)

- Exported `1-3s` (256², Map_Ren, 136 bld) and `1-3as` (192², Map_Diyu, 274 bld) via scene_export.py. Added to maps/index.json. Minimap PNGs generated.
- Go-trigger chain now playable: **1-0s ↔ 1-1s ↔ 1-2s ↔ 1-3s ↔ 1-3as**.
- The 1-3s→1-3as and return doors sit on MAP cells flagged non-walkable (scripted entrances). Opened short corridors in walk_grid (`meta.scripted_paths`) so the remake can enter; marked as remake-side.
- Trigger radius 4.5; standing on a go-trigger no longer gets walkable-nudged away.
- Shots: `assets/samples/phase18/at_1-3as.png`, `back_1-3s.png`, `at_1-2s.png`, `at_1-3s.png`.

## Phase 18b — NPC talk + quest gate (2026-10-10 15:11 UTC+8)

- Exported `web/public/game/dialog/`: Dialog_Public1/2/3, 65 talk scripts, NPC names from trigger/flag.txt.
- New `web/src/dialog.ts`: flag table, IsFlag cond (op1 = flag&lt;v, op2 = flag≥v), SetFlag / SetExitTextID, auto + choice menus.
- **E near NPC** runs talk by ONT EventID. Talking to **沈云 (sy)** runs the auto line → dialog 26, `SetFlag sy1 1`, `SetExitTextID 1-1s -1`.
- Town north exit: locked with exitText 308 while sy1&lt;1 (dialog 308 missing from Public1 → fallback copy「前方的路还不能走——先去和沈云说说吧。」). Gate cells (70–72,24) stay blocked until unlock.
- **F9** debug unlock mirrors the sy talk result.
- Verified: talk sets sy1=1; locked exit shows the fallback; F9 then walk/warp reaches 1-1s.
- Shots: `talk_sy.png`, `exit_locked.png`, `unlock_to_1-1s.png`.

## Phase 18c — damage/stamina RE (2026-10-10 15:11 UTC+8)

- Strings scan of ComeOn.exe found `ChangeObjHp`, `ATB HP`, `ATB MAXHP`, `ATB MP`, `ATB HPRESUME`, `PoisonRate` / `define.ini` (matches known DoT). No `Stamina` ASCII string; no 耐力 hits in a quick GBK pass.
- Opened the PE in REA successfully; `search_strings` then failed with an MCP schema error (`result`/`evidence_id` required), so no xrefs or decompile of the damage path.
- **Still blocked:** original damage formula and stamina-bar draw. Placeholders remain (AT−DF/2 ±10%; Wine-cropped stamina strip).

## Phase 19a — Player + town NPC sprites (2026-10-10 Asia/Shanghai)

**Priority change:** fix ResPlayer / town NPC models before inventory/skills.

### Player (ResPlayer paper-doll composite)
- Legs = `ResPlayer1.lib[0]` (32 = 8×4 walk), body = `[256]` (shirtless CA), attack body ≈ `[260]`.
- Foot-aligned composite → `web/public/game/player/{walk,idle,attack}/{dir}_{frame}.png` + HD sheet.
- Client (`main.ts`) loads 8-dir walk/idle/attack; no more Phase-6 striped stub as primary.
- Spr.lib 901 / full HD+RH+TK part map still open (heads/weapons approximate; saber layers still blocked).

### Town NPCs (瓦当镇 ONT)
- Role.graph entries often RLE-empty (shadow-only); used visual ResNpc3 matches:
  - sy→1008, zs→1014, cjg→1007, sws→624, tj→630, gbw→625, td→618, cds→1112, bq/zhs→620, xn→bag-ish ResNpc2.
- Exported to `web/public/game/map/props/npc_*.png` + `map/npcs/{ev}_{dir}.png`; meta `file`/`npc_dirs` wired; NPCs face player.
- Script: `tools/phase19_sprites.py`.

### Samples
- `assets/samples/phase19/player_sheet(_hd).png`, `town_npcs.png`, `web_town.png`, `wine_town*.png`, `compare_wine_web.png`.

### Deploy
- Rebuild + Pages + NAS after this section (see commit).

### Still blocked / paused
- Full Spr↔ResPlayer part table (CA/HD/RH/TK exact IDs).
- Saber ghost multi-layer (lep header offsets).
- Inventory / F1–F2 skills / further dialog / more act-1 maps (paused per steering).

## Phase 19b — SprRole paper-doll polish (2026-10-10 Asia/Shanghai)

**Goal:** Crack Spr↔part map so player/NPC sprites match Wine placement.

### SprRole.h breakthrough
- `slr/SprRole.h` maps `SPR_ROLE_{role}_{PART}_{var}_001` → **Spr.lib index**.
- Player 901: `CA→34`, `HD→112`, `TK→114`, `RH_005→116` (starting saber).
- Each Spr part entry ≈512 slots; `res = ResPlayer1 base+dir` (CA 0–7, HD 128–135, TK 256–263, RH 384–391); `ox/oy` = foot hotspot.
- Composite order (bitmap): legs(CA) → torso(TK) → head(HD) → weapon(RH) at shared hotspot (64,100).

### Town NPCs
- `SPR_ROLE_{graph}_TK_001_001` → Spr (e.g. 623→1619) → ResExNpc/ResNpc frames + ox/oy.
- Civilian fallbacks when SprRole hits combat/partial art: sy→n3:1008, zs→1014, cjg→1007, td→618, cds→619, etc.
- Client draws NPCs with `ox/oy` foot anchors from SprRole.

### Samples
- `assets/samples/phase19b/player_sheet(_hd).png`, `town_npcs.png`
- `compare_player_wine_web.png`, `compare_npcs.png`

### Deploy
- Pages + NAS after this section.

### Still open
- Per-frame `n` sync for attack cycles; RH fine gaps on some dirs; inventory/skills still paused until sprites solid.

## Phase 19c — Inventory / skills / dialog (2026-10-10 Asia/Shanghai)

**Resume** after sprite OK confirmation.

### Inventory & equipment
- `Init.txt` loadout: 金钱400；小血瓶×2、小气瓶×2、飞蝗石×5、指南珠×2；装备 paper-doll `CA/HD/TK/RH_002`.
- Data: `web/public/game/data/{init,props,skills,equip901}.json`.
- `web/src/inventory.ts`: bag (I), potion keys 1/3 from PropMdl heals, 5=飞蝗石, 6=指南珠回出生点.
- HUD shows 金 / 兵器名 / F1·F2 skill names.
- Blacksmith: talk 买卖物品 → `ShowJM …86` shop; 镶嵌 → embed stub (+AT, 200金). `AddWeaponNum` / `Acquire` / `Miss` / `IsProp` wired in dialog.

### Skills F1 / F2 (Skill.txt)
- 初始左手=6 **扫叶**（耗气9，环攻；intro Text 133）.
- 初始右手=35 **疾电**（耗气18，加攻×2，远距；intro Text 138）.
- F1 whirl AOE；F2 frontal heavy；Q retained as prior whirl.

### Dialog after 沈云
- `sy.txt` menu 交谈→自我介绍/关于爷爷 from Dialog_Public1 29–32；gate unlock unchanged.
- Result cmds: Acquire/Miss/AddWeaponNum/ShowJM；IsProp for 蜀水→铁匠强化链.

### Samples / deploy
- `assets/samples/phase19c/web_town_inv.png`
- Pages + NAS this milestone.

### Blocked / deferred
- Full JM shop/embed UI art (ShowJM panels); gem socket rules; Skill.ini frame VFX; act-1 maps beyond dialog; damage formula REA.

## Phase 20 — JM panels, skill VFX, 蜀水 chain, contiguous maps (2026-10-10)

### 1. ShowJM shop / embed panel art
- JMMDL: `JM_DEAL` id86 anim **834**, `JM_Enchase` id62 anim **814**, `JM_DAOJU` id20 anim `9*900`, `JM_Attribute` id92 anim **877**.
- **Blocker:** ResJM entries 813/814/834/835/836/877/900 are tiny empty LEPs (w≈4–6, no opaque pixels) — not usable panel art. Close/button anims 10–12 are ~20×23 glyphs only.
- **Fallback (size-matched):** scanned ResJM for 180–420px stone UI frames:
  - `panel_1550` → shop/DEAL list frame
  - `panel_591` → equip/embed (crossed swords + armor)
  - `panel_625` → bag/grid
- Wired in client: `ShowJM 20|86` → shop frame, `ShowJM 20|62|92` → embed frame, `I` → bag frame (`web/src/style.css` `.jm-frame`, `renderInv` in `main.ts`). Assets: `web/public/game/hud/panels/`.

### 2. Skill attack VFX (F1/F2/Q)
- Skill.ini / Skill.gop: 扫叶 chain `77→46→71` (base 33), 疾电 `482` (base 265). These are **behavior action IDs**, not ResJM/ResEx sprite indices (those IDs decode as map props / paper-doll fragments).
- New `web/src/fx.ts`: canvas overlays — leaf whirl (扫叶), lightning bolts (疾电), cyclone (Q), slash arc (Space). Spawned from F1/F2/Q/Space handlers.
- **Blocker:** true particle/effect lib map for skill overlays not cracked yet.

### 3. Act-1 dialog / 蜀水 past 沈云 (scripts only)
- After `sy1=1` (沈云 / F9): town menus already expose 铁匠 choices including「关于蜀水」(public1 58/59), 蔡大婶→铁蛋 (cds/td), 翠娟/泊祁/沈万山 further flags.
- **蜀水 item (prop 120):** scene `1-6s.txt` `SetPropToObj shushui` when `xss<1` and no prop 120. BNT trigger at **(100,32)** script `shushui`.
- Client: E near `shushui` acquires 蜀水 + sets `xss=1`; blue marker on map until taken. Hand-in to 铁匠 still requires real flag `sy1≥99` (`tj` talk id2/3) — not invented.
- Debug: **Shift+F9** grants 蜀水 for UI testing only.

### 4. Contiguous go-trigger maps exported
New under `web/public/game/maps/` (also in `index.json`):
| scene | name | notes |
|-------|------|-------|
| 1-4s | 隐峰山 | go↔1-0s, 2 NPCs |
| 1-5s | 宣风林地 | →1-7s |
| 1-6s | 堰兵冢 | 蜀水, →1-7s |
| 1-7s | 冰火沼 | |
| 1-7as | | ↔1-0s,1-7s |
| 1-8s | 九天池 | 74 NPCs |
| 1-9s | 炎炀关 | ↔1-0s,1-10s, 25 NPCs |

Still not exported: 1-10s / 1-10a* / 1-11s (next after 炎炀关).

### 5. Damage formula REA
- `user-rea` `search_strings` still fails MCP output schema (`result`/`evidence_id` required). Placeholder remains: `AT − DF/2 ±10%` in `hud.ts`.

### Samples
- `assets/samples/phase20/jm_panels.png` — raw ResJM frames
- `assets/samples/phase20/web_jm_ui.png` — wired shop/embed/bag UI
- `assets/samples/phase20/web_town.png` — ren with new map buttons
- `assets/samples/phase20/web_1-4s.png`, `web_1-6s.png`, `maps_new.png`

### Deploy
- Source `eb5a9f7`, Pages `f4c5ca2`, NAS_OK.


## Phase 21 — Remaining act-1 maps + 蜀水 sy1 chain (2026-10-10)

### 1. Maps exported & wired
Added to `web/public/game/maps/` + `index.json` (go-transitions via existing warp):
| scene | label | notes |
|-------|-------|-------|
| 1-10s | 紫凤坪 | ↔1-9s, 1-10a1s, 1-11s |
| 1-10a1s…a6s | 连珠塔层 | chain a1↔…↔a6 |
| 1-11s | 气凝洞 | ↔1-10s |
| sws | 沈万山遇袭 | dialog `go sws` target |

Samples: `assets/samples/phase21/maps_act1_rest.png`, `web_1-10s.png`, `web_1-11s.png`, `web_sws.png`, `web_1-3as.png`.

### 2. Real sy1 → 蜀水 hand-in chain (scripts only)
Traced from `talk/*.txt` + `scene/*.txt` — **sy1≥99 is satisfied when bq sets sy1=100**:

1. **沈云** `sy1<1` → `SetFlag sy1 1` + unlock 1-1s  
2. **沈万山** `sy1<19` → dialog + **`go sws`**  
3. **SWS.txt**: timer (or sy1≥18) → `go 1-3s` + **`SetFlag sy1 19`**  
4. **sws** talk `sy1≥18 ∧ sy1<20` → `SetFlag sy1 20` + AddFellow  
5. **1-3as**: `sy1<30` places 玉净甘露 on **bossyuheng**; defeat → prop **118**; with 118+sy1≥20 → **`SetFlag sy1 30`**  
6. **sws** `sy1≥29` → `SetFlag sy1 40`  
7. **泊祁** `IsProp 118` + sy1≥29 + sy1<100 → **`SetFlag sy1 100*miss 118`**  
8. Now **铁匠** `sy1≥99` 蜀水 quest / hand-in (`Miss 120*AddWeaponNum`) can fire; 1-6s `shushui` still supplies prop 120

**Client wiring (Phase 21):**
- `dialog.applyResult`: case-insensitive ops; **`go <scene>`** → `onGo`; **`miss`** lowercase fixed for bq  
- `jump_type 4` → `onCombat` (bossyuheng → spawn 玉衡; death → Acquire 118, sy1→30 if ≥20)  
- `runSceneEnter('sws')`: compressed timer → sy1=19 + warp 1-3s  
- `runSceneEnter('1-3as')`: sy1 bump when holding 118  
- Re-exported 1-3as NPCs: bossyuheng @ (101,96), sws @ (49,20)  
- DEBUG: Alt+Shift+F9 → sy1=100 + 蜀水 (hand-in test only)

### 3. Skill VFX / ShowJM anim
- ResJM.chs/.cht/.eng entry **834** still empty (len 162, 0 opaque) — no other JM lang pack has art.  
- Left Phase 20 canvas FX + size-matched panels.

### 4. Damage REA
Skipped (schema still broken).

### Blockers
- AddFellow / TransToPlayer / SetFlagTable / ScreenEffect / PlayAvi not simulated (fellow AI absent; sws must be talked on map).  
- 玉衡 fight is HP-scaled stub (400 vs RolePrivate 5900); no ResNpc3 boss set wired.  
- Type-12 NPC sprites on 1-3as/sws often missing (placeholder dots).  
- Full act-1 side quests (cds/td, cjg, …) not required for 蜀水 but still flag-gated.

### Deploy
- Source `7e5dc16`, Pages `a1316de`, NAS_OK.




## Phase 34 — CRITICAL facing fix (RIGHT was LEFT)

**Date:** 2026-10-10 (UTC+8)

### Bug
Walk/run RIGHT used `facing=(7-oct)%8` → art dir **7**, which does not face screen-east. User saw RIGHT→faces LEFT/wrong.

### Fix
Screen oct from `atan2(sdy,sdx)` (0=E…6=N). **`facing=(oct+6)%8`** so D→**6** (verified side-profile east). Attack cones via `facingWorldAng` (inverse map). Walk and Shift-run share same facing.

### Proof
- `assets/samples/phase34/06_wine_vs_web_east_FINAL.png`
- `05_east_walk_proof.png`, `05_east_run_proof.png`, `01_wasd_fixed.png`, `walk_right_crop.png`

### Deploy
- Source `3f46feb` · Pages `7ede74f` (main)

---

## Phase 33 — walk polish + xn multi-face

**Date:** 2026-10-10 (UTC+8)

### Changes
1. **Player walk:** nest idxs `0,2,4,6` from first-8 walk pool; **ping-pong** 0-1-2-3-2-1; distance stride `×2.4`.
2. **xn 行囊:** SprRole only has ResExNpc1 `2178/2179` (no other dir res). Remake: back(2178)+side(2179)+horizontal mirrors → 8 dirs.
3. Screenshots under `assets/samples/phase33/`.

### Deploy
- Source `1b3de6d` · Pages `21dc898` (main) · NAS FAILED again (ssh SOCKS)

### Note
Walk closer to Wine but still may look off to users; xn mirrors are remake convenience (original single/few facings).

---

## Phase 32 — act-1 QA + user bugs

**Date:** 2026-10-10 (UTC+8)

### Story / QA
1. Town pads only for original BNT exits; **north locked until 沈云 sy1≥1**; E/W/S locked by bq1/bq2 (scene/1-0s.txt).
2. Sparse markers (props≤16, exits≤9, hide after acquire; locked exits show ·锁).
3. Walk: paper-doll re-export; **distance-locked stride** (no moonwalk when blocked).

### User bugs
1. **Walk** — SprRole re-composite + distance stride; Wine compare `assets/samples/phase32/11_wine_vs_web_walk.png`.
2. **Dialog** — centered + viewport clamp; shot `09_dialog_centered.png`.
3. **cds / xn** — remapped from **ResExNpc1** (cds←1508 蔡大婶+篮; xn←2178 驮箱驴). Was wrong ResNpc3/warrior/legs.
4. **Run** — Shift sprints (stamina). **原版无跳跃** — not wired; documented in README + combat.help.

### Deploy
- Source `280e9c5` / `3722cf3` · Pages `c70646b` (main) · NAS FAILED (ssh SOCKS timeout to 100.100.214.12)

### Samples
- `assets/samples/phase32/`

### Playtest readiness (honest)
Act-1 is **playable without debug keys** for the opening loop: talk 沈云 → north unlock → field maps → props/quests with markers → S/L save. Combat uses scene-tier caps (not soft-DF). Full clear to bq2=100 is possible but still rough (dialog trees need correct choices; late maps; walk closer to Wine but not pixel-identical; xn donkey single-facing). **Recommend user playtest of act-1 town→蜀水 chain now**; not a finished remake.

---

## Phase 31 — act-1 residual (warps / markers / save / smoke)

**Date:** 2026-10-10 (UTC+8)

### Fixes
1. **Town warps missing** — `ren`/`game/map` had 0 triggers; injected reachable北/东/西/南 pads (`go 1-1s/1-4s/1-7as/1-9s`) + phase10 BNT triggers; punch blocked border at pads.
2. **Quest markers** — sparkle diamonds + labels for `shushui/bjsm/qnxbz/tzxs/jiguan*` and nearby exits; ground-loot pulse.
3. **Quicksave** — `S`/`L` → `localStorage djfm_act1_v1` (flags, exit/lock, bldStatus, inv, stats, pos, scene).
4. **Smoke** — `tools/phase31_smoke.py` town→bq2=100.

### Deploy
- Source `4662970`; Pages `284c641`; NAS `/volume4/web/djfm/`

### Samples
- `assets/samples/phase31/`

---

## Phase 30 — act-1 polish (SFX / camera / death / guide)

**Date:** 2026-10-10 (UTC+8)

### Goals
1. Optional SFX from `sy/*.sy` (WAV) — attack/hit/hurt/death/potion/step/UI.
2. Smoother camera follow; minimap scale without `/2` mismatch.
3. Death overlay + delayed respawn; potion cooldown veil + toast.
4. Wine vs web idle/walk/attack sheet.
5. README act-1 play guide (controls + quest outline).

### Notes
- SFX: `web/public/game/sfx/*.wav` (copied from Leyi `sy/`); mute with **M** or `?sfx=0`.
- Remake death UX is web-side (not ComeOn script).

### Deploy
- Source `e5fa02c` / `43f7536`; Pages `59bb005`; NAS `/volume4/web/djfm/`

### Samples
- `assets/samples/phase30/`

---

## Phase 29 — act-1 polish (names / combat feel / dialog / density)

**Date:** 2026-10-10 (UTC+8)

### Goals
1. Field-map NPC **and** monster nameplates everywhere (`drawNameplate`).
2. Combat feel: floating damage, clearer hurt flash, player hit vignette.
3. Dialog board styled from ResJM (JM_DlgModel corner tiles → `dialog_board.png`).
4. Walk: sequential frames + faster stride sync (fix phase28 wide-leg hang).
5. Remake tuning: late-map trash thin + sight/leash (`combat.remake`). Treat ONT `event=auto` as trash; keep real bosses. Example 1-9s 24→9, 1-11s→12.

### Deploy
- Source `6904bc9` / `dc50647`; Pages `60a12ce`; NAS `/volume4/web/djfm/`

### Samples
- `assets/samples/phase29/`

---

## Phase 28 — act-1 polish (JM / VFX / Init growth / gait)

**Date:** 2026-10-10 (UTC+8)

### Goals
1. Tighten walk gait vs Wine (stride ↔ speed).
2. ShowJM shop/embed/bag closer to original ResJM 326×226.
3. Skill VFX timing + ice hazard art animation.
4. Player Level/AT/DF/HP/MP from `mb/player/Init.txt` (not only foe caps).

### Changes
- **Walk:** `animT += speed * dt * 1.15` (distance-locked stride); walk 4.6 / run 7.2; stamina regen/use from Init.
- **ShowJM:** panels sized **326×226**; shop BUY/SELL/CLOSE strip; embed gem 25×25 grid; bag list with prop icons.
- **VFX:** `loadFxSprites` from `game/fx/index.json` (jidian/q/ice frames); slash peak-timed 0.24s; ice hazards cycle Map_Icecave plates @1.35× with pulse.
- **Growth:** `setInitGrowth` / `applyInitLevel` / `tryLevelUp` in `hud.ts` — AT+4 DF+4 HP+80 MP+1.2 per lv; HUD shows `AT`; `game/data/init_male.json` + `game.json` combat.init_male.
- Foes still **RolePrivate → scene_tier cap** (raw AT 315+ unwinnable at Init scale).

### Samples
- `assets/samples/phase28/` (shop, embed, bag, ice, walk, HUD AT)

### Deploy
- Source `46265f3` (+CSS url fix); Pages `62b9546`+; NAS `/volume4/web/djfm/`

---

## Phase 27 — act-1 polish (walk + NPC names priority)

**Date:** 2026-10-10 (UTC+8)

### Highest-priority user feedback
1. **Player walk** looked wrong vs Wine — fixed frame source, foot hotspot, direction mapping, gait timing.
2. **NPC names** missing — draw Role/ONT/dialog names above NPCs.

### Walk fixes
- Re-exported SprRole paper-doll walk as **fixed 128×128** canvas (no bbox crop) with foot at **(64,100)** from Spr ox/oy averages.
- Walk frames = ResPlayer nested **[0:4]** per dir (CA/HD/TK/RH); dir-aware draw order (RH under when facing away).
- Screen-space 8-dir facing: `sdx=dx-dy, sdy=dx+dy` → `facing = (7 - oct) % 8` matching d0=NE…d5=S…d7=E.
- Ping-pong cycle `0,1,2,3,2,1`; gait `animT += dt * (6|9)` walk/sprint.
- Draw with hotspot offset instead of `height+10` bottom-center (stops sliding).

### NPC names
- Labels from `o.name` / `dlg.names[EventID]` (GBK→UTF-8 Role + dialog table).
- Centered above head, stroke+fill cream; skip Autos / 天冰.
- Backfilled `name` onto map metas (town `ren` objects + scene NPCs).

### Samples
- `assets/samples/phase27/walk_sheet_p27.png` (foot=red)
- `walk_cycle_web_east.png` / `walk_cycle_web_north.png`
- `wine_vs_web_walk.png` / `wine_vs_web_walk_sheet.png`
- `web_npc_names_town.png`

### Deploy
- Source `0ea512a` (master); Pages `4c1b1a4` (main); NAS `/volume4/web/djfm/` (player+index+ren names).

---

## Phase 27 — Act-1 fine polish (人物/UI/动作/数值)

**No act-2.** Continue act-1 comfort playability.

### Done
1. **Characters**
   - 天冰: Map_Icecave ice tile → `game/fx/ice_hazard.png` (+ shimmer); 74 hazards draw real art.
   - Type-12 gaps: SprRole paper-dolls for **狐狸刀兵 (015)** and **号角小妖 (607)** wired into 1-7s / 1-4s.
   - Player **attack frame sync**: windup (walk) → hit (attack) → recover.
2. **UI**
   - Inventory always JM panel mode (bag `panel_625`); larger JM frames.
   - Potion HUD shows ×qty; dimmed empty slots.
   - Combat help banner: placeholder AT−DF/2 + foe caps (`?softdf=1` only).
3. **Motion**
   - Skill VFX: sharper slash; `ice` burst on 天冰 contact.
   - Hurt 0.28s / death 0.9s.
4. **Numbers**
   - ComeOn.exe: only `RolePrivate.txt` name string — no melee formula (GBK/UTF-16 empty).
   - `define.ini`: Ice/Fire/Poison DoT rates only.
   - Init.txt 男主角 AT40+4/lv in `game.json` `combat.init_male`; scene-tier caps remain PLACEHOLDER.
5. **Pathing playthrough** (`tools/phase27_walk_playthrough.py`): greedy walks + faceAttack.
   - Reached **bq2=100** with sy1=100 / 玲珑心.
   - Friction: boss approach sometimes misses; 1-11s jiguan walks can miss switches.

### Screenshots
`assets/samples/phase27/` — web_town/inv/shop/ice/fox, `wine_vs_web_*.png`, `panel_vs_web_shop.png`.

### Remaining
- Exe melee formula still unknown (needs deeper disasm).
- Collision A* on MAP walk bytes not in harness.
- Act-2 deferred.

### Deploy
- Source `c12f826` (master)
- Pages `main` `9bdef5f`
- NAS_OK `/volume4/web/djfm/` (+ ice/fox/horn map props)


## Phase 26 — Act-1 polish (playable town → bq2=100 without soft-DF / killFlag)

**Stopped act-2 export expansion** (user priority). Prior act-2 map export (16 maps) remains in tree; quest scripting deferred.

### Done
1. **Combat (no soft-DF cheat by default)**
   - Soft-DF formula hack is **opt-in only**: `?softdf=1`. Default OFF.
   - **PLACEHOLDER foe caps** via `game.json` `combat.scene_tier` / `df_cap` / `hp_cap` / `at_cap` so Init AT+4/lv can clear act-1. HUD shows `·占位数值` (or `·软DF` when query on).
   - Boss onCombat HP/AT soft-capped similarly (玉衡/魔豕兽/战象/天机).
   - Melee cone widened slightly for human Space swings.
2. **1-8s 天冰 hazards** — Model 220 Autos → ice contact damage zones (74), cyan draw; no Type-12 art yet.
3. **SetBldAni** dialog op → flash stub; locks/SetBldStatus already wired.
4. **Quest polish** — 玲珑心 needs bq tumble→wake (bq1 50→60) then sdyx with 天芝; dual 天机 fair Space/faceAttack clears → bq2=50→…→100 → `go 2-0s` / ChangeAct.
5. **WASD-like retest** (`tools/phase26_wasd_playthrough.py`): no `omniAttack` / `killFlag` / softdf. Map teleports for time; combat is single-direction `faceAttack` (=Space). **Reached bq2=100**, scene `2-0s`.

### Screenshots
`assets/samples/phase26/wasd_*.png`, log `wasd_playthrough_log.txt`.

### Remaining blockers (human WASD, no debug)
- **Full walk (no map teleport)** not timed; trash pack density on 1-9s/1-11s still high — human may grind or kite.
- **Paper-doll**: PLI draw-order/anchors improved earlier; Type-12 / Autos (天冰) still placeholders.
- **ShowJM shop/embed** still simplified JM frames; inventory polish partial; stamina bar exists (Wine) + Shift run drain.
- **Damage formula** still AT−DF/2 placeholder until exe formula known — caps labeled, not soft-DF.
- Human path still requires 甘露→泊祁 for sy1=100 (story); combat does not need soft-DF.
- Act-2 quest scripting intentionally **not** started.

### Deploy
- Source `cdfbead` (master)
- Pages `main` `9685549` (PROGRESS) / `ab38a2d` (dist)
- NAS_OK `/volume4/web/djfm/` (core assets + game.json; full map re-sync skipped this pass)

---

### Earlier Phase 26 note (act-2 export — stopped)

## Phase 26: act-2 map export + enter 芭蕉村 (2026-10-10)

### Done
1. **Exported 16 act-2 maps** reachable by BNT `go` from 2-0s (BFS):  
   `2-0s` 芭蕉村 → 2-1s 伐木场, 2-2s 明光寺, 2-7s 芭蕉园 → … → 2-13s/2-13as 出水洞.  
   Via `tools/scene_export.py`; libs Map_Nanfang / Map_Diyu. Added to `maps/index.json` with Chinese names from `trigger/flag.txt`.
2. **`go 2-0s` after bq2=100** loads 芭蕉村 (bq.txt lines 13/24).  
3. **ChangeAct / ShowActForeword**: dialog hooks + fullscreen foreword (public2 text 114 for act 2). Scene enter on 2-0s runs ChangeAct 1 and one-shot Act2 foreword (`act2` flag).
4. **Warps**: existing trigger/`go` pipeline; 2-0s exit locks for 2-1s/2-2s/2-7s when quest flags unset (from scene script).
5. Soft-DF unchanged and still labeled `·软DF`.

### Playthrough
Harness: act-1 clear flags → talk 泊祁 → **2-0s** with chapter foreword → talk 2bq/2sws/2sy → load 2-1s, 2-2s, 2-7s, 2-3s, 2-5s, 2-8s, 2-13s, 2-13as. Log: `assets/samples/phase26/playthrough_log.txt`.

### How far act-2 goes / first blockers
- **All 16 maps load** (buildings + named NPCs + warps).
- **Almost no combat packs**: ONT Autos stay as NPCs (not remapped to monster_sets); only 2-13s has 2 RolePrivate monsters. Late act-2 fights (天璇/天枢 etc.) need SprRole paper-doll / phase23-style remaps.
- **Act-2 quest chain not scripted beyond exported talks**: 2bq1 starts on talk; sq1/2bq2 exit locks present but full 消灭摇光/天璇 chain, SetPropToObj, IsDead bosses, jiguan — not wired scene-by-scene yet (no invented quests).
- Nanfang **overlay tiles** often miss in compose (ok=0 on overlay pass) — ground+buildings still show.
- 2-4as / 2-13as lack flag.txt display names (kept id).
- Minimap / BGM per act-2 scene not specialized.

### Deploy
- source `e4fd05c`, Pages `2212e23`, .

### Samples
- `assets/samples/phase26/act2_grid.png`, `pt_*.png`, `2-0s.png`…

## Phase 25: act-1 main quest after sy1=100 (2026-10-10)

### Done (from real talk/scene scripts only)
1. **IsFlag bare = equality** — bare `IsFlag name value` is now `==` (was `>=`), so bq.txt stage gates (30→31 vs 40→50) no longer clobber each other.
2. **玲珑心链 (bq1)** via talk + scene props:
   - bq→bq1=1 → sws→10 + unlock 1-4s → sdyx→20 → bq→30 + unlock 1-7as
   - **1-7s jiutianchi** SetLockTextID 208 while bq1∈[30,50); unlock at 50
   - Quest props on triggers: bjsm→122, qnxbz→123, tzxs→121 (E pickup); tzxs sets bq1=40
   - bq→50 (with 121) →60 → sdyx Miss121 Acquire119 (玲珑心) bq1=70 → sws→71 → bq→100 + bq2=1 + unlock 1-9s
3. **战象 / 张珊 (zhs1)**: IsDead bossdaxiang → zhs1=10; talk zs → zhs1=100. Combat spawn nudges onto walkable (standability).
4. **1-11s switches**: E on jiguan1/2/3 → bldStatus; all three + xqnz<1 → 气凝珠(124) + PlayAvi 1-11s + bq2=40.
5. **1-10a6s dual 天机**: onCombat bosstianji/boss (pd613); IsDead both → bq2=50 + avi.
6. **Act-end**: bq talk after bq2=50 →60; sws→70; bq→**bq2=100*go 2-0s** (2-0s not exported → stays in town; flag is the clear mark).
7. **Scene loot**: AddItem pools from scene scripts scatter potions near spawn (once/scene).
8. **PLACEHOLDER soft-DF** (`hud.dmg`): effective DF capped at 0.85×AT so Init.txt AT+4/lv matters vs RolePrivate DF 160+. HUD shows `·软DF`. Soft-cap spawn HP≤2500. Real formula still exe-only.
9. **PLI per-frame draw order** wired into paper-doll compositor when PLI order table parses; 天机 graph 613 exported as pd613.

### Playthrough (scripted harness past sy1=100)
Log: `assets/samples/phase25/playthrough_log.txt`. Boot at sy1=100 lv8 (Init growth), then real flag/talk/pick/kill path.
Reached **bq2=100, zhs1=100, bq1=100, xqnz=1** with props 122/123/124 acquired along the way.

### Still blocks / gaps for a clean act-1 clear
- **Act-2 map 2-0s not exported** — `go 2-0s` cannot leave town.
- Soft-DF / HP soft-cap are placeholders; balance ≠ Wine.
- Scene AddItem is a simplified scatter, not full AddItem RNG/coords.
- 1-8s 天冰 Autos still placeholders; ChangeAct / ShowActForeword / SetBldAni still stubs.
- PLI order parser is heuristic (can over-read); some frames may still mis-layer.
- Harness uses omniAttack + killFlag for boss deaths after engaging (not pure WASD play).

### Deploy
- source `b7ee77e` / note `7c12ce7`, Pages `c27a7d2`, NAS NAS_OK.

### Samples
- `assets/samples/phase25/playthrough_grid.png`, `pt_*.png`, `console.txt`, `playthrough_log.txt`

## Phase 24: cutscenes, SprRole paper-dolls, act-1 playthrough (2026-10-10)

### Done
1. **DHP → mp4**: act-1 clips (1-2s, 1-3s, 1-3as, 1-10a6s, 1-11s, swss) transcoded with ffmpeg (640w H.264 CRF30 + AAC 64k, faststart) to `web/public/game/cutscenes/*.mp4`, about 1.8 MB total. `PlayAvi` plays a fullscreen `<video>`. Click, Esc, Space or Enter skips it. Scene-enter hooks follow the scripts: 1-2s/1-3s (sy1<10), 1-3as (sy1<30), 1-10a6s (bq2<50). Each clip plays once.
2. **Real Spr/PLI paper-doll composites** (`tools/phase24_paperdoll.py`, `tools/phase24_export_sets.py`):
   - `SprRole.h` part → Spr.lib groups. Frame record packed = `(sub<<24)|(libnibble<<20)|res`, plus ox/oy. Lib nibbles: 2 ResPrior, 3 ResPlayer1, 4 ResBoss, 5 ResNpc2, 10 ResExNpc1. Shadow parts (`*S`) are skipped.
   - Each 8-group block = one action in 8 directions. Blocks were picked visually from `assets/samples/phase24/pd_<graph>.png`.
   - Remapped: 魔豕兽/野猪王 **006**, 战象 **009** (humanoid elephant warrior), 魔猿 **008** (1-10s Autos are now monsters), 狐猴 **601**, 1-11s 狐精弓箭兵 **003** / 雪地巨人 **113**.
   - Phase 23 interim sets r348/rex72/boss564 were removed.
3. **Saber ghost layers solved**: 持刀鬼兵 **602** (saber + shield + banner) and 持枪鬼兵 **603** now use the true composites. The old ResNpc3 594 stand-in is gone.
4. **Scripted act-1 playthrough** (`tools/phase24_playthrough.py`, log `assets/samples/phase24/playthrough_log.txt`):
   - The harness runs the quest chain through a debug handle (`window.__djfmDbg`): map loads, talk choices, and real Space attacks.
   - What works: 沈云 → north gate, 1-2s cutscene, 魔豕兽 kill → 猪心 → cjg1 10, sws → sy1 19/20 → 1-3as cutscene, 玉衡 kill → 118 → sy1 30/40, 泊祁 + 铁匠 hand-in → sy1 100, and every act-1 map loads.
   - Bugs fixed: a `monster_sets` note string crashed 1-3as loading; frames iteration is now guarded.

### Still blocks act-1 E2E
- **Main bq1/bq2/zhs1 chain after sy1=100 is not scripted**: 1-7s jiutianchi lock (bq1 30–50), 1-5s/1-7s/1-8s quest props 122/123/121 (bq1 40), 1-9s `IsDead bossdaxiang → zhs1 10`, 1-11s jiguan BldStatus + prop 124 → bq2 40, 1-10a6s bosstianji/boss combat (onCombat not wired) → bq2 50, ChangeAct / ShowActForeword.
- **Damage/balance**: the RolePrivate stats used are too strong for the player, e.g. 狐猴 DF 171 vs player AT 40 = 1 damage per hit, and 战象 HP 10000. The real formula and level curve live in the exe, so the late maps can't be won without cheats.
- Scene `AddItem` drops/potions (IsScnIn/IsHitBox) are not implemented.
- 1-8s 天冰 (220, graph 0) Autos are still placeholders (probably hazards).
- Paper-doll draw order is fixed (CA→arms→TK→HD), not the per-frame PLI order, so some frames layer the weapon/arm wrong.
- The 蜀水 pickup was simulated in the harness. The 1-6s proximity pickup itself was not re-tested.

### Samples
- `assets/samples/phase24/pd_{006,009,008,601,602,603,003,113}.png`: composite sheets
- `assets/samples/phase24/combat_grid.png` + `combat_*.png`
- `assets/samples/phase24/pt_*.png`, `pt_avi_*.png`, `playthrough_log.txt`

## Phase 23 — sprite remaps, RemItem/SetFlagTable, combat polish, DHP stub (2026-10-10)

### Done
1. **Monster/NPC remaps** (`tools/phase23_fix_sprites.py`):
   - **狐猴 (189)** Autos on graph 601 (halberd torso / paper-doll idle) → **ResExNpc1 set 72** full-body (`rex72`); converted Type-13 Auto → monsters on 1-9s/1-10s/1-10a*.
   - **魔豕兽 (10/11)** set0 human walk + **1712×1 death strip** → **ResNpc3 set 48** (`r348`) full walk/idle/hurt/attack/death (strip frames filtered). Exact Spr/PLI graph-006 composite still open — set48 is best full-body match.
   - **战象 / bossdaxiang (158)** graph 009 nests are 1px strips → **ResBoss set 564** (`boss564`) interim full-body; talk NPC restored with `npc_daxiang.png`. Exact paper-doll 009 still open.
   - Ghosts 190/191 stay ResNpc3 **594**.
2. **RemItem / SetFlagTable / ResetObj**: `dialog.ts` + `main.ts` `onRem` / `hiddenEvents` / `flagTable[111]`. Scene-enter hooks for 1-0s, 1-2s, 1-3as per scripts.
3. **Combat polish**: foe HP bars (already), hurt frames + **knockback**, death anim ~1.4s then **remove** (no 12s respawn). `bossdaxiang` combat wired.
4. **DHP**: MPEG-1 PES confirmed (`ffprobe`); stub frames via ffmpeg → `web/public/game/cutscenes/{1-3s,swss}.png`; `PlayAvi` shows overlay ~2.8s (not full video playback).
5. **Act-2 export**: **skipped** — act-1 sprite exactness (魔豕/战象 PLI) and 魔猿(46) Autos on 1-10s still open.

### Samples
- `assets/samples/phase23/fixed_monsters.png` — r348 / rex72 / boss564 / 594 / DHP frame
- `assets/samples/phase23/web_1-2s.png`, `web_1-9s.png`, `web_1-10s.png`
- `assets/samples/phase23/dhp_1-3s_f0.png`

### Deploy
- Source `c6e96bf`, Pages `e5bd92d`, NAS check below.

### Remaining gaps → playable act-1 E2E
- Exact **魔豕/野猪王** graph-006 and **战象** graph-009 Spr/PLI paper-doll composites (interim sets are wrong species for 战象).
- **魔猿 (46)** graph 008 Autos still NPC placeholders on 1-10s.
- True skill particle lib; pixel-exact ShowJM; damage formula (REA); gem sockets; saber multi-layer.
- Full DHP video playback (only still-frame stub).
- Side-quest / flag coverage beyond sy1/蜀水/cds/td/cjg subset.
- Act-2 maps not started.


## Phase 22 — 玉衡 sprites, AddFellow, Type-12 NPCs, side quests (2026-10-10)

### 1. 玉衡 boss art (ResNpc / ResExNpc)
- Role 196 graph 608; **ResExNpc1.lib entries 196 (walk) / 197 (idle)** are full-body constellation-banner boss (confirmed visually).
- Attack/death entries (200+) are small VFX-sized layers only → combat reuse walk/idle body frames.
- Wired: `monster_sets["196"]` on 1-3as; `onCombat('bossyuheng')` spawns set 196 foe; NPC dirs from idle.
- Samples: `assets/samples/phase22/yuheng_idle.png`, `yuheng_walk.png`, `boss_fellow_preview.png`.

### 2. AddFellow (沈万山)
- Dialog `AddFellow sws 1/0` → `onFellow`; companion follows player using `game/fellow/sws/{0–7}.png` (Role graph 624 / town sheets).
- Scene hooks: 1-3as / 1-3s while `19 ≤ sy1 < 30` auto-enable fellow (matches ResetObj/AddFellow scene lines).
- `TransToPlayer` / `SetFlagTable` still not simulated beyond follow AI.

### 3. Type-12 NPC sprites
- Backfill `npc_dirs` from ResNpc3/2 for maps missing art (~80 NPCs: sws, 1-10*, 1-9s, 1-3as, …).
- Blocker: some graphs wrong (e.g. bossdaxiang 1712×1 strip); auto EventID=601 reused for unnamed autos.

### 4. ScreenEffect / PlayAvi
- `ScreenEffect` / `PlayAvi` → toast only. DHP files exist under `extract/.../dhp/` (incl. `swss.dhp`, `1-3s.dhp`) but **no dhp decoder** — skipped as too heavy.

### 5. Side quests cds / td / cjg (scripts only)
- **cds→td:** talk already sets `cds1`; td sets `cds1=100` + ScreenEffect toast; cds reward Acquire 28 when cds1≥100.
- **cjg:** talk sets `cjg1=1` (needs `1-2s` flag still 0 = talk before visit); 1-2s places fight vs **bossyezhu** (ModelID 10); death → prop **54 猪心** + `cjg1≥10`; hand-in Miss 54 / Acquire 143.
- 1-2s monster set `10` exported from ResNpc3 set0 (beast body — may not be exact 魔豕 art; better than ellipse).

### Blockers
- 玉衡 attack/death lep layers are VFX-only; no full-body attack sheet found in ResExNpc1.
- Exact 魔豕兽 ResNpc set ID not verified (using set 0 placeholder beast).
- DHP/AVI playback not implemented.
- SetFlagTable / TransToPlayer / RemItem object visibility incomplete.
- Some Type-12 auto NPCs share wrong graph 601.

### Deploy
- Source `368f54c`, Pages `1853f90`, NAS_OK.


- Deploy: source `9faf5ea`, Pages `7af67d0`, NAS OK.

