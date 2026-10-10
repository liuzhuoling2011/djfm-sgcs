// Phase 19c: inventory / equipment / potions from Init.txt + PropMdl.txt
export type InvItem = { id: number; qty: number }
export type PropDef = {
  id: number; name: string; type: string; value: string; func: string; desc: string
  heal_hp: string | number; heal_mp: string | number; icon: string
}
export type SkillDef = {
  id: number; name: string; mp: number; at_mult: string; range: string; intro: string
  hits?: string; combo?: string; level?: string
}
export type InitData = {
  money: number; items: InvItem[]; skill_left: number; skill_right: number
  equip: { body: number; head: number; weapon: number }; equip_parts: string
}

const load = async <T>(url: string, fallback: T): Promise<T> => {
  try { return await (await fetch(url)).json() as T } catch { return fallback }
}

export class Inventory {
  props: Record<string, PropDef> = {}
  skills: Record<string, SkillDef> = {}
  init: InitData = { money: 0, items: [], skill_left: 6, skill_right: 35, equip: { body: 11, head: 6, weapon: 0 }, equip_parts: '' }
  items: InvItem[] = []
  money = 0
  weaponSlots = 1 // AddWeaponNum from blacksmith
  open = false
  shopOpen = false // blacksmith 买卖
  embedOpen = false // 镶嵌 stub
  toast = ''
  toastT = 0
  potCd = 0  // shared potion cooldown (s)
  potCdMax = 1.1

  async load(base = 'game/data') {
    const [props, skills, init] = await Promise.all([
      load<Record<string, PropDef>>(`${base}/props.json`, {}),
      load<Record<string, SkillDef>>(`${base}/skills.json`, {}),
      load<InitData>(`${base}/init.json`, this.init),
    ])
    this.props = props; this.skills = skills; this.init = init
    this.money = init.money
    this.items = init.items.map((i) => ({ ...i }))
  }

  qty(id: number) { return this.items.find((i) => i.id === id)?.qty ?? 0 }

  add(id: number, n = 1) {
    const it = this.items.find((i) => i.id === id)
    if (it) it.qty += n
    else this.items.push({ id, qty: n })
  }

  miss(id: number, n = 1) {
    const it = this.items.find((i) => i.id === id)
    if (!it) return false
    it.qty -= n
    if (it.qty <= 0) this.items = this.items.filter((x) => x.id !== id)
    return true
  }

  /** Potion slot counts for HUD: [小血瓶, 0, 小气瓶, 0] matching Wine 1–4 keys (HP on 1, MP on 3). */
  potSlots(): [number, number, number, number] {
    return [this.qty(4), 0, this.qty(8), 0]
  }

  usePotionSlot(slot: number, stats: { hp: number; maxHp: number; mp: number; maxMp: number }) {
    const id = slot < 2 ? 4 : 8
    if (this.qty(id) <= 0) { this.flash('没有药剂'); return false }
    if (this.potCd > 0) { this.flash(`药剂冷却 ${this.potCd.toFixed(1)}s`); return false }
    const def = this.props[String(id)]
    this.miss(id, 1)
    if (id === 4) {
      const v = Number(def?.heal_hp || 400)
      stats.hp = Math.min(stats.maxHp, stats.hp + v)
    } else {
      const v = Number(def?.heal_mp || 18)
      stats.mp = Math.min(stats.maxMp, stats.mp + v)
    }
    this.potCd = this.potCdMax
    this.flash(`使用 ${def?.name ?? id}`)
    return true
  }

  /** 飞蝗石 — ranged chip damage */
  throwStone(): boolean {
    if (this.qty(63) <= 0) return false
    this.miss(63, 1)
    this.flash('掷出飞蝗石')
    return true
  }

  /** 指南珠 — return to town spawn */
  useCompass(): boolean {
    if (this.qty(62) <= 0) return false
    this.miss(62, 1)
    this.flash('指南珠：空间之门开启')
    return true
  }

  skill(which: 'left' | 'right') {
    const id = which === 'left' ? this.init.skill_left : this.init.skill_right
    return this.skills[String(id)]
  }

  weaponName() {
    // EquipStr901 id 0 = starter RH_002 — display as 初锻剑
    const names: Record<number, string> = { 0: '初锻剑', 1: '精锻剑', 2: '玄铁剑', 3: '疾风刃' }
    return names[this.init.equip.weapon] ?? `兵器#${this.init.equip.weapon}`
  }

  flash(msg: string) { this.toast = msg; this.toastT = 2.8 }

  tick(dt: number) { if (this.toastT > 0) this.toastT -= dt; if (this.potCd > 0) this.potCd = Math.max(0, this.potCd - dt) }

  /** Simple blacksmith shop: buy 小血瓶/小气瓶/飞蝗石 */
  shopCatalog() {
    return [
      { id: 4, price: 40 },
      { id: 8, price: 40 },
      { id: 63, price: 10 },
      { id: 5, price: 130 },
      { id: 9, price: 130 },
    ]
  }

  buy(id: number) {
    const row = this.shopCatalog().find((r) => r.id === id)
    if (!row || this.money < row.price) { this.flash('金钱不足'); return false }
    this.money -= row.price
    this.add(id, 1)
    this.flash(`购入 ${this.props[String(id)]?.name ?? id}`)
    return true
  }

  /** 镶嵌 stub: spend 蜀水 (120) already handled by dialog; here spend money to +AT */
  embedUpgrade(stats: { at?: number }) {
    if (this.money < 200) { this.flash('镶嵌需要 200 金钱'); return false }
    this.money -= 200
    stats.at = (stats.at ?? 40) + 2 * this.weaponSlots
    this.flash(`${this.weaponName()} 镶嵌强化 AT+${2 * this.weaponSlots}`)
    return true
  }
}
