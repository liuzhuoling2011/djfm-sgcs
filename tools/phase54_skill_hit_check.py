#!/usr/bin/env python3
"""Phase 54 — skill.txt 命中率 → effectiveHit → Phase53 hitChance.

Mirrors web/src/hud.ts effectiveHit + hitChance.
F1 扫叶(id6) hit=1; F2 疾电(id35) hit=1 (both ×1 character hit).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P_MIN, P_MAX = 0.08, 0.95
GUARANTEE_AT = 100
GUARANTEE_VAL = 1e6


def effective_hit(base: float, skill_hit) -> float:
    H = max(0.0, float(base))
    if skill_hit is None or skill_hit == "":
        return H
    try:
        v = float(skill_hit)
    except (TypeError, ValueError):
        return H
    if v == 0:
        return H
    if v >= GUARANTEE_AT:
        return GUARANTEE_VAL
    if v < 0:
        return max(0.0, H + v)
    return H * v


def hit_chance(hit: float, dodge: float) -> float:
    h, d = max(0.0, hit), max(0.0, dodge)
    if h + d <= 0:
        return P_MAX
    return max(P_MIN, min(P_MAX, h / (h + d)))


def main() -> int:
    skills = json.loads((ROOT / "web/public/game/data/skills.json").read_text(encoding="utf-8"))
    init = json.loads((ROOT / "web/public/game/data/init.json").read_text(encoding="utf-8"))
    g = json.loads((ROOT / "web/public/game/data/game.json").read_text(encoding="utf-8"))
    base = float(g["combat"]["init_male"]["hit"])  # 21
    df = 37.0  # 持刀鬼兵 DF

    left_id = str(init["skill_left"])   # 6 扫叶
    right_id = str(init["skill_right"])  # 35 疾电
    saoye = skills[left_id]
    jidian = skills[right_id]

    print("=== Phase 54 skill hit check ===")
    print(f"F1 id={left_id} {saoye['name']} hit={saoye.get('hit')} at_mult={saoye.get('at_mult')}")
    print(f"F2 id={right_id} {jidian['name']} hit={jidian.get('hit')} at_mult={jidian.get('at_mult')}")
    print(f"player Init hit={base} vs DF={df}")

    cases = []
    # normal melee
    eh = effective_hit(base, None)
    p = hit_chance(eh, df)
    cases.append(("Space melee", eh, p, abs(eh - base) < 1e-9 and 0.30 <= p <= 0.40))

    # F1 扫叶 hit=1 → same as melee
    eh1 = effective_hit(base, saoye.get("hit"))
    p1 = hit_chance(eh1, df)
    cases.append(("F1 扫叶 hit=1", eh1, p1, abs(eh1 - base) < 1e-9 and abs(p1 - p) < 1e-9))

    # F2 疾电 hit=1 → same as melee
    eh2 = effective_hit(base, jidian.get("hit"))
    p2 = hit_chance(eh2, df)
    cases.append(("F2 疾电 hit=1", eh2, p2, abs(eh2 - base) < 1e-9 and abs(p2 - p) < 1e-9))

    # synthetic multiplier 2
    eh_m = effective_hit(base, 2)
    p_m = hit_chance(eh_m, df)
    cases.append(("synth hit×2", eh_m, p_m, abs(eh_m - 42) < 1e-9 and p_m > p + 0.05))

    # synthetic guarantee 999
    eh_g = effective_hit(base, 999)
    p_g = hit_chance(eh_g, df)
    cases.append(("synth hit=999", eh_g, p_g, eh_g >= GUARANTEE_AT and abs(p_g - P_MAX) < 1e-9))

    # negative additive
    eh_n = effective_hit(base, -10)
    cases.append(("synth hit-10", eh_n, hit_chance(eh_n, df), abs(eh_n - 11) < 1e-9))

    print(f"{'case':22s} {'effHit':>8} {'p vs DF37':>10}  status")
    ok_all = True
    for label, ehv, pv, ok in cases:
        ok_all = ok_all and ok
        print(f"{label:22s} {ehv:8.1f} {pv:10.3f}  {'OK' if ok else 'BAD'}")

    hud = (ROOT / "web/src/hud.ts").read_text(encoding="utf-8")
    main_ts = (ROOT / "web/src/main.ts").read_text(encoding="utf-8")
    wired = (
        "effectiveHit" in hud
        and "skillHit" in main_ts
        and "skillHit: sk?.hit" in main_ts
    )
    print(f"code wired: {'OK' if wired else 'BAD'}")
    ok_all = ok_all and wired

    # table confirms F1/F2 both 1
    table_ok = str(saoye.get("hit")) == "1" and str(jidian.get("hit")) == "1"
    print(f"table F1/F2 hit==1: {'OK' if table_ok else 'BAD'}")
    ok_all = ok_all and table_ok

    print("RESULT:", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
