# Original vs Web remake — 瓦当镇 comparison

**Date:** 2026-10-10 Asia/Shanghai

## How original was captured

- **Not a licensed Windows XP ISO** (Microsoft no longer ships XP evaluation media; none on box/NAS reachable).
- **QEMU + ReactOS 0.4.16** (NT 5.2-compatible FOSS) booted to Live desktop (`reactos_live_now.png`). KVM unavailable (permission denied → TCG). Game disk FAT copy incomplete; ReactOS not used for gameplay shots.
- **Fallback used:** Wine 10 + Xvfb, `ComeOn.exe` from extracted tree (adware `launcher.exe` / Setup URLs **not** run). Path case fixes (`ZY`, `ResJM.lib` → `.chs`). dgVoodoo wrappers removed (Wine builtin ddraw).
- Confirmed in-game: minimap label **瓦当镇**, rainy day, spawn near gate/roof/arch.

## Screenshot paths

| Path | Content |
|------|---------|
| `orig_wadang/00_main_menu.png` | Title / 新游戏 |
| `orig_wadang/01_gate_rain.png` | Spawn vicinity: dirt path, stone arch, tiled roof, rain |
| `orig_wadang/02_path_arch.png` | Path + arch + NPC |
| `orig_wadang/03_stone_tablet.png` | Stone tablet / donkey / autumn tree |
| `orig_wadang/04_donkey_tree.png` | Donkey + tree + roof |
| `steam_ref/ss_*.jpg` | Official Steam store shots (other scenes) |
| `web_remake_view.png` | Current Phase 12 web client |
| `COMPARE_orig_vs_web.png` | Side-by-side |
| `reactos016_boot.png` / `reactos_live_now.png` | ReactOS Live status |

## Map differences (original vs web)

1. **Ground**: Original has soft dirt/grass blend with gravel path; web ground_full is flatter olive grass with mud patches and still slightly wrong path topology vs camera around spawn (improved vs identity-grid bug, but path curvature/arch approach still diverge).
2. **Buildings**: Original roofs/walls are coherent painted sprites (tiled roofs, stone arch, wooden tower). Web buildings still show **vertical smear / blue striping** and fragmented props — dominant visual error.
3. **Props**: Original places donkey+crates, stone tablet, hay, mossy roofs as clean objects. Web places many yellow markers / shredded sprites.
4. **Lighting/weather**: Original rainy day + soft shadows under feet. Web has no weather, brighter flat lighting.
5. **HUD**: Original full ComeOn HUD + minimap「瓦当镇」. Web debug overlay only.
6. **No clear remaining grid-pitch bug** from these spawn shots alone: diamond iso orientation matches; remaining issues are **asset decode** (buildings) and **object placement/layering**, not another full-map transpose.

## Fixes applied this session

- None to web map assembler (no new definite pitch/offset bug from comparison).
- Wine/ReactOS harness + reference pack under `assets/samples/xp_compare/`.

## Blockers / next

- For true XP guest: user must supply a legally owned XP ISO/VHD on NAS or local path.
- ReactOS Live is up; finish FAT/NTFS game disk + DirectDraw stack if Wine path insufficient.
- Priority remake work: building lep smear decode; prop sprites; weather optional.
