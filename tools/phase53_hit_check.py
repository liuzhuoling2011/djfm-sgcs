#!/usr/bin/env python3
"""Phase 53 — deterministic hitChance samples (must match web/src/hud.ts HEURISTIC).

p = clamp( hit / (hit + dodgeEff), 0.08, 0.95 )
dodgeEff = eva if eva > 0 else df   # RolePrivate 闪避率 empty → DF (FAQ 防御≈闪避)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P_MIN, P_MAX = 0.08, 0.95


def dodge_stat(df: float, eva: float = 0.0) -> float:
    return eva if eva > 0 else max(0.0, df)


def hit_chance(hit: float, dodge: float) -> float:
    h, d = max(0.0, hit), max(0.0, dodge)
    if h + d <= 0:
        return P_MAX
    return max(P_MIN, min(P_MAX, h / (h + d)))


def main() -> int:
    g = json.loads((ROOT / "web/public/game/data/game.json").read_text(encoding="utf-8"))
    init = g["combat"]["init_male"]
    ph = float(init["hit"])
    ph10 = ph + float(init["hit_per_lv"]) * 9  # lv10

    cases = [
        # label, atk_hit, def_df, def_eva, expect_lo, expect_hi (inclusive band)
        ("P lv1 → 僵尸 DF24", ph, 24, 0, 0.40, 0.50),       # 21/45=0.466
        ("P lv1 → 鬼兵 DF37", ph, 37, 0, 0.30, 0.40),       # 21/58=0.362
        ("P lv1 → tier1 DF28", ph, 28, 0, 0.40, 0.48),      # 21/49=0.429
        ("P lv1 → 狐猴 DF171", ph, 171, 0, 0.08, 0.15),     # 21/192=0.109
        ("P lv10 → 鬼兵 DF37", ph10, 37, 0, 0.50, 0.62),    # 48/85=0.565
        ("僵尸 hit20 → P DF30", 20, 30, 0, 0.35, 0.45),      # 20/50=0.40
        ("eva override", 40, 100, 10, 0.75, 0.85),          # 40/50=0.80 (eva wins)
        ("floor clamp", 1, 1000, 0, 0.08, 0.08),            # → pMin
    ]

    print("=== Phase 53 hit/dodge check ===")
    print(f"model: {g['combat'].get('hit_model')} | player hit lv1={ph} lv10={ph10}")
    print(f"{'case':28s} {'hit':>5} {'dodge':>6} {'p':>7}  status")
    ok_all = True
    for label, hit, df, eva, lo, hi in cases:
        dodge = dodge_stat(df, eva)
        p = hit_chance(hit, dodge)
        ok = lo - 1e-9 <= p <= hi + 1e-9
        ok_all = ok_all and ok
        print(f"{label:28s} {hit:5.0f} {dodge:6.0f} {p:7.3f}  {'OK' if ok else 'BAD'} (expect {lo:.2f}..{hi:.2f})")

    # evidence.ts / hud must mention HIT
    ev = (ROOT / "web/src/evidence.ts").read_text(encoding="utf-8")
    hud = (ROOT / "web/src/hud.ts").read_text(encoding="utf-8")
    wired = "export const HIT" in ev and "hitChance" in hud and "rollHit" in hud and "MISS" in hud
    print(f"code wired (HIT+rollHit+MISS): {'OK' if wired else 'BAD'}")
    ok_all = ok_all and wired

    # never guaranteed: cone foe with DF>0 must have p < 1
    p_z = hit_chance(ph, dodge_stat(24))
    print(f"not guaranteed vs DF24: p={p_z:.3f} < 1.0 → {'OK' if p_z < 1 else 'BAD'}")
    ok_all = ok_all and p_z < 1

    print("RESULT:", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
