// Phase 15: original HUD (ResJM.Lib.chs) + HP/MP orbs + simple combat model.
export type Foe = {
  x: number; y: number; hp: number; maxHp: number; cd: number; hitT: number; dead: number
  at?: number; df?: number; exp?: number; sight?: number; spd?: number; name?: string; set?: number | string
  hx?: number; hy?: number; act?: 'idle' | 'walk' | 'attack' | 'hurt' | 'death'; actT?: number; dir?: number
  kbX?: number; kbY?: number; gone?: boolean; event?: string
}
export type Stats = { hp: number; maxHp: number; mp: number; maxMp: number; exp: number; lvl: number; at?: number; df?: number; sp?: number }
/** mb/player/Init.txt 男主角 growth */
export type InitGrowth = {
  at: number; at_per_lv: number; df: number; df_per_lv: number
  hp: number; hp_per_lv: number; mp: number; mp_per_lv: number
  stamina?: number; stamina_per_lv?: number; exp_per_lv?: number
  hp_regen?: number; mp_regen?: number; stamina_regen?: number; stamina_use?: number
}
export const DEFAULT_INIT: InitGrowth = {
  at: 40, at_per_lv: 4, df: 30, df_per_lv: 4, hp: 800, hp_per_lv: 80, mp: 36, mp_per_lv: 1.2,
  stamina: 80, stamina_per_lv: 0.4, exp_per_lv: 100, hp_regen: 1.4, mp_regen: 1.2, stamina_regen: 3, stamina_use: 10,
}
export let INIT = { ...DEFAULT_INIT }
export function setInitGrowth(g: Partial<InitGrowth>) { INIT = { ...DEFAULT_INIT, ...g } }
/** Apply Init.txt stats for absolute level (1-based). */
export function applyInitLevel(st: Stats, lvl: number) {
  const L = Math.max(1, Math.floor(lvl))
  const n = L - 1
  st.lvl = L
  st.at = INIT.at + INIT.at_per_lv * n
  st.df = INIT.df + INIT.df_per_lv * n
  st.maxHp = INIT.hp + INIT.hp_per_lv * n
  st.maxMp = INIT.mp + INIT.mp_per_lv * n
  st.hp = Math.min(st.hp, st.maxHp)
  st.mp = Math.min(st.mp, st.maxMp)
}
export function tryLevelUp(st: Stats): boolean {
  const need = (INIT.exp_per_lv ?? 100) * st.lvl
  if (st.exp < need) return false
  st.exp -= need
  applyInitLevel(st, st.lvl + 1)
  st.hp = st.maxHp
  st.mp = st.maxMp
  return true
}
// Damage: original formula is exe-only. Working model AT−DF/2 ±10% min1 (PROGRESS Phase 17c).
// Soft-DF formula hack is OPT-IN only (?softdf=1). Default uses raw DF; act-1 playability comes from
// PLACEHOLDER foe stat caps in main.ts (game.json combat.scene_tier), not this formula.
export let SOFT_DF = false
export function setSoftDf(on: boolean) { SOFT_DF = on }
export const dmg = (at: number, df: number) => {
  const use = SOFT_DF ? Math.min(df, at * 0.85) : df
  return Math.max(1, (at - use / 2) * (0.9 + Math.random() * 0.2))
}

/** Remake tuning (not from tables): late-map trash density / leash — see game.json combat.remake */
export let REMAKE = { sight_cap: 5.5, leash: 9, max_trash: 12, trash_scenes: ['1-9s','1-10s','1-10a1s','1-10a2s','1-10a3s','1-10a4s','1-10a5s','1-10a6s','1-11s'] as string[] }
export function setRemakeTuning(t: Partial<typeof REMAKE>) { REMAKE = { ...REMAKE, ...t, trash_scenes: t.trash_scenes ?? REMAKE.trash_scenes } }

export type FloatDmg = { x: number; y: number; text: string; t: number; max: number; crit?: boolean; color?: string }


const L = (s: string) => new Promise<HTMLImageElement>((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = no; i.src = s })

export class Hud {
  mapFrame?: HTMLImageElement
  /** Kept so potion hotkeys can still mirror counts; the bar itself is #hud in the DOM. */
  pots = [2, 2, 2, 2]
  async load(base = 'game/hud') {
    try { this.mapFrame = await L(`${base}/jm_1549.png`) } catch { /* minimap optional */ }
  }
  /**
   * Status chrome (HP/MP, potions, weapon/Q, money) is the HTML bar in main.ts.
   * Drawing used to scale jm_1478 across the canvas; that strip is no longer painted.
   */
  draw(_ctx: CanvasRenderingContext2D, _s: Stats, _extra?: { skillL?: string; skillR?: string; money?: number; weapon?: string; potCd?: number; potCdMax?: number; attackCd?: number; attackReady?: boolean }) {
    /* DOM */
  }
  // Minimap frame stays on the canvas corner. Status numbers live in the HTML bar.
  drawMinimap(ctx: CanvasRenderingContext2D, ground: CanvasImageSource | null, gx: number, gy: number, k: number,
    dots: { x: number; y: number; c: string }[], name: string) {
    if (!this.mapFrame) return
    const sc = ctx.canvas.width / 800
    const smooth = ctx.imageSmoothingEnabled
    ctx.save()
    ctx.imageSmoothingEnabled = true
    ctx.translate(ctx.canvas.width - 137 * sc, 0)
    ctx.scale(sc, sc)
    const ix = 6, iy = 6, iw = 125, ih = 98
    ctx.save(); ctx.beginPath(); ctx.rect(ix, iy, iw, ih); ctx.clip()
    ctx.fillStyle = '#000'; ctx.fillRect(ix, iy, iw, ih)
    if (ground) ctx.drawImage(ground, gx - iw / 2 / k, gy - ih / 2 / k, iw / k, ih / k, ix, iy, iw, ih)
    for (const d of dots) { ctx.fillStyle = d.c; ctx.fillRect(Math.round(ix + iw / 2 + (d.x - gx) * k) - 1, Math.round(iy + ih / 2 + (d.y - gy) * k) - 1, 3, 3) }
    ctx.restore()
    ctx.drawImage(this.mapFrame, 0, 0)
    ctx.fillStyle = '#e8e8e8'; ctx.font = '11px ui-sans-serif,system-ui'; ctx.textAlign = 'center'
    ctx.fillText(name, 68, 122); ctx.textAlign = 'left'
    ctx.restore()
    ctx.imageSmoothingEnabled = smooth
  }
}

