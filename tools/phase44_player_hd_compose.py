#!/usr/bin/env python3
"""Phase44: HD player via part-wise Real-ESRGAN + scaled paper-doll compose.

Whole-frame ESRGAN separates sword from fist. Fix: upscale CA/TK/HD/RH parts
individually, then alpha_composite on canvas×scale with ox/oy×scale so the grip
stays locked. Falls back to SD phase41 geometry (RH_002, (body+3)%8).

Reproduce:
  python3 tools/phase44_player_hd_compose.py
  python3 tools/phase44_player_hd_compose.py --samples-only
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leyilib as L
import bld_rle as B
import phase24_paperdoll as P24
import phase41_player_sprites as P41

ROOT = Path(__file__).resolve().parents[1]
Z = ROOT / "extract/Blade And Sword 2 Ancient Legend/zy"
WEB = ROOT / "web/public/game"
SAMPLES = ROOT / "assets/samples/phase44_hd"
ESR_BIN = ROOT / "tools/realesrgan/realesrgan-ncnn-vulkan"
MODEL_DIR = ROOT / "tools/realesrgan/models"
MODEL = "realesrgan-x4plus-anime"
SCALE = 4
PART_CACHE = ROOT / "tools/realesrgan/cache_parts"
PLAYER_HD = WEB / "player_hd"
PLAYER_SD = WEB / "player"

# Phase41 intended layering: sword behind for S..NE, over for E/SE
RH_UNDER_BODY = [0, 1, 2, 3, 4, 5]

# Optional per-body-dir RH pixel nudge in SD space (then ×SCALE). Tune if grip still off.
# Positive ox moves part left on canvas (because paste at CX-ox).
RH_NUDGE_SD: dict[int, tuple[int, int]] = {
    0: (-10, -10),   # S from rh_grip_nudges (canvas +10,+10)
    1: (-3, -2),   # SW from rh_grip_nudges (canvas +3,+2)
    3: (-1, 8),   # NW from rh_grip_nudges (canvas +1,-8)
    4: (-3, -11),   # N from rh_grip_nudges (canvas +3,+11)
    5: (-6, -5),   # NE from rh_grip_nudges (canvas +6,+5)
    6: (0, -2),   # E from rh_grip_nudges (canvas +0,+2)
    7: (11, -1),   # SE from rh_grip_nudges (canvas -11,+1)
}

ART_DIR_NAMES = P41.ART_DIR_NAMES
CX, CY = P41.CX, P41.CY
CANVAS = P41.CANVAS
BODY = P41.BODY
RH_SID, RH_BASE = P41.RH_SID, P41.RH_BASE
RH_DIR_OFF = P41.RH_DIR_OFF
DEFAULT_OXOY = P41.DEFAULT_OXOY


def ensure_env() -> None:
    os.environ.setdefault("XDG_RUNTIME_DIR", "/tmp")
    icd = Path("/usr/share/vulkan/icd.d/lvp_icd.json")
    if icd.exists() and "VK_ICD_FILENAMES" not in os.environ:
        os.environ["VK_ICD_FILENAMES"] = str(icd)


def nested(r, res):
    out = []
    for _, lep in L.find_nested_leps(r.entry_bytes(res)):
        try:
            im = B.decode(lep)
        except Exception:
            continue
        if im is not None and (np.array(im)[:, :, 3] > 0).sum() > 15:
            out.append(im)
    return out


def _alpha_centroid(alpha: np.ndarray) -> tuple[float, float]:
    ys, xs = np.where(alpha > 128)
    if len(xs) == 0:
        return 0.0, 0.0
    return float(xs.mean()), float(ys.mean())


def _opaque_origin(alpha: np.ndarray) -> tuple[int, int]:
    ys, xs = np.where(alpha > 128)
    if len(xs) == 0:
        return 0, 0
    return int(xs.min()), int(ys.min())


def align_hd_to_nn(hd: Image.Image, sd: Image.Image, scale: int) -> Image.Image:
    """Register ESRGAN part onto nearest×scale geometry so ox/oy paste stays valid.

    Use opaque bbox origin (not centroid): long swords have blade-mass centroids
    that drift under ESRGAN and would pull the hilt off the fist.
    """
    nn = sd.resize((sd.width * scale, sd.height * scale), Image.Resampling.NEAREST).convert("RGBA")
    if hd.size != nn.size:
        hd = hd.resize(nn.size, Image.Resampling.LANCZOS)
    ha = np.array(hd.convert("RGBA"))
    na = np.array(nn)
    # Kill halo outside SD silhouette
    ha[..., 3] = np.where(na[..., 3] < 8, 0, ha[..., 3])
    hx, hy = _opaque_origin(ha[..., 3])
    nx, ny = _opaque_origin(na[..., 3])
    dx, dy = nx - hx, ny - hy
    if dx == 0 and dy == 0:
        out_im = Image.fromarray(ha, "RGBA")
    else:
        out = Image.new("RGBA", nn.size, (0, 0, 0, 0))
        out.alpha_composite(Image.fromarray(ha, "RGBA"), (dx, dy))
        out_im = out
    oa = np.array(out_im)
    # Soft-fill interior from HD but keep exterior = NN transparent
    oa[..., 3] = np.where(na[..., 3] < 8, 0, oa[..., 3])
    return Image.fromarray(oa, "RGBA")


def upscale_part(im: Image.Image, key: str) -> Image.Image:
    """Upscale one RGBA part; cache by content hash. Align to NN so grip locks."""
    PART_CACHE.mkdir(parents=True, exist_ok=True)
    raw = im.convert("RGBA").tobytes()
    h = hashlib.sha1(raw + f"|{im.size}|{SCALE}|{MODEL}|alignv3".encode()).hexdigest()[:16]
    cache = PART_CACHE / f"{key}_{h}_x{SCALE}.png"
    if cache.exists():
        return Image.open(cache).convert("RGBA")
    tmp_in = PART_CACHE / f"_in_{h}.png"
    tmp_out = PART_CACHE / f"_out_{h}.png"
    im.convert("RGBA").save(tmp_in)
    cmd = [
        str(ESR_BIN), "-i", str(tmp_in), "-o", str(tmp_out),
        "-n", MODEL, "-s", str(SCALE), "-m", str(MODEL_DIR), "-f", "png", "-j", "1:2:2",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not tmp_out.exists():
        hd = im.resize((im.width * SCALE, im.height * SCALE), Image.Resampling.NEAREST)
        hd.save(cache)
        tmp_in.unlink(missing_ok=True)
        return hd
    hd = Image.open(tmp_out).convert("RGBA")
    hd = align_hd_to_nn(hd, im, SCALE)
    hd.save(cache)
    tmp_in.unlink(missing_ok=True)
    tmp_out.unlink(missing_ok=True)
    return hd


def font(size=14):
    for fp in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def build() -> dict:
    ensure_env()
    r1 = L.LeyiLib.open(Z / "ResPlayer1.lib")
    body_frames = {k: {d: nested(r1, base + d) for d in range(8)} for k, (_, base) in BODY.items()}
    rh_frames = {d: nested(r1, RH_BASE + d) for d in range(8)}
    body_oxoy = {k: {d: P41.sole_oxoy_map(sid, base, d) for d in range(8)} for k, (sid, base) in BODY.items()}
    rh_oxoy = {d: P41.sole_oxoy_map(RH_SID, RH_BASE, d) for d in range(8)}
    ca_walk = {d: P41.loco_subs(34, 0, d, which=0) for d in range(8)}
    ca_run = {d: P41.loco_subs(34, 0, d, which=1) for d in range(8)}

    # Only upscale nests referenced by walk/run/idle/attack (not entire strip)
    print("== collecting needed nest indices ==")
    need_body = {k: {d: set() for d in range(8)} for k in BODY}
    need_rh = {d: set() for d in range(8)}
    for d in range(8):
        for mode, subs_map in (("walk", ca_walk), ("run", ca_run)):
            for fi in range(4):
                sub1 = subs_map[d][fi % len(subs_map[d])]
                nest_i = max(0, sub1 - 1)
                for k in BODY:
                    need_body[k][d].add(nest_i)
                rh_d = (d + RH_DIR_OFF) % 8
                rh_subs = P41.loco_subs(RH_SID, RH_BASE, rh_d, which=(1 if mode == "run" else 0))
                rh_sub1 = rh_subs[fi % len(rh_subs)]
                need_rh[rh_d].add(max(0, rh_sub1 - 1))
        # attack nest
        n_ca = max(1, len(body_frames["CA"][d]))
        ai_sub = min(n_ca, max(ca_walk[d][-1] + 4, n_ca // 2))
        ni = min(n_ca - 1, ai_sub - 1)
        for k in BODY:
            need_body[k][d].add(ni)
        rh_d = (d + RH_DIR_OFF) % 8
        need_rh[rh_d].add(min(max(0, len(rh_frames[rh_d]) - 1), ni))

    print("== upscaling needed parts ==")
    body_hd = {k: {d: [None] * len(body_frames[k][d]) for d in range(8)} for k in BODY}
    rh_hd = {d: [None] * len(rh_frames[d]) for d in range(8)}
    n_up = 0
    for k in BODY:
        for d in range(8):
            for i in sorted(need_body[k][d]):
                if i >= len(body_frames[k][d]):
                    continue
                body_hd[k][d][i] = upscale_part(body_frames[k][d][i], f"{k}_d{d}_n{i}")
                n_up += 1
            print(f"  {k} dir{d}: {len(need_body[k][d])} nests")
    for d in range(8):
        for i in sorted(need_rh[d]):
            if i >= len(rh_frames[d]):
                continue
            rh_hd[d][i] = upscale_part(rh_frames[d][i], f"RH_d{d}_n{i}")
            n_up += 1
        print(f"  RH dir{d}: {len(need_rh[d])} nests")
    print(f"  total upscaled parts: {n_up}")

    cx, cy = CX * SCALE, CY * SCALE
    canvas = (CANVAS[0] * SCALE, CANVAS[1] * SCALE)
    anchors = {k: [] for k in list(BODY) + ["RH"]}

    def composite(body_d: int, fi: int, mode: str = "walk") -> Image.Image:
        subs = ca_run[body_d] if mode == "run" else ca_walk[body_d]
        sub1 = subs[fi % len(subs)]
        nest_i = max(0, sub1 - 1)
        rh_d = (body_d + RH_DIR_OFF) % 8
        rh_subs = P41.loco_subs(RH_SID, RH_BASE, rh_d, which=(1 if mode == "run" else 0))
        rh_sub1 = rh_subs[fi % len(rh_subs)]
        rh_nest = max(0, rh_sub1 - 1)

        c = Image.new("RGBA", canvas, (0, 0, 0, 0))
        under = body_d in RH_UNDER_BODY
        order = ["RH", "CA", "TK", "HD"] if under else ["CA", "TK", "HD", "RH"]
        for k in order:
            if k == "RH":
                ims = rh_hd[rh_d]
                ni, s1 = rh_nest, rh_sub1
                ox, oy = P41.lookup_oxoy(rh_oxoy[rh_d], s1, DEFAULT_OXOY["RH"])
                dox, doy = RH_NUDGE_SD.get(body_d, (0, 0))
                ox, oy = ox + dox, oy + doy
            else:
                ims = body_hd[k][body_d]
                ni, s1 = nest_i, sub1
                ox, oy = P41.lookup_oxoy(body_oxoy[k][body_d], s1, DEFAULT_OXOY[k])
            if ni >= len(ims) or ims[ni] is None:
                continue
            px = cx - ox * SCALE
            py = cy - oy * SCALE
            c.alpha_composite(ims[ni], (px, py))
        return c

    print("== composing player_hd ==")
    for sub in ("walk", "run", "idle", "attack"):
        (PLAYER_HD / sub).mkdir(parents=True, exist_ok=True)

    for d in range(8):
        for fi in range(4):
            composite(d, fi, "walk").save(PLAYER_HD / "walk" / f"{d}_{fi}.png")
            composite(d, fi, "run").save(PLAYER_HD / "run" / f"{d}_{fi}.png")
            if fi == 0:
                composite(d, 0, "walk").save(PLAYER_HD / "idle" / f"{d}_0.png")
                sub1 = ca_walk[d][0]
                for k in BODY:
                    ox, oy = P41.lookup_oxoy(body_oxoy[k][d], sub1, DEFAULT_OXOY[k])
                    anchors[k].append([ox * SCALE, oy * SCALE])
                rh_d = (d + RH_DIR_OFF) % 8
                rh_s = P41.loco_subs(RH_SID, RH_BASE, rh_d, which=0)[0]
                ox, oy = P41.lookup_oxoy(rh_oxoy[rh_d], rh_s, DEFAULT_OXOY["RH"])
                dox, doy = RH_NUDGE_SD.get(d, (0, 0))
                anchors["RH"].append([(ox + dox) * SCALE, (oy + doy) * SCALE])
        # attack
        n_ca = max(1, len(body_hd["CA"][d]))
        ai_sub = min(n_ca, max(ca_walk[d][-1] + 4, n_ca // 2))
        rh_d = (d + RH_DIR_OFF) % 8
        c = Image.new("RGBA", canvas, (0, 0, 0, 0))
        under = d in RH_UNDER_BODY
        order = ["RH", "CA", "TK", "HD"] if under else ["CA", "TK", "HD", "RH"]
        ni = min(n_ca - 1, ai_sub - 1)
        for k in order:
            if k == "RH":
                ims = rh_hd[rh_d]
                rni = min(len(ims) - 1, ni) if ims else 0
                ox, oy = P41.lookup_oxoy(rh_oxoy[rh_d], rni + 1, DEFAULT_OXOY["RH"])
                dox, doy = RH_NUDGE_SD.get(d, (0, 0))
                ox, oy = ox + dox, oy + doy
                if ims:
                    c.alpha_composite(ims[rni], (cx - ox * SCALE, cy - oy * SCALE))
            else:
                ims = body_hd[k][d]
                ox, oy = P41.lookup_oxoy(body_oxoy[k][d], ni + 1, DEFAULT_OXOY[k])
                if ims and ni < len(ims):
                    c.alpha_composite(ims[ni], (cx - ox * SCALE, cy - oy * SCALE))
        c.save(PLAYER_HD / "attack" / f"{d}_0.png")
        print(f"  dir {d} ({ART_DIR_NAMES[d]}) done")

    meta = {
        "dirs": 8,
        "walk_frames": 4,
        "run_frames": 4,
        "gait": "pingpong_012321",
        "hd": True,
        "scale": SCALE,
        "model": MODEL,
        "compose": "partwise_realesrgan_then_alpha_composite",
        "hotspot": [cx, cy],
        "hotspot_base": [CX, CY],
        "canvas": list(canvas),
        "source_canvas": list(CANVAS),
        "frame_order": "spr_loco_subs_walk0_run1",
        "ca_walk_subs": ca_walk,
        "ca_run_subs": ca_run,
        "dir_convention": "E→6 SE→7 S→0 SW→1 W→2 NW→3 N→4 NE→5; facing=(oct+6)%8",
        "art_dir_names": ART_DIR_NAMES,
        "rh_index": f"(body+{RH_DIR_OFF})%8",
        "rh_under_dirs": RH_UNDER_BODY,
        "rh_part": "RH_002",
        "rh_spr": RH_SID,
        "rh_base": RH_BASE,
        "rh_nudge_sd": {str(k): list(v) for k, v in RH_NUDGE_SD.items()},
        "anchors": anchors,
        "source": "Phase44 part-wise HD: ESRGAN parts + ox/oy×scale; RH_UNDER S..NE; grip locked",
    }
    (PLAYER_HD / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    return meta


def make_samples() -> list[str]:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    paths = []
    f = font(15)
    fsm = font(12)

    # after strip: same layout as before
    dirs = [0, 2, 4, 6]
    labels = ["S", "W", "N", "E"]
    cell = 200
    canvas = Image.new("RGBA", (cell * 4 + 20, cell * 2 + 70), (30, 30, 40, 255))
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), "AFTER: SD (top) vs part-compose HD (bottom) — hand on hilt", fill=(255, 255, 255, 255), font=f)
    for i, (di, lab) in enumerate(zip(dirs, labels)):
        sd = Image.open(PLAYER_SD / "walk" / f"{di}_0.png").convert("RGBA")
        hd = Image.open(PLAYER_HD / "walk" / f"{di}_0.png").convert("RGBA")
        sd2 = sd.copy(); sd2.thumbnail((cell - 10, cell - 10), Image.Resampling.NEAREST)
        hd2 = hd.copy(); hd2.thumbnail((cell - 10, cell - 10), Image.Resampling.LANCZOS)
        x = 10 + i * cell
        canvas.paste(sd2, (x + (cell - sd2.width) // 2, 36 + (cell - sd2.height) // 2), sd2)
        canvas.paste(hd2, (x + (cell - hd2.width) // 2, 46 + cell + (cell - hd2.height) // 2), hd2)
        d.text((x + 8, 34), f"{lab} SD", fill=(200, 200, 200, 255), font=fsm)
        d.text((x + 8, 44 + cell), f"{lab} HD", fill=(180, 220, 180, 255), font=fsm)
    p = SAMPLES / "rh_aligned_after.png"
    canvas.save(p); paths.append(str(p.relative_to(ROOT)))

    # 8-dir HD grip proof
    cell = 170
    grid = Image.new("RGBA", (cell * 8 + 16, cell + 50), (28, 28, 36, 255))
    d = ImageDraw.Draw(grid)
    d.text((8, 8), "rh_align_8dir — part-compose HD walk0 (hand on hilt, sword not floating)", fill=(240, 240, 240, 255), font=f)
    for di in range(8):
        hd = Image.open(PLAYER_HD / "walk" / f"{di}_0.png").convert("RGBA")
        hd2 = hd.copy(); hd2.thumbnail((cell - 8, cell - 8), Image.Resampling.LANCZOS)
        x = 8 + di * cell
        grid.paste(hd2, (x + (cell - hd2.width) // 2, 36 + (cell - 8 - hd2.height) // 2), hd2)
        d.text((x + 8, cell + 28), ART_DIR_NAMES[di], fill=(200, 200, 210, 255), font=fsm)
    p = SAMPLES / "rh_align_8dir.png"
    grid.save(p); paths.append(str(p.relative_to(ROOT)))

    # zoom crop on E grip for clarity
    hd = Image.open(PLAYER_HD / "walk" / "6_0.png").convert("RGBA")
    # crop torso/sword region
    crop = hd.crop((160, 80, 420, 360)).resize((520, 560), Image.Resampling.NEAREST)
    board = Image.new("RGBA", (540, 600), (30, 30, 40, 255))
    board.paste(crop, (10, 30), crop)
    ImageDraw.Draw(board).text((10, 6), "E walk0 HD zoom — expect fist on red grip", fill=(255, 255, 255, 255), font=f)
    p = SAMPLES / "rh_grip_zoom_E.png"
    board.save(p); paths.append(str(p.relative_to(ROOT)))

    print("samples", paths)
    return paths


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples-only", action="store_true")
    args = ap.parse_args()
    if not args.samples_only:
        if not ESR_BIN.exists():
            print("missing", ESR_BIN, file=sys.stderr)
            return 1
        meta = build()
        print("meta scale", meta["scale"], "hotspot", meta["hotspot"])
    make_samples()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
