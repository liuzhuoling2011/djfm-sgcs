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
