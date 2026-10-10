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

/** Wine 800×600 menu cluster, bar-relative (jm_515–520 matched on wine_alive). */
const MENU_ICONS: { file: string; x: number; y: number }[] = [
  { file: 'jm_516', x: 728, y: 22 },
  { file: 'jm_515', x: 756, y: 23 },
  { file: 'jm_517', x: 708, y: 48 },
  { file: 'jm_518', x: 771, y: 48 },
  { file: 'jm_520', x: 708, y: 82 },
  { file: 'jm_519', x: 775, y: 83 },
]

export class Hud {
  bar?: HTMLImageElement; hpOrb?: HTMLImageElement; mpOrb?: HTMLImageElement; weapon?: HTMLImageElement
  q?: HTMLImageElement; potR?: HTMLImageElement; potB?: HTMLImageElement; mapFrame?: HTMLImageElement; stam?: HTMLImageElement
  menu: HTMLImageElement[] = []
  pots = [2, 2, 2, 2]  // PropMdl: 小血瓶 (id4) Atb HP 400, 小气瓶 (id8) Atb MP 18; Init gives 2 of each
  async load(base = 'game/hud') {
    try {
      ;[this.bar, this.hpOrb, this.mpOrb, this.weapon] = await Promise.all(
        ['jm_1478', 'jm_417', 'jm_415', 'jm_1910'].map((n) => L(`${base}/${n}.png`)))
    } catch { /* HUD optional */ }
    try {
      ;[this.q, this.potR, this.potB, this.mapFrame, this.stam] = await Promise.all(
        ['jm_63', 'jm_92', 'jm_90', 'jm_1549', 'stamina_wine'].map((n) => L(`${base}/${n}.png`)))
    } catch { /* optional */ }
    try {
      this.menu = await Promise.all(MENU_ICONS.map((m) => L(`${base}/${m.file}.png`)))
    } catch { this.menu = [] }
  }
  /**
   * Wine bar is 800×110 at the bottom of an 800×600 window (top y=490).
   * Coordinates below are that 800-space. The bar is scaled to the canvas width
   * so orbs / hotbar / Q / menu keep Wine's alignment and span the playfield.
   */
  draw(ctx: CanvasRenderingContext2D, s: Stats, extra?: { skillL?: string; skillR?: string; money?: number; weapon?: string; potCd?: number; potCdMax?: number; attackCd?: number; attackReady?: boolean }) {
    const W = ctx.canvas.width, H = ctx.canvas.height
    if (!this.bar) return
    const sc = W / 800
    const smooth = ctx.imageSmoothingEnabled
    ctx.save()
    ctx.imageSmoothingEnabled = true
    ctx.translate(0, H - 110 * sc)
    ctx.scale(sc, sc)
    const orb = (img: HTMLImageElement | undefined, ox: number, oy: number, f: number) => {
      if (!img) return
      const h = Math.round(img.height * Math.max(0, Math.min(1, f)))
      if (h > 0) ctx.drawImage(img, 0, img.height - h, img.width, h, ox, oy + img.height - h, img.width, h)
    }
    ctx.drawImage(this.bar, 0, 0)
    // orb halves drawn over the yin-yang (as in Wine), drained from the top by HP/MP ratio
    orb(this.hpOrb, 11, 20, s.hp / s.maxHp)
    orb(this.mpOrb, 41, 18, s.mp / s.maxMp)
    // Orange stamina bar (Wine: x255..388, y555..561 → bar-relative (255,65)); drains from the right
    const sf = Math.max(0, Math.min(1, s.sp ?? 1))
    if (this.stam) { const w = Math.round(this.stam.width * sf); if (w > 0) ctx.drawImage(this.stam, 0, 0, w, this.stam.height, 255, 65, w, this.stam.height) }
    // EXP: thin strip in the right-hand groove (x415..555)
    const expNeed = (INIT.exp_per_lv ?? 100) * s.lvl
    ctx.fillStyle = '#c89a3a'
    ctx.fillRect(415, 66, Math.round(140 * Math.min(1, s.exp / Math.max(1, expNeed))), 3)
    // Potion slots 1–4. Wine icons JM 92/90 at (258+24k, 82). Yellow key digits sit on the
    // stamina's lower edge (measured y≈63–68), not on top of the 8px bottle sprites.
    ctx.font = 'bold 11px ui-sans-serif,system-ui'
    ctx.textBaseline = 'top'
    for (let k = 0; k < 4; k++) {
      const img = k < 2 ? this.potR : this.potB
      const px = 258 + 24 * k, py = 82
      if (img) { ctx.globalAlpha = this.pots[k] > 0 ? 1 : 0.35; ctx.drawImage(img, px, py); ctx.globalAlpha = 1 }
      ctx.fillStyle = '#f8e800'
      ctx.fillText(String(k + 1), px + 1, 63)
      if (this.pots[k] > 0) {
        ctx.save()
        ctx.font = 'bold 9px ui-sans-serif,system-ui'
        ctx.fillStyle = '#1a1004'
        ctx.fillText('×' + this.pots[k], px + 10, 64)
        ctx.fillStyle = '#fff8e0'
        ctx.fillText('×' + this.pots[k], px + 9, 63)
        ctx.restore()
      }
      const pcd = extra?.potCd ?? 0, pmax = extra?.potCdMax ?? 1.1
      if (pcd > 0 && pmax > 0 && img) {
        const frac = Math.min(1, pcd / pmax)
        const vh = Math.max(2, Math.round(img.height * frac))
        ctx.fillStyle = 'rgba(0,0,0,0.55)'
        ctx.fillRect(px, py + img.height - vh, img.width, vh)
        if (k === 0) {
          ctx.fillStyle = '#ffd24a'
          ctx.font = '9px ui-sans-serif,system-ui'
          ctx.fillText(pcd.toFixed(1), px + 20, 74)
        }
      }
      ctx.font = 'bold 11px ui-sans-serif,system-ui'
    }
    // Skill slots F1/F2 (Wine x425/448, y552 → bar 61). Names live in the bag, not over the slots.
    ctx.fillStyle = '#f8e800'
    ctx.fillText('F1', 425, 61)
    ctx.fillText('F2', 448, 61)
    const glow = (bx: number, by: number, bw: number, bh: number, on: boolean, alpha: number) => {
      if (!on || alpha <= 0) return
      const g = ctx.createRadialGradient(bx + bw / 2, by + bh / 2, 2, bx + bw / 2, by + bh / 2, Math.max(bw, bh) * 0.95)
      g.addColorStop(0, `rgba(255,236,160,${0.85 * alpha})`)
      g.addColorStop(0.45, `rgba(255,170,40,${0.45 * alpha})`)
      g.addColorStop(1, 'rgba(255,120,0,0)')
      ctx.fillStyle = g
      ctx.fillRect(bx - 10, by - 8, bw + 20, bh + 16)
    }
    const ready = extra?.attackReady !== false && (extra?.attackCd ?? 0) <= 0.02
    const swinging = (extra?.attackCd ?? 0) > 0.02 && (extra?.attackCd ?? 0) < 0.45
    const pulse = 0.78 + 0.22 * Math.sin(performance.now() / 140)
    glow(156, 61, 43, 47, ready || swinging, swinging ? 1 : pulse)
    glow(606, 61, 43, 47, ready, pulse * 0.9)
    if (swinging) {
      ctx.strokeStyle = 'rgba(255,244,200,0.95)'
      ctx.lineWidth = 2
      ctx.strokeRect(155.5, 60.5, 44, 48)
    }
    if (this.q) {
      ctx.drawImage(this.q, 606, 61)
      ctx.fillStyle = '#fff'
      ctx.fillText('Q', 641, 62)
    }
    if (this.weapon) ctx.drawImage(this.weapon, 156, 61)
    for (let i = 0; i < this.menu.length; i++) {
      const slot = MENU_ICONS[i]
      if (slot && this.menu[i]) ctx.drawImage(this.menu[i], slot.x, slot.y)
    }
    ctx.restore()
    ctx.imageSmoothingEnabled = smooth
  }
  // Minimap: JM 1549 frame (137×133) at Wine (663,0); scaled with the same 800-space factor as the bar.
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
