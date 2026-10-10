// Phase 20/28: skill VFX. Prefer ResJM/fx strip frames when present; canvas fallback otherwise.
export type FxKind = 'saoye' | 'jidian' | 'q' | 'slash' | 'ice'

export type SkillFx = {
  kind: FxKind; t: number; max: number; ang: number
  frames?: HTMLImageElement[]; fi?: number
}

const bank: Partial<Record<FxKind, HTMLImageElement[]>> = {}

export async function loadFxSprites(base = 'game/fx') {
  try {
    const idx = await (await fetch(`${base}/index.json`)).json() as {
      jidian_frames?: string[]; q_frames?: string[]; ice_hazard_frames?: string[]
    }
    const load = (n: string) => new Promise<HTMLImageElement>((ok, no) => {
      const i = new Image(); i.onload = () => ok(i); i.onerror = no; i.src = `${base}/${n}`
    })
    if (idx.jidian_frames?.length) {
      bank.jidian = []
      for (const n of idx.jidian_frames) { try { bank.jidian.push(await load(n)) } catch { /* */ } }
    }
    if (idx.q_frames?.length) {
      bank.q = []
      for (const n of idx.q_frames) { try { bank.q.push(await load(n)) } catch { /* */ } }
    }
    if (idx.ice_hazard_frames?.length) {
      bank.ice = []
      for (const n of idx.ice_hazard_frames) { try { bank.ice.push(await load(n)) } catch { /* */ } }
    }
  } catch { /* optional */ }
}

export function spawnFx(kind: FxKind, ang: number, dur?: number): SkillFx {
  const d = dur ?? (kind === 'slash' ? 0.22 : kind === 'jidian' ? 0.42 : kind === 'saoye' ? 0.55 : kind === 'q' ? 0.48 : 0.35)
  return { kind, t: d, max: d, ang, frames: bank[kind], fi: 0 }
}

export function tickFx(fx: SkillFx | null, dt: number): SkillFx | null {
  if (!fx) return null
  fx.t -= dt
  if (fx.frames?.length) {
    const u = 1 - fx.t / fx.max
    fx.fi = Math.min(fx.frames.length - 1, Math.floor(u * fx.frames.length))
  }
  return fx.t > 0 ? fx : null
}

/** Draw at player screen position (foot). */
export function drawFx(
  ctx: CanvasRenderingContext2D,
  fx: SkillFx,
  sx: number,
  sy: number,
) {
  const u = 1 - fx.t / fx.max
  const a = Math.min(1, fx.t * 3.5)
  ctx.save()
  ctx.translate(sx, sy - 14)
  const spr = fx.frames?.[fx.fi ?? 0]
  if (spr && (fx.kind === 'jidian' || fx.kind === 'q' || fx.kind === 'ice')) {
    ctx.globalAlpha = a
    const sc = fx.kind === 'ice' ? 1.4 : 1.15
    ctx.drawImage(spr, -spr.width * sc / 2, -spr.height * sc * 0.85, spr.width * sc, spr.height * sc)
    ctx.globalAlpha = 1
    if (fx.kind !== 'jidian') { ctx.restore(); return }
    // jidian: sprite + bolt overlay
  }
  if (fx.kind === 'saoye') {
    for (let i = 0; i < 8; i++) {
      const ang = fx.ang + i * (Math.PI / 4) + u * Math.PI * 2
      const r = 18 + u * 22
      ctx.strokeStyle = `rgba(120,220,90,${a * 0.85})`
      ctx.lineWidth = 2.5
      ctx.beginPath()
      ctx.arc(0, 0, r, ang - 0.35, ang + 0.55)
      ctx.stroke()
      ctx.fillStyle = `rgba(180,255,120,${a})`
      ctx.beginPath()
      ctx.ellipse(Math.cos(ang) * r, Math.sin(ang) * r * 0.55, 5, 2.5, ang, 0, Math.PI * 2)
      ctx.fill()
    }
  } else if (fx.kind === 'jidian') {
    const reach = 36 + u * 28
    for (let b = -1; b <= 1; b++) {
      const ang = fx.ang + b * 0.22
      ctx.strokeStyle = `rgba(160,210,255,${a})`
      ctx.lineWidth = 2
      ctx.beginPath()
      let x = 0, y = 0
      ctx.moveTo(x, y)
      for (let s = 1; s <= 5; s++) {
        const t = s / 5
        x = Math.cos(ang) * reach * t + Math.sin(s * 9 + u * 20) * 5
        y = Math.sin(ang) * reach * t * 0.6 + Math.cos(s * 7 + u * 18) * 4
        ctx.lineTo(x, y)
      }
      ctx.stroke()
    }
    ctx.fillStyle = `rgba(200,230,255,${a * 0.45})`
    ctx.beginPath(); ctx.arc(0, 0, 10 + u * 8, 0, Math.PI * 2); ctx.fill()
  } else if (fx.kind === 'q') {
    if (!spr) {
      ctx.strokeStyle = `rgba(255,200,80,${a})`
      ctx.lineWidth = 3
      ctx.beginPath()
      ctx.ellipse(0, 4, 28 + u * 18, 12 + u * 6, 0, 0, Math.PI * 2)
      ctx.stroke()
    }
  } else if (fx.kind === 'ice') {
    if (!spr) {
      for (let i = 0; i < 6; i++) {
        const ang = i * Math.PI / 3 + u * 2
        const r = 10 + u * 16
        ctx.fillStyle = `rgba(180,230,255,${a * 0.85})`
        ctx.beginPath()
        ctx.moveTo(Math.cos(ang) * r, Math.sin(ang) * r * 0.55)
        ctx.lineTo(Math.cos(ang + 0.2) * (r + 8), Math.sin(ang + 0.2) * (r + 8) * 0.55)
        ctx.lineTo(Math.cos(ang - 0.2) * (r + 4), Math.sin(ang - 0.2) * (r + 4) * 0.55)
        ctx.fill()
      }
    }
  } else {
    // slash — peak at mid windup
    const peak = Math.sin(Math.min(1, u / 0.45) * Math.PI)
    ctx.strokeStyle = `rgba(255,240,180,${a * (0.55 + 0.45 * peak)})`
    ctx.lineWidth = 3 + peak * 2
    ctx.beginPath()
    ctx.arc(0, 0, 28 + peak * 10, fx.ang - 0.9, fx.ang + 0.9)
    ctx.stroke()
    ctx.strokeStyle = `rgba(255,255,255,${a * 0.5 * peak})`
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.arc(0, 0, 34 + peak * 8, fx.ang - 0.55, fx.ang + 0.55)
    ctx.stroke()
  }
  ctx.restore()
}
