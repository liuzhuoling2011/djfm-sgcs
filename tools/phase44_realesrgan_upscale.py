#!/usr/bin/env python3
"""Phase44: Real-ESRGAN HD upscale for player / town NPCs / act1 mons.

Uses realesrgan-ncnn-vulkan (anime model). On machines without a real GPU,
set VK_ICD_FILENAMES to Mesa llvmpipe (lavapipe) so ncnn can run on CPU.

Outputs:
  web/public/game/player_hd/{walk,run,idle,attack}/
  web/public/game/map/npcs_hd/
  web/public/game/maps/1-2s/mon_hd/   (first fight map; other 1-* left as backlog)
  assets/samples/phase44_hd/
  */meta.json with scale/hotspot/canvas

Usage:
  python3 tools/phase44_realesrgan_upscale.py              # all priority targets
  python3 tools/phase44_realesrgan_upscale.py --only player
  python3 tools/phase44_realesrgan_upscale.py --only npc
  python3 tools/phase44_realesrgan_upscale.py --only mon
  python3 tools/phase44_realesrgan_upscale.py --samples-only
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ESR_DIR = ROOT / "tools" / "realesrgan"
ESR_BIN = ESR_DIR / "realesrgan-ncnn-vulkan"
MODEL_DIR = ESR_DIR / "models"
# Anime/hand-drawn friendly; avoids photo-real skin
MODEL = "realesrgan-x4plus-anime"
PLAYER_SCALE = 4
NPC_SCALE = 4
# Large paper-doll mons → 2× to keep VRAM/CPU and on-screen size sane
MON_SCALE = 2
MON_SCALE_SMALL = 4  # if max(w,h) <= this threshold use 4×
MON_SMALL_MAX = 128

PLAYER_SRC = ROOT / "web/public/game/player"
PLAYER_HD = ROOT / "web/public/game/player_hd"
NPC_SRC = ROOT / "web/public/game/map/npcs"
NPC_HD = ROOT / "web/public/game/map/npcs_hd"
MON_SRC = ROOT / "web/public/game/maps/1-2s/mon"
MON_HD = ROOT / "web/public/game/maps/1-2s/mon_hd"
SAMPLES = ROOT / "assets/samples/phase44_hd"

DIR_NAMES = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]


def ensure_env() -> None:
    """Prefer lavapipe when no discrete GPU Vulkan device exists."""
    os.environ.setdefault("XDG_RUNTIME_DIR", "/tmp")
    icd = Path("/usr/share/vulkan/icd.d/lvp_icd.json")
    if icd.exists() and "VK_ICD_FILENAMES" not in os.environ:
        # Only force lavapipe if a quick probe would fail without it — keep simple:
        os.environ["VK_ICD_FILENAMES"] = str(icd)


def run_esrgan(inp: Path, out: Path, scale: int, model: str = MODEL) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_mtime >= inp.stat().st_mtime:
        return
    cmd = [
        str(ESR_BIN),
        "-i", str(inp),
        "-o", str(out),
        "-n", model,
        "-s", str(scale),
        "-m", str(MODEL_DIR),
        "-f", "png",
        "-j", "1:2:2",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(
            f"realesrgan failed ({r.returncode}) {inp} -> {out}\n"
            f"stdout: {r.stdout[-500:]}\nstderr: {r.stderr[-500:]}"
        )


def run_esrgan_dir(inp_dir: Path, out_dir: Path, scale: int, model: str = MODEL) -> int:
    """Batch a whole directory (faster). Returns number of pngs expected."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pngs = sorted(inp_dir.glob("*.png"))
    if not pngs:
        return 0
    # Skip if all outputs already fresh
    pending = [
        p for p in pngs
        if not (out_dir / p.name).exists()
        or (out_dir / p.name).stat().st_mtime < p.stat().st_mtime
    ]
    if not pending:
        return len(pngs)
    # If only a few pending, do file-by-file; else whole dir (re-runs all)
    if len(pending) < len(pngs) and len(pending) <= 8:
        for p in pending:
            run_esrgan(p, out_dir / p.name, scale, model)
        return len(pngs)
    cmd = [
        str(ESR_BIN),
        "-i", str(inp_dir),
        "-o", str(out_dir),
        "-n", model,
        "-s", str(scale),
        "-m", str(MODEL_DIR),
        "-f", "png",
        "-j", "2:4:2",
    ]
    print(f"  batch {inp_dir.name}: {len(pngs)} files ×{scale} ({model})")
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        # Fall back per-file
        print(f"  batch failed, falling back per-file: {r.stderr[-200:]}")
        for p in pending:
            run_esrgan(p, out_dir / p.name, scale, model)
    else:
        print(f"  done in {time.time() - t0:.1f}s")
    return len(pngs)


