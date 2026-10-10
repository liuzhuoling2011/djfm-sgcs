# Phase 8 — CombineLib / .fol / ScnInfo static RE

ComeOn.exe never executed. Capstone + strings only.

## CombineLib mount list

`InitGameFileProperty` string table (file off ~0x1741F0):

```
cj \0 slr \0 mb \0 fol \0 Zy\PixelGame.lib
```

Startup at VA ~0x401437 registers extension `fol` then pushes pack basenames `mb`, `slr`, `cj` into an in-memory list (`call 0x54074d`).
Runtime opens `cj.fol` / `slr.fol` / `mb.fol` as virtual roots mirrored by path prefixes `cj\`, `Slr\`/`slr\`, `mb\` (also present as string constants next to `%s%s.lib` / `leyiLib2.0`).

## On-disk .fol

- `cj.fol`: 23225568 bytes, header `ff000080` (pattern `xx 00 00 80`), entropy(first64k)≈7.942
- `mb.fol`: 2165553 bytes, header `b0000080` (pattern `xx 00 00 80`), entropy(first64k)≈7.934
- `slr.fol`: 444201 bytes, header `97000080` (pattern `xx 00 00 80`), entropy(first64k)≈7.951

No plaintext `ScnInfo`, `leyiLib2.0`, `.scn`, `.rmd`, or `MapFile` inside fol blobs (single-byte / period-4 XOR probes negative on first 500k of cj.fol).
Treat as **custom encrypted container**; decrypt key/stream not recovered from static inspection of ComeOn.exe (no obvious constant-key XOR loop tied to these buffers yet).

## ScnInfo schema (from .rdata string cluster)

Missing loose file `ScnInfo.txt` (and `ScnInfoMdl`) — expected inside decrypted `cj\` after CombineLib.
INI-like keys referenced by loader:

| Key | Role (inferred) |
|-----|-----------------|
| MapFile | Ground map / LeyiMap asset name |
| BldFile | Building layer (`leyibld1.50`) |
| ObjFile | Object/actor placements |
| PreScn | Previous / linked scene id |
| PortalNum | Portal count |
| MapX / MapY | Scene map coordinates |
| ModelID / Type / RadarID / Dir | Object instance fields |
| Logic_* (PathMapX/Y, cx/cy, MoveRange*, MoveLevel, …) | Pathing / height-adjacent logic grid |

Related extensions: `.scn` (scene script; strcat in loader), `.rmd` (LeyiMap1.50 companion).
Debug/build strings: `BuildMap`, `LoadMap`, `BuildBld`, `Not Find This Scn Name !`.

## BeginScn → map pack

`ComeOn.ini` has `BeginScn=0`. No plaintext table maps scene index → `map_*.lib` yet (would live in ScnInfo `MapFile`).
Heuristic used by web client: scene 0 / starting 瓦当镇 arc → `map_ren.lib` (human realm).
Other packs present on disk: `map_diyu`, `map_snow`, `map_nanfang`, `map_grave`, `Map_Icecave` — exposed as switchable previews.

## idx.lib

Plaintext loader list (`num=14` + Res* names only) — does **not** enumerate map packs; maps load via ScnInfo `MapFile` / `%s%s.lib` under `Zy\`.


---
**Superseded by Phase 9: fol CRACKED.** See `assets/samples/phase9/FOL_SCN_FINDINGS.md`.
