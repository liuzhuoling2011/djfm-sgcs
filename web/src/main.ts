import './style.css'
import { DialogSys } from './dialog'
import { Hud, stepFoes, playerAttack, type Foe, type Stats } from './hud'
import { Inventory } from './inventory'

type Vec = { x: number; y: number }
type MapObj = {
  lx?: number; ly?: number; x?: number; y?: number; MapX?: number; MapY?: number
  ModelID?: number; Type?: number; EventID?: string; file?: string; sw?: number; sh?: number; npc_dirs?: string[]; ox?: number; oy?: number; graph?: number
}
type BldPart = { file: string; ox: number; oy: number; w: number; h: number }
type Building = { x: number; y: number; bid: number; name: string; parts: BldPart[]; fw?: number; fh?: number }
type Atlas = { x: number; y: number; w: number; h: number; file: string }
type MapMeta = {
  chunk_size: [number, number]; tile_pixel: [number, number]; unique_tiles: number; grid: number[][]
  source?: string; chunk_origin?: [number, number]; fill_rate?: number; pack_id?: string
  spawn?: [number, number]; spawn_world?: [number, number]; scene?: string; scene_name?: string
  objects?: MapObj[]; buildings?: Building[]; npcs?: MapObj[]; blocked_sample?: [number, number][]
  ground_full?: { file: string; min_sx: number; min_sy: number; tile_w: number; tile_h: number; scale: number }
  lazy?: { chunk: number; atlases: Atlas[]; mode: string }
  walk_grid?: string[]
  monsters?: { x: number; y: number; role: number; name: string; set: number; hp: number; at: number; df: number; exp: number; spd: number; sight: number }[]
  monster_sets?: Record<string, Record<string, { per_dir: number; frames: ([string, number, number] | null)[] }>>
}
type GameData = {
  bgm: { file: string; name: string }
  dialogs: Record<string, { name: string; lines: string[] }>
  attack: { name: string; range: number; cooldown_ms: number }
  interact_key: string; interact_range: number
}
type PackIndex = { begin_scn_mapping: string; default: string; packs: { id: string }[] }

async function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const im = new Image()
    im.onload = () => resolve(im)
    im.onerror = () => reject(new Error(src))
    im.src = src
  })
}

let WG: { g: string[]; ox: number; oy: number } | null = null
function walkableNow(x: number, y: number, mapW: number, mapH: number, blocked: Set<string>): boolean {
  const ix = Math.round(x), iy = Math.round(y)
  if (WG) { const r = WG.g[iy + WG.oy]; return !!r && r[ix + WG.ox] === '1' }
  if (ix < 0 || iy < 0 || ix >= mapW || iy >= mapH) return false
  return !blocked.has(`${ix},${iy}`)
}

