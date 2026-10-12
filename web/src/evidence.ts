/**
 * Phase 51 — table / script evidence for act-1 vertical slice.
 *
 * Labels:
 *   VERIFIED  = read from original mb tables / scene scripts (fol extract)
 *   HEURISTIC = remake world-unit scale or timing fitted to prior Wine feel
 *   PLACEHOLDER = still unknown (hit/dodge eq; DF4..DF0; difficulty AT scale)
 *
 * REA: ComeOn.exe opened OK (sha256 97ae4c23…, PE32 x86). binary_overview timed out;
 * search_strings / list_strings / search_procedures returned MCP schema errors
 * (missing result/evidence_id) — same class of failure as Phase 18c. No address-level
 * move/damage constants this run. Static tables below are the evidence source.
 */

/** RolePrivate.txt 男主角 lv1 — columns 战斗速度 / 跑步速度 */
export const ROLE_PRIVATE_MALE = {
  roleId: 4,
  level: 1,
  /** VERIFIED mb/RolePrivate.txt col 战斗速度 */
  fightSpeed: 8,
  /** VERIFIED mb/RolePrivate.txt col 跑步速度 */
  runSpeed: 16,
  at: 40,
  df: 30,
  hp: 70,
} as const

/** mb/player/Init.txt 男主角 — 移动速度 + stamina drain while running */
export const INIT_MALE_MOVE = {
  /** VERIFIED Init.txt col 移动速度 */
  moveSpeed: 16,
  /** VERIFIED Init.txt Stamina消耗率 (points/s while running) */
  staminaUse: 10,
  /** VERIFIED Init.txt Stamina回復率 */
  staminaRegen: 3,
  /** VERIFIED Init.txt Stamina base */
  stamina: 80,
} as const

/**
 * Remake cell-units/sec. Foes already use `spd / FOE_SPD_DIV`.
 * Choose walk so RolePrivate fightSpeed maps to prior remake walk (~4.5):
 *   CELL_SCALE = fightSpeed / 4.5 ≈ 1.777…
 * Then run = runSpeed / CELL_SCALE = 16/1.777… = 9.0 (table ratio 2× walk).
 *
 * Wine hold GIFs previously suggested ~1.45× walk (HEURISTIC 6.5); Phase 51
 * prefers the VERIFIED RolePrivate 8:16 ratio and keeps walk feel stable.
 */
export const FOE_SPD_DIV = 3.8 // existing remake divisor in hud.stepFoes (HEURISTIC)
export const CELL_SCALE_HEURISTIC = ROLE_PRIVATE_MALE.fightSpeed / 4.5
export const PLAYER_WALK_CELLS =
  ROLE_PRIVATE_MALE.fightSpeed / CELL_SCALE_HEURISTIC // 4.5
export const PLAYER_RUN_CELLS =
  ROLE_PRIVATE_MALE.runSpeed / CELL_SCALE_HEURISTIC // 9.0

/**
 * Skill.ini rows 剑客_普通攻击1 — float triplet near action body reads 0.3 / 0.3 / 1.0
 * (first combo). Full column map not RE'd; treat as table-backed HEURISTIC for
 * remake melee duration / hit threshold.
 */
export const MELEE = {
  /** HEURISTIC from Skill.ini 剑客_普通攻击1 (~0.3s) + prior Wine windup 0.34 */
  durationS: 0.34,
  /** Hit when remaining attackT crosses this (lands ~0.14s into swing) */
  hitWhenRemainingS: 0.2,
  /** game.json attack.range — Skill stub */
  range: 1.75,
  /** See DAMAGE — on-hit no longer subtracts DF */
  damageNote: 'on-hit ≈ AT±10% (DF is dodge; see DAMAGE)',
} as const

/**
 * Melee on-hit damage (Phase 52).
 *
 * VERIFIED (design / tables, not exe address):
 * - Community FAQ (刀剑封魔录系列): 防御≈闪避 — DF lowers enemy hit chance, does NOT
 *   subtract from damage when a hit lands. HP vs AT decides survivability on contact.
 *   Source: game773 FAQ mirrored in PROGRESS Phase 52.
 * - Tables separate 命中率 (Init / RolePrivate) and 闪避率 (RolePrivate) from AT/DF;
 *   skill.txt 「加攻击力」 scales AT for skills, not a DF term.
 * - define.ini only documents poison/fire DoT rates — no physical AT−DF formula.
 *
 * HEURISTIC:
 * - On-hit: max(1, AT * U(0.9,1.1)) — DF unused in damage path.
 * - ±10% keep prior remake variance feel.
 *
 * LEGACY / debug:
 * - ?softdf=1 or ?legacydf=1 → old AT−DF/2 ±10% (Phase 17c PLACEHOLDER) for A/B.
 *
 * Still unresolved (PLACEHOLDER): Init DF4..DF0 meaning; difficulty AT/HP scale.
 */
export const DAMAGE = {
  model: 'at_flat' as const,
  varianceMin: 0.9,
  varianceMax: 1.1,
  minDealt: 1,
  label: 'VERIFIED-direction / HEURISTIC-magnitude: on-hit≈AT±10%; DF→dodge not mitigation',
  legacyNote: 'AT-DF/2 ±10% only with ?softdf=1 or ?legacydf=1',
} as const

/**
 * 瓦当镇北门 → 1-1s
 * scene/1-0s.txt: IsScnIn*IsFlag sy1 1 1 → SetExitTextID 1-1s 308
 * talk/sy.txt #1: IsFlag sy1 1 1 → SetFlag sy1 1 * SetExitTextID 1-1s -1
 * Text.txt 308: 是谁救了我？得先向他道谢才是。
 * IsFlag mode 1 ≈ flag < value (same convention as other act-1 locks).
 */
export const NORTH_GATE = {
  dest: '1-1s',
  flag: 'sy1',
  unlockAt: 1,
  lockDialogId: 308,
  lockDialogZh: '是谁救了我？得先向他道谢才是。',
  sources: [
    'mb/trigger/scene/1-0s.txt',
    'mb/trigger/talk/sy.txt',
    'mb/Text.txt#308',
  ],
} as const


/**
 * Hit / dodge (Phase 53).
 *
 * VERIFIED (tables + FAQ, not exe address):
 * - Init.txt 男主角: 命中率=21, +3/lv (also game.json combat.init_male.hit).
 * - RolePrivate: 命中率 filled per foe; 闪避率 column empty on all 249 rows (meta.eva=0).
 * - Series FAQ: 防御≈闪避 — when 闪避率 is empty, use DF as dodge stat.
 * - skill.txt 「命中率」 for basic skills is usually 1 (treat as ×1); large values (999) ≈ guarantee.
 * - define.ini: no hit/dodge equation.
 *
 * HEURISTIC probability (no exe formula found):
 *   dodgeEff = eva > 0 ? eva : df
 *   pHit = clamp( hit / (hit + dodgeEff), 0.08, 0.95 )
 * Same units for hit & DF in RolePrivate make a ratio model the natural HEURISTIC.
 */
export const HIT = {
  model: 'ratio' as const,
  pMin: 0.08,
  pMax: 0.95,
  /** Init.txt 男主角 base / per-level */
  playerHitBase: 21,
  playerHitPerLv: 3,
  label: 'VERIFIED stats (命中/DF→dodge); HEURISTIC p=hit/(hit+dodgeEff) clamped',
} as const

/** Facing art column — keep unless address-level REA proves otherwise */
export const FACING_OCT_OFFSET = 6 // facing = (oct + 6) % 8
