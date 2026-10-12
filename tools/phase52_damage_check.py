#!/usr/bin/env python3
"""Phase 52 — print sample AT/DF → expected mid-roll damage (new vs legacy).

Default model (HEURISTIC magnitude, VERIFIED direction): dealt = AT * 1.0 mid (±10% in game)
Legacy PLACEHOLDER: dealt = (AT - min(DF, AT*0.85)/2) * 1.0 mid
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def mid_at(at: float) -> float:
    return max(1.0, at * 1.0)  # mid of 0.9..1.1 is 1.0


def mid_legacy(at: float, df: float, soft: bool = False) -> float:
    use = min(df, at * 0.85) if soft else df
    return max(1.0, (at - use / 2) * 1.0)


def main() -> int:
    g = json.loads((ROOT / "web/public/game/data/game.json").read_text(encoding="utf-8"))
    combat = g["combat"]
    init = combat["init_male"]
    pat, pdf = float(init["at"]), float(init["df"])

    # Act-1 sample foes from RolePrivate (raw) + typical scene_tier-1 caps
    foes = [
        ("食腐僵尸 raw", 120, 24, 150),
        ("持刀鬼兵 raw", 140, 37, 300),
        ("野猪 raw", 210, 43, 2100),
        ("tier1 capped trash", 22, 28, 220),  # game.json at_cap/df_cap/hp_cap[0]
    ]
    df_cap0 = combat["df_cap"][0]
    at_cap0 = combat["at_cap"][0]
    hp_cap0 = combat["hp_cap"][0]

    print("=== Phase 52 damage check ===")
    print(f"model: {combat.get('damage_model')} | note: {combat['note'][:80]}...")
    print(f"player lv1 Init AT={pat} DF={pdf} HP={init['hp']}")
    print()
    print(f"{'case':24s} {'AT':>6} {'DF':>6} {'new≈AT':>8} {'legacy':>8} {'hits_to_kill@HP':>16}")
    # player → foe
    for name, at, df, hp in [
        ("P→僵尸", pat, 24, 150),
        ("P→鬼兵", pat, 37, 300),
        ("P→野猪", pat, 43, 2100),
        ("P→tier1cap", pat, df_cap0, hp_cap0),
    ]:
        n, leg = mid_at(pat), mid_legacy(pat, df)
        hits = int((hp + n - 1) // n)
        print(f"{name:24s} {pat:6.0f} {df:6.0f} {n:8.1f} {leg:8.1f} {hits:16d} (hp={hp})")
    print()
    # foe → player
    php = float(init["hp"])
    for name, at, df, _hp in foes[:3]:
        n, leg = mid_at(at), mid_legacy(at, pdf)
        print(f"{'F→P '+name:24s} {at:6.0f} {pdf:6.0f} {n:8.1f} {leg:8.1f}  P_hp_left≈{php-n:.0f}")
    # capped foe → player
    n = mid_at(at_cap0)
    print(f"{'F→P tier1cap':24s} {at_cap0:6.0f} {pdf:6.0f} {n:8.1f} {mid_legacy(at_cap0,pdf):8.1f}  P_hp_left≈{php-n:.0f}")

    # sanity: high DF no longer nullifies player damage
    fox_df = 171
    new_v = mid_at(pat)
    leg_raw = mid_legacy(pat, fox_df, soft=False)
    leg_soft = mid_legacy(pat, fox_df, soft=True)
    ok = new_v >= 30 and leg_raw <= 1.01
    print()
    print(f"P→狐猴DF{fox_df}: new={new_v:.1f} legacy_raw={leg_raw:.1f} legacy_soft={leg_soft:.1f}")
    print(f"  [{'OK: new keeps AT; raw AT-DF/2 floors to 1' if ok else 'CHECK'}]")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