async function main() {
  let packIndex: PackIndex | null = null
  try { packIndex = await (await fetch('game/maps/index.json')).json() } catch { /* */ }
  const packIds = packIndex?.packs.map((p) => p.id) ?? ['ren']
  let packId = new URLSearchParams(location.search).get('pack') ?? packIndex?.default ?? 'ren'

  let gameData: GameData | null = null
  try { gameData = await (await fetch('game/data/game.json')).json() } catch { /* */ }

  const app = document.querySelector<HTMLDivElement>('#app')!
  app.innerHTML = `
    <header>
      <h1>刀剑封魔录外传 · Phase 12</h1>
      <p>瓦当镇 · 地面钻石修复 + 图集 · BGM · E对话 / Space攻击 · WASD</p>
    </header>
    <div class="toolbar" id="packs"></div>
    <canvas id="c" width="1280" height="720"></canvas>
    <p class="hint" id="hint">Loading…</p>
    <div id="dialog" class="dialog hidden"></div>
    <section class="panel"><h2>样本</h2><div class="grid" id="grid"></div></section>
  `

  const packsEl = document.querySelector<HTMLDivElement>('#packs')!
  const hint = document.querySelector<HTMLParagraphElement>('#hint')!
  const invEl = document.createElement('div'); invEl.id='inv'; invEl.className='inv-panel hidden'; document.body.append(invEl)
  const toastEl = document.createElement('div'); toastEl.className='toast hidden'; document.body.append(toastEl)
  const dialogEl = document.querySelector<HTMLDivElement>('#dialog')!
  if (packIndex) hint.textContent = (packIndex.begin_scn_mapping ?? '') + ' · I行囊 F1/F2技能 1/3药'
  for (const id of packIds) {
    const btn = document.createElement('button')
    btn.textContent = id
    btn.dataset.pack = id
    if (id === packId) btn.classList.add('active')
    packsEl.append(btn)
  }

  const canvas = document.querySelector<HTMLCanvasElement>('#c')!
  const ctx = canvas.getContext('2d')!
  ctx.imageSmoothingEnabled = false

  let mapW = 20, mapH = 16, tileW = 64, tileH = 32
  let mapLabel = 'loading'
  let blocked = new Set<string>()
  let walkGrid: string[] | null = null
  let objects: MapObj[] = []
  let buildings: Building[] = []
  let buildingImgs = new Map<string, HTMLImageElement>()
  let npcImgs = new Map<string, HTMLImageElement>()
  let origin = { x: 0, y: 0 }
  const qs = new URLSearchParams(location.search)
  let tintOn = qs.get('tint') !== '0'
  let rainOn = qs.get('rain') !== '0'
  let ground: HTMLImageElement | null = null
  let groundMeta: MapMeta['ground_full'] | null = null
  let miniImg: HTMLImageElement | null = null
  let useGround = true
  let atlases: Atlas[] = []
  const atlasImgs = new Map<string, HTMLImageElement>()
  const atlasLoading = new Set<string>()
  let base = 'game/map'
  const pos: Vec = { x: 10, y: 10 }
  const cam: Vec = { x: 0, y: 0 }

  // BGM
  let audio: HTMLAudioElement | null = null
  let muted = false
  if (gameData?.bgm?.file) {
    audio = new Audio(gameData.bgm.file)
    audio.loop = true
    audio.volume = 0.35
    const tryPlay = () => audio?.play().catch(() => {})
    window.addEventListener('pointerdown', tryPlay, { once: true })
    window.addEventListener('keydown', tryPlay, { once: true })
  }

  // Dialog / attack state
  let dialogOpen = false
  let dialogLines: string[] = []
  let dialogIdx = 0
  let dialogNpc = ''
  let attackT = 0
  const hud = new Hud()
  const inv = new Inventory()
  const dlg = new DialogSys()
  dlg.onChange = () => { renderDialog(); renderInv() }
  void (async () => {
    await Promise.all([hud.load(), inv.load(), dlg.load()])
    dlg.inv = {
      hasProp: (id) => inv.qty(id) > 0,
      acquire: (id, n) => { inv.add(id, n); inv.flash(`获得 ${inv.props[String(id)]?.name ?? id}×${n}`) },
      miss: (id, n) => { inv.miss(id, n) },
      addWeaponNum: () => { inv.weaponSlots++; inv.flash('兵器强化槽 +1') },
      showShop: () => { inv.shopOpen = true; inv.open = true; renderInv() },
      showEmbed: () => { inv.embedOpen = true; inv.open = true; renderInv() },
    }
    const ps = inv.potSlots(); hud.pots = [...ps]
  })()
  // mb/player/Init.txt 男主角: AT40(+4/lv) DF30(+4) HP800(+80) regen1.4 MP36 Stamina80 regen3/s use10/s
  const stats: Stats = { hp: 800, maxHp: 800, mp: 36, maxMp: 36, exp: 0, lvl: 1, at: 40, df: 30, sp: 1 }
  let monSets: NonNullable<MapMeta['monster_sets']> = {}
  const monImgs = new Map<string, HTMLImageElement>()
  let foes: Foe[] = []
  let spawnPos = { x: 0, y: 0 }
  let attackCd = 0

  function showDialog(eid: string) {
    const d = gameData?.dialogs?.[eid]
    dialogLines = d?.lines?.length ? d.lines : [`（${eid}）……`]
    dialogIdx = 0
    dialogNpc = eid
    dialogOpen = true
    renderDialog()
  }
  
  function renderInv() {
    invEl.classList.toggle('hidden', !inv.open && !inv.shopOpen && !inv.embedOpen)
    if (!inv.open && !inv.shopOpen && !inv.embedOpen) return
    const rows = inv.items.map((it) => {
      const d = inv.props[String(it.id)]
      return `<li><span>${d?.name ?? '#'+it.id}</span><span>×${it.qty}</span></li>`
    }).join('') || '<li>（空）</li>'
    let shop = ''
    if (inv.shopOpen) {
      shop = `<div class="shop"><b>铁匠铺 · 买卖</b><br/>` + inv.shopCatalog().map((r,i) => {
        const n = inv.props[String(r.id)]?.name ?? r.id
        return `<button data-buy="${r.id}">${i+1}. ${n} ${r.price}金</button>`
      }).join('') + `<br/><button data-close-shop>关闭店铺</button></div>`
    }
    if (inv.embedOpen) {
      shop += `<div class="shop"><b>镶嵌</b><p>花费 200 金强化当前兵器（槽×${inv.weaponSlots}）</p>
        <button data-embed>确认镶嵌</button> <button data-close-embed>取消</button></div>`
    }
    invEl.innerHTML = `<div class="box"><h3>行囊 · ${inv.money} 金</h3>
      <div class="eq">装备：${inv.weaponName()}　F1 ${inv.skill('left')?.name ?? ''}　F2 ${inv.skill('right')?.name ?? ''}<br/>
      <small>I 开关 · 1/3 用药 · 5 飞蝗石 · 6 指南珠 · Esc 关</small></div>
      <ul>${rows}</ul>${shop}</div>`
    invEl.querySelectorAll('[data-buy]').forEach((b) => b.addEventListener('click', () => {
      inv.buy(Number((b as HTMLElement).dataset.buy)); const ps=inv.potSlots(); hud.pots=[...ps]; renderInv()
    }))
    invEl.querySelector('[data-close-shop]')?.addEventListener('click', () => { inv.shopOpen=false; renderInv() })
    invEl.querySelector('[data-embed]')?.addEventListener('click', () => { inv.embedUpgrade(stats); inv.embedOpen=false; renderInv() })
    invEl.querySelector('[data-close-embed]')?.addEventListener('click', () => { inv.embedOpen=false; renderInv() })
  }
  function renderToast() {
    toastEl.classList.toggle('hidden', inv.toastT <= 0)
    if (inv.toastT > 0) toastEl.textContent = inv.toast
  }

  function renderDialog() {
    if (dlg.open) {
      dialogOpen = true
      dialogEl.style.display = 'block'
      if (dlg.choices.length) {
        const opts = dlg.choices.map((c, i) => `<button data-i="${i}" style="display:block;margin:4px 0">${i + 1}. ${c.label}</button>`).join('')
        dialogEl.innerHTML = `<div class="box"><b>${dlg.npc}</b><div>${opts}</div><small>数字键选择 · Esc 关闭</small></div>`
        dialogEl.querySelectorAll('button').forEach((b) => b.addEventListener('click', () => { dlg.pick(Number((b as HTMLButtonElement).dataset.i)); dialogOpen = dlg.open; renderDialog() }))
      } else {
        const line = dlg.lines[dlg.idx] ?? ''
        dialogEl.innerHTML = `<div class="box"><b>${dlg.npc}</b><p>${line}</p><small>E / Enter 继续 · Esc 关闭</small></div>`
      }
      return
    }
    if (!dialogOpen) { dialogEl.style.display = 'none'; return }
    dialogEl.style.display = 'block'
    const line = dialogLines[dialogIdx] ?? ''
    dialogEl.innerHTML = `<div class="box"><b>${dialogNpc}</b><p>${line}</p><small>E / Enter 继续 · Esc 关闭</small></div>`
  }
  function advanceDialog() {
    if (!dialogOpen && !dlg.open) return
    if (dlg.open) {
      if (dlg.choices.length) return
      dlg.advance(); dialogOpen = dlg.open; renderDialog(); return
    }
    dialogIdx++
    if (dialogIdx >= dialogLines.length) dialogOpen = false
    renderDialog()
  }

  async function ensureAtlas(a: Atlas) {
    if (atlasImgs.has(a.file) || atlasLoading.has(a.file)) return
    atlasLoading.add(a.file)
    try {
      atlasImgs.set(a.file, await loadImage(`${base}/chunks/${a.file}`))
    } catch { /* */ }
    atlasLoading.delete(a.file)
  }

  let warpArmed = true, curScene = '1-0s', curTriggers: { x: number; y: number; script: string }[] = [], warpCd = 0, firstLoad = true
  const packOf = (scene: string) => (scene === '1-0s' ? 'ren' : scene)
  async function applyPack(id: string, arriveFrom?: string) {
    packId = id
    for (const b of packsEl.querySelectorAll('button')) {
      b.classList.toggle('active', (b as HTMLButtonElement).dataset.pack === id)
    }
    base = id === 'ren' ? 'game/map' : `game/maps/${id}`
    hint.textContent = `Loading ${id}…`
    const meta = (await (await fetch(`${base}/meta.json`)).json()) as MapMeta
    mapW = meta.chunk_size[0]
    mapH = meta.chunk_size[1]
    tileW = meta.tile_pixel?.[0] || 64
    tileH = meta.tile_pixel?.[1] || 32
    origin = { x: meta.chunk_origin?.[0] ?? 0, y: meta.chunk_origin?.[1] ?? 0 }
    buildings = meta.buildings ?? []
    objects = meta.npcs ?? meta.objects ?? []
    atlases = meta.lazy?.atlases ?? []
    atlasImgs.clear()

    walkGrid = meta.walk_grid ?? null
    WG = walkGrid ? { g: walkGrid, ox: origin.x, oy: origin.y } : null
    blocked = new Set()
    for (const b of meta.blocked_sample ?? []) blocked.add(`${b[0]},${b[1]}`)
    for (let x = 0; x < mapW; x++) { blocked.add(`${x},0`); blocked.add(`${x},${mapH - 1}`) }
    for (let y = 0; y < mapH; y++) { blocked.add(`0,${y}`); blocked.add(`${mapW - 1},${y}`) }

    buildingImgs = new Map()
    npcImgs = new Map()
    await Promise.all([
      ...[...new Set(buildings.flatMap((b) => (b.parts ?? []).map((q) => q.file)))].map(async (f) => {
        try { buildingImgs.set(f, await loadImage(`${base}/props/${f}`)) } catch { /* */ }
      }),
      ...[...new Set(objects.filter((n) => n.file).map((n) => n.file!))].map(async (f) => {
        try { npcImgs.set(f, await loadImage(`${base}/props/${f}`)) } catch { /* */ }
      }),
      ...objects.flatMap((n) => (n.npc_dirs ?? []).map(async (f, i) => {
        try { npcImgs.set(`${n.EventID}_${i}`, await loadImage(`${base}/npcs/${f}`)) } catch { /* */ }
      })),
    ])
    ground = null
    groundMeta = meta.ground_full ?? null
    if (groundMeta?.file) {
      try { ground = await loadImage(`${base}/${groundMeta.file}`) } catch { ground = null }
    }
    useGround = !!ground
    miniImg = null
    const mm = (meta as { minimap?: { file: string } }).minimap
    if (mm) loadImage(`${base}/${mm.file}`).then((im) => { miniImg = im }).catch(() => {})

    mapLabel = `${meta.scene_name ?? meta.scene ?? id} ${mapW}x${mapH} bld=${buildings.length} npc=${objects.length} atlases=${atlases.length}`
    pos.x = meta.spawn?.[0] ?? mapW / 2
    pos.y = meta.spawn?.[1] ?? mapH / 2
    curScene = (meta.scene ?? id).toLowerCase()
    curTriggers = ((meta as { triggers?: { x: number; y: number; script?: string }[] }).triggers ?? [])
      .filter((g) => g.x < 4096 && g.y < 4096 && /^go\s/.test(g.script ?? '')).map((g) => ({ x: g.x, y: g.y, script: g.script! }))
    if (arriveFrom) {
      // real exit pairing: arrive next to this map's own 'go <previous scene>' trigger, stepped toward the map centre
      const back = curTriggers.filter((g) => g.script.split(/\s+/)[1]?.toLowerCase() === arriveFrom)
      if (back.length) {
        const cx = back.reduce((s, g) => s + g.x, 0) / back.length - origin.x, cy = back.reduce((s, g) => s + g.y, 0) / back.length - origin.y
        const vx = mapW / 2 - cx, vy = mapH / 2 - cy, vl = Math.hypot(vx, vy) || 1
        pos.x = cx; pos.y = cy
        for (let s = 4; s < 40; s++) { const px = Math.round(cx + vx / vl * s), py = Math.round(cy + vy / vl * s); if (walkable(px, py)) { pos.x = px; pos.y = py; break } }
      }
      warpCd = 0.5; warpArmed = false
    }
    if (firstLoad) { firstLoad = false; const at = new URLSearchParams(location.search).get('at'); if (at) { const [ax, ay] = at.split(',').map(Number); pos.x = ax - origin.x; pos.y = ay - origin.y } }
    const onTrig = curTriggers.some((g) => Math.hypot(g.x - origin.x - pos.x, g.y - origin.y - pos.y) < 2.5)
    if (!walkableNow(pos.x, pos.y, mapW, mapH, blocked) && !onTrig) {
      search: for (let r = 1; r < 40; r++) {
        for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
          if (walkableNow(pos.x + dx, pos.y + dy, mapW, mapH, blocked)) { pos.x += dx; pos.y += dy; break search }
        }
      }
    }
    spawnPos = { x: pos.x, y: pos.y }
    // Act-1 town: lock 1-1s exit until 沈云 sets sy1 (scene script IsFlag sy1 1 1 → SetExitTextID 1-1s 308)
    if (curScene === '1-0s' && (dlg.flags.sy1 ?? 0) < 1 && dlg.exitText['1-1s'] === undefined) dlg.exitText['1-1s'] = 308
    const gateCells = (meta as { quest_gate_cells?: [number, number][] }).quest_gate_cells
    if (gateCells && walkGrid) {
      const open = (dlg.flags.sy1 ?? 0) >= 1 || dlg.exitText['1-1s'] === -1
      for (const [gx, gy] of gateCells) {
        if (gy >= 0 && gy < walkGrid.length && gx >= 0 && gx < walkGrid[gy].length) {
          const row = walkGrid[gy].split(''); row[gx] = open ? '1' : '0'; walkGrid[gy] = row.join('')
        }
      }
      WG = walkGrid ? { g: walkGrid, ox: origin.x, oy: origin.y } : null
    }
    foes = []
    monSets = meta.monster_sets ?? {}
    for (const [sid, acts] of Object.entries(monSets)) for (const a of Object.values(acts)) for (const f of a.frames) {
      if (f && !monImgs.has(f[0])) { const k = f[0]; loadImage(`${base}/mon/${k}`).then((im) => monImgs.set(k, im)).catch(() => {}) ; void sid }
    }
    for (const m of meta.monsters ?? []) {
      const lx = m.x - origin.x, ly = m.y - origin.y
      foes.push({ x: lx, y: ly, hx: lx, hy: ly, hp: m.hp, maxHp: m.hp, cd: 1, hitT: 0, dead: 0, at: m.at, df: m.df, exp: m.exp, sight: m.sight, spd: m.spd, name: m.name, set: m.set, act: 'idle', actT: 0, dir: 0 })
    }
    const nf = Number(qs.get('foe') ?? '0')
    for (let i = 0; i < nf; i++) {
      const a = (i / Math.max(1, nf)) * Math.PI * 2, fx = pos.x + Math.cos(a) * 4, fy = pos.y + Math.sin(a) * 4
      if (walkableNow(fx, fy, mapW, mapH, blocked)) foes.push({ x: fx, y: fy, hp: 60, maxHp: 60, cd: 1, hitT: 0, dead: 0 })
    }
    hint.textContent = packIndex?.begin_scn_mapping ?? mapLabel
  }

  await applyPack(packId)
  packsEl.addEventListener('click', (e) => {
    const t = e.target as HTMLElement
    if (t.tagName === 'BUTTON' && t.dataset.pack) applyPack(t.dataset.pack).catch(console.error)
  })

  // Phase 19: paper-doll composite sheets (8 dirs × 4 walk / 1 idle / 1 attack)
  const playerWalk: HTMLImageElement[][] = Array.from({ length: 8 }, () => [])
  const playerIdle: HTMLImageElement[] = []
  const playerAttackSpr: HTMLImageElement[] = []
  await Promise.all(Array.from({ length: 8 }, async (_, d) => {
    for (let f = 0; f < 4; f++) {
      try { playerWalk[d].push(await loadImage(`game/player/walk/${d}_${f}.png`)) } catch { /* */ }
    }
    try { playerIdle[d] = await loadImage(`game/player/idle/${d}_0.png`) } catch { /* */ }
    try { playerAttackSpr[d] = await loadImage(`game/player/attack/${d}_0.png`) } catch { /* */ }
  }))
  let player: HTMLImageElement
  try { player = playerIdle[0] ?? await loadImage('game/player.png') } catch { player = await loadImage('game/player_fallback.png') }
  const walkFrames: HTMLImageElement[] = playerWalk.flat()

  const gridEl = document.querySelector<HTMLDivElement>('#grid')!
  for (const src of ['game/map/props/bld_225.png', 'game/map/props/npc_618.png', 'game/map/props/npc_661.png', 'game/map/chunks/c_32_32.png']) {
    const img = document.createElement('img'); img.src = src; img.style.width = '100%'; gridEl.append(img)
  }

  const keys = new Set<string>()
  let facing = 0, animT = 0, moving = false
  window.addEventListener('keydown', (e) => {
    const k = e.key.toLowerCase()
    keys.add(k)
    if (['arrowup','arrowdown','arrowleft','arrowright',' '].includes(k)) e.preventDefault()
    if (k === 'g') useGround = !useGround
    if (k === 'm' && audio) { muted = !muted; audio.muted = muted }
    if (k === 'escape') { dialogOpen = false; renderDialog() }
    if ((k === 'e' || k === 'enter') && dialogOpen) { advanceDialog(); e.preventDefault(); return }
    if (k === 'e' && !dialogOpen) {
      // nearest NPC
      let best: { d: number; o: MapObj } | null = null
      const range = gameData?.interact_range ?? 2
      for (const o of objects) {
        const ox = o.lx ?? (o.x != null ? o.x - origin.x : null)
        const oy = o.ly ?? (o.y != null ? o.y - origin.y : null)
        if (ox == null || oy == null) continue
        const d = Math.hypot(ox - pos.x, oy - pos.y)
        if (d <= range && (!best || d < best.d)) best = { d, o }
      }
      if (best?.o.EventID) { dlg.state = 0; dlg.start(String(best.o.EventID)); dialogOpen = dlg.open; renderDialog() }
    }
    if (k === ' ' && !dialogOpen && attackCd <= 0) {
      attackT = 0.28
      attackCd = (gameData?.attack?.cooldown_ms ?? 450) / 1000
      playerAttack(foes, pos, (facing % 8) * (Math.PI / 4) - Math.PI, stats)
    }
    if (dlg.open && dlg.choices.length && ['1','2','3','4','5','6','7','8','9'].includes(k)) {
      dlg.pick(Number(k) - 1); dialogOpen = dlg.open; renderDialog(); return
    }
    if (k === 'escape' && dlg.open) { dlg.close(); dialogOpen = false; renderDialog(); return }
    // Inventory toggle
    if (k === 'i' && !dialogOpen) { inv.open = !inv.open; if (!inv.open) { inv.shopOpen = false; inv.embedOpen = false }; renderInv(); return }
    if (k === 'escape' && (inv.open || inv.shopOpen || inv.embedOpen)) {
      inv.open = inv.shopOpen = inv.embedOpen = false; renderInv(); return
    }
    // Potions from Init stacks: key1 = 小血瓶, key3 = 小气瓶 (slots 0 & 2)
    if (['1', '2', '3', '4'].includes(k) && !dialogOpen && !inv.shopOpen) {
      const i = Number(k) - 1
      if (inv.usePotionSlot(i, stats)) { hud.pots = [...inv.potSlots()]; renderInv() }
    }
    // 5 = 飞蝗石 throw, 6 = 指南珠 return spawn
    if (k === '5' && !dialogOpen) {
      if (inv.throwStone()) {
        const ang = (facing % 8) * (Math.PI / 4) - Math.PI
        // chip nearest foe in facing cone
        let best: Foe | null = null; let bd = 9
        for (const f of foes) {
          if (f.dead > 0) continue
          const dx = f.x - pos.x, dy = f.y - pos.y, d = Math.hypot(dx, dy)
          if (d > 5 || d >= bd) continue
          const a = Math.atan2(dy, dx), diff = Math.abs(Math.atan2(Math.sin(a - ang), Math.cos(a - ang)))
          if (diff < 0.9) { best = f; bd = d }
        }
        if (best) { best.hp -= 25; best.hitT = 0.2; if (best.hp <= 0) { best.dead = 12; stats.exp += best.exp ?? 15 } }
        hud.pots = [...inv.potSlots()]
      }
    }
    if (k === '6' && !dialogOpen) {
      if (inv.useCompass()) { pos.x = spawnPos.x; pos.y = spawnPos.y }
    }
    // F1 = 扫叶 (Init left skill 6): whirl AOE, MP from Skill.txt
    if (k === 'f1' && !dialogOpen && attackCd <= 0) {
      const sk = inv.skill('left')
      const cost = sk?.mp ?? 9
      if (stats.mp >= cost) {
        stats.mp -= cost; attackT = 0.45; attackCd = 0.9
        const mult = Math.abs(Number(sk?.at_mult ?? 1)) || 1
        const at0 = stats.at ?? 40; stats.at = at0 * (mult > 0 && mult < 5 ? Math.max(mult, 1) : 1.2)
        for (let a = 0; a < 8; a++) playerAttack(foes.filter((f) => f.hitT <= 0), pos, a * Math.PI / 4, stats, 2.2)
        stats.at = at0
        inv.flash(`${sk?.name ?? '扫叶'}！`)
      } else inv.flash('真气不足')
    }
    // F2 = 疾电 (Init right skill 35): strong frontal hit, range from Skill.txt 384≈3 cells
    if (k === 'f2' && !dialogOpen && attackCd <= 0) {
      const sk = inv.skill('right')
      const cost = sk?.mp ?? 18
      if (stats.mp >= cost) {
        stats.mp -= cost; attackT = 0.35; attackCd = 0.85
        const mult = Number(sk?.at_mult ?? 2) || 2
        const at0 = stats.at ?? 40; stats.at = at0 * mult
        playerAttack(foes, pos, (facing % 8) * (Math.PI / 4) - Math.PI, stats, 3.2)
        stats.at = at0
        inv.flash(`${sk?.name ?? '疾电'}！`)
      } else inv.flash('真气不足')
    }
    if (k === 'f9') {
      dlg.unlockNorthGate()
      // reopen gate cells immediately
      if (walkGrid) {
        for (const [gx, gy] of [[70,24],[71,24],[72,24]] as [number,number][]) {
          if (gy < walkGrid.length) { const row = walkGrid[gy].split(''); row[gx] = '1'; walkGrid[gy] = row.join('') }
        }
        WG = { g: walkGrid, ox: origin.x, oy: origin.y }
      }
      hint.textContent = 'DEBUG: 北门已开 (sy1=1, exit 1-1s unlocked) — 同与沈云对话'
    }
    if (k === 'q' && !dialogOpen && attackCd <= 0 && stats.mp >= 10) {
      stats.mp -= 10; attackT = 0.4; attackCd = 0.8
      for (let a = 0; a < 8; a++) playerAttack(foes.filter((f) => f.hitT <= 0), pos, a * Math.PI / 4, stats, 2.5)
    }
  })
  window.addEventListener('keyup', (e) => keys.delete(e.key.toLowerCase()))

  function iso(x: number, y: number): Vec {
    return { x: (x - y) * (tileW / 2), y: (x + y) * (tileH / 2) }
  }
  function walkable(x: number, y: number): boolean {
    return walkableNow(x, y, mapW, mapH, blocked)
  }
  function inView(sx: number, sy: number, margin = 160): boolean {
    return sx > -margin && sy > -margin && sx < canvas.width + margin && sy < canvas.height + margin
  }

  let last = performance.now()
  function frame(now: number) {
    const dt = Math.min(0.05, (now - last) / 1000)
    last = now
    if (attackCd > 0) attackCd -= dt
    if (attackT > 0) attackT -= dt
    inv.tick(dt); if (inv.toastT > 0) renderToast()

    let dx = 0, dy = 0
    if (!dialogOpen) {
      if (keys.has('w') || keys.has('arrowup')) { dx -= 1; dy -= 1 }
      if (keys.has('s') || keys.has('arrowdown')) { dx += 1; dy += 1 }
      if (keys.has('a') || keys.has('arrowleft')) { dx -= 1; dy += 1 }
      if (keys.has('d') || keys.has('arrowright')) { dx += 1; dy -= 1 }
    }
    const len = Math.hypot(dx, dy) || 1
    moving = dx !== 0 || dy !== 0
    if (moving) {
      facing = Math.round((Math.atan2(dy, dx) + Math.PI) / (Math.PI / 4)) % 8
      animT += dt * 8
    }
    const running = keys.has('shift') && (dx !== 0 || dy !== 0) && (stats.sp ?? 1) > 0.02
    stats.sp = Math.max(0, Math.min(1, (stats.sp ?? 1) + (running ? -10 / 80 : 3 / 80) * dt))
    const speed = running ? 8 : 5
    const nx = pos.x + (dx / len) * speed * dt
    const ny = pos.y + (dy / len) * speed * dt
    if (walkable(nx, pos.y)) pos.x = nx
    if (walkable(pos.x, ny)) pos.y = ny
    pos.x = Math.max(0, Math.min(mapW - 1, pos.x))
    pos.y = Math.max(0, Math.min(mapH - 1, pos.y))

    stepFoes(foes, pos, stats, dt, walkable)
    warpCd -= dt; (window as unknown as { __djfm: unknown }).__djfm = { scene: curScene, nt: curTriggers.length, cd: warpCd, near: Math.min(...curTriggers.map((g) => Math.hypot(g.x - origin.x - pos.x, g.y - origin.y - pos.y))), x: pos.x + origin.x, y: pos.y + origin.y, sy1: dlg.flags.sy1 ?? 0, exit11: dlg.exitText['1-1s'] ?? null }
    const nearT = curTriggers.some((g) => Math.hypot(g.x - origin.x - pos.x, g.y - origin.y - pos.y) < 4.5)
    if (!nearT) warpArmed = true
    if (warpCd <= 0 && warpArmed) for (const g of curTriggers) {
      if (Math.hypot(g.x - origin.x - pos.x, g.y - origin.y - pos.y) < 3.2) {
        const dest = g.script.split(/\s+/)[1]?.toLowerCase()
        if (dest && packIndex?.packs.some((p) => p.id === packOf(dest))) {
          const lock = dlg.exitLock(dest)
          if (lock) {
            dlg.npc = '出口'; dlg.lines = (dlg.text(lock).replace(/^\(对话 \d+\)$/, '') || '（前方的路还不能走——先去和沈云说说吧。）').split('\n').filter(Boolean)
            if (!dlg.lines.length) dlg.lines = ['（前方的路还不能走——先去和沈云说说吧。）']; dlg.idx = 0; dlg.choices = []; dlg.open = true
            dialogOpen = true; renderDialog(); warpCd = 0.8; break
          }
          warpCd = 99; void applyPack(packOf(dest), curScene); break
        }
      }
    }
    stats.mp = Math.min(stats.maxMp, stats.mp + dt * 1.2)
    stats.hp = Math.min(stats.maxHp, stats.hp + dt * 1.4)
    if (stats.hp <= 0) { stats.hp = stats.maxHp; pos.x = spawnPos.x; pos.y = spawnPos.y }
    const focus = iso(pos.x, pos.y)
    cam.x += (canvas.width / 2 - focus.x - cam.x) * Math.min(1, 6 * dt)
    cam.y += (canvas.height / 2 - focus.y - 40 - cam.y) * Math.min(1, 6 * dt)

    ctx.fillStyle = '#0a1220'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    if (useGround && ground && groundMeta) {
      const tw = groundMeta.tile_w, th = groundMeta.tile_h
      const wx = pos.x + origin.x, wy = pos.y + origin.y
      const gFocusX = (wx - wy) * (tw / 2) - groundMeta.min_sx
      const gFocusY = (wx + wy) * (th / 2) - groundMeta.min_sy
      ctx.globalAlpha = 0.92
      // ground_full is exported at half pitch (tile_w=32); buildings use full 64x32 iso → scale ground to match
      const gs = tileW / tw
      ctx.imageSmoothingEnabled = false
      ctx.drawImage(ground, canvas.width / 2 - gFocusX * gs, canvas.height / 2 - 40 - gFocusY * gs, ground.width * gs, ground.height * gs)
      ctx.globalAlpha = 1
    }

    type Draw = { z: number; fn: () => void }
    const draws: Draw[] = []

    // Lazy atlas chunks — only when ground_full is off (G toggles)
    if (!useGround || !ground) {
      for (const a of atlases) {
        const mid = iso(a.x + a.w / 2, a.y + a.h / 2)
        if (!inView(mid.x + cam.x, mid.y + cam.y, 400)) continue
        void ensureAtlas(a)
        const img = atlasImgs.get(a.file)
        if (!img) continue
        for (let ly = 0; ly < a.h; ly++) {
          for (let lx = 0; lx < a.w; lx++) {
            const x = a.x + lx, y = a.y + ly
            const p = iso(x, y)
            const sx = p.x + cam.x, sy = p.y + cam.y
            if (!inView(sx, sy, tileW)) continue
            draws.push({
              z: x + y,
              fn: () => {
                ctx.drawImage(img, lx * tileW, ly * tileH, tileW, tileH, sx - tileW / 2, sy - tileH / 2, tileW, tileH)
              },
            })
          }
        }
      }
    }

    for (const b of buildings) {
      const lx = b.x - origin.x, ly = b.y - origin.y
      if (lx < -30 || ly < -30 || lx > mapW + 30 || ly > mapH + 30) continue
      const op = iso(lx, ly)
      for (const q of b.parts ?? []) {
        const img = buildingImgs.get(q.file)
        if (!img) continue
        const sx0 = op.x + cam.x + q.ox, sy0 = op.y + cam.y + q.oy
        if (sx0 > canvas.width || sy0 > canvas.height || sx0 + img.width < 0 || sy0 + img.height < 0) continue
        // Phase 13: hotspot from BLD part (ox,oy); depth = anchor cell iso row
        // footprint rule: anchor = front corner of footprint; player is behind iff not past anchor on either axis
        const pz = pos.x + pos.y + 0.25
        const inFoot = pos.x <= lx + 0.5 && pos.y <= ly + 0.5 && pos.x > lx - (b.fw ?? 1) - 0.5 && pos.y > ly - (b.fh ?? 1) - 0.5
        const past = pos.x > lx + 0.5 || pos.y > ly + 0.5
        let z = lx + ly + 0.2
        if (inFoot) z = Math.max(z, pz + 0.01)       // player under/behind this building's footprint → building on top
        else if (past) z = Math.min(z, pz - 0.01)    // player past the front corner → player on top
        draws.push({ z, fn: () => ctx.drawImage(img, sx0, sy0) })
      }
    }

    for (const o of objects) {
      const ox = o.lx ?? (o.x != null ? o.x - origin.x : o.MapX != null ? o.MapX - origin.x : null)
      const oy = o.ly ?? (o.y != null ? o.y - origin.y : o.MapY != null ? o.MapY - origin.y : null)
      if (ox == null || oy == null) continue
      const op = iso(ox, oy)
      const sx = op.x + cam.x, sy = op.y + cam.y
      const dirKey = o.EventID != null ? `${o.EventID}_${Math.round((Math.atan2(pos.y - oy, pos.x - ox) + Math.PI) / (Math.PI / 4)) % 8}` : ''
      const img = (dirKey && npcImgs.get(dirKey)) || (o.file ? npcImgs.get(o.file) : undefined)
      if (!inView(sx, sy, 200)) continue
      draws.push({
        z: ox + oy + 0.2,
        fn: () => {
          if (img) {
            // SprRole oy = foot hotspot Y in sprite; fallback bottom-center
            const hotY = o.oy != null && o.oy > 0 ? o.oy : img.height - 8
            const hotX = o.ox != null && o.ox > 0 ? o.ox : img.width / 2
            ctx.drawImage(img, sx - hotX, sy - hotY)
          }

          else { ctx.fillStyle = '#ffd24a'; ctx.beginPath(); ctx.arc(sx, sy, 5, 0, Math.PI * 2); ctx.fill() }
          ctx.fillStyle = '#ffe9a0'; ctx.font = '10px ui-sans-serif,system-ui'
          ctx.fillText(String(o.EventID ?? o.ModelID ?? '?'), sx + 6, sy - 4)
        },
      })
    }

    let spr = player
    {
      const d = ((facing % 8) + 8) % 8
      if (attackT > 0 && playerAttackSpr[d]) spr = playerAttackSpr[d]
      else if (moving && playerWalk[d]?.length) spr = playerWalk[d][Math.floor(animT) % playerWalk[d].length]
      else if (playerIdle[d]) spr = playerIdle[d]
    }
    const pp = iso(pos.x, pos.y)
    draws.push({
      z: pos.x + pos.y + 0.25,
      fn: () => {
        ctx.drawImage(spr, pp.x + cam.x - spr.width / 2, pp.y + cam.y - spr.height + 10)
        if (attackT > 0) {
          const ang = (facing % 8) * (Math.PI / 4) - Math.PI
          const reach = 28
          ctx.strokeStyle = `rgba(255,220,120,${Math.min(1, attackT * 4)})`
          ctx.lineWidth = 3
          ctx.beginPath()
          ctx.arc(pp.x + cam.x, pp.y + cam.y - 12, reach, ang - 0.7, ang + 0.7)
          ctx.stroke()
        }
      },
    })
    for (const f of foes) {
      if (f.dead > 0 && f.dead < 9) continue
      const fp = iso(f.x, f.y), fx = fp.x + cam.x, fy = fp.y + cam.y
      if (!inView(fx, fy, 200)) continue
      const set = f.set != null ? monSets[String(f.set)] : undefined
      const act = set?.[f.act ?? 'idle'] ?? set?.idle
      let img: HTMLImageElement | undefined
      if (act) {
        const per = act.per_dir, nd = Math.max(1, Math.floor(act.frames.length / per))
        const fps = f.act === 'walk' ? 10 : f.act === 'attack' ? 10 : 4
        let k = Math.floor((f.actT ?? 0) * fps)
        k = f.act === 'death' || f.act === 'attack' ? Math.min(per - 1, k) : k % per
        const fr = act.frames[((f.dir ?? 0) % nd) * per + k]
        if (fr) img = monImgs.get(fr[0])
      }
      draws.push({ z: f.x + f.y + 0.24, fn: () => {
        if (img) {
          if (f.hitT > 0) ctx.filter = 'brightness(1.8)'
          ctx.drawImage(img, fx - img.width / 2, fy - img.height + 6)
          ctx.filter = 'none'
        } else { ctx.fillStyle = '#7a2a2a'; ctx.beginPath(); ctx.ellipse(fx, fy - 18, 10, 18, 0, 0, Math.PI * 2); ctx.fill() }
        if (f.dead <= 0) {
          const top = fy - (img?.height ?? 40) - 6
          ctx.fillStyle = '#000'; ctx.fillRect(fx - 18, top, 36, 4)
          ctx.fillStyle = '#e33'; ctx.fillRect(fx - 18, top, 36 * Math.max(0, f.hp / f.maxHp), 4)
          ctx.fillStyle = '#ffd9a0'; ctx.font = '10px ui-sans-serif,system-ui'; ctx.fillText(f.name ?? '', fx - 18, top - 3)
        }
      } })
    }
    draws.sort((a, b) => a.z - b.z)
    for (const d of draws) d.fn()

    // Phase 14: scene light tint (fit vs Wine 1-0s: rgb*≈(0.63,0.63,0.80)+(8,9,10)) + rain (ScnInfo BigRain15/SmallRain20)
    if (tintOn) {
      ctx.save()
      ctx.globalCompositeOperation = 'multiply'
      ctx.fillStyle = 'rgb(161,161,204)'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.globalCompositeOperation = 'lighter'
      ctx.fillStyle = 'rgb(8,9,10)'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.restore()
    }
    if (rainOn) {
      ctx.save(); ctx.strokeStyle = 'rgba(190,200,220,0.35)'; ctx.lineWidth = 1; ctx.beginPath()
      const tt = performance.now() / 1000
      for (let i = 0; i < 140; i++) {
        const rx = ((i * 97.13 + tt * 60) % (canvas.width + 60)) - 30
        const ry = ((i * 53.71 + tt * 520 + (i % 7) * 40) % (canvas.height + 40)) - 20
        ctx.moveTo(rx, ry); ctx.lineTo(rx - 3, ry + 14)
      }
      ctx.stroke(); ctx.restore()
    }

    hud.draw(ctx, stats, { skillL: inv.skill('left')?.name, skillR: inv.skill('right')?.name, money: inv.money, weapon: inv.weaponName() })
    if (ground && groundMeta) {
      const tw = groundMeta.tile_w, th = groundMeta.tile_h
      const g = (x: number, y: number) => ({ x: (x + origin.x - y - origin.y) * (tw / 2) - groundMeta!.min_sx, y: (x + origin.x + y + origin.y) * (th / 2) - groundMeta!.min_sy })
      const me = g(pos.x, pos.y)
      const dots = [...foes.filter((f) => f.dead <= 0).map((f) => ({ ...g(f.x, f.y), c: '#ff3030' })), ...objects.map((o) => ({ ...g((o.x ?? 0) - origin.x, (o.y ?? 0) - origin.y), c: '#3a6cff' })), { ...me, c: '#30ff30' }]
      if (miniImg) hud.drawMinimap(ctx, miniImg, me.x / 2, me.y / 2, 0.75, dots.map((d) => ({ ...d, x: d.x / 2, y: d.y / 2 })), mapLabel.split(' ')[0])
      else hud.drawMinimap(ctx, ground, me.x, me.y, 0.25, dots, mapLabel.split(' ')[0])
    }
    ctx.fillStyle = '#9ecbff'
    ctx.font = '12px ui-sans-serif,system-ui'
    const wx = (pos.x + origin.x).toFixed(1), wy = (pos.y + origin.y).toFixed(1)
    const bgmState = muted ? 'BGM:mute' : 'BGM:on'
    ctx.fillText(
      `[${packId}] ${mapLabel} | (${wx},${wy}) ${bgmState} | E谈 Space砍 G地 M静音`,
      12, 20,
    )
    requestAnimationFrame(frame)
  }
  requestAnimationFrame(frame)
}

main().catch((e) => { document.body.textContent = String(e) })
