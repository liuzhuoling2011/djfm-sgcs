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
export function evalCond(cond: string, flags: Flags): boolean {
  if (!cond.trim()) return true
  return cond.split('*').every((c) => {
    const p = c.trim().split(/\s+/)
    if (p[0] !== 'IsFlag' || p.length < 3) return true // unknown predicates treated as true for now
    const name = p[1].toLowerCase(), v = Number(p[2]), op = p[3] !== undefined ? Number(p[3]) : 2
    const cur = flags[name] ?? 0
    return op === 1 ? cur < v : cur >= v
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
  lines: string[] = []
  idx = 0
  choices: { label: string; entry: TalkEntry }[] = []
  state = 0 // talk "当前号"
  onChange: () => void = () => {}

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
      if (p[0] === 'SetFlag' && p.length >= 3) this.flags[p[1].toLowerCase()] = Number(p[2])
      else if (p[0] === 'SetExitTextID' && p.length >= 3) this.exitText[p[1].toLowerCase()] = Number(p[2])
      // Acquire / Miss / go / ShowJM / ScreenEffect / Atb ignored for now
    }
  }

  /** Start talk with NPC EventID (e.g. 'sy'). Returns true if a conversation opened. */
  start(eventId: string): boolean {
    const key = eventId.toLowerCase()
    const entries = this.talks[key]
    if (!entries?.length) {
      this.npc = this.names[key] ?? eventId
      this.lines = [`（${this.npc}没有更多的话了。）`]
      this.idx = 0; this.choices = []; this.open = true; this.onChange(); return true
    }
    // Prefer auto entries whose condition matches, in order
    for (const e of entries) {
      if (e.auto && e.cur === this.state && evalCond(e.cond, this.flags)) {
        this.applyResult(e.result)
        if (e.jump_type === 1 && e.jump_data) {
          this.npc = this.names[key] ?? eventId
          this.lines = this.text(e.jump_data).split('\n').filter(Boolean)
          this.idx = 0; this.choices = []; this.open = true; this.onChange(); return true
        }
      }
    }
    // Menu: entries with jump_type 2 (choice root) or cur matching state with choice_text
    const menu = entries.filter((e) => !e.auto && e.cur === this.state && evalCond(e.cond, this.flags) && e.choice_text)
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
      const key = Object.keys(this.names).find((k) => this.names[k] === this.npc) ?? this.npc
      this.start(key); return
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

  close() { this.open = false; this.choices = []; this.lines = []; this.state = 0; this.onChange() }

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
