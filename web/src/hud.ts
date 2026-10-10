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

const L = (s: string) => new Promise<HTMLImageElement>((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = no; i.src = s })

export class Hud {
  bar?: HTMLImageElement; hpOrb?: HTMLImageElement; mpOrb?: HTMLImageElement; weapon?: HTMLImageElement
  q?: HTMLImageElement; potR?: HTMLImageElement; potB?: HTMLImageElement; mapFrame?: HTMLImageElement; stam?: HTMLImageElement
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
  }
  // Layout measured on Wine 800x600: bar top y=490; HP orb (11,+20); MP orb (41,+18); weapon (156,+61)
  draw(ctx: CanvasRenderingContext2D, s: Stats, extra?: { skillL?: string; skillR?: string; money?: number; weapon?: string }) {
    const W = ctx.canvas.width, H = ctx.canvas.height
    if (!this.bar) return
    const x0 = Math.round((W - 800) / 2), y0 = H - 110
    if (W > 800) { ctx.fillStyle = 'rgba(0,0,0,0.55)'; ctx.fillRect(0, H - 50, W, 50) }
    const orb = (img: HTMLImageElement | undefined, ox: number, oy: number, f: number) => {
      if (!img) return
      const h = Math.round(img.height * Math.max(0, Math.min(1, f)))
      if (h > 0) ctx.drawImage(img, 0, img.height - h, img.width, h, x0 + ox, y0 + oy + img.height - h, img.width, h)
    }
    ctx.drawImage(this.bar, x0, y0)
    // orb halves drawn over the yin-yang (as in Wine), drained from the top by HP/MP ratio
    orb(this.hpOrb, 11, 20, s.hp / s.maxHp)
    orb(this.mpOrb, 41, 18, s.mp / s.maxMp)
    if (this.weapon) ctx.drawImage(this.weapon, x0 + 156, y0 + 61)
    // Orange stamina bar (Wine: x255..388, y555..561 → bar-relative (255,65)); drains from the right
    const sf = Math.max(0, Math.min(1, s.sp ?? 1))
    if (this.stam) { const w = Math.round(this.stam.width * sf); if (w > 0) ctx.drawImage(this.stam, 0, 0, w, this.stam.height, x0 + 255, y0 + 65, w, this.stam.height) }
    // EXP: thin strip in the right-hand groove (x415..555); the bar art there is empty in Wine at 0 EXP
    const expNeed = (INIT.exp_per_lv ?? 100) * s.lvl; ctx.fillStyle = '#c89a3a'; ctx.fillRect(x0 + 415, y0 + 66, Math.round(140 * Math.min(1, s.exp / Math.max(1, expNeed))), 3)
    // Potion slots 1–4 (Wine: icons at x258+24k, y572; JM 92 red, 90 blue; yellow key digit at +10,+5)
    ctx.font = 'bold 11px ui-sans-serif,system-ui'; ctx.textBaseline = 'top'
    for (let k = 0; k < 4; k++) {
      const img = k < 2 ? this.potR : this.potB, px = x0 + 258 + 24 * k, py = y0 + 82
      if (img) { ctx.globalAlpha = this.pots[k] > 0 ? 1 : 0.35; ctx.drawImage(img, px, py); ctx.globalAlpha = 1 }
      ctx.fillStyle = '#f8e800'; ctx.fillText(String(k + 1), px + 10, py - 1)
      if (this.pots[k] > 0) { ctx.fillStyle = '#fff'; ctx.font = 'bold 10px ui-sans-serif,system-ui'; ctx.fillText('×'+this.pots[k], px + 2, py + 18) }
      ctx.font = 'bold 11px ui-sans-serif,system-ui'
    }
    // Skill slots F1/F2 (Wine x425/448, y552) — labels from Skill.txt 扫叶/疾电
    ctx.fillStyle = '#f8e800'; ctx.fillText('F1', x0 + 425, y0 + 61); ctx.fillText('F2', x0 + 448, y0 + 61)
    if (extra?.skillL) { ctx.fillStyle = '#cfe6ff'; ctx.font = '9px ui-sans-serif,system-ui'; ctx.fillText(extra.skillL, x0 + 420, y0 + 78) }
    if (extra?.skillR) { ctx.fillStyle = '#cfe6ff'; ctx.font = '9px ui-sans-serif,system-ui'; ctx.fillText(extra.skillR, x0 + 448, y0 + 78) }
    ctx.font = 'bold 11px ui-sans-serif,system-ui' 
    // Q skill icon (JM 63 at Wine (606,551)) + 'Q' label
    if (this.q) { ctx.drawImage(this.q, x0 + 606, y0 + 61); ctx.fillStyle = '#fff'; ctx.fillText('Q', x0 + 641, y0 + 62) }
    ctx.textBaseline = 'alphabetic'
    ctx.fillStyle = '#ffe9a0'; ctx.font = '11px ui-sans-serif,system-ui'
    ctx.fillText(`HP ${Math.ceil(s.hp)}/${s.maxHp}  MP ${Math.ceil(s.mp)}/${s.maxMp}  Lv${s.lvl} AT${Math.round(s.at ?? INIT.at)}` + (SOFT_DF ? '  ·软DF(?softdf=1)' : '  ·Init成长') + (extra?.money != null ? `  金${extra.money}` : '') + (extra?.weapon ? `  ${extra.weapon}` : ''), x0 + 255, y0 + 52)
  }
  // Minimap: JM 1549 frame (137×133) at Wine (663,0) = top-right; interior 6..131 × 6..104; name strip below
  drawMinimap(ctx: CanvasRenderingContext2D, ground: CanvasImageSource | null, gx: number, gy: number, k: number,
    dots: { x: number; y: number; c: string }[], name: string) {
    if (!this.mapFrame) return
    const fx = ctx.canvas.width - 137, ix = fx + 6, iy = 6, iw = 125, ih = 98
    ctx.save(); ctx.beginPath(); ctx.rect(ix, iy, iw, ih); ctx.clip()
    ctx.fillStyle = '#000'; ctx.fillRect(ix, iy, iw, ih)
    if (ground) ctx.drawImage(ground, gx - iw / 2 / k, gy - ih / 2 / k, iw / k, ih / k, ix, iy, iw, ih)
    for (const d of dots) { ctx.fillStyle = d.c; ctx.fillRect(Math.round(ix + iw / 2 + (d.x - gx) * k) - 1, Math.round(iy + ih / 2 + (d.y - gy) * k) - 1, 3, 3) }
    ctx.restore()
    ctx.drawImage(this.mapFrame, fx, 0)
    ctx.fillStyle = '#e8e8e8'; ctx.font = '11px ui-sans-serif,system-ui'; ctx.textAlign = 'center'
    ctx.fillText(name, fx + 68, 122); ctx.textAlign = 'left'
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
    const sight = f.sight ?? 7
    if (d > 0.01) f.dir = (Math.round(Math.atan2(dy, dx) / (Math.PI / 4)) + 8) % 8
    if (f.hitT > 0) { f.act = 'hurt'; continue }
    if (f.act === 'attack' && (f.actT ?? 0) < 0.8) continue
    if (d < sight && d > 1.1) {
      const sp = (f.spd ? f.spd / 3.5 : 2.2) * dt, nx = f.x + dx / d * sp, ny = f.y + dy / d * sp
      if (walk(nx, f.y)) f.x = nx
      if (walk(f.x, ny)) f.y = ny
      if (f.act !== 'walk') { f.act = 'walk'; f.actT = 0 }
    } else if (d <= 1.3 && f.cd <= 0) {
      st.hp -= dmg(f.at ?? 20, st.df ?? 10); f.cd = 1.4; f.act = 'attack'; f.actT = 0
    } else if (f.act !== 'idle') { f.act = 'idle'; f.actT = 0 }
  }
}

// melee arc: hits foes within range in facing half-plane
export function playerAttack(foes: Foe[], p: { x: number; y: number }, facingAng: number, st: Stats, range = 2.1) {
  let hits = 0
  for (const f of foes) {
    if (f.dead > 0 || f.gone) continue
    const dx = f.x - p.x, dy = f.y - p.y, d = Math.hypot(dx, dy)
    if (d > range) continue
    const a = Math.atan2(dy, dx), diff = Math.abs(Math.atan2(Math.sin(a - facingAng), Math.cos(a - facingAng)))
    if (d < 1.05 || diff < 1.35) {
      f.hp -= dmg(st.at ?? 40, f.df ?? 10); f.hitT = 0.28; hits++
      // knockback away from player
      if (d > 0.01) { f.kbX = (dx / d) * 4.5; f.kbY = (dy / d) * 4.5 }
      if (f.hp <= 0) { f.dead = 0.9; f.actT = 0; st.exp += f.exp ?? 25; while (tryLevelUp(st)) { /* Init.txt growth */ } }
    }
  }
  return hits
}
