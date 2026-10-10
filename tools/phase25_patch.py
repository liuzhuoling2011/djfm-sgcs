"""Phase 25: patch client for post-sy1=100 quest chain, soft DF, loot, PLI order."""
from pathlib import Path
import re

ROOT = Path('/workspace/djfm-sgcs')

# --- hud.ts: soft DF placeholder ---
hud = ROOT/'web/src/hud.ts'
t = hud.read_text()
t = t.replace(
"""// Damage: the original formula is not in any data table (searched mb/*.txt|ini, player/*); it lives in the exe.
// Working model: AT − DF/2, ±10%, min 1 (assumption, see PROGRESS Phase 17c).
export const dmg = (at: number, df: number) => Math.max(1, (at - df / 2) * (0.9 + Math.random() * 0.2))""",
"""// Damage: original formula is exe-only (not in mb tables). Working model AT−DF/2 ±10% min1.
// PLACEHOLDER soft-DF (Phase 25): RolePrivate DF 160–180 makes late act-1 do 1 dmg/hit forever at Init AT curve.
// Cap effective DF at 0.85×AT so growth from Init.txt (AT+4/lv) matters; remove when real formula is known.
export const dmg = (at: number, df: number) => {
  const soft = Math.min(df, at * 0.85)
  return Math.max(1, (at - soft / 2) * (0.9 + Math.random() * 0.2))
}
export const SOFT_DF = true // label for HUD/PROGRESS""")
# level-up already matches Init 男主角 AT+4 DF+4 HP+80
if 'SOFT_DF' not in hud.read_text() or 'soft =' not in t:
    hud.write_text(t)
    print('hud ok')
else:
    hud.write_text(t); print('hud updated')

# --- dialog.ts: SetLockTextID, SetBldStatus via onRem-like hooks ---
dlg = ROOT/'web/src/dialog.ts'
d = dlg.read_text()
if 'onBld?' not in d:
    d = d.replace(
        "export type RemHook = (eventId: string, mode: 'rem' | 'reset' | 'table', slot?: number, val?: number) => void",
        "export type RemHook = (eventId: string, mode: 'rem' | 'reset' | 'table', slot?: number, val?: number) => void\n"
        "export type BldHook = (name: string, status: number) => void\n"
        "export type LockHook = (name: string, textId: number) => void\n"
        "export type DeadCheck = (eventId: string) => boolean")
    d = d.replace('  onRem?: RemHook', '  onRem?: RemHook\n  onBld?: BldHook\n  onLock?: LockHook\n  isDead?: DeadCheck\n  lockText: Record<string, number> = {}\n  bldStatus: Record<string, number> = {}')
    d = d.replace(
        "      } else if (op === 'setflagtable' && p.length >= 4) {\n        this.onRem?.(p[1].toLowerCase(), 'table', Number(p[2]), Number(p[3]))\n      }",
        "      } else if (op === 'setflagtable' && p.length >= 4) {\n        this.onRem?.(p[1].toLowerCase(), 'table', Number(p[2]), Number(p[3]))\n      }"
        " else if (op === 'setbldstatus' && p.length >= 3) {\n        this.bldStatus[p[1].toLowerCase()] = Number(p[2]); this.onBld?.(p[1].toLowerCase(), Number(p[2]))\n      }"
        " else if (op === 'setlocktextid' && p.length >= 3) {\n        this.lockText[p[1].toLowerCase()] = Number(p[2]); this.onLock?.(p[1].toLowerCase(), Number(p[2]))\n      }")
    # IsBldStatus / IsDead / IsPropInBody in evalCond
    d = d.replace(
        "    if (p[0] === 'IsProp' && p.length >= 2) {\n      return inv?.hasProp(Number(p[1])) ?? false\n    }\n    return true // unknown predicates ignored",
        "    if (p[0] === 'IsProp' && p.length >= 2) {\n      const has = inv?.hasProp(Number(p[1])) ?? false\n      if (p.length >= 3 && Number(p[2]) === 0) return !has\n      return has\n    }\n"
        "    if (p[0] === 'IsPropInBody' && p.length >= 2) {\n      const has = inv?.hasProp(Number(p[1])) ?? false\n      if (p.length >= 3 && Number(p[2]) === 0) return !has\n      return has\n    }\n"
        "    if (p[0] === 'IsBldStatus' && p.length >= 3) {\n      // evaluated in main via dlg.bldStatus; here read from a module-level bridge set on DialogSys\n      return true // deferred — scene scripts not evalCond\n    }\n"
        "    if (p[0] === 'IsDead' && p.length >= 2) {\n      return true // deferred to scene runner\n    }\n"
        "    return true // unknown predicates ignored")
    dlg.write_text(d); print('dialog ok')
else:
    print('dialog already patched')

print('base patches done')