def upscale_player() -> dict:
    print("== player ==")
    src_meta = json.loads((PLAYER_SRC / "meta.json").read_text())
    counts = {}
    for anim in ("walk", "run", "idle", "attack"):
        n = run_esrgan_dir(PLAYER_SRC / anim, PLAYER_HD / anim, PLAYER_SCALE)
        counts[anim] = n
    hs = src_meta.get("hotspot", [64, 100])
    canvas = src_meta.get("canvas", [128, 128])
    meta = {
        **src_meta,
        "hd": True,
        "scale": PLAYER_SCALE,
        "model": MODEL,
        "source_canvas": canvas,
        "canvas": [canvas[0] * PLAYER_SCALE, canvas[1] * PLAYER_SCALE],
        "hotspot": [hs[0] * PLAYER_SCALE, hs[1] * PLAYER_SCALE],
        "hotspot_base": hs,
        "gait": src_meta.get("gait", "pingpong_012321"),
        "walk_frames": 4,
        "run_frames": 4,
        "note": "Phase44 Real-ESRGAN HD; web loads player_hd then falls back to player",
    }
    (PLAYER_HD / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    print(f"  player_hd meta scale={PLAYER_SCALE} counts={counts}")
    return {"counts": counts, "scale": PLAYER_SCALE, "model": MODEL}


def upscale_npcs() -> dict:
    print("== npcs (town) ==")
    NPC_HD.mkdir(parents=True, exist_ok=True)
    # Prefer 8-dir sheets + base; skip index.json
    files = sorted(p for p in NPC_SRC.glob("*.png"))
    # Batch via temp dirs grouped by scale (all 4×)
    # Copy pending into a staging dir for one batch if many missing
    pending = [
        p for p in files
        if not (NPC_HD / p.name).exists()
        or (NPC_HD / p.name).stat().st_mtime < p.stat().st_mtime
    ]
    print(f"  {len(files)} pngs, {len(pending)} pending")
    for i, p in enumerate(pending, 1):
        if i == 1 or i % 20 == 0 or i == len(pending):
            print(f"  [{i}/{len(pending)}] {p.name}")
        run_esrgan(p, NPC_HD / p.name, NPC_SCALE)
    # meta from index + scale
    idx = {}
    idx_path = NPC_SRC / "index.json"
    if idx_path.exists():
        idx = json.loads(idx_path.read_text())
    hd_index = {}
    for key, info in idx.items():
        if not isinstance(info, dict):
            continue
        entry = dict(info)
        entry["scale"] = NPC_SCALE
        if "ox" in entry:
            entry["ox_base"] = entry["ox"]
            entry["ox"] = int(entry["ox"]) * NPC_SCALE
        if "oy" in entry:
            entry["oy_base"] = entry["oy"]
            entry["oy"] = int(entry["oy"]) * NPC_SCALE
        if "w" in entry:
            entry["w_base"] = entry["w"]
            entry["w"] = int(entry["w"]) * NPC_SCALE
        if "h" in entry:
            entry["h_base"] = entry["h"]
            entry["h"] = int(entry["h"]) * NPC_SCALE
        if "dirs" in entry:
            entry["dirs"] = list(entry["dirs"])
        hd_index[key] = entry
    meta = {
        "hd": True,
        "scale": NPC_SCALE,
        "model": MODEL,
        "count": len(files),
        "npcs": hd_index,
        "note": "Phase44: ox/oy/w/h already ×scale for HD sheets",
    }
    (NPC_HD / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    shutil.copy2(idx_path, NPC_HD / "index.json") if idx_path.exists() else None
    return {"count": len(files), "scale": NPC_SCALE}


def pick_mon_scale(path: Path) -> int:
    im = Image.open(path)
    return MON_SCALE_SMALL if max(im.size) <= MON_SMALL_MAX else MON_SCALE


def upscale_mons() -> dict:
    print("== mon (1-2s first-fight map) ==")
    import tempfile
    MON_HD.mkdir(parents=True, exist_ok=True)
    files = sorted(MON_SRC.glob("*.png"))

    def prio(p: Path) -> tuple:
        act = p.name.split("_")[1] if "_" in p.name else "z"
        order = {"walk": 0, "idle": 1, "attack": 2, "hurt": 3, "death": 4}.get(act, 5)
        return (order, p.name)

    files = sorted(files, key=prio)
    pending = [
        p for p in files
        if not (MON_HD / p.name).exists()
        or (MON_HD / p.name).stat().st_mtime < p.stat().st_mtime
    ]
    print(f"  {len(files)} pngs, {len(pending)} pending")
    # Bucket by scale, then batch via staging dirs (avoids per-file process spawn)
    buckets: dict[int, list[Path]] = {}
    for p in pending:
        sc = pick_mon_scale(p)
        buckets.setdefault(sc, []).append(p)
    scales_used = {sc: len(ps) for sc, ps in buckets.items()}
    for sc, ps in sorted(buckets.items(), reverse=True):
        # process in chunks of 40
        for i in range(0, len(ps), 40):
            chunk = ps[i : i + 40]
            with tempfile.TemporaryDirectory(prefix="mon_esr_") as td:
                tin = Path(td) / "in"
                tout = Path(td) / "out"
                tin.mkdir(); tout.mkdir()
                for p in chunk:
                    # hardlink or copy
                    try:
                        (tin / p.name).hardlink_to(p)
                    except OSError:
                        shutil.copy2(p, tin / p.name)
                print(f"  batch ×{sc} [{i+1}-{i+len(chunk)}/{len(ps)}]")
                run_esrgan_dir(tin, tout, sc)
                for p in chunk:
                    src = tout / p.name
                    if src.exists():
                        shutil.move(str(src), str(MON_HD / p.name))
    meta = {
        "hd": True,
        "default_scale": MON_SCALE,
        "small_scale": MON_SCALE_SMALL,
        "small_max_edge": MON_SMALL_MAX,
        "model": MODEL,
        "count": len(files),
        "scales_used": scales_used,
        "note": "Phase44: mon drawn by image size (bottom-center foot); HD replaces path mon/→mon_hd/",
    }
    (MON_HD / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    return {"count": len(files), "scales_used": scales_used}


def _font(size: int = 14):
    for fp in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def make_samples() -> list[str]:
    print("== samples ==")
    SAMPLES.mkdir(parents=True, exist_ok=True)
    out_paths = []
    font = _font(16)
    font_sm = _font(12)

    # 1) Player 8-dir walk grid (frame 0)
    cell = 160
    grid = Image.new("RGBA", (cell * 8, cell + 36), (28, 28, 36, 255))
    draw = ImageDraw.Draw(grid)
    draw.text((8, 8), "player_hd walk frame0 — 8 dirs (Phase44)", fill=(240, 240, 240, 255), font=font)
    for d in range(8):
        p = PLAYER_HD / "walk" / f"{d}_0.png"
        if not p.exists():
            p = PLAYER_SRC / "walk" / f"{d}_0.png"
        im = Image.open(p).convert("RGBA")
        im.thumbnail((cell - 8, cell - 8), Image.Resampling.LANCZOS)
        x = d * cell + (cell - im.width) // 2
        y = 36 + (cell - 8 - im.height) // 2
        grid.paste(im, (x, y), im)
        draw.text((d * cell + 8, cell + 16), DIR_NAMES[d], fill=(200, 200, 210, 255), font=font_sm)
    path = SAMPLES / "player_walk_8dir_grid.png"
    grid.save(path)
    out_paths.append(str(path.relative_to(ROOT)))

    # 2) Before/after strip for a few player frames
    pairs = [
        ("walk/0_0.png", "S walk0"),
        ("walk/6_1.png", "E walk1"),
        ("run/0_0.png", "S run0"),
        ("idle/4_0.png", "N idle"),
        ("attack/6_0.png", "E attack"),
    ]
    thumb = 192
    strip = Image.new("RGBA", (thumb * 2 + 24, (thumb + 28) * len(pairs) + 40), (28, 28, 36, 255))
    d = ImageDraw.Draw(strip)
    d.text((8, 8), "before (src) vs after (realesrgan-x4plus-anime ×4)", fill=(240, 240, 240, 255), font=font)
    for i, (rel, label) in enumerate(pairs):
        src = Image.open(PLAYER_SRC / rel).convert("RGBA")
        hd = Image.open(PLAYER_HD / rel).convert("RGBA") if (PLAYER_HD / rel).exists() else src.resize(
            (src.width * 4, src.height * 4), Image.Resampling.NEAREST
        )
        src_s = src.copy()
        src_s.thumbnail((thumb - 8, thumb - 8), Image.Resampling.NEAREST)
        hd_s = hd.copy()
        hd_s.thumbnail((thumb - 8, thumb - 8), Image.Resampling.LANCZOS)
        y0 = 40 + i * (thumb + 28)
        strip.paste(src_s, (12 + (thumb - src_s.width) // 2, y0 + (thumb - src_s.height) // 2), src_s)
        strip.paste(hd_s, (thumb + 24 + (thumb - hd_s.width) // 2, y0 + (thumb - hd_s.height) // 2), hd_s)
        d.text((12, y0 + thumb + 4), f"{label} src", fill=(180, 180, 190, 255), font=font_sm)
        d.text((thumb + 24, y0 + thumb + 4), f"{label} HD", fill=(180, 220, 180, 255), font=font_sm)
    path = SAMPLES / "player_before_after.png"
    strip.save(path)
    out_paths.append(str(path.relative_to(ROOT)))

    # 3) NPC samples (8-dir row for a few town NPCs)
    npc_keys = ["td", "cds", "cjg", "bq", "sy", "sws", "xn", "zhs"]
    rows = []
    for key in npc_keys:
        imgs = []
        for di in range(8):
            p = NPC_HD / f"{key}_{di}.png"
            if not p.exists():
                p = NPC_SRC / f"{key}_{di}.png"
            if p.exists():
                imgs.append(Image.open(p).convert("RGBA"))
        if imgs:
            rows.append((key, imgs))
    if rows:
        cell_h = 140
        cell_w = 100
        canvas = Image.new(
            "RGBA",
            (cell_w * 8 + 80, cell_h * len(rows) + 40),
            (28, 28, 36, 255),
        )
        d = ImageDraw.Draw(canvas)
        d.text((8, 8), "town NPC HD 8-dir (Phase44)", fill=(240, 240, 240, 255), font=font)
        for ri, (key, imgs) in enumerate(rows):
            y0 = 36 + ri * cell_h
            d.text((8, y0 + 40), key, fill=(200, 200, 210, 255), font=font_sm)
            for di, im in enumerate(imgs):
                im2 = im.copy()
                im2.thumbnail((cell_w - 8, cell_h - 20), Image.Resampling.LANCZOS)
                x = 70 + di * cell_w + (cell_w - im2.width) // 2
                y = y0 + (cell_h - 20 - im2.height) // 2
                canvas.paste(im2, (x, y), im2)
        path = SAMPLES / "npc_8dir_grid.png"
        canvas.save(path)
        out_paths.append(str(path.relative_to(ROOT)))

    # 4) Mon samples
    mon_samples = [
        "pd006_walk_0_0.png",
        "pd006_idle_0_0.png",
        "pd602_walk_0_0.png",
        "r348_walk_0_0.png",
        "r3594_attack_0_0.png",
    ]
    cells = []
    for name in mon_samples:
        src_p = MON_SRC / name
        hd_p = MON_HD / name
        if not src_p.exists():
            continue
        src = Image.open(src_p).convert("RGBA")
        hd = Image.open(hd_p).convert("RGBA") if hd_p.exists() else None
        cells.append((name, src, hd))
    if cells:
        tw = 220
        canvas = Image.new("RGBA", (tw * 2 + 24, (tw + 32) * len(cells) + 40), (28, 28, 36, 255))
        d = ImageDraw.Draw(canvas)
        d.text((8, 8), "1-2s mon before/after (×2 or ×4)", fill=(240, 240, 240, 255), font=font)
        for i, (name, src, hd) in enumerate(cells):
            y0 = 40 + i * (tw + 32)
            s = src.copy()
            s.thumbnail((tw - 8, tw - 8), Image.Resampling.NEAREST)
            canvas.paste(s, (12 + (tw - s.width) // 2, y0 + (tw - s.height) // 2), s)
            d.text((12, y0 + tw + 4), name + " src", fill=(180, 180, 190, 255), font=font_sm)
            if hd is not None:
                h = hd.copy()
                h.thumbnail((tw - 8, tw - 8), Image.Resampling.LANCZOS)
                canvas.paste(h, (tw + 24 + (tw - h.width) // 2, y0 + (tw - h.height) // 2), h)
                d.text((tw + 24, y0 + tw + 4), "HD", fill=(180, 220, 180, 255), font=font_sm)
        path = SAMPLES / "mon_before_after.png"
        canvas.save(path)
        out_paths.append(str(path.relative_to(ROOT)))

    # 5) README
    readme = SAMPLES / "README.md"
    readme.write_text(
        "# Phase44 HD samples\n\n"
        f"- Model: `{MODEL}`\n"
        f"- Player/NPC scale: ×{PLAYER_SCALE}; mon: ×{MON_SCALE} (×{MON_SCALE_SMALL} if edge≤{MON_SMALL_MAX})\n"
        "- Engine: realesrgan-ncnn-vulkan (lavapipe CPU if no GPU)\n"
        "- Re-run: `python3 tools/phase44_realesrgan_upscale.py`\n"
    )
    out_paths.append(str(readme.relative_to(ROOT)))
    print("  wrote", out_paths)
    return out_paths


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["player", "npc", "mon", "all"], default="all")
    ap.add_argument("--samples-only", action="store_true")
    args = ap.parse_args()

    if not ESR_BIN.exists():
        print("Missing", ESR_BIN, file=sys.stderr)
        print("Download: https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip", file=sys.stderr)
        return 1

    ensure_env()
    report = {
        "model": MODEL,
        "bin": str(ESR_BIN.relative_to(ROOT)),
        "vk_icd": os.environ.get("VK_ICD_FILENAMES"),
    }

    if args.samples_only:
        report["samples"] = make_samples()
    else:
        if args.only in ("all", "player"):
            report["player"] = upscale_player()
        if args.only in ("all", "npc"):
            report["npc"] = upscale_npcs()
        if args.only in ("all", "mon"):
            report["mon"] = upscale_mons()
        report["samples"] = make_samples()

    out = SAMPLES / "phase44_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("REPORT", json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
