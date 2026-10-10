import json, time, sys
from playwright.sync_api import sync_playwright
OUT='assets/samples/phase24/'; log=[]
def L(*a): s=' '.join(str(x) for x in a); print(s); log.append(s)
with sync_playwright() as pw:
    b=pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required']); pg=b.new_page(viewport={'width':1100,'height':760})
    errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/'); pg.wait_for_function('window.__djfmDbg', timeout=30000); time.sleep(2)
    E=lambda js: pg.evaluate(js)
    def shot(n): time.sleep(0.6); pg.screenshot(path=OUT+f'pt_{n}.png')
    def skipvid():
        if E("!!document.querySelector('.cutscene')"): L('  ▶ cutscene', E('window.__djfmAvi')); time.sleep(1.5); shot('avi_'+E('window.__djfmAvi')); pg.keyboard.press('Escape'); time.sleep(0.3); L('  skipped:', not E("!!document.querySelector('.cutscene')"))
    def go(s):
        E(f"window.__djfmDbg.applyPack('{s}')"); time.sleep(2.5); skipvid(); L(f'[{s}] scene={E("window.__djfmDbg.scene()")} npcs={E("window.__djfmDbg.objects.map(o=>o.EventID).join(\',\')")} foes={E("window.__djfmDbg.foes.length")} flags={json.dumps(E("window.__djfmDbg.dlg.flags"))}')
    def talk(e, picks=()):
        E(f"window.__djfmDbg.talk('{e}')"); pk=list(picks); lines=[]
        for _ in range(40):
            d=E("(()=>{const d=window.__djfmDbg.dlg;return {open:d.open,l:d.lines[d.idx],c:d.choices.map(c=>c.label)}})()")
            if not d['open']: break
            if d['c']:
                i=pk.pop(0) if pk else 0; lines.append(f"?{d['c']}->{i}"); E(f"window.__djfmDbg.dlg.pick({i})")
            else: lines.append(d['l']); E("window.__djfmDbg.dlg.advance()")
        E('window.__djfmDbg.sync()'); L(f'  talk {e}:', ' | '.join(str(x)[:40] for x in lines[:8]), '… flags', json.dumps(E("window.__djfmDbg.dlg.flags")))
    def fight(name=None, maxn=60):
        n=0
        for _ in range(400):
            alive=E(f"window.__djfmDbg.foes.filter(f=>f.dead<=0&&!f.gone{'&&f.name==='+json.dumps(name) if name else ''}).length")
            if not alive or n>=maxn: break
            E(f"(()=>{{const d=window.__djfmDbg,f=d.foes.find(f=>f.dead<=0&&!f.gone{'&&f.name==='+json.dumps(name) if name else ''});d.pos.x=f.x-0.6;d.pos.y=f.y;d.stats.hp=d.stats.maxHp;f.hp=Math.min(f.hp,30)}})()")
            pg.keyboard.press('Space'); time.sleep(0.25); n+=1
        L(f'  fight {name or "all"}: swings={n} left={E("window.__djfmDbg.foes.filter(f=>f.dead<=0&&!f.gone).length")} exp={E("window.__djfmDbg.stats.exp")}')
    go('ren'); shot('01_town'); talk('sy'); L('  exit 1-1s lock', E("window.__djfmDbg.dlg.exitText['1-1s']"))
    go('1-1s'); shot('02_1-1s')
    go('1-2s'); shot('03_1-2s')
    E("window.__djfmDbg.dlg.flags.cjg1=1"); talk('bossyezhu'); time.sleep(1); shot('04_mozhu_fight'); fight('魔豕兽'); time.sleep(1.5); L('  猪心54', E("window.__djfmDbg.inv.qty(54)")); shot('05_mozhu_dead')
    fight(maxn=30); shot('06_ghosts')
    go('ren'); talk('sws'); time.sleep(4); skipvid(); L('  after sws scene', E("window.__djfmDbg.scene()"), E("window.__djfmDbg.dlg.flags.sy1"))
    if E("window.__djfmDbg.scene()")!='1-3s': go('1-3s')
    shot('07_1-3s'); talk('sws')
    go('1-3as'); shot('08_1-3as'); talk('bossyuheng'); time.sleep(1); shot('09_yuheng'); fight('玉衡'); time.sleep(1.5); L('  118', E("window.__djfmDbg.inv.qty(118)"), 'sy1', E("window.__djfmDbg.dlg.flags.sy1"))
    go('1-3s'); talk('sws'); go('ren'); talk('sws'); talk('bq'); L('  sy1', E("window.__djfmDbg.dlg.flags.sy1"))
    go('1-6s'); E("window.__djfmDbg.inv.add(120,1)"); L('  (蜀水 pickup simulated via inv.add — proximity trigger)'); go('ren'); talk('tj'); talk('bq')
    for s in ['1-4s','1-5s','1-7s','1-8s']: go(s)
    shot('10_1-8s')
    go('1-9s'); shot('11_1-9s'); talk('bossdaxiang'); time.sleep(1); shot('12_daxiang'); fight('战象'); L('  zhs1', E("window.__djfmDbg.dlg.flags.zhs1"))
    go('1-10s'); shot('13_1-10s'); fight(maxn=25); shot('14_1-10s_fight')
    for s in ['1-10a1s','1-10a2s','1-10a3s','1-10a4s','1-10a5s']: go(s)
    go('1-10a6s'); shot('15_1-10a6s'); talk('bosstianji')
    go('1-11s'); shot('16_1-11s')
    L('page errors:', errs[:5]); b.close()
open(OUT+'playthrough_log.txt','w').write('\n'.join(log))
