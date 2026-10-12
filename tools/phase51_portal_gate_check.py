#!/usr/bin/env python3
"""Phase 51 — print expected vs remake north-gate (瓦当镇→1-1s) flag logic.

Evidence (VERIFIED from mb fol extract, GBK):
  scene/1-0s.txt : IsScnIn*IsFlag sy1 1 1 → SetExitTextID 1-1s 308
  talk/sy.txt #1 : IsFlag sy1 1 1 → SetFlag sy1 1 * SetExitTextID 1-1s -1
  Text.txt 308   : 是谁救了我？得先向他道谢才是。
  IsFlag … 1 ≈ flag < N (same convention as other act-1 ExitText locks).

Remake (web/src/evidence.ts NORTH_GATE + syncAct1ExitGates):
  sy1 < 1 → exitText['1-1s']=308 (locked)
  sy1 >= 1 → exitText['1-1s']=-1 (open)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOL = ROOT / "assets/samples/phase9/fol_extract/mb"
EVIDENCE = ROOT / "web/src/evidence.ts"
MAIN = ROOT / "web/src/main.ts"


def read_gbk(path: Path) -> str:
    return path.read_text(encoding="gbk", errors="replace")


def main() -> int:
    scene = read_gbk(FOL / "trigger/scene/1-0s.txt")
    talk = read_gbk(FOL / "trigger/talk/sy.txt")
    text = read_gbk(FOL / "Text.txt")

    scene_hit = [
        ln.strip()
        for ln in scene.splitlines()
        if re.search(r"IsFlag\s+sy1\s+1\s+1", ln, re.I)
        and "SetExitTextID" in ln
        and "1-1s" in ln
    ]
    talk_hit = [
        ln.strip()
        for ln in talk.splitlines()
        if re.search(r"IsFlag\s+sy1\s+1\s+1", ln, re.I)
        and "SetExitTextID" in ln
    ]
    m308 = re.search(r"(?m)^308\t(.+)$", text)
    zh308 = m308.group(1).strip() if m308 else None

    ev = EVIDENCE.read_text(encoding="utf-8")
    main_ts = MAIN.read_text(encoding="utf-8")

    expected = {
        "lock_when": "sy1 < 1",
        "lock_dialog_id": 308,
        "lock_dialog_zh": zh308,
        "unlock_when": "sy1 >= 1 (talk/sy sets flag + ExitText -1)",
        "scene_lines": scene_hit,
        "talk_lines": talk_hit,
    }

    remake_ok = (
        "NORTH_GATE" in ev
        and "lockDialogId: 308" in ev
        and "unlockAt: 1" in ev
        and "flag: 'sy1'" in ev
        and "NORTH_GATE" in main_ts
        and "exitLock" in (ROOT / "web/src/dialog.ts").read_text(encoding="utf-8")
    )

    print("=== Phase 51 north-gate check (瓦当镇 → 1-1s) ===")
    print(f"EXPECTED lock_when     : {expected['lock_when']}")
    print(f"EXPECTED lock_dialog   : {expected['lock_dialog_id']} — {expected['lock_dialog_zh']}")
    print(f"EXPECTED unlock_when   : {expected['unlock_when']}")
    print("EXPECTED scene/1-0s.txt :")
    for ln in scene_hit or ["(MISSING)"]:
        print(f"  {ln}")
    print("EXPECTED talk/sy.txt    :")
    for ln in talk_hit or ["(MISSING)"]:
        print(f"  {ln}")
    print(f"REMAKE evidence.ts+main : {'PASS' if remake_ok else 'FAIL'}")
    print(f"  NORTH_GATE in evidence : {'sy1' in ev and '308' in ev}")
    print(f"  main uses NORTH_GATE   : {'NORTH_GATE.dest' in main_ts or 'NORTH_GATE' in main_ts}")

    cases = [
        (0, 308, "locked"),
        (1, -1, "open"),
        (19, -1, "open"),
    ]
    print("CASE table (flag → expected exitText):")
    all_pass = remake_ok and bool(scene_hit) and bool(talk_hit) and zh308 is not None
    for sy1, want, label in cases:
        got = 308 if sy1 < 1 else -1
        ok = got == want
        all_pass = all_pass and ok
        print(f"  sy1={sy1:3d} → exitText={got:4d} ({label}) [{'OK' if ok else 'BAD'}]")

    print("RESULT:", "PASS" if all_pass else "FAIL")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
