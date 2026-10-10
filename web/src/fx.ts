// Phase 20: skill attack VFX. Skill.ini action IDs (77/46/71 扫叶, 482/265 疾电) are
// behavior graphs, not ResJM/ResEx sprite indices (those IDs decode as map props / paper-doll
 // fragments). Canvas overlays approximate the leaf-whirl / lightning / slash looks until a
// true effect-lib map is cracked.
export type FxKind = 'saoye' | 'jidian' | 'q' | 'slash' | 'ice'

export type SkillFx = { kind: FxKind; t: number; max: number; ang: number }

export function spawnFx(kind: FxKind, ang: number, dur = 0.45): SkillFx {
  return { kind, t: dur, max: dur, ang }
}

export function tickFx(fx: SkillFx | null, dt: number): SkillFx | null {
  if (!fx) return null
  fx.t -= dt
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
  const a = Math.min(1, fx.t * 3)
  ctx.save()
  ctx.translate(sx, sy - 14)
  if (fx.kind === 'saoye') {
    // leaf whirl — green arcs around body
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
    // lightning bolts forward
    const reach = 36 + u * 28
    for (let b = -1; b <= 1; b++) {
      const ang = fx.ang + b * 0.22
      ctx.strokeStyle = `rgba(160,210,255,${a})`
      ctx.lineWidth = 2
      ctx.beginPath()
      let x = 0, y = 0
      ctx.moveTo(x, y)
      const steps = 5
      for (let s = 1; s <= steps; s++) {
        const t = s / steps
        x = Math.cos(ang) * reach * t + (Math.random() - 0.5) * 8
        y = Math.sin(ang) * reach * t * 0.6 + (Math.random() - 0.5) * 6
        ctx.lineTo(x, y)
      }
      ctx.stroke()
      ctx.strokeStyle = `rgba(255,255,255,${a * 0.7})`
      ctx.lineWidth = 1
      ctx.stroke()
    }
    ctx.fillStyle = `rgba(200,230,255,${a * 0.5})`
    ctx.beginPath(); ctx.arc(0, 0, 10 + u * 8, 0, Math.PI * 2); ctx.fill()
  } else if (fx.kind === 'q') {
    // cyclonic ring
    ctx.strokeStyle = `rgba(255,200,80,${a})`
    ctx.lineWidth = 3
    ctx.beginPath()
    ctx.ellipse(0, 4, 28 + u * 18, 12 + u * 6, 0, 0, Math.PI * 2)
    ctx.stroke()
    for (let i = 0; i < 6; i++) {
      const ang = i * Math.PI / 3 + u * 4
      ctx.fillStyle = `rgba(255,240,160,${a})`
      ctx.fillRect(Math.cos(ang) * (22 + u * 14) - 2, Math.sin(ang) * (10 + u * 6) - 2, 4, 4)
    }
  } else if (fx.kind === 'ice') {
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
  } else {
    // slash arc + trailing gleam
    ctx.strokeStyle = `rgba(255,240,180,${a})`
    ctx.lineWidth = 4
    ctx.beginPath()
    ctx.arc(0, 0, 30 + u * 6, fx.ang - 0.85, fx.ang + 0.85)
    ctx.stroke()
    ctx.strokeStyle = `rgba(255,255,255,${a * 0.55})`
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.arc(0, 0, 34 + u * 8, fx.ang - 0.5, fx.ang + 0.5)
    ctx.stroke()
  }
  ctx.restore()
}
