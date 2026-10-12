// Phase 18: talk scripts (mb/trigger/talk) + Dialog_Public* lines.
export type TalkEntry = {
  id: number; cond: string; cur: number; choice_text: number
  jump_type: number; jump_data: number; result: string; auto: boolean
}
export type Flags = Record<string, number>

const load = async <T>(url: string, fallback: T): Promise<T> => {
  try { return await (await fetch(url)).json() as T } catch { return fallback }
}

/** IsFlag name value [op]; op 1 = flag < value (not yet), op 2 = flag >= value. Bare IsFlag name value = flag >= value. */
export type InvHook = { hasProp: (id: number) => boolean; acquire: (id: number, n: number) => void; miss: (id: number, n: number) => void; addWeaponNum: () => void; showShop: () => void; showEmbed: () => void }
export type GoHook = (scene: string) => void
export type CombatHook = (battleId: number, eventId: string) => void
export type FellowHook = (eventId: string, enable: boolean) => void
export type FxHook = (kind: string, arg?: string) => void
export type ActHook = (act: number) => void
export type ForewordHook = (textId: number, jmId: number, act: number) => void
export type RemHook = (eventId: string, mode: 'rem' | 'reset' | 'table', slot?: number, val?: number) => void
export type BldHook = (name: string, status: number) => void
export type LockHook = (name: string, textId: number) => void
export type DeadCheck = (eventId: string) => boolean

export function evalCond(cond: string, flags: Flags, inv?: InvHook): boolean {
  if (!cond.trim()) return true
  return cond.split('*').every((c) => {
    const p = c.trim().split(/\s+/)
    if (p[0] === 'IsFlag' && p.length >= 3) {
      const name = p[1].toLowerCase(), v = Number(p[2]), cur = flags[name] ?? 0
      if (p[3] === undefined) return cur === v // bare = equality (quest stage gates)
      const op = Number(p[3])
      return op === 1 ? cur < v : cur >= v
    }
    if (p[0] === 'IsProp' && p.length >= 2) {
      const has = inv?.hasProp(Number(p[1])) ?? false
      if (p.length >= 3 && Number(p[2]) === 0) return !has
      return has
    }
    if (p[0] === 'IsPropInBody' && p.length >= 2) {
      const has = inv?.hasProp(Number(p[1])) ?? false
      if (p.length >= 3 && Number(p[2]) === 0) return !has
      return has
    }
    if (p[0] === 'IsBldStatus' && p.length >= 3) {
      // evaluated in main via dlg.bldStatus; here read from a module-level bridge set on DialogSys
      return true // deferred — scene scripts not evalCond
    }
    if (p[0] === 'IsDead' && p.length >= 2) {
      return true // deferred to scene runner
    }
    return true // unknown predicates ignored
  })
}

export class DialogSys {
  dialogs: Record<string, Record<string, string>> = {}
  talks: Record<string, TalkEntry[]> = {}
  names: Record<string, string> = {}
  flags: Flags = {}
  exitText: Record<string, number> = {} // scene → dialog id; -1 = unlocked
  pack = 'public1'
  open = false
  npc = ''
  lastEventId = ''
  lines: string[] = []
  idx = 0
  choices: { label: string; entry: TalkEntry }[] = []
  state = 0 // talk "当前号"
  onChange: () => void = () => {}
  inv?: InvHook
  onGo?: GoHook
  onCombat?: CombatHook
  onFellow?: FellowHook
  onFx?: FxHook
  onAct?: ActHook
  onForeword?: ForewordHook
  currentAct = 0
  onRem?: RemHook
  onBld?: BldHook
  onLock?: LockHook
  isDead?: DeadCheck
  lockText: Record<string, number> = {}
  bldStatus: Record<string, number> = {}
  pendingGo: string | null = null

  async load(base = 'game/dialog') {
    ;[this.dialogs, this.talks, this.names] = await Promise.all([
      load(`${base}/dialogs.json`, {}),
      load(`${base}/talks.json`, {}),
      load(`${base}/npc_names.json`, {}),
    ])
  }

  text(id: number): string {
    return this.dialogs[this.pack]?.[String(id)] ?? this.dialogs.public1?.[String(id)] ?? `(对话 ${id})`
  }

