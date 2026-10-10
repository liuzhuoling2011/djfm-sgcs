/** Phase 30: optional .sy→wav SFX stubs (Leyi sy/ pack). Mute with M (shares BGM mute) or ?sfx=0 */
export type SfxId = 'attack' | 'slash' | 'hit' | 'hit2' | 'hurt' | 'death' | 'potion' | 'step' | 'pickup' | 'ui'

const bank = new Map<SfxId, HTMLAudioElement[]>()
let enabled = true
let volume = 0.55
const lastAt: Partial<Record<SfxId, number>> = {}

export function setSfxEnabled(on: boolean) { enabled = on }
export function setSfxVolume(v: number) { volume = Math.max(0, Math.min(1, v)) }

export async function loadSfx(base = 'game/sfx') {
  if (new URLSearchParams(location.search).get('sfx') === '0') { enabled = false; return }
  try {
    const idx = await (await fetch(`${base}/index.json`)).json() as Record<string, string>
    const ids: SfxId[] = ['attack', 'slash', 'hit', 'hit2', 'hurt', 'death', 'potion', 'step', 'pickup', 'ui']
    await Promise.all(ids.map(async (id) => {
      const file = idx[id]
      if (!file || file.endsWith('.json')) return
      const a = new Audio(`${base}/${file}`)
      a.preload = 'auto'
      a.volume = volume
      bank.set(id, [a])
    }))
  } catch { /* optional */ }
}

/** Play one-shot; pools a clone so overlaps work. Soft rate-limit per id. */
export function playSfx(id: SfxId, opts?: { vol?: number; minGap?: number }) {
  if (!enabled) return
  const now = performance.now()
  const gap = opts?.minGap ?? (id === 'step' ? 220 : 40)
  if ((lastAt[id] ?? 0) + gap > now) return
  lastAt[id] = now
  const pool = bank.get(id)
  if (!pool?.length) return
  let a = pool.find((x) => x.paused || x.ended)
  if (!a) {
    a = pool[0].cloneNode(true) as HTMLAudioElement
    pool.push(a)
    if (pool.length > 4) pool.shift()
  }
  a.volume = (opts?.vol ?? 1) * volume
  a.currentTime = 0
  void a.play().catch(() => {})
}