export function stepFoes(foes: Foe[], p: { x: number; y: number }, st: Stats, dt: number, walk: (x: number, y: number) => boolean) {
  for (const f of foes) {
    f.actT = (f.actT ?? 0) + dt
    if (f.gone) continue
    if (f.dead > 0) {
      f.act = 'death'; f.dead -= dt
      // play death anim ~1.2s then remove (was 12s respawn)
      if (f.dead <= 0) { f.gone = true; f.act = 'death' }
      continue
    }
    f.cd -= dt; f.hitT = Math.max(0, f.hitT - dt)
    // knockback while hurt
    if (f.hitT > 0 && (f.kbX || f.kbY)) {
      const nx = f.x + (f.kbX ?? 0) * dt, ny = f.y + (f.kbY ?? 0) * dt
      if (walk(nx, f.y)) f.x = nx
      if (walk(f.x, ny)) f.y = ny
    }
    const dx = p.x - f.x, dy = p.y - f.y, d = Math.hypot(dx, dy)
    const homeX = f.hx ?? f.x, homeY = f.hy ?? f.y
    const homeD = Math.hypot(p.x - homeX, p.y - homeY)
    const sight = Math.min(f.sight ?? 7, REMAKE.sight_cap)
    // Leash: stop chasing far from spawn home (remake tuning)
    const aggro = d < sight && homeD < REMAKE.leash
    if (d > 0.01) f.dir = (Math.round(Math.atan2(dy, dx) / (Math.PI / 4)) + 8) % 8
    if (f.hitT > 0) { f.act = 'hurt'; continue }
    if (f.act === 'attack' && (f.actT ?? 0) < 0.55) continue
    if (!aggro && homeD > 0.4) {
      // return home slowly
      const hx = homeX - f.x, hy = homeY - f.y, hd = Math.hypot(hx, hy) || 1
      const sp = 1.6 * dt, nx = f.x + hx / hd * sp, ny = f.y + hy / hd * sp
      if (walk(nx, f.y)) f.x = nx
      if (walk(f.x, ny)) f.y = ny
      if (f.act !== 'walk') { f.act = 'walk'; f.actT = 0 }
    } else if (aggro && d > 1.1) {
      const sp = (f.spd ? f.spd / 3.8 : 2.0) * dt, nx = f.x + dx / d * sp, ny = f.y + dy / d * sp
      if (walk(nx, f.y)) f.x = nx
      if (walk(f.x, ny)) f.y = ny
      if (f.act !== 'walk') { f.act = 'walk'; f.actT = 0 }
    } else if (aggro && d <= 1.3 && f.cd <= 0) {
      st.hp -= dmg(f.at ?? 20, st.df ?? 10); f.cd = 1.5; f.act = 'attack'; f.actT = 0
    } else if (f.act !== 'idle') { f.act = 'idle'; f.actT = 0 }
  }
}

// melee arc: hits foes within range in facing half-plane
export function playerAttack(foes: Foe[], p: { x: number; y: number }, facingAng: number, st: Stats, range = 1.55): FloatDmg[] {
  const floats: FloatDmg[] = []
  for (const f of foes) {
    if (f.dead > 0 || f.gone) continue
    const dx = f.x - p.x, dy = f.y - p.y, d = Math.hypot(dx, dy)
    if (d > range) continue
    const a = Math.atan2(dy, dx), diff = Math.abs(Math.atan2(Math.sin(a - facingAng), Math.cos(a - facingAng)))
    // Phase 36: tighter cone + short knockback (Wine melee, not arcade shove)
    if (d < 0.85 || diff < 0.92) {
      const dealt = dmg(st.at ?? 40, f.df ?? 10)
      f.hp -= dealt; f.hitT = 0.22; f.act = 'hurt'; f.actT = 0
      if (d > 0.01) { f.kbX = (dx / d) * 1.75; f.kbY = (dy / d) * 1.75 }
      floats.push({ x: f.x, y: f.y, text: String(Math.round(dealt)), t: 0.55, max: 0.55, crit: dealt > (st.at ?? 40) * 0.75 })
      if (f.hp <= 0) { f.dead = 0.9; f.actT = 0; st.exp += f.exp ?? 25; while (tryLevelUp(st)) { /* Init.txt growth */ } }
    }
  }
  return floats
}
