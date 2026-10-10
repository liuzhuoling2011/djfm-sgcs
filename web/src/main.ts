import './style.css'
import { DialogSys } from './dialog'
import { Hud, SOFT_DF, playerAttack, setSoftDf, stepFoes, setInitGrowth, applyInitLevel, setRemakeTuning, INIT, REMAKE, type Foe, type Stats, type FloatDmg } from './hud'
import { Inventory } from './inventory'
import { spawnFx, tickFx, drawFx, loadFxSprites, type SkillFx } from './fx'
import { loadSfx, playSfx, setSfxEnabled } from './sfx'

type Vec = { x: number; y: number }
type MapObj = {
  lx?: number; ly?: number; x?: number; y?: number; MapX?: number; MapY?: number
  ModelID?: number; Type?: number; EventID?: string; name?: string; file?: string; sw?: number; sh?: number; npc_dirs?: string[]; ox?: number; oy?: number; graph?: number
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

/** Prefer HD path, fall back to SD. */
async function loadImageHd(hd: string, sd: string): Promise<HTMLImageElement> {
  try { return await loadImage(hd) } catch { return await loadImage(sd) }
}

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
      <h1>刀剑封魔录外传 · Phase 50 HD</h1>
      <p>瓦当镇 · 原版 JM 底栏 · 现代对话/行囊 · Real-ESRGAN 高清 · WASD</p>
    </header>
    <div class="toolbar" id="packs"></div>
    <div id="stage">
      <canvas id="c" width="1280" height="720"></canvas>
      <div id="toast" class="toast hidden"></div>
      <div id="dialog" class="dialog hidden"></div>
      <div id="inv" class="desk-wrap hidden"></div>
    </div>
    <p class="hint" id="hint">Loading…</p>
    <section class="panel"><h2>样本</h2><div class="grid" id="grid"></div></section>
  `

  const packsEl = document.querySelector<HTMLDivElement>('#packs')!
  const hint = document.querySelector<HTMLParagraphElement>('#hint')!
  const stageEl = document.querySelector<HTMLDivElement>('#stage')!
  const invEl = document.querySelector<HTMLDivElement>('#inv')!
  const toastEl = document.querySelector<HTMLDivElement>('#toast')!
  const dialogEl = document.querySelector<HTMLDivElement>('#dialog')!
  if (packIndex) hint.textContent = (packIndex.begin_scn_mapping ?? '') + ' · WASD移动 · Shift奔跑 · E对话 · Space攻击 · I行囊 · 1/3药'
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
  setSoftDf(qs.get('softdf') === '1')
  const helpEl = document.createElement('div')
  helpEl.className = 'combat-help'
  helpEl.id = 'combat-help'
  const helpTxt = (gameData as { combat?: { help?: string } } | null)?.combat?.help
    ?? 'Init成长 AT40+4/lv；伤害 AT−DF/2；怪物 RolePrivate+场景封顶。?softdf=1 软DF。'
  helpEl.innerHTML = helpTxt + ' <button type="button" style="margin-left:8px">知道了</button>'
  document.body.append(helpEl)
  helpEl.querySelector('button')?.addEventListener('click', () => helpEl.classList.add('hidden'))
  window.setTimeout(() => helpEl.classList.add('hidden'), 14000)
  if (SOFT_DF) console.info('[djfm] soft-DF ON (?softdf=1)')
  else console.info('[djfm] soft-DF off; using placeholder foe caps')
  {
    const ig = (gameData as { combat?: { init_male?: Record<string, number> } })?.combat?.init_male
    if (ig) setInitGrowth(ig)
    try {
      const j = await (await fetch('game/data/init_male.json')).json()
      setInitGrowth(j)
    } catch { /* game.json combat.init_male already applied */ }
  }
  await loadFxSprites()
  await loadSfx()
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
  let skillFx: SkillFx | null = null
  let floaters: FloatDmg[] = []
  let playerHurtFlash = 0
  let dying = 0  // death overlay timer; >0 = respawning
  type Fellow = { id: string; x: number; y: number; dir: number; imgs: HTMLImageElement[] }
  let fellow: Fellow | null = null
  const fellowImgs = new Map<string, HTMLImageElement[]>()
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
      showShop: () => { inv.embedOpen = false; inv.shopMode = 'buy'; inv.shopOpen = true; inv.open = false; renderInv() },
      showEmbed: () => { inv.shopOpen = false; inv.embedOpen = true; inv.open = false; renderInv() },
    }
    dlg.onAct = (act) => { dlg.currentAct = act; inv.flash(`切换至第 ${act + 1} 章`) }
    dlg.onForeword = (textId, jm, act) => { showActForeword(textId, jm, act) }
        dlg.onGo = (scene) => {
      const id = packOf(scene === 'sws' ? 'sws' : scene)
      if (packIndex?.packs.some((p) => p.id === id)) {
        inv.flash(`前往 ${dlg.names[scene] ?? scene}…`)
        void applyPack(id, curScene)
      } else inv.flash(`（地图 ${scene} 尚未导出）`)
    }
    dlg.onCombat = (battleId, eventId) => {
      if (eventId === 'bossyuheng') {
        const o = objects.find((x) => String(x.EventID).toLowerCase() === 'bossyuheng')
        const bx = o ? ((o.lx ?? (o.x != null ? o.x - origin.x : pos.x))) : pos.x + 2
        const by = o ? ((o.ly ?? (o.y != null ? o.y - origin.y : pos.y))) : pos.y
        foes = foes.filter((f) => f.name !== '玉衡')
        const st = monSets['196']
        foes.push({
          x: bx, y: by, hx: bx, hy: by, hp: 520, maxHp: 520, cd: 0.8, hitT: 0, dead: 0,
          at: 34, df: 42, exp: 200, sight: 8, spd: 12, name: '玉衡', set: 196, act: 'idle', actT: 0, dir: 0,
        })
        // ensure frames loaded
        if (st) for (const a of Object.values(st)) for (const f of ((a as { frames?: unknown[] })?.frames ?? []) as ([string, number, number] | null)[]) {
          if (f && !monImgs.has(f[0])) loadImageHd(`${base}/mon_hd/${f[0]}`, `${base}/mon/${f[0]}`).then((im) => monImgs.set(f[0], im)).catch(() => {})
        }
        inv.flash('玉衡来袭！')
        ;(window as unknown as { __djfmBoss?: string }).__djfmBoss = 'bossyuheng'
      } else if (eventId === 'bossyezhu') {
        const o = objects.find((x) => String(x.EventID).toLowerCase() === 'bossyezhu')
        const bx = o ? ((o.lx ?? (o.x != null ? o.x - origin.x : pos.x))) : pos.x + 2
        const by = o ? ((o.ly ?? (o.y != null ? o.y - origin.y : pos.y))) : pos.y
        foes = foes.filter((f) => f.name !== '魔豕兽')
        foes.push({
          x: bx, y: by, hx: bx, hy: by, hp: 400, maxHp: 400, cd: 1, hitT: 0, dead: 0,
          at: 35, df: 20, exp: 80, sight: 7, spd: 10, name: '魔豕兽', set: 'pd006', act: 'idle', actT: 0, dir: 0, event: 'bossyezhu',
        })
        const st = monSets['pd006']
        if (st) for (const a of Object.values(st)) for (const f of ((a as { frames?: unknown[] })?.frames ?? []) as ([string, number, number] | null)[]) {
          if (f && !monImgs.has(f[0])) loadImageHd(`${base}/mon_hd/${f[0]}`, `${base}/mon/${f[0]}`).then((im) => monImgs.set(f[0], im)).catch(() => {})
        }
        inv.flash('魔豕兽出现！')
        ;(window as unknown as { __djfmBoss?: string }).__djfmBoss = 'bossyezhu'
      } else if (eventId === 'bossdaxiang') {
        const o = objects.find((x) => String(x.EventID).toLowerCase() === 'bossdaxiang')
        let bx = o ? ((o.lx ?? (o.x != null ? o.x - origin.x : pos.x))) : pos.x + 2
        let by = o ? ((o.ly ?? (o.y != null ? o.y - origin.y : pos.y))) : pos.y
        if (!walkableNow(bx, by, mapW, mapH, blocked)) {
          // Phase 25: 战象 standability — place on nearest walkable (or beside player)
          let found = false
          search: for (let r = 1; r < 10; r++) for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++)
            if (walkableNow(bx + dx, by + dy, mapW, mapH, blocked)) { bx += dx; by += dy; found = true; break search }
          if (!found) { bx = pos.x + 1.5; by = pos.y }
        }
        foes = foes.filter((f) => f.name !== '战象')
        foes.push({
          x: bx, y: by, hx: bx, hy: by, hp: 650, maxHp: 650, cd: 1.1, hitT: 0, dead: 0,
          at: 42, df: 45, exp: 250, sight: 8, spd: 8, name: '战象', set: 'pd009', act: 'idle', actT: 0, dir: 0, event: 'bossdaxiang',
        })
        const st = monSets['pd009']
        if (st) for (const a of Object.values(st)) for (const f of ((a as { frames?: unknown[] })?.frames ?? []) as ([string, number, number] | null)[]) {
          if (f && !monImgs.has(f[0])) loadImageHd(`${base}/mon_hd/${f[0]}`, `${base}/mon/${f[0]}`).then((im) => monImgs.set(f[0], im)).catch(() => {})
        }
        inv.flash('战象来袭！')
        ;(window as unknown as { __djfmBoss?: string }).__djfmBoss = 'bossdaxiang'
      } else if (eventId === 'bosstianji' || eventId === 'boss') {
        const spawnOne = (ev: string, ox: number, oy: number) => {
          foes = foes.filter((f) => f.event !== ev)
          const set = monSets['pd613'] ? 'pd613' : (monSets['pd009'] ? 'pd009' : 'pd008')
          foes.push({
            x: ox, y: oy, hx: ox, hy: oy, hp: 720, maxHp: 720, cd: 1.0, hitT: 0, dead: 0,
            at: 50, df: 48, exp: 300, sight: 9, spd: 9, name: '天机', set, act: 'idle', actT: 0, dir: 0, event: ev,
          })
          const st = monSets[set]
          if (st) for (const a of Object.values(st)) for (const f of ((a as { frames?: unknown[] })?.frames ?? []) as ([string, number, number] | null)[]) {
            if (f && !monImgs.has(f[0])) loadImageHd(`${base}/mon_hd/${f[0]}`, `${base}/mon/${f[0]}`).then((im) => monImgs.set(f[0], im)).catch(() => {})
          }
        }
        const o1 = objects.find((x) => String(x.EventID).toLowerCase() === 'bosstianji')
        const o2 = objects.find((x) => String(x.EventID).toLowerCase() === 'boss')
        const near = (o: typeof o1, fb: number) => {
          const bx = o ? ((o.lx ?? (o.x != null ? o.x - origin.x : pos.x + fb))) : pos.x + fb
          const by = o ? ((o.ly ?? (o.y != null ? o.y - origin.y : pos.y))) : pos.y
          // standability: nudge onto walkable
          let x = bx, y = by
          if (!walkableNow(x, y, mapW, mapH, blocked)) {
            search: for (let r = 1; r < 8; r++) for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++)
              if (walkableNow(bx + dx, by + dy, mapW, mapH, blocked)) { x = bx + dx; y = by + dy; break search }
          }
          return { x, y }
        }
        if (eventId === 'bosstianji' || !foes.some((f) => f.event === 'bosstianji')) {
          const p1 = near(o1, 1.5); spawnOne('bosstianji', p1.x, p1.y)
        }
        if (eventId === 'boss' || !foes.some((f) => f.event === 'boss')) {
          const p2 = near(o2, -1.5); spawnOne('boss', p2.x, p2.y)
        }
        inv.flash('双天机来袭！')
        ;(window as unknown as { __djfmBoss?: string }).__djfmBoss = 'bosstianji'
      } else {
        inv.flash(`（战斗 ${battleId}/${eventId} 未接线）`)
      }
    }
    dlg.onFellow = (eventId, enable) => {
      if (!enable) { fellow = null; inv.flash(`${eventId} 离开队伍`); return }
      void (async () => {
        let imgs = fellowImgs.get(eventId)
        if (!imgs) {
          imgs = []
          for (let d = 0; d < 8; d++) {
            try { imgs.push(await loadImage(`game/fellow/${eventId}/${d}.png`)) } catch {
              try { imgs.push(await loadImage(`game/map/npcs/${eventId}_${d}.png`)) } catch { /* */ }
            }
          }
          fellowImgs.set(eventId, imgs)
        }
        if (!imgs.length) { inv.flash(`（同伴 ${eventId} 无立绘）`); return }
        fellow = { id: eventId, x: pos.x - 1.2, y: pos.y - 0.5, dir: facing, imgs }
        inv.flash(`${dlg.names[eventId] ?? eventId} 加入同行`)
      })()
    }
    dlg.onRem = (eventId, mode, slot, val) => {
      const k = eventId.toLowerCase()
      if (mode === 'rem') {
        hiddenEvents.add(k)
        foes = foes.filter((f) => (f.event ?? '').toLowerCase() !== k && (f.name ?? '') !== k)
        inv.flash(`移除 ${dlg.names[k] ?? k}`)
      } else if (mode === 'reset') {
        hiddenEvents.delete(k)
        if (flagTable[k]) flagTable[k][111] = 0
        inv.flash(`重置 ${dlg.names[k] ?? k}`)
      } else if (mode === 'table' && slot != null) {
        flagTable[k] = flagTable[k] ?? {}
        flagTable[k][slot] = val ?? 0
        if (slot === 111 && val === 1) hiddenEvents.add(k)
        if (slot === 111 && val === 0) hiddenEvents.delete(k)
      }
    }
    dlg.onFx = (kind, arg) => {
      if (kind === 'screen') inv.flash(`（ScreenEffect ${arg ?? ''}）`)
      else if (kind === 'bldani') inv.flash(`（机关动画 ${arg ?? ''}）`)
      else if (kind === 'avi') playAvi((arg ?? '').trim().toLowerCase().replace(/\.dhp$/i, ''))
    }
    const ps = inv.potSlots(); hud.pots = [...ps]
  })()
  // mb/player/Init.txt 男主角 — applied via applyInitLevel / setInitGrowth
  const stats: Stats = { hp: INIT.hp, maxHp: INIT.hp, mp: INIT.mp, maxMp: INIT.mp, exp: 0, lvl: 1, at: INIT.at, df: INIT.df, sp: 1 }
  applyInitLevel(stats, 1)
  let monSets: NonNullable<MapMeta['monster_sets']> = {}
  const monImgs = new Map<string, HTMLImageElement>()
  let foes: Foe[] = []
  let cutscene: { img: HTMLImageElement; t: number } | null = null
  const hiddenEvents = new Set<string>()
  const flagTable: Record<string, Record<number, number>> = {}
  const isHidden = (eid: string) => {
    const k = eid.toLowerCase()
    if (hiddenEvents.has(k)) return true
    const slot = flagTable[k]?.[111]
    return slot === 1
  }
  let spawnPos = { x: 0, y: 0 }
  let attackCd = 0
  let hitStop = 0 // Phase 40: brief freeze on melee connect

  function showDialog(eid: string) {
    const d = gameData?.dialogs?.[eid]
    dialogLines = d?.lines?.length ? d.lines : [`（${eid}）……`]
    dialogIdx = 0
    dialogNpc = eid
    dialogOpen = true
    renderDialog()
  }
  
  function renderInv() {
    const show = inv.open || inv.shopOpen || inv.embedOpen
    invEl.classList.toggle('hidden', !show)
    if (!show) { placeChrome(); return }
    // panel_625 paints five grooves (y 32–154). Keep one name per groove when the bag is that short.
    const bagSlots: ({ id: number; qty: number } | null)[] = [...inv.items]
    if (bagSlots.length <= 5) while (bagSlots.length < 5) bagSlots.push(null)
    const rows = bagSlots.map((it) => {
      if (!it) return '<li class="groove empty"></li>'
      const d = inv.props[String(it.id)]
      return `<li class="groove"><span class="nm">${d?.name ?? '#'+it.id}</span><span class="qty">×${it.qty}</span></li>`
    }).join('')
    const bagScroll = inv.items.length > 5 ? ' scroll' : ''
    const head = (title: string, closeAttr: string) =>
      `<header class="desk-head"><h3>${title}</h3><button type="button" class="desk-x" ${closeAttr} aria-label="关闭">×</button></header>`
    if (inv.shopOpen) {
      // ShowJM 20|86 → JM_DEAL; panel_1550 = 326×226
      const buyMode = inv.shopMode === 'buy'
      let slots = ''
      if (buyMode) {
        slots = inv.shopCatalog().map((r, i) => {
          const n = inv.props[String(r.id)]?.name ?? r.id
          const have = inv.qty(r.id)
          return `<button type="button" data-buy="${r.id}"><span class="nm">${i + 1}. ${n}<i class="have">×${have}</i></span><span class="pr">${r.price} 金</span></button>`
        }).join('')
      } else {
        // Only goods the blacksmith stocks (potions / 飞蝗石). Quest props stay in the bag.
        const sellable = inv.shopCatalog().filter((r) => inv.qty(r.id) > 0)
        slots = sellable.map((r, i) => {
          const n = inv.props[String(r.id)]?.name ?? r.id
          const pr = inv.sellPrice(r.id)
          return `<button type="button" data-sell="${r.id}"><span class="nm">${i + 1}. ${n}<i class="have">×${inv.qty(r.id)}</i></span><span class="pr">售 ${pr} 金</span></button>`
        }).join('') || '<div class="jm-empty">行囊里没有铁匠收购的药品或飞蝗石</div>'
      }
      invEl.innerHTML = `<div class="desk shop">
        ${head('买卖', 'data-close-shop')}
        <div class="desk-list">${slots}</div>
        <footer class="desk-foot">
          <div class="money">金钱 ${inv.money}</div>
          <div class="desk-actions">
            <button type="button" class="${buyMode ? 'on' : ''}" data-shop-mode="buy">购入</button>
            <button type="button" class="${buyMode ? '' : 'on'}" data-shop-mode="sell">卖出</button>
            <button type="button" data-close-shop>关闭</button>
          </div>
        </div>
      </div></div>`
    } else if (inv.embedOpen) {
      // ShowJM 20|62|92 → JM_Enchase; panel_591 326×226
      const gain = 2 * Math.max(1, inv.weaponSlots)
      invEl.innerHTML = `<div class="box"><div class="jm-frame embed">
        <div class="jm-title">镶嵌</div>
        <button type="button" class="jm-close" data-close-embed aria-label="关闭">×</button>
        <div class="jm-embed-info">兵器：${inv.weaponName()}　槽 ×${inv.weaponSlots}　已嵌 ${inv.embedGems}<br/>
          攻击 ${stats.at ?? 40}　金钱 ${inv.money}　蜀水 ×${inv.qty(120)}<br/>
          花费 200 金或 1 蜀水（AT+${gain}）</div>
        <div class="jm-gem-grid" aria-hidden="true">
          ${Array.from({ length: 6 }, (_, i) => `<div class="jm-gem${i < inv.embedGems ? ' on' : ''}"></div>`).join('')}
        </div>
        <div class="jm-embed-actions">
          <button type="button" data-embed>确认镶嵌</button>
          <button type="button" data-close-embed>关闭</button>
        </div>
      </div></div>`
    } else {
      invEl.innerHTML = `<div class="desk bag">
        ${head('行囊', 'data-close-inv')}
        <ul class="desk-list${bagScroll}">${rows}</ul>
        <footer class="desk-foot">
          <div class="equip">装备 ${inv.weaponName()} · F1 ${inv.skill('left')?.name ?? '—'} · F2 ${inv.skill('right')?.name ?? '—'} · 镶嵌 ${inv.embedGems}</div>
          <div class="money">金钱 ${inv.money}</div>
        </footer>
      </div>`
    }
    const syncPots = () => { hud.pots = [...inv.potSlots()] }
    invEl.querySelectorAll('[data-buy]').forEach((b) => b.addEventListener('click', () => {
      inv.buy(Number((b as HTMLElement).dataset.buy)); syncPots(); renderInv()
    }))
    invEl.querySelectorAll('[data-sell]').forEach((b) => b.addEventListener('click', () => {
      inv.sell(Number((b as HTMLElement).dataset.sell)); syncPots(); renderInv()
    }))
    invEl.querySelectorAll('[data-shop-mode]').forEach((b) => b.addEventListener('click', () => {
      inv.shopMode = ((b as HTMLElement).dataset.shopMode === 'sell' ? 'sell' : 'buy')
      renderInv()
    }))
    invEl.querySelectorAll('[data-close-shop]').forEach((b) => b.addEventListener('click', () => {
      inv.shopOpen = false; renderInv()
    }))
    invEl.querySelector('[data-embed]')?.addEventListener('click', () => {
      if (inv.embedUpgrade(stats)) { inv.embedOpen = false }
      renderInv()
    })
    invEl.querySelectorAll('[data-close-embed]').forEach((b) => b.addEventListener('click', () => {
      inv.embedOpen = false; renderInv()
    }))
    invEl.querySelector('[data-close-inv]')?.addEventListener('click', () => { inv.open = false; renderInv() })
    placeChrome()
  }
  /** Lift HTML dialog and desks above the canvas stone bar (110px in 800-space, scaled with the view). */
  let hudSpace = 0
  function placeChrome() {
    const w = canvas.getBoundingClientRect().width
    if (w < 8) return
    const space = Math.round(110 * (w / 800) + 10)
    if (space === hudSpace) return
    hudSpace = space
    stageEl.style.setProperty('--hud-space', `${space}px`)
  }
  window.addEventListener('resize', () => placeChrome())
  window.addEventListener('scroll', () => placeChrome(), true)
  function renderToast() {
    toastEl.classList.toggle('hidden', inv.toastT <= 0)
    if (inv.toastT > 0) toastEl.textContent = inv.toast
  }

  function clampDialog() {
    requestAnimationFrame(() => placeChrome())
  }
  function renderDialog() {
    const wrap = (title: string, body: string, hint: string, next: boolean) =>
      `<div class="dlg-board"><div class="dlg-title">${title}</div><div class="dlg-body">${body}</div>${next ? '<button type="button" class="dlg-next" data-dlg-next>继续</button>' : ''}<div class="dlg-hint">${hint}</div></div>`
    const bindBoard = () => {
      dialogEl.querySelector('.dlg-board')?.addEventListener('click', (ev) => {
        if ((ev.target as HTMLElement).closest('button')) return
        advanceDialog()
      })
      dialogEl.querySelector('[data-dlg-next]')?.addEventListener('click', () => advanceDialog())
    }
    if (dlg.open) {
      dialogOpen = true
      dialogEl.classList.remove('hidden')
      if (dlg.choices.length) {
        const opts = dlg.choices.map((c, i) => `<button type="button" class="dlg-choice" data-i="${i}">${i + 1}. ${c.label}</button>`).join('')
        dialogEl.innerHTML = wrap(dlg.npc || '对话', opts, '点选或数字键 · Esc 关闭', false)
        dialogEl.querySelectorAll('.dlg-choice').forEach((b) => b.addEventListener('click', () => { dlg.pick(Number((b as HTMLButtonElement).dataset.i)); dialogOpen = dlg.open; renderDialog() }))
      } else {
        const line = dlg.lines[dlg.idx] ?? ''
        dialogEl.innerHTML = wrap(dlg.npc || '对话', `<p>${line}</p>`, '继续 / E / Enter · Esc 关闭', true)
        bindBoard()
      }
      clampDialog()
      return
    }
    if (!dialogOpen) {
      dialogEl.classList.add('hidden')
      dialogEl.style.transform = ''
      dialogEl.style.bottom = ''
      return
    }
    dialogEl.classList.remove('hidden')
    const line = dialogLines[dialogIdx] ?? ''
    dialogEl.innerHTML = wrap(dialogNpc || '对话', `<p>${line}</p>`, '继续 / E / Enter · Esc 关闭', true)
    bindBoard()
    clampDialog()
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



  // Phase 26: ShowActForeword — dialog text overlay, click/Esc skips
  function showActForeword(textId: number, _jm: number, act: number) {
    const wrap = document.createElement('div'); wrap.className = 'cutscene foreword'
    const box = document.createElement('div'); box.className = 'fore-box'
    const title = document.createElement('div'); title.className = 'fore-title'; title.textContent = `第 ${act + 1} 章`
    const body = document.createElement('div'); body.className = 'fore-body'
    const pack = act <= 0 ? 'public1' : act === 1 ? 'public2' : 'public3'
    const raw = dlg.dialogs[pack]?.[String(textId)] ?? dlg.dialogs.public1?.[String(textId)] ?? dlg.text(textId)
    body.textContent = (raw || '').replace(/\/\/\/\//g, '\n\n').replace(/%\d+%/g, '……')
    const tip = document.createElement('div'); tip.className = 'cut-tip'; tip.textContent = '点击 / Esc 继续'
    box.append(title, body); wrap.append(box, tip); document.body.append(wrap)
    const done = () => { window.removeEventListener('keydown', key, true); wrap.remove() }
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape' || e.key === ' ' || e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); done() } }
    window.addEventListener('keydown', key, true)
    wrap.addEventListener('click', done)
  }

  // Phase 24: DHP (MPEG-1) → mp4 cutscenes; click/Esc/Space skips
  const playedAvi = new Set<string>()
  function playAvi(name: string, once = false) {
    if (!name || (once && playedAvi.has(name))) return
    playedAvi.add(name)
    const wrap = document.createElement('div'); wrap.className = 'cutscene'
    const v = document.createElement('video'); v.src = `game/cutscenes/${name}.mp4`; v.autoplay = true; v.playsInline = true
    const tip = document.createElement('div'); tip.className = 'cut-tip'; tip.textContent = '点击 / Esc 跳过'
    wrap.append(v, tip); document.body.append(wrap)
    const done = () => { window.removeEventListener('keydown', key, true); v.pause(); wrap.remove() }
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape' || e.key === ' ' || e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); done() } }
    window.addEventListener('keydown', key, true)
    wrap.addEventListener('click', done); v.addEventListener('ended', done); v.addEventListener('error', () => { inv.flash(`（PlayAvi ${name} 无视频）`); done() })
    ;(window as unknown as { __djfmAvi?: string }).__djfmAvi = name
  }


  type CombatBal = { scene_tier?: Record<string, number>; df_cap?: number[]; hp_cap?: number[]; at_cap?: number[] }
  function balanceFoe(raw: { hp: number; at: number; df: number }, scene: string) {
    // PLACEHOLDER balance (not soft-DF): cap RolePrivate stats so Init AT+4/lv can clear act-1.
    const bal = (gameData as { combat?: CombatBal } | null)?.combat
    const tier = Math.max(0, Math.min(5, bal?.scene_tier?.[scene] ?? 2))
    const dfCap = bal?.df_cap?.[tier] ?? (28 + tier * 8)
    const hpCap = bal?.hp_cap?.[tier] ?? (220 + tier * 150)
    const atCap = bal?.at_cap?.[tier] ?? (22 + tier * 8)
    return {
      hp: Math.max(40, Math.min(raw.hp, hpCap)),
      at: Math.max(8, Math.min(raw.at, atCap)),
      df: Math.max(5, Math.min(raw.df, dfCap)),
    }
  }

  // Phase 25: quest props on triggers (scene SetPropToObj → E pickup)
  const PROP_TRIG: Record<string, { id: number; flag: string; name: string }> = {
    shushui: { id: 120, flag: 'xss', name: '蜀水' },
    bjsm: { id: 122, flag: 'xbjsm', name: '冰晶石木' },
    qnxbz: { id: 123, flag: 'xqnxbz', name: '千年玄冰柱' },
    tzxs: { id: 121, flag: 'xtzxs', name: '天芝血参' },
  }
  // Scene AddItem pools (from trigger/scene/*.txt) — mode-3 scatter; web drops a few near spawn once
  const SCENE_LOOT: Record<string, number[]> = {
    '1-1s': [5, 6, 16, 25, 197],
    '1-4s': [22, 162, 195, 192, 190, 191],
    '1-5s': [22, 162, 66, 98, 99],
    '1-6s': [22, 162, 66, 98, 99],
    '1-7s': [22, 162, 66, 98, 99],
    '1-9s': [162, 189],
    '1-10s': [162, 189, 46],
    '1-11s': [162, 12, 55],
    '1-10a1s': [162, 189, 46],
    '1-10a2s': [162, 189, 46],
    '1-10a3s': [162, 189, 46],
  }
  const lootedScenes = new Set<string>()
  type GroundLoot = { x: number; y: number; id: number; taken?: boolean }
  let groundLoot: GroundLoot[] = []
  type IceHaz = { x: number; y: number }
  let iceHazards: IceHaz[] = []
  const iceFrames: HTMLImageElement[] = []
  for (const n of ['ice_hazard.png', 'ice_hazard_b.png', 'ice_2472.png', 'ice_2417.png']) {
    try { iceFrames.push(await loadImage(`game/fx/${n}`)) } catch { /* */ }
  }
  const iceImg = iceFrames[0] ?? null
  const iceImgB = iceFrames[1] ?? iceFrames[0] ?? null
  function spawnSceneLoot(scene: string) {
    groundLoot = []
    if (lootedScenes.has(scene)) return
    const pool = SCENE_LOOT[scene]
    if (!pool?.length) return
    lootedScenes.add(scene)
    const n = Math.min(4, 2 + Math.floor(Math.random() * 3))
    for (let i = 0; i < n; i++) {
      const ang = Math.random() * Math.PI * 2, r = 2 + Math.random() * 4
      const x = pos.x + Math.cos(ang) * r, y = pos.y + Math.sin(ang) * r
      if (!walkableNow(x, y, mapW, mapH, blocked)) continue
      groundLoot.push({ x, y, id: pool[Math.floor(Math.random() * pool.length)] })
    }
    if (groundLoot.length) inv.flash(`附近散落了 ${groundLoot.length} 件物资（走近按 E）`)
  }
  function tryPickProp(): boolean {
    const range = gameData?.interact_range ?? 2
    // ground loot
    for (const g of groundLoot) {
      if (g.taken) continue
      if (Math.hypot(g.x - pos.x, g.y - pos.y) > range + 0.5) continue
      g.taken = true
      inv.add(g.id, 1)
      const nm = inv.props[g.id]?.name ?? `道具${g.id}`
      inv.flash(`拾取 ${nm}`)
      return true
    }
    const wx = pos.x + origin.x, wy = pos.y + origin.y
    for (const tr of curTriggers) {
      let key = (tr.script || '').trim().toLowerCase().split(/\s+/).filter(Boolean)[0] || ''
      // 1-11s: empty script at jiguan1 spot
      if (!key && curScene === '1-11s' && Math.hypot(tr.x - 197, tr.y - 157) < 3) key = 'jiguan1'
      if (key.startsWith('jiguan')) {
        const d = Math.hypot(tr.x - wx, tr.y - wy)
        if (d > range + 1.5) continue
        const st = dlg.bldStatus[key] ?? 0
        if (st >= 1) { inv.flash(`${key} 已启动`); return true }
        dlg.bldStatus[key] = 1
        inv.flash(`${key} 机关启动！`)
        checkJiguanReward()
        return true
      }
      const def = PROP_TRIG[key]
      if (!def) continue
      const d = Math.hypot(tr.x - wx, tr.y - wy)
      if (d > range + 1.5) continue
      if (inv.qty(def.id) > 0 || (dlg.flags[def.flag] ?? 0) >= 1) { inv.flash(`此处的${def.name}已被取走`); return true }
      // scene gates: tzxs needs bq1 in [30,40) roughly — script IsFlag bq1 40 1
      if (key === 'tzxs' && (dlg.flags.bq1 ?? 0) >= 40) { inv.flash('天芝血参已不在此处'); return true }
      if (key === 'tzxs' && (dlg.flags.bq1 ?? 0) < 30) { inv.flash('（尚不可取 — 需泊祁指引至九天池）'); return true }
      inv.add(def.id, 1); dlg.flags[def.flag] = 1
      if (key === 'tzxs' && (dlg.flags.bq1 ?? 0) < 40) dlg.flags.bq1 = Math.max(dlg.flags.bq1 ?? 0, 40)
      inv.flash(`获得 ${def.name}`)
      return true
    }
    return false
  }
  function checkJiguanReward() {
    // scene/1-11s: all three jiguan on + xqnz<1 → ResetObj boss*SetPropToObj boss 0 124*PlayAvi
    const a = dlg.bldStatus.jiguan1 ?? 0, b = dlg.bldStatus.jiguan2 ?? 0, c = dlg.bldStatus.jiguan3 ?? 0
    if (a >= 1 && b >= 1 && c >= 1 && (dlg.flags.xqnz ?? 0) < 1) {
      dlg.onRem?.('boss', 'rem')
      if (inv.qty(124) <= 0) {
        inv.add(124, 1); dlg.flags.xqnz = 1
        inv.flash('获得 气凝珠！')
        playAvi('1-11s', true)
      }
      if ((dlg.flags.bq2 ?? 0) < 40) dlg.flags.bq2 = Math.max(dlg.flags.bq2 ?? 0, 40)
    }
  }
  function onFoeKilled(f: Foe) {
    const ev = (f.event || '').toLowerCase()
    // 1-9s: IsDead bossdaxiang → SetFlag zhs1 10
    if (ev === 'bossdaxiang' || f.name === '战象') {
      if ((dlg.flags.zhs1 ?? 0) < 10) {
        dlg.flags.zhs1 = Math.max(dlg.flags.zhs1 ?? 0, 10)
        inv.flash('战象倒下 — zhs1→10（可回镇找张珊/张河生）')
        dlg.onRem?.('bossdaxiang', 'rem')
      }
    }
    // 1-10a6s: IsDead bosstianji*IsDead boss → SetFlag bq2 50
    if (ev === 'bosstianji' || ev === 'boss' || f.name === '天机') {
      const left = foes.filter((x) => !x.gone && x.dead <= 0 && (x.event === 'bosstianji' || x.event === 'boss' || x.name === '天机'))
      // current foe already dying; count others still alive
      const others = foes.filter((x) => x !== f && !x.gone && x.dead <= 0 && (x.event === 'bosstianji' || x.event === 'boss' || x.name === '天机'))
      if (others.length === 0 && (dlg.flags.bq2 ?? 0) < 50) {
        dlg.flags.bq2 = Math.max(dlg.flags.bq2 ?? 0, 50)
        inv.flash('双天机已灭 — bq2→50')
        playedAvi.delete('1-10a6s'); playAvi('1-10a6s', true)
      }
    }
    // 1-2s pig heart already handled elsewhere via qty
  }

  /** Scene script hooks from mb/trigger/scene/*.txt (only sy1/蜀水-related subset). */
  let swsTimer: number | null = null
  function runSceneEnter(scene: string) {
    if (swsTimer != null) { window.clearTimeout(swsTimer); swsTimer = null }
    if (scene === 'sws') {
      // SWS.txt: IsScnIn*IsFlag sy1 18 2 → go 1-3s; else SetTimer 90 → go 1-3s*SetFlag sy1 19
      const sy = dlg.flags.sy1 ?? 0
      if (sy >= 18) {
        inv.flash('赶往落马坡…')
        swsTimer = window.setTimeout(() => { void applyPack('1-3s', 'sws') }, 900)
      } else {
        inv.flash('沈万山遇袭！（计时后赶往落马坡）')
        swsTimer = window.setTimeout(() => {
          dlg.flags.sy1 = Math.max(dlg.flags.sy1 ?? 0, 19)
          inv.flash('sy1→19 · 前往 1-3s 落马坡')
          void applyPack('1-3s', 'sws')
        }, 2500)
      }
      return
    }
    if (scene === '1-3as') {
      if ((dlg.flags.sy1 ?? 0) < 30) playAvi('1-3as', true)
      // IsProp 118 + sy1≥20 → SetFlag sy1 30
      if (inv.qty(118) > 0 && (dlg.flags.sy1 ?? 0) >= 20)
        dlg.flags.sy1 = Math.max(dlg.flags.sy1 ?? 0, 30)
      // RemItem / SetFlagTable / AddFellow from 1-3as.txt
      if ((dlg.flags.sy1 ?? 0) >= 99) dlg.onRem?.('sws', 'rem')
      if ((dlg.flags.sy1 ?? 0) >= 20) dlg.onRem?.('sws', 'rem')
      if ((dlg.flags.sy1 ?? 0) >= 19 && (dlg.flags.sy1 ?? 0) < 30) {
        dlg.onRem?.('sws', 'reset')
        dlg.onRem?.('sws', 'table', 111, 0)
        dlg.onFellow?.('sws', true)
      }
      if ((dlg.flags.sy1 ?? 0) >= 29) dlg.onRem?.('bossyuheng', 'rem')
      if ((dlg.flags.sy1 ?? 0) < 30 && inv.qty(118) <= 0)
        inv.flash('洞中有妖气——玉衡看守着玉净甘露（E 对话开战）')
    }
    if (scene === '1-2s') {
      if ((dlg.flags.sy1 ?? 0) < 10) playAvi('1-2s', true)
      // cjg quest: SetPropToObj bossyezhu when cjg1∈[0,10); RemItem when cjg1≥1 after clear
      if ((dlg.flags.cjg1 ?? 0) >= 1) dlg.onRem?.('bossyezhu', 'rem')
      if ((dlg.flags.cjg1 ?? 0) >= 1 && (dlg.flags.cjg1 ?? 0) < 10 && inv.qty(54) <= 0)
        inv.flash('魔豕兽就在附近（E 对话开战，取心脏交翠娟）')
      if (inv.qty(54) > 0 && (dlg.flags.cjg1 ?? 0) < 10)
        dlg.flags.cjg1 = Math.max(dlg.flags.cjg1 ?? 0, 10)
    }
    if (scene === '1-10a6s') {
      if ((dlg.flags.bq2 ?? 0) < 50) playAvi('1-10a6s', true)
      // RemItem bosses when not yet on quest / after clear
      if ((dlg.flags.bq2 ?? 0) < 10) { dlg.onRem?.('boss', 'rem'); dlg.onRem?.('bosstianji', 'rem') }
      if ((dlg.flags.bq2 ?? 0) >= 50) { dlg.onRem?.('boss', 'rem'); dlg.onRem?.('bosstianji', 'rem') }
      else if ((dlg.flags.bq2 ?? 0) >= 10) {
        // ensure dual bosses fightable — combat via E talk (jump 4) or auto-spawn if missing
        if (!foes.some((f) => f.event === 'bosstianji' || f.name === '天机')) {
          // fall through — talk starts combat
        }
      }
      if ((dlg.flags.bq2 ?? 0) >= 10 && (dlg.flags.bq2 ?? 0) < 50 && inv.qty(124) <= 0)
        inv.flash('双天机在此（需气凝珠在身；E 对话开战）')
      if ((dlg.flags.bq2 ?? 0) < 10 && inv.qty(124) > 0) dlg.flags.bq2 = Math.max(dlg.flags.bq2 ?? 0, 10)
    }
    if (scene === '1-4s') {
      if ((dlg.flags.bq1 ?? 0) < 10) inv.flash('（玲珑心线：先与沈万山/泊祁对话至 bq1≥10）')
    }
    if (scene === '1-5s') {
      // SetPropToObj bjsm when xbjsm<1
      if ((dlg.flags.xbjsm ?? 0) < 1 && inv.qty(122) <= 0)
        inv.flash('附近有冰晶石木可采（触发器 bjsm，按 E）')
    }
    if (scene === '1-7s') {
      if ((dlg.flags.bq1 ?? 0) >= 30 && (dlg.flags.bq1 ?? 0) < 50)
        dlg.lockText['jiutianchi'] = 208
      if ((dlg.flags.bq1 ?? 0) >= 50)
        dlg.lockText['jiutianchi'] = -1
      if ((dlg.flags.xqnxbz ?? 0) < 1 && inv.qty(123) <= 0)
        inv.flash('附近有千年玄冰柱（qnxbz，按 E）')
    }
    if (scene === '1-8s') {
      if ((dlg.flags.bq1 ?? 0) >= 30 && (dlg.flags.bq1 ?? 0) < 40 && inv.qty(121) <= 0)
        inv.flash('九天池有天芝血参（tzxs，按 E）')
      if (inv.qty(121) > 0 && (dlg.flags.bq1 ?? 0) < 40)
        dlg.flags.bq1 = Math.max(dlg.flags.bq1 ?? 0, 40)
    }
    if (scene === '1-9s') {
      if ((dlg.flags.zhs1 ?? 0) >= 1) { dlg.onRem?.('zs', 'rem'); dlg.onRem?.('bossdaxiang', 'rem') }
      if ((dlg.flags.zhs1 ?? 0) >= 100) dlg.onRem?.('zs', 'rem')
      if ((dlg.flags.zhs1 ?? 0) < 10)
        inv.flash('炎炀关 — 战象拦路（E 对话开战）')
      // standability: ensure walkable cells around boss NPC
      const bo = objects.find((x) => String(x.EventID).toLowerCase() === 'bossdaxiang')
      if (bo && walkGrid) {
        const bx = Math.round((bo.x ?? 0) - origin.x), by = Math.round((bo.y ?? 0) - origin.y)
        for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
          const gx = bx + dx + origin.x, gy = by + dy + origin.y
          const ly = gy, lx = gx
          if (ly >= 0 && ly < walkGrid.length && lx >= 0 && lx < (walkGrid[ly]?.length ?? 0)) {
            const row = walkGrid[ly].split(''); row[lx] = '1'; walkGrid[ly] = row.join('')
          }
          blocked.delete(`${bx + dx},${by + dy}`)
        }
        WG = { g: walkGrid, ox: origin.x, oy: origin.y }
      }
    }
    if (scene === '1-11s') {
      if ((dlg.flags.xqnz ?? 0) >= 1 || inv.qty(124) > 0) dlg.onRem?.('boss', 'rem')
      // reset jiguan open when xqnz==0 per script
      if ((dlg.flags.xqnz ?? 0) < 1) {
        if ((dlg.bldStatus.jiguan1 ?? 0) < 1) { /* default closed until E */ }
      }
      inv.flash('气凝洞 — 启动三处机关 jiguan1/2/3 可获气凝珠')
      if (inv.qty(124) > 0 && (dlg.flags.bq2 ?? 0) < 40)
        dlg.flags.bq2 = Math.max(dlg.flags.bq2 ?? 0, 40)
    }
    if (scene === '1-0s' || scene === 'ren') {
      // scene/1-0s.txt + talk/sy SetExitTextID: flag gates (force lock/unlock each enter)
      dlg.exitText['1-1s'] = (dlg.flags.sy1 ?? 0) < 1 ? 308 : -1
      dlg.exitText['1-4s'] = (dlg.flags.bq1 ?? 0) < 10 ? 303 : -1
      dlg.exitText['1-7as'] = (dlg.flags.bq1 ?? 0) < 30 ? 303 : -1
      dlg.exitText['1-9s'] = (dlg.flags.bq2 ?? 0) < 1 ? 303 : -1
    }
    if (scene === '2-0s') {
      // scene/2-0s.txt: ChangeAct 1; ShowActForeword 114 1447 1 once; SetFlagTable 2sws 111 1
      dlg.currentAct = 1
      dlg.onAct?.(1)
      if ((dlg.flags.act2 ?? 0) < 1) {
        dlg.flags.act2 = 1
        showActForeword(114, 1447, 1)
      }
      dlg.onRem?.('2sws', 'table', 111, 1)
      // exit locks from scene script
      if ((dlg.flags.sq1 ?? 0) < 1 && dlg.exitText['2-1s'] !== -1) dlg.exitText['2-1s'] = dlg.exitText['2-1s'] ?? 303
      if ((dlg.flags['2bq1'] ?? 0) < 1 && dlg.exitText['2-2s'] !== -1) dlg.exitText['2-2s'] = dlg.exitText['2-2s'] ?? 303
      if ((dlg.flags['2bq2'] ?? 0) < 1 && dlg.exitText['2-7s'] !== -1) dlg.exitText['2-7s'] = dlg.exitText['2-7s'] ?? 303
      inv.flash('芭蕉村 — 第二幕')
    }
    if (scene === '1-3s') {
      if ((dlg.flags.sy1 ?? 0) < 10) playAvi('1-3s', true)
      // fellow while escorting before sy1 30
      if ((dlg.flags.sy1 ?? 0) >= 19 && (dlg.flags.sy1 ?? 0) < 30)
        dlg.onFellow?.('sws', true)
    }
    if (scene === '1-0s' || scene === 'ren') {
      // scene/1-0s.txt RemItem / SetFlagTable visibility
      if ((dlg.flags.sy1 ?? 0) >= 100) dlg.onRem?.('sws', 'rem')
      else dlg.onRem?.('sws', 'table', 111, 1) // SetFlagTable sws 111 1 on enter
      if ((dlg.flags.bq1 ?? 0) >= 70) dlg.onRem?.('zhs', 'rem')
      if ((dlg.flags.cjg1 ?? 0) >= 100) dlg.onRem?.('zhs', 'rem')
      if ((dlg.flags.cds1 ?? 0) >= 100) dlg.onRem?.('td', 'rem')
      if ((dlg.flags.zhs1 ?? 0) >= 100) dlg.onRem?.('zs', 'rem')
    }
  }

  const SAVE_KEY = 'djfm_act1_v1'
  function quickSave() {
    const data = {
      v: 1,
      scene: curScene,
      pack: packId,
      pos: { x: pos.x, y: pos.y },
      origin,
      flags: { ...dlg.flags },
      exitText: { ...dlg.exitText },
      lockText: { ...dlg.lockText },
      bldStatus: { ...dlg.bldStatus },
      hidden: [...hiddenEvents],
      inv: { money: inv.money, items: inv.items.map((i) => ({ ...i })), weaponSlots: inv.weaponSlots, embedGems: inv.embedGems },
      stats: { ...stats },
      looted: [...lootedScenes],
      t: Date.now(),
    }
    try {
      localStorage.setItem(SAVE_KEY, JSON.stringify(data))
      inv.flash('速存 ✓（S）'); playSfx('ui')
    } catch { inv.flash('速存失败') }
  }
  async function quickLoad() {
    try {
      const raw = localStorage.getItem(SAVE_KEY)
      if (!raw) { inv.flash('没有存档'); return }
      const data = JSON.parse(raw) as {
        pack: string; scene: string; pos: { x: number; y: number }
        flags: Record<string, number>; exitText: Record<string, number>; lockText: Record<string, number>
        bldStatus: Record<string, number>; hidden: string[]
        inv: { money: number; items: { id: number; qty: number }[]; weaponSlots: number; embedGems?: number }
        stats: typeof stats; looted: string[]
      }
      Object.assign(dlg.flags, data.flags || {})
      Object.assign(dlg.exitText, data.exitText || {})
      Object.assign(dlg.lockText, data.lockText || {})
      Object.assign(dlg.bldStatus, data.bldStatus || {})
      hiddenEvents.clear(); for (const h of data.hidden || []) hiddenEvents.add(h)
      lootedScenes.clear(); for (const s of data.looted || []) lootedScenes.add(s)
      inv.money = data.inv?.money ?? inv.money
      inv.items = (data.inv?.items || []).map((i) => ({ ...i }))
      inv.weaponSlots = data.inv?.weaponSlots ?? inv.weaponSlots
      inv.embedGems = data.inv?.embedGems ?? inv.embedGems
      Object.assign(stats, data.stats || {})
      await applyPack(data.pack || packOf(data.scene), undefined)
      pos.x = data.pos?.x ?? pos.x; pos.y = data.pos?.y ?? pos.y
      spawnPos = { x: pos.x, y: pos.y }
      hud.pots = [...inv.potSlots()]
      inv.flash(`读档 ← ${data.scene}`); playSfx('ui'); renderInv()
    } catch (e) { inv.flash('读档失败'); console.warn(e) }
  }

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
    iceHazards = []
    {
      const scn = String(meta.scene ?? id).toLowerCase()
      if (scn === '1-8s') {
        const keep: typeof objects = []
        for (const o of objects) {
          if (Number(o.ModelID) === 220 || String((o as {name?: string}).name ?? '') === '天冰') {
            iceHazards.push({ x: (o.x ?? 0) - ((meta.chunk_origin?.[0] ?? 0)), y: (o.y ?? 0) - ((meta.chunk_origin?.[1] ?? 0)) })
          } else keep.push(o)
        }
        objects = keep
        if (iceHazards.length) inv.flash(`九天池寒冰 ×${iceHazards.length}（踩上受伤）`)
      }
    }
    atlases = meta.lazy?.atlases ?? []
    atlasImgs.clear()

    walkGrid = meta.walk_grid ?? null
    WG = walkGrid ? { g: walkGrid, ox: origin.x, oy: origin.y } : null
    blocked = new Set()
    for (const b of meta.blocked_sample ?? []) blocked.add(`${b[0]},${b[1]}`)
    for (let x = 0; x < mapW; x++) { blocked.add(`${x},0`); blocked.add(`${x},${mapH - 1}`) }
    for (let y = 0; y < mapH; y++) { blocked.add(`0,${y}`); blocked.add(`${mapW - 1},${y}`) }
    // Phase 31: punch holes at warp pads so exits are approachable
    for (const tr of ((meta as { triggers?: { x: number; y: number; script?: string }[] }).triggers ?? [])) {
      if (!/\bgo\s/i.test(tr.script ?? '')) continue
      const lx = Math.round(tr.x - origin.x), ly = Math.round(tr.y - origin.y)
      for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
        const x = lx + dx, y = ly + dy
        if (x >= 0 && y >= 0 && x < mapW && y < mapH) blocked.delete(`${x},${y}`)
      }
    }

    buildingImgs = new Map()
    npcImgs = new Map()
    await Promise.all([
      ...[...new Set(buildings.flatMap((b) => (b.parts ?? []).map((q) => q.file)))].map(async (f) => {
        try { buildingImgs.set(f, await loadImageHd(`${base}/props_hd/${f}`, `${base}/props/${f}`)) } catch { /* */ }
      }),
      ...[...new Set(objects.filter((n) => n.file).map((n) => n.file!))].map(async (f) => {
        try { npcImgs.set(f, await loadImage(`${base}/props/${f}`)) } catch { /* */ }
      }),
      ...objects.flatMap((n) => (n.npc_dirs ?? []).map(async (f, i) => {
        try { npcImgs.set(`${n.EventID}_${i}`, await loadImageHd(`${base}/npcs_hd/${f}`, `${base}/npcs/${f}`)) } catch { /* */ }
      })),
    ])
    ground = null
    groundMeta = meta.ground_full ?? null
    if (groundMeta?.file) {
      const gf = groundMeta.file
      const gfJpg = gf.replace(/\.png$/i, '.jpg')
      // Prefer JPEG ground_hd (Pages size), then PNG ground_hd, then SD
      try { ground = await loadImage(`${base}/ground_hd/${gfJpg}`) }
      catch {
        try { ground = await loadImageHd(`${base}/ground_hd/${gf}`, `${base}/${gf}`) }
        catch { ground = null }
      }
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
      .filter((g) => g.x < 4096 && g.y < 4096 && (/\bgo\s/i.test(g.script ?? '') || /^(shushui|bjsm|qnxbz|tzxs|tianshu\d*|jiguan\d*)/i.test((g.script ?? '').trim()) || (curScene === '1-11s' && !(g.script ?? '').trim()))).map((g) => ({ x: g.x, y: g.y, script: g.script! }))
    if (arriveFrom) {
      // real exit pairing: arrive next to this map's own 'go <previous scene>' trigger, stepped toward the map centre
      const back = curTriggers.filter((g) => { const p=g.script.trim().split(/\s+/); const i=p.findIndex(x=>x.toLowerCase()==='go'); return (i>=0?p[i+1]:p[1])?.toLowerCase()===arriveFrom })
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
    // Act-1 town: north gate locked until 沈云 (sy1≥1 / exitText -1). Re-sync on every load.
    if (curScene === '1-0s') {
      dlg.exitText['1-1s'] = (dlg.flags.sy1 ?? 0) < 1 ? 308 : -1
      dlg.exitText['1-4s'] = (dlg.flags.bq1 ?? 0) < 10 ? 303 : -1
      dlg.exitText['1-7as'] = (dlg.flags.bq1 ?? 0) < 30 ? 303 : -1
      dlg.exitText['1-9s'] = (dlg.flags.bq2 ?? 0) < 1 ? 303 : -1
    }
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
    for (const [sid, acts] of Object.entries(monSets)) for (const a of Object.values(acts)) for (const f of ((a as { frames?: unknown[] })?.frames ?? []) as ([string, number, number] | null)[]) {
      if (f && !monImgs.has(f[0])) { const k = f[0]; loadImageHd(`${base}/mon_hd/${k}`, `${base}/mon/${k}`).then((im) => monImgs.set(k, im)).catch(() => {}) ; void sid }
    }
    {
      let mons = [...(meta.monsters ?? [])]
      // Remake tuning: thin late-map trash (not from data tables)
      const cap = Math.max(4, Number(REMAKE.max_trash) || 12)
      if (REMAKE.trash_scenes.includes(curScene) && mons.length > cap) {
        const keep: typeof mons = []
        const trash: typeof mons = []
        for (const mo of mons) {
          const nm = mo.name || ''
          const ev = String((mo as { event?: string }).event || '').toLowerCase()
          const isBoss = (ev && ev !== 'auto') || /boss|天机|战象|玉衡/i.test(nm)
          if (isBoss) keep.push(mo)
          else trash.push(mo)
        }
        const slots = Math.max(0, cap - keep.length)
        const step = Math.max(1, Math.ceil(trash.length / Math.max(1, slots)))
        mons = [...keep, ...trash.filter((_, i) => i % step === 0).slice(0, slots)]
        console.info(`[djfm] remake trash thin ${curScene}: ${meta.monsters?.length}→${mons.length} (cap=${cap} step=${step})`)
      }
      for (const mo of mons) {
        const lx = mo.x - origin.x, ly = mo.y - origin.y
        const b = balanceFoe({ hp: mo.hp, at: mo.at, df: mo.df }, curScene)
        foes.push({ x: lx, y: ly, hx: lx, hy: ly, hp: b.hp, maxHp: b.hp, cd: 1, hitT: 0, dead: 0, at: b.at, df: b.df, exp: mo.exp, sight: Math.min(mo.sight ?? 7, REMAKE.sight_cap), spd: mo.spd, name: mo.name, set: mo.set, act: 'idle', actT: 0, dir: 0, event: (mo as {event?: string}).event })
      }
    }
    // Phase 25: scene loot from AddItem tables (scatter potions near spawn, once per scene visit)
    spawnSceneLoot(curScene)
    const nf = Number(qs.get('foe') ?? '0')
    for (let i = 0; i < nf; i++) {
      const a = (i / Math.max(1, nf)) * Math.PI * 2, fx = pos.x + Math.cos(a) * 4, fy = pos.y + Math.sin(a) * 4
      if (walkableNow(fx, fy, mapW, mapH, blocked)) foes.push({ x: fx, y: fy, hp: 60, maxHp: 60, cd: 1, hitT: 0, dead: 0 })
    }
    hint.textContent = packIndex?.begin_scn_mapping ?? mapLabel
    runSceneEnter(curScene)
  }

  await applyPack(packId)
  packsEl.addEventListener('click', (e) => {
    const t = e.target as HTMLElement
    if (t.tagName === 'BUTTON' && t.dataset.pack) applyPack(t.dataset.pack).catch(console.error)
  })

  // Phase 50: HD paper-doll (player_hd) with SD fallback; draw ~2× original size
  let playerHotspot = { x: 64, y: 100 }
  let playerCanvas = { w: 128, h: 128 }
  let playerHd = false
  try {
    const pm = await (await fetch('game/player_hd/meta.json')).json() as { hotspot?: number[]; canvas?: number[] }
    playerHotspot = { x: pm.hotspot?.[0] ?? 256, y: pm.hotspot?.[1] ?? 400 }
    playerCanvas = { w: pm.canvas?.[0] ?? 512, h: pm.canvas?.[1] ?? 512 }
    playerHd = true
  } catch {
    try {
      const pm = await (await fetch('game/player/meta.json')).json() as { hotspot?: number[]; canvas?: number[] }
      if (pm.hotspot) playerHotspot = { x: pm.hotspot[0], y: pm.hotspot[1] }
      if (pm.canvas) playerCanvas = { w: pm.canvas[0], h: pm.canvas[1] }
    } catch { /* */ }
  }
  const playerBase = playerHd ? 'game/player_hd' : 'game/player'
  const hdDisplayMul = playerHd ? 2 : 1
  const hdSrcScale = playerHd ? (playerCanvas.w / 128) : 1
  const playerDrawScale = hdDisplayMul / Math.max(1, hdSrcScale)
  const playerWalk: HTMLImageElement[][] = Array.from({ length: 8 }, () => [])
  const playerRun: HTMLImageElement[][] = Array.from({ length: 8 }, () => [])
  const playerIdle: HTMLImageElement[] = []
  const playerAttackSpr: HTMLImageElement[] = []
  // Phase41: ping-pong gait 0,1,2,3,2,1 (Spr code-6 / Wine half-cycle)
  const GAIT_PP = [0, 1, 2, 3, 2, 1]
  await Promise.all(Array.from({ length: 8 }, async (_, d) => {
    for (let f = 0; f < 4; f++) {
      try { playerWalk[d].push(await loadImageHd(`${playerBase}/walk/${d}_${f}.png`, `game/player/walk/${d}_${f}.png`)) } catch { /* */ }
      try { playerRun[d].push(await loadImageHd(`${playerBase}/run/${d}_${f}.png`, `game/player/run/${d}_${f}.png`)) } catch { /* */ }
    }
    try { playerIdle[d] = await loadImageHd(`${playerBase}/idle/${d}_0.png`, `game/player/idle/${d}_0.png`) } catch { /* */ }
    try { playerAttackSpr[d] = await loadImageHd(`${playerBase}/attack/${d}_0.png`, `game/player/attack/${d}_0.png`) } catch { /* */ }
  }))
  let player: HTMLImageElement
  try { player = playerIdle[0] ?? await loadImage('game/player.png') } catch { player = await loadImage('game/player_fallback.png') }
  const walkFrames: HTMLImageElement[] = playerWalk.flat()

  const gridEl = document.querySelector<HTMLDivElement>('#grid')!
  for (const src of ['game/map/props/bld_225.png', 'game/map/props/npc_618.png', 'game/map/props/npc_661.png', 'game/map/chunks/c_32_32.png']) {
    const img = document.createElement('img'); img.src = src; img.style.width = '100%'; gridEl.append(img)
  }

  function doMelee() {
    if (dialogOpen || attackCd > 0) return
    // Phase 36: Wine-like melee — windup then hit (not instant arcade)
    attackT = 0.34
    attackPending = true
    skillFx = spawnFx('slash', facingWorldAng(facing), 0.34)
    playSfx('attack')
    playSfx('slash', { vol: 0.65 })
    attackCd = Math.max(0.52, (gameData?.attack?.cooldown_ms ?? 520) / 1000)
  }
  function doQSkill() {
    if (dialogOpen || attackCd > 0 || stats.mp < 10) return
    stats.mp -= 10; attackT = 0.4; attackCd = 0.8
    skillFx = spawnFx('q', 0)
    for (let a = 0; a < 8; a++) playerAttack(foes.filter((f) => f.hitT <= 0), pos, a * Math.PI / 4, stats, 2.5)
  }
  function doSkillLeft() {
    if (dialogOpen || attackCd > 0) return
    const sk = inv.skill('left')
    const cost = sk?.mp ?? 9
    if (stats.mp >= cost) {
      stats.mp -= cost; attackT = 0.45; attackCd = 0.9
      const mult = Math.abs(Number(sk?.at_mult ?? 1)) || 1
      const at0 = stats.at ?? 40; stats.at = at0 * (mult > 0 && mult < 5 ? Math.max(mult, 1) : 1.2)
      for (let a = 0; a < 8; a++) playerAttack(foes.filter((f) => f.hitT <= 0), pos, a * Math.PI / 4, stats, 2.2)
      stats.at = at0
      skillFx = spawnFx('saoye', 0)
      inv.flash(`${sk?.name ?? '扫叶'}！`)
    } else inv.flash('真气不足')
  }
  function doSkillRight() {
    if (dialogOpen || attackCd > 0) return
    const sk = inv.skill('right')
    const cost = sk?.mp ?? 18
    if (stats.mp >= cost) {
      stats.mp -= cost; attackT = 0.35; attackCd = 0.85
      const mult = Number(sk?.at_mult ?? 2) || 2
      const at0 = stats.at ?? 40; stats.at = at0 * mult
      { const fl = playerAttack(foes, pos, facingWorldAng(facing), stats, 3.2); floaters.push(...fl); if (fl.length) playSfx('hit2') }
      stats.at = at0
      skillFx = spawnFx('jidian', facingWorldAng(facing))
      inv.flash(`${sk?.name ?? '疾电'}！`)
    } else inv.flash('真气不足')
  }
  function doPotion(slot: number) {
    if (dialogOpen || inv.shopOpen || inv.embedOpen) return
    if (inv.usePotionSlot(slot, stats)) { playSfx('potion'); hud.pots = [...inv.potSlots()]; renderInv() }
  }

  const keys = new Set<string>()
  let facing = 0, animT = 0, moving = false, attackPending = false
  window.addEventListener('keydown', (e) => {
    const k = e.key.toLowerCase()
    keys.add(k)
    if (['arrowup','arrowdown','arrowleft','arrowright',' '].includes(k)) e.preventDefault()
    if (k === 'g') useGround = !useGround
    if (k === 'm') { muted = !muted; if (audio) audio.muted = muted; setSfxEnabled(!muted) }
    if (k === 's' && !dialogOpen && !inv.shopOpen) { quickSave(); return }
    if (k === 'l' && !dialogOpen) { void quickLoad(); return }
    if (k === 'escape') {
      // One overlay at a time: dialog, else the desk that is actually open.
      if (dlg.open || dialogOpen) {
        dialogOpen = false
        dlg.close()
        return
      }
      if (inv.shopOpen) { inv.shopOpen = false; renderInv(); return }
      if (inv.embedOpen) { inv.embedOpen = false; renderInv(); return }
      if (inv.open) { inv.open = false; renderInv(); return }
      return
    }
    if ((k === 'e' || k === 'enter') && dialogOpen) { advanceDialog(); e.preventDefault(); return }
    if (k === 'e' && !dialogOpen) {
      // nearest NPC
      let best: { d: number; o: MapObj } | null = null
      const range = gameData?.interact_range ?? 2
      for (const o of objects) {
      if (o.EventID && isHidden(String(o.EventID))) continue
        const ox = o.lx ?? (o.x != null ? o.x - origin.x : null)
        const oy = o.ly ?? (o.y != null ? o.y - origin.y : null)
        if (ox == null || oy == null) continue
        const d = Math.hypot(ox - pos.x, oy - pos.y)
        if (d <= range && (!best || d < best.d)) best = { d, o }
      }
      if (best?.o.EventID) { dlg.state = 0; dlg.start(String(best.o.EventID)); dialogOpen = dlg.open; renderDialog() }
      else if (tryPickProp()) { /* quest prop / jiguan / ground loot */ }
    }
    if (k === ' ' && !dialogOpen) doMelee()
    if (dlg.open && dlg.choices.length && ['1','2','3','4','5','6','7','8','9'].includes(k)) {
      dlg.pick(Number(k) - 1); dialogOpen = dlg.open; renderDialog(); return
    }
    // Inventory toggle
    // Phase 40: Wine-style B bag + I (same toggle)
    if ((k === 'i' || k === 'b') && !dialogOpen) {
      // I/B is 行囊. If the blacksmith desk is up, dismiss it and show the bag.
      if (inv.shopOpen || inv.embedOpen) { inv.shopOpen = false; inv.embedOpen = false; inv.open = true }
      else inv.open = !inv.open
      playSfx('ui'); renderInv(); return
    }
    // Potions from Init stacks: key1 = 小血瓶, key3 = 小气瓶 (slots 0 & 2)
    if (['1', '2', '3', '4'].includes(k) && !dialogOpen && !inv.shopOpen && !inv.embedOpen) {
      doPotion(Number(k) - 1)
    }
    // 5 = 飞蝗石 throw, 6 = 指南珠 return spawn
    if (k === '5' && !dialogOpen) {
      if (inv.throwStone()) {
        const ang = facingWorldAng(facing)
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
    if (k === 'f1') doSkillLeft()
    if (k === 'f2') doSkillRight()
    if (k === 'f9') {
      dlg.unlockNorthGate()
      // reopen gate cells immediately
      if (walkGrid) {
        for (const [gx, gy] of [[70,24],[71,24],[72,24]] as [number,number][]) {
          if (gy < walkGrid.length) { const row = walkGrid[gy].split(''); row[gx] = '1'; walkGrid[gy] = row.join('') }
        }
        WG = { g: walkGrid, ox: origin.x, oy: origin.y }
      }
      // Shift+F9: grant 蜀水 for blacksmith chain testing (real pickup is shushui on 1-6s)
      if (e.shiftKey && e.altKey) {
        // DEBUG only: jump to pre-蜀水 hand-in state (bq sets sy1=100 in real scripts)
        dlg.flags.sy1 = Math.max(dlg.flags.sy1 ?? 0, 100)
        inv.add(120, 1); dlg.flags.xss = 1
        inv.flash('DEBUG: sy1=100 + 蜀水 — 可与铁匠交蜀水')
        hint.textContent = 'DEBUG: 蜀水手交条件已满足（正式链：沈云→sws→玉衡→泊祁）'
      } else if (e.shiftKey) {
        inv.add(120, 1); dlg.flags.xss = 1; inv.flash('DEBUG: 获得蜀水')
        hint.textContent = 'DEBUG: 蜀水×1 — Alt+Shift+F9 亦置 sy1=100'
      } else {
        hint.textContent = 'DEBUG: 北门已开 (sy1=1) — Shift+F9 蜀水 / Alt+Shift+F9 手交就绪'
      }
    }
    if (k === 'q') doQSkill()
  })
  window.addEventListener('keyup', (e) => keys.delete(e.key.toLowerCase()))

  function iso(x: number, y: number): Vec {
    return { x: (x - y) * (tileW / 2), y: (x + y) * (tileH / 2) }
  }
  /** World cell atan2 for attack cones — inverse of facing=(screenOct+6)%8 */
  function facingWorldAng(f: number): number {
    const o = (f + 2) % 8
    const sx = Math.cos(o * Math.PI / 4), sy = Math.sin(o * Math.PI / 4)
    return Math.atan2((sy - sx) / 2, (sx + sy) / 2)
  }
  function drawNameplate(ctx: CanvasRenderingContext2D, label: string, sx: number, sy: number, kind: 'npc' | 'mon' = 'npc') {
    if (!label) return
    ctx.save()
    ctx.font = '11px "Microsoft YaHei","PingFang SC",ui-sans-serif,system-ui'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'bottom'
    ctx.lineWidth = 3
    ctx.strokeStyle = 'rgba(0,0,0,0.8)'
    ctx.strokeText(label, sx, sy)
    ctx.fillStyle = kind === 'mon' ? '#ffb0a0' : '#ffe9a0'
    ctx.fillText(label, sx, sy)
    ctx.restore()
  }
  function walkable(x: number, y: number): boolean {
    return walkableNow(x, y, mapW, mapH, blocked)
  }
  function inView(sx: number, sy: number, margin = 160): boolean {
    return sx > -margin && sy > -margin && sx < canvas.width + margin && sy < canvas.height + margin
  }

  let last = performance.now()
  function frame(now: number) {
    let dt = Math.min(0.05, (now - last) / 1000)
    if (hitStop > 0) { hitStop = Math.max(0, hitStop - dt); dt *= 0.12 }
    last = now
    if (attackCd > 0) attackCd -= dt
    if (attackT > 0) attackT -= dt
    // Hit lands ~mid swing (Wine: contact on attack frame, not keydown)
    if (attackPending && attackT > 0 && attackT <= 0.20) {
      attackPending = false
      const before = foes.filter((f) => f.dead <= 0 && !f.gone)
      const range = gameData?.attack?.range ?? 1.55
      const fl = playerAttack(foes, pos, facingWorldAng(facing), stats, range)
      floaters.push(...fl)
      if (fl.length) { playSfx('hit'); hitStop = Math.max(hitStop, 0.055) }
      else playSfx('slash', { vol: 0.25 })
      for (const f of before) if (f.dead > 0) onFoeKilled(f)
    }
    if (attackT <= 0) attackPending = false
    skillFx = tickFx(skillFx, dt)
    if (playerHurtFlash > 0) playerHurtFlash -= dt
    for (const fl of floaters) fl.t -= dt
    floaters = floaters.filter((fl) => fl.t > 0)
    inv.tick(dt); renderToast()

    let dx = 0, dy = 0
    if (dying > 0) { /* freeze controls while downed */ }
    else if (!dialogOpen) {
      if (keys.has('w') || keys.has('arrowup')) { dx -= 1; dy -= 1 }
      if (keys.has('s') || keys.has('arrowdown')) { dx += 1; dy += 1 }
      if (keys.has('a') || keys.has('arrowleft')) { dx -= 1; dy += 1 }
      if (keys.has('d') || keys.has('arrowright')) { dx += 1; dy -= 1 }
    }
    const len = Math.hypot(dx, dy) || 1
    moving = dx !== 0 || dy !== 0
    if (moving) {
      // Screen-space 8-dir: atan2(sdy,sdx) oct 0=screen-E … 2=S … 4=W … 6=N
      // Art dirs: S=0 SW=1 W=2 NW=3 N=4 NE=5 E=6 SE=7. facing=(oct+6)%8 → E→6…SE→7.
      // Phase39: RH_002 at (body+3)%8 fixes saber; keep P34 facing (D→art6 east profile).
      const sdx = dx - dy, sdy = dx + dy
      const oct = ((Math.round(Math.atan2(sdy, sdx) / (Math.PI / 4)) % 8) + 8) % 8
      facing = (oct + 6) % 8
    }
    const running = keys.has('shift') && (dx !== 0 || dy !== 0) && (stats.sp ?? 1) > 0.02
    const stamUse = (INIT.stamina_use ?? 10) / Math.max(1, INIT.stamina ?? 80)
    const stamRegen = (INIT.stamina_regen ?? 3) / Math.max(1, INIT.stamina ?? 80)
    stats.sp = Math.max(0, Math.min(1, (stats.sp ?? 1) + (running ? -stamUse : stamRegen) * dt))
    const ox0 = pos.x, oy0 = pos.y
    // Phase41: Wine run ~1.45× walk; keep stride locked to displacement
    const speed = running ? 6.5 : 4.5
    const nx = pos.x + (dx / len) * speed * dt
    const ny = pos.y + (dy / len) * speed * dt
    if (walkable(nx, pos.y)) pos.x = nx
    if (walkable(pos.x, ny)) pos.y = ny
    pos.x = Math.max(0, Math.min(mapW - 1, pos.x))
    pos.y = Math.max(0, Math.min(mapH - 1, pos.y))
    // Phase 32: stride from actual displacement (Wine: feet only advance when body moves)
    const moved = Math.hypot(pos.x - ox0, pos.y - oy0)
    if (moved > 1e-5) {
      const prev = animT
      // Phase42: Wine hold GIFs — walk ~2.0 (weightier), run ~1.65 (longer stride per cycle)
      animT += moved * (running ? 1.65 : 2.0)
      if (Math.floor(animT) !== Math.floor(prev)) playSfx('step', { vol: 0.28, minGap: 200 })
    }

    // AddFellow companion follows player (TransToPlayer approx)
    if (fellow) {
      const dx = pos.x - fellow.x, dy = pos.y - fellow.y, d = Math.hypot(dx, dy)
      if (d > 1.4) {
        const sp = 4.2 * dt
        fellow.x += (dx / d) * sp
        fellow.y += (dy / d) * sp
        fellow.dir = (Math.round(Math.atan2(dy, dx) / (Math.PI / 4)) + 8) % 8
      }
    }

    {
      const hp0 = stats.hp
      stepFoes(foes, pos, stats, dt, walkable)
      if (stats.hp < hp0 - 0.5) {
        playerHurtFlash = 0.35
        playSfx('hurt')
        floaters.push({ x: pos.x, y: pos.y, text: String(Math.round(hp0 - stats.hp)), t: 0.7, max: 0.7, color: '#ff6060' })
      }
    }
    for (const hz of iceHazards) {
      if (Math.hypot(hz.x - pos.x, hz.y - pos.y) < 0.85) {
        stats.hp -= 12 * dt
        if (!skillFx || skillFx.kind !== 'ice') skillFx = spawnFx('ice', 0, 0.35)
      }
    }
    // Boss death loot from scene scripts
    {
      const w = (window as unknown as { __djfmBoss?: string })
      if (w.__djfmBoss === 'bossyuheng') {
        const boss = foes.find((f) => f.name === '玉衡')
        if (boss && boss.dead > 0 && inv.qty(118) <= 0) {
          inv.add(118, 1)
          inv.flash('获得 玉净甘露 — 交予泊祁可救沈云（sy1→100）')
          if ((dlg.flags.sy1 ?? 0) >= 20) dlg.flags.sy1 = Math.max(dlg.flags.sy1 ?? 0, 30)
          w.__djfmBoss = undefined
        }
      } else if (w.__djfmBoss === 'bossyezhu') {
        const boss = foes.find((f) => f.name === '魔豕兽')
        if (boss && boss.dead > 0 && inv.qty(54) <= 0) {
          inv.add(54, 1)
          // scene/1-2s: IsProp 54 → SetFlag cjg1 10
          if ((dlg.flags.cjg1 ?? 0) < 10) dlg.flags.cjg1 = Math.max(dlg.flags.cjg1 ?? 0, 10)
          inv.flash('获得 魔豕兽心脏 — 交予翠娟（cjg1≥9）')
          w.__djfmBoss = undefined
        }
      }
    }
    ;(window as unknown as { __djfmDbg: unknown }).__djfmDbg = { applyPack, dlg, inv, stats, setFacing: (d: number) => { facing = ((d % 8) + 8) % 8 }, getFacing: () => facing, getAnim: () => ({ facing, animT, moving }), get foes() { return foes }, get objects() { return objects }, pos, origin: () => origin, scene: () => curScene, hidden: () => [...hiddenEvents], sync: () => { dialogOpen = dlg.open; renderDialog() }, talk: (e: string) => { dlg.state = 0; dlg.start(e); dialogOpen = dlg.open; renderDialog() }, pickProp: () => tryPickProp(), renderInv, openShop: () => { inv.shopOpen = true; inv.embedOpen = false; inv.shopMode = 'buy'; inv.open = false; playSfx('ui'); renderInv() }, openEmbed: () => { inv.embedOpen = true; inv.shopOpen = false; inv.open = false; playSfx('ui'); renderInv() }, groundLoot: () => groundLoot, iceHazards: () => iceHazards, remake: () => REMAKE, triggers: () => curTriggers, quickSave, quickLoad, killFlag: (ev: string) => {
      const match = (x: Foe) => !x.gone && (x.event === ev || x.name === ev || (ev === 'bossdaxiang' && x.name === '战象') || ((ev === 'bosstianji' || ev === 'boss') && x.name === '天机'))
      const f = foes.find(match)
      if (f) { f.hp = 0; f.dead = 0.05; onFoeKilled(f); f.gone = true }
    }, faceAttack: (ang?: number) => { const a = ang ?? (facingWorldAng(facing)); const before = foes.filter(f => f.dead <= 0 && !f.gone); floaters.push(...playerAttack(foes.filter(f => f.hitT <= 0), pos, a, stats)); for (const f of before) if (f.dead > 0) onFoeKilled(f) }, omniAttack: () => { /* debug only */ const before = foes.filter(f => f.dead <= 0 && !f.gone); for (let a = 0; a < 8; a++) floaters.push(...playerAttack(foes.filter(f => f.hitT <= 0), pos, a * Math.PI / 4, stats, 3.5)); for (const f of before) if (f.dead > 0) onFoeKilled(f) } }
    warpCd -= dt; (window as unknown as { __djfm: unknown }).__djfm = { scene: curScene, nt: curTriggers.length, cd: warpCd, near: Math.min(...curTriggers.map((g) => Math.hypot(g.x - origin.x - pos.x, g.y - origin.y - pos.y))), x: pos.x + origin.x, y: pos.y + origin.y, sy1: dlg.flags.sy1 ?? 0, exit11: dlg.exitText['1-1s'] ?? null }
    const nearT = curTriggers.some((g) => Math.hypot(g.x - origin.x - pos.x, g.y - origin.y - pos.y) < 4.5)
    if (!nearT) warpArmed = true
    if (warpCd <= 0 && warpArmed) for (const g of curTriggers) {
      if (Math.hypot(g.x - origin.x - pos.x, g.y - origin.y - pos.y) < 3.2) {
        const parts = g.script.trim().split(/\s+/)
        // 'go 1-8s' | 'jiutianchi go 1-8s' | 'bjsm  jsm'
        const gi = parts.findIndex((x) => x.toLowerCase() === 'go')
        const dest = (gi >= 0 ? parts[gi + 1] : parts[1])?.toLowerCase()
        const lockName = parts[0]?.toLowerCase()
        // Phase 25: SetLockTextID jiutianchi 208 while bq1∈[30,50)
        if (lockName && (dlg.lockText[lockName] ?? -1) >= 0) {
          const lid = dlg.lockText[lockName]
          dlg.npc = '出口'; dlg.lines = [dlg.text(lid).replace(/^\(对话 \d+\)$/, '') || '（此路未开——先完成泊祁的玲珑心指引。）']
          dlg.idx = 0; dlg.choices = []; dlg.open = true
          dialogOpen = true; renderDialog(); warpCd = 0.8; break
        }
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
    stats.hp = Math.min(stats.maxHp, stats.hp + dt * (INIT.hp_regen ?? 1.4))
    stats.mp = Math.min(stats.maxMp, stats.mp + dt * (INIT.mp_regen ?? 1.2))
    // Death / respawn (Phase 30): brief overlay then return to scene spawn
    if (dying > 0) {
      dying -= dt
      if (dying <= 0) {
        stats.hp = stats.maxHp; stats.mp = Math.max(stats.mp, stats.maxMp * 0.35)
        pos.x = spawnPos.x; pos.y = spawnPos.y
        inv.flash('重生于落脚处')
        playSfx('ui')
      }
    } else if (stats.hp <= 0) {
      dying = 1.6
      playSfx('death')
      inv.flash('你倒下了…')
      stats.hp = 0.01 // hold until overlay ends
    }
    // Phase 35: Wine-style locked camera — player fixed on screen, world scrolls.
    // Integer pixels only (no lerp / no subpixel) — kills ground wobble vs buildings.
    const focus = iso(pos.x, pos.y)
    cam.x = Math.round(canvas.width / 2 - focus.x)
    cam.y = Math.round(canvas.height / 2 - 36 - focus.y)

    ctx.fillStyle = '#0a1220'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.imageSmoothingEnabled = false

    if (useGround && ground && groundMeta) {
      const tw = groundMeta.tile_w, th = groundMeta.tile_h
      const wx = pos.x + origin.x, wy = pos.y + origin.y
      const gFocusX = (wx - wy) * (tw / 2) - groundMeta.min_sx
      const gFocusY = (wx + wy) * (th / 2) - groundMeta.min_sy
      // Same lock point as cam (-36), integer blit — must stay in sync with entity cam
      // HD ground may be 2× pixels; lock world scale to meta tile size
      // Prefer meta.pixel_size (SD native) so HD ×1 enhance or ×2 both scale correctly
      const ps = (groundMeta as { pixel_size?: number[]; px_w?: number }).pixel_size
      const nativeW = (ps && ps[0]) || (groundMeta as { px_w?: number }).px_w || 0
      const srcScale = nativeW > 0 ? ground.width / nativeW : 1
      const gs = (tileW / tw) / Math.max(1, srcScale)
      const gx = Math.round(canvas.width / 2 - gFocusX * (tileW / tw))
      const gy = Math.round(canvas.height / 2 - 36 - gFocusY * (tileW / tw))
      // blit using focus in SD ground space mapped to HD pixels
      ctx.imageSmoothingEnabled = true
      ctx.imageSmoothingQuality = 'high'
      ctx.globalAlpha = 0.92
      ctx.drawImage(ground, gx, gy, ground.width * gs, ground.height * gs)
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
        const _pw = q.w && q.w > 0 ? q.w : img.width
        const _ph = q.h && q.h > 0 ? q.h : img.height
        if (sx0 > canvas.width || sy0 > canvas.height || sx0 + _pw < 0 || sy0 + _ph < 0) continue
        // Phase 13: hotspot from BLD part (ox,oy); depth = anchor cell iso row
        // footprint rule: anchor = front corner of footprint; player is behind iff not past anchor on either axis
        const pz = pos.x + pos.y + 0.25
        const inFoot = pos.x <= lx + 0.5 && pos.y <= ly + 0.5 && pos.x > lx - (b.fw ?? 1) - 0.5 && pos.y > ly - (b.fh ?? 1) - 0.5
        const past = pos.x > lx + 0.5 || pos.y > ly + 0.5
        let z = lx + ly + 0.2
        if (inFoot) z = Math.max(z, pz + 0.01)       // player under/behind this building's footprint → building on top
        else if (past) z = Math.min(z, pz - 0.01)    // player past the front corner → player on top
                draws.push({ z, fn: () => {
          // props_hd may be 2×; scale to original part size
          const pw = q.w && q.w > 0 ? q.w : img.width
          const ph = q.h && q.h > 0 ? q.h : img.height
          const sc = img.width / pw
          const disp = sc >= 1.5 ? 1 : 1 // keep 1× world size (sharp HD downscale)
          ctx.imageSmoothingEnabled = true
          ctx.drawImage(img, sx0, sy0, pw * disp, ph * disp)
        } })
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
            // HD NPC sheets ×4 → draw ~2× original logical size (sharp, not screen-filling)
            const baseW = o.sw && o.sw > 0 ? o.sw : img.width
            const baseH = o.sh && o.sh > 0 ? o.sh : img.height
            const sc = img.width / baseW
            const disp = sc >= 2 ? 2 : 1
            const hotY = (o.oy != null && o.oy > 0 ? o.oy : baseH - 8) * disp
            const hotX = (o.ox != null && o.ox > 0 ? o.ox : baseW / 2) * disp
            ctx.imageSmoothingEnabled = true
            ctx.drawImage(img, sx - hotX, sy - hotY, baseW * disp, baseH * disp)
          }

          else { ctx.fillStyle = '#ffd24a'; ctx.beginPath(); ctx.arc(sx, sy, 5, 0, Math.PI * 2); ctx.fill() }
          // NPC nameplate (Wine-like): Role/ONT name above head; skip Autos / empty
          const eid = o.EventID != null ? String(o.EventID) : ''
          const rawName = (o as { name?: string }).name || (eid ? (dlg.names[eid] ?? '') : '')
          const skip = !rawName || /^auto$/i.test(eid) || rawName === '天冰' || Number(o.ModelID) === 220
          if (!skip) {
            const baseH2 = o.sh && o.sh > 0 ? o.sh : (img?.height ?? 24)
            const sc2 = img && o.sh && o.sh > 0 ? img.height / o.sh : 1
            const disp2 = sc2 >= 2 ? 2 : sc2
            const top = img ? (sy - (o.oy != null && o.oy > 0 ? o.oy * disp2 : baseH2 * disp2 - 8) - 4) : sy - 18
            drawNameplate(ctx, rawName, sx, top, 'npc')
          }
        },
      })
    }

    if (fellow && fellow.imgs.length) {
      const fp = iso(fellow.x, fellow.y)
      const fim = fellow.imgs[((fellow.dir % 8) + 8) % 8] ?? fellow.imgs[0]
      if (fim) draws.push({ z: fellow.x + fellow.y + 0.2, fn: () => {
        ctx.drawImage(fim, fp.x + cam.x - fim.width / 2, fp.y + cam.y - fim.height + 10)
        ctx.fillStyle = '#9fdf9f'; ctx.font = '10px ui-sans-serif'
        ctx.fillText(dlg.names[fellow!.id] ?? fellow!.id, fp.x + cam.x + 6, fp.y + cam.y - fim.height)
      }})
    }
    let spr = player
    {
      const d = ((facing % 8) + 8) % 8
      // Phase 27: attack frame sync — windup (walk), hit (attack), recover (idle)
      if (attackT > 0) {
        const u = attackT / 0.34
        // windup → strike pose → recover
        if (u > 0.72 && playerWalk[d]?.[0]) spr = playerWalk[d][0]
        else if (u > 0.22 && playerAttackSpr[d]) spr = playerAttackSpr[d]
        else if (playerIdle[d]) spr = playerIdle[d]
        else if (playerWalk[d]?.[1]) spr = playerWalk[d][1]
      }
      else if (moving) {
        // Phase41: ping-pong 0,1,2,3,2,1; run uses dedicated Spr loco group atlas
        const sheet = (running && playerRun[d]?.length) ? playerRun[d] : playerWalk[d]
        if (sheet?.length) {
          const n = sheet.length
          let fi: number
          if (n === 4) {
            fi = GAIT_PP[((Math.floor(animT) % 6) + 6) % 6]
          } else {
            fi = ((Math.floor(animT) % n) + n) % n
          }
          spr = sheet[fi]
        } else if (playerIdle[d]) spr = playerIdle[d]
      } else if (playerIdle[d]) spr = playerIdle[d]
    }
    const pp = iso(pos.x, pos.y)
    draws.push({
      z: pos.x + pos.y + 0.25,
      fn: () => {
        // foot hotspot: meta in canvas space (SD 128 or HD 512); draw ~2× original when HD
        const hx = playerHotspot.x * (spr.width / playerCanvas.w) * playerDrawScale
        const hy = playerHotspot.y * (spr.height / playerCanvas.h) * playerDrawScale
        const dw = spr.width * playerDrawScale, dh = spr.height * playerDrawScale
        ctx.imageSmoothingEnabled = true
        ctx.imageSmoothingQuality = 'high'
        ctx.drawImage(spr, Math.round(pp.x + cam.x - hx), Math.round(pp.y + cam.y - hy), dw, dh)
        if (skillFx) drawFx(ctx, skillFx, pp.x + cam.x, pp.y + cam.y)
        else if (attackT > 0) {
          const ang = facingWorldAng(facing)
          // Phase 40: punchier Wine-like slash wedge
          const a = Math.min(1, attackT * 4)
          ctx.strokeStyle = `rgba(255,230,140,${a})`
          ctx.lineWidth = 4
          ctx.beginPath()
          ctx.arc(pp.x + cam.x, pp.y + cam.y - 12, 30, ang - 0.85, ang + 0.85)
          ctx.stroke()
          ctx.strokeStyle = `rgba(255,180,60,${a * 0.45})`
          ctx.lineWidth = 8
          ctx.beginPath()
          ctx.arc(pp.x + cam.x, pp.y + cam.y - 12, 22, ang - 0.55, ang + 0.55)
          ctx.stroke()
        }
      },
    })
    for (const f of foes) {
      if (f.gone) continue
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
          if (f.hitT > 0) { ctx.filter = 'brightness(2.4) saturate(1.6)'; ctx.globalAlpha = 0.92 }
          {
            const mw = img.width, mh = img.height
            const msc = mw > 256 ? 0.5 : mw > 160 ? 0.75 : 1
            const dw = mw * msc, dh = mh * msc
            ctx.imageSmoothingEnabled = true
            ctx.drawImage(img, fx - dw / 2, fy - dh + 6, dw, dh)
          }
          ctx.filter = 'none'
        } else { ctx.fillStyle = '#7a2a2a'; ctx.beginPath(); ctx.ellipse(fx, fy - 18, 10, 18, 0, 0, Math.PI * 2); ctx.fill() }
        if (f.dead <= 0) {
          const top = fy - (img?.height ?? 40) - 6
          ctx.fillStyle = '#000'; ctx.fillRect(fx - 18, top, 36, 4)
          ctx.fillStyle = '#e33'; ctx.fillRect(fx - 18, top, 36 * Math.max(0, f.hp / f.maxHp), 4)
          if (f.name) drawNameplate(ctx, f.name, fx, top - 2, 'mon')
        }
      } })
    }
    for (const hz of iceHazards) {
      const p = iso(hz.x, hz.y)
      const x = p.x + cam.x, y = p.y + cam.y
      const fi = iceFrames.length
        ? (Math.floor(performance.now() / 280) + Math.floor(hz.x * 3 + hz.y * 5)) % iceFrames.length
        : 0
      const im = iceFrames[fi] || iceImg
      if (im) {
        ctx.save()
        ctx.globalAlpha = 0.88 + 0.1 * Math.sin(performance.now() / 400 + hz.x)
        // slight scale pulse so plate reads as live hazard (Map_Icecave art)
        const sc = 1.35
        ctx.drawImage(im, x - im.width * sc / 2, y - im.height * sc + 6, im.width * sc, im.height * sc)
        ctx.restore()
      } else {
        ctx.fillStyle = 'rgba(140,210,255,0.45)'; ctx.beginPath(); ctx.ellipse(x, y, 16, 9, 0, 0, Math.PI * 2); ctx.fill()
      }
    }
    // Phase 31: ground loot sparkles
    for (const g of groundLoot) {
      if (g.taken) continue
      const p = iso(g.x, g.y)
      draws.push({ z: g.x + g.y + 0.05, fn: () => {
        const x = p.x + cam.x, y = p.y + cam.y
        const pulse = 0.65 + 0.35 * Math.sin(performance.now() / 200)
        ctx.fillStyle = `rgba(255,210,120,${pulse})`
        ctx.beginPath(); ctx.arc(x, y - 10, 5, 0, Math.PI * 2); ctx.fill()
        ctx.strokeStyle = `rgba(255,255,200,${pulse})`; ctx.lineWidth = 1
        ctx.beginPath(); ctx.arc(x, y - 10, 8 + pulse * 2, 0, Math.PI * 2); ctx.stroke()
      }})
    }
    // Phase 32: sparse quest markers — hide after acquire; exits only when close
    {
      const pwx = pos.x + origin.x, pwy = pos.y + origin.y
      const seenGo = new Set<string>()
      for (const tr of curTriggers) {
        let key = (tr.script || '').trim().toLowerCase().split(/\s+/).filter(Boolean)[0] || ''
        if (!key && curScene === '1-11s' && Math.hypot(tr.x - 197, tr.y - 157) < 3) key = 'jiguan1'
        const prop = PROP_TRIG[key]
        const isJig = key.startsWith('jiguan')
        const isGo = /\bgo\s/i.test(tr.script || '')
        if (!prop && !isJig && !isGo) continue
        if (prop && ((dlg.flags[prop.flag] ?? 0) >= 1 || inv.qty(prop.id) > 0)) continue
        if (isJig && (dlg.bldStatus[key] ?? 0) >= 1) continue
        const dist = Math.hypot(tr.x - pwx, tr.y - pwy)
        // props/jiguan: within 16; exits: within 9, one marker per dest
        if (prop || isJig) { if (dist > 16) continue }
        else {
          if (dist > 9) continue
          const dest = (tr.script.match(/go\s+(\S+)/i)?.[1] || '').toLowerCase()
          if (!dest || seenGo.has(dest)) continue
          seenGo.add(dest)
        }
        const lx = tr.x - origin.x, ly = tr.y - origin.y
        const sp = iso(lx, ly)
        const goDest = tr.script.match(/go\s+(\S+)/i)?.[1]
        const locked = isGo && goDest ? dlg.exitLock(goDest) : 0
        const label = prop?.name || (isJig ? key : (locked ? `${goDest}·锁` : (goDest ?? '出口')))
        const rgb = prop ? '126,200,255' : isJig ? '255,176,96' : (locked ? '180,120,120' : '160,224,128')
        draws.push({ z: lx + ly + 0.08, fn: () => {
          const x = sp.x + cam.x, y = sp.y + cam.y
          const pulse = 0.5 + 0.4 * Math.sin(performance.now() / 280 + tr.x)
          ctx.fillStyle = `rgba(${rgb},${pulse * (locked ? 0.55 : 0.9)})`
          ctx.beginPath()
          ctx.moveTo(x, y - 20 - pulse * 3); ctx.lineTo(x + 5, y - 13); ctx.lineTo(x, y - 6); ctx.lineTo(x - 5, y - 13)
          ctx.closePath(); ctx.fill()
          drawNameplate(ctx, label, x, y - 26 - pulse * 2, 'npc')
        }})
      }
    }
    draws.sort((a, b) => a.z - b.z)
    for (const d of draws) d.fn()
    // Floating damage numbers
    for (const fl of floaters) {
      const fp = iso(fl.x, fl.y)
      const u = 1 - fl.t / fl.max
      const sx = fp.x + cam.x, sy = fp.y + cam.y - 36 - u * 28
      ctx.save()
      ctx.globalAlpha = Math.min(1, fl.t * 2)
      ctx.font = `bold ${fl.crit ? 16 : 13}px ui-sans-serif,system-ui`
      ctx.textAlign = 'center'
      ctx.lineWidth = 3
      ctx.strokeStyle = '#000'
      ctx.strokeText(fl.text, sx, sy)
      ctx.fillStyle = fl.color ?? (fl.crit ? '#ffe060' : '#fff0c0')
      ctx.fillText(fl.text, sx, sy)
      ctx.restore()
    }
    // Player hurt red flash
    if (playerHurtFlash > 0) {
      ctx.fillStyle = `rgba(180,0,0,${Math.min(0.35, playerHurtFlash)})`
      ctx.fillRect(0, 0, canvas.width, canvas.height)
    }

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

    if (cutscene) {
      cutscene.t -= dt
      const a = Math.min(1, cutscene.t)
      ctx.fillStyle = `rgba(0,0,0,${0.55 * a})`
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      const im = cutscene.img
      const sc = Math.min((canvas.width - 40) / im.width, (canvas.height - 80) / im.height, 1)
      const dw = im.width * sc, dh = im.height * sc
      ctx.globalAlpha = a
      ctx.drawImage(im, (canvas.width - dw) / 2, (canvas.height - dh) / 2 - 20, dw, dh)
      ctx.globalAlpha = 1
      if (cutscene.t <= 0) cutscene = null
    }
    if (dying > 0) {
      ctx.fillStyle = `rgba(0,0,0,${Math.min(0.75, 0.25 + (1.6 - dying) * 0.35)})`
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.fillStyle = '#ffb0a0'
      ctx.font = 'bold 28px "Microsoft YaHei",ui-sans-serif,system-ui'
      ctx.textAlign = 'center'
      ctx.fillText('阵亡', canvas.width / 2, canvas.height / 2 - 10)
      ctx.font = '14px ui-sans-serif,system-ui'
      ctx.fillStyle = '#c9a86a'
      ctx.fillText('正在返回落脚处…', canvas.width / 2, canvas.height / 2 + 22)
      ctx.textAlign = 'left'
    }
    hud.draw(ctx, stats, { skillL: inv.skill('left')?.name, skillR: inv.skill('right')?.name, money: inv.money, weapon: inv.weaponName(), potCd: inv.potCd, potCdMax: inv.potCdMax, attackCd, attackReady: attackCd <= 0 && attackT <= 0 })
    placeChrome()
    if (ground && groundMeta) {
      const tw = groundMeta.tile_w, th = groundMeta.tile_h
      const g = (x: number, y: number) => ({ x: (x + origin.x - y - origin.y) * (tw / 2) - groundMeta!.min_sx, y: (x + origin.x + y + origin.y) * (th / 2) - groundMeta!.min_sy })
      const me = g(pos.x, pos.y)
      const dots = [...foes.filter((f) => f.dead <= 0).map((f) => ({ ...g(f.x, f.y), c: '#ff3030' })), ...objects.map((o) => ({ ...g((o.x ?? 0) - origin.x, (o.y ?? 0) - origin.y), c: '#3a6cff' })), { ...me, c: '#30ff30' }]
      // Phase 30: consistent ground-pixel space (no /2 mismatch); scale by map size
      const mapSpan = Math.max(mapW, mapH, 64)
      const kMini = miniImg ? Math.min(0.55, 90 / (mapSpan * (tw / 2))) : Math.min(0.35, 70 / (mapSpan * (tw / 2)))
      hud.drawMinimap(ctx, miniImg ?? ground, me.x, me.y, kMini, dots, mapLabel.split(' ')[0])
    }
    ctx.fillStyle = '#9ecbff'
    ctx.font = '12px ui-sans-serif,system-ui'
    const wx = (pos.x + origin.x).toFixed(1), wy = (pos.y + origin.y).toFixed(1)
    const bgmState = muted ? 'BGM:mute' : 'BGM:on'
    ctx.fillText(
      `[${packId}] ${mapLabel} | (${wx},${wy}) ${bgmState} | WASD Shift跑 E谈 Space砍 I/B囊 S存 L读 M静音`,
      12, 20,
    )
    requestAnimationFrame(frame)
  }
  requestAnimationFrame(frame)
}

main().catch((e) => { document.body.textContent = String(e) })