  applyResult(result: string) {
    if (!result) return
    for (const cmd of result.split('*')) {
      const p = cmd.trim().split(/\s+/)
      if (!p[0]) continue
      const op = p[0].toLowerCase()
      if (op === 'setflag' && p.length >= 3) this.flags[p[1].toLowerCase()] = Number(p[2])
      else if (op === 'setexittextid' && p.length >= 3) this.exitText[p[1].toLowerCase()] = Number(p[2])
      else if (op === 'acquire' && p.length >= 2) this.inv?.acquire(Number(p[1]), Number(p[2] ?? 1))
      else if (op === 'miss' && p.length >= 2) this.inv?.miss(Number(p[1]), Number(p[2] ?? 1))
      else if (op === 'addweaponnum') this.inv?.addWeaponNum()
      else if (op === 'showjm') {
        // ShowJM 20|86 = shop, 20|62|92 = embed (from tj.txt)
        const arg = p.slice(1).join(' ')
        if (arg.includes('86')) this.inv?.showShop()
        else if (arg.includes('62')) this.inv?.showEmbed()
      } else if (op === 'go' && p.length >= 2) {
        // talk/sws.txt: go sws → scene warp (SWS.txt then sets sy1 19 → 1-3s)
        this.pendingGo = p[1].toLowerCase()
      } else if (op === 'addfellow' && p.length >= 3) {
        // AddFellow sws 1 | AddFellow sws 0
        this.onFellow?.(p[1].toLowerCase(), Number(p[2]) !== 0)
      } else if (op === 'screeneffect') {
        this.onFx?.('screen', p[1])
      } else if (op === 'playavi') {
        this.onFx?.('avi', p.slice(1).join(' '))
      } else if (op === 'settumble') {
        this.onFx?.('tumble')
      } else if (op === 'remitem' && p.length >= 2) {
        this.onRem?.(p[1].toLowerCase(), 'rem')
      } else if (op === 'resetobj' && p.length >= 2) {
        this.onRem?.(p[1].toLowerCase(), 'reset')
      } else if (op === 'setflagtable' && p.length >= 4) {
        // SetFlagTable sws 111 0|1 — slot 111 gates world visibility
        this.onRem?.(p[1].toLowerCase(), 'table', Number(p[2]), Number(p[3]))
      }
      else if (op === 'changeact' && p.length >= 2) {
        this.currentAct = Number(p[1]); this.onAct?.(this.currentAct)
      } else if (op === 'setbldani') {
        this.onFx?.('bldani', p.slice(1).join(' '))
      } else if (op === 'showactforeword' && p.length >= 2) {
        this.onForeword?.(Number(p[1]), Number(p[2] ?? 0), Number(p[3] ?? this.currentAct))
      }
      // Atb / TransToPlayer still stubbed
    }
  }

  /** Start talk with NPC EventID (e.g. 'sy'). Returns true if a conversation opened. */
  start(eventId: string): boolean {
    const key = eventId.toLowerCase()
    this.lastEventId = key
    const entries = this.talks[key]
    if (!entries?.length) {
      this.npc = this.names[key] ?? eventId
      this.lines = [`（${this.npc}没有更多的话了。）`]
      this.idx = 0; this.choices = []; this.open = true; this.onChange(); return true
    }
    // Prefer auto entries whose condition matches, in order
    for (const e of entries) {
      if (e.auto && e.cur === this.state && evalCond(e.cond, this.flags, this.inv)) {
        this.applyResult(e.result)
        if (e.jump_type === 1 && e.jump_data) {
          this.npc = this.names[key] ?? eventId
          this.lines = this.text(e.jump_data).split('\n').filter(Boolean)
          this.idx = 0; this.choices = []; this.open = true; this.onChange(); return true
        }
        if (e.jump_type === 4) {
          // battle / special: bossyuheng.txt jump_data 126
          this.npc = this.names[key] ?? eventId
          this.lines = [`（${this.npc}拦住了去路！）`]
          this.idx = 0; this.choices = []; this.open = true; this.onChange()
          this.onCombat?.(e.jump_data, key)
          return true
        }
      }
    }
    // Menu: entries with jump_type 2 (choice root) or cur matching state with choice_text
    const menu = entries.filter((e) => !e.auto && e.cur === this.state && evalCond(e.cond, this.flags, this.inv) && e.choice_text)
    if (menu.length) {
      this.npc = this.names[key] ?? eventId
      this.lines = []
      this.choices = menu.map((e) => ({ label: this.text(e.choice_text), entry: e }))
      this.idx = 0; this.open = true; this.onChange(); return true
    }
    this.npc = this.names[key] ?? eventId
    this.lines = [`（${this.npc}看着你，没有说话。）`]
    this.idx = 0; this.choices = []; this.open = true; this.onChange(); return true
  }

  pick(i: number) {
    const c = this.choices[i]; if (!c) return
    this.applyResult(c.entry.result)
    if (c.entry.jump_type === 0) { this.close(); return }
    if (c.entry.jump_type === 1 && c.entry.jump_data) {
      this.lines = this.text(c.entry.jump_data).split('\n').filter(Boolean)
      this.idx = 0; this.choices = []; this.onChange(); return
    }
    if (c.entry.jump_type === 2) {
      this.state = c.entry.jump_data
      // re-enter menu at new state — caller should start() again; do it here with same npc
      this.start(this.lastEventId || this.npc); return
    }
    if (c.entry.jump_type === 3) { this.close(); return }
    this.close()
  }

  advance() {
    if (!this.open) return
    if (this.choices.length) return // wait for pick
    this.idx++
    if (this.idx >= this.lines.length) this.close()
    else this.onChange()
  }

  close() {
    this.open = false; this.choices = []; this.lines = []; this.state = 0
    const go = this.pendingGo; this.pendingGo = null
    this.onChange()
    if (go) this.onGo?.(go)
  }

  /** Whether a go-exit to `dest` is locked. Returns lock dialog id or 0 if free. */
  exitLock(dest: string): number {
    const v = this.exitText[dest.toLowerCase()]
    if (v === undefined) return 0
    return v < 0 ? 0 : v
  }

  /** Debug / story: unlock the 瓦当镇 → 1-1s gate the way talking to 沈云 does. */
  unlockNorthGate() {
    this.flags.sy1 = Math.max(this.flags.sy1 ?? 0, 1)
    this.exitText['1-1s'] = -1
  }
}
