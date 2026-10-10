"""Phase 25: scripted act-1 playthrough past sy1=100 from real talk/scene flags."""
import json, time, os
from playwright.sync_api import sync_playwright
OUT = 'assets/samples/phase25/'
os.makedirs(OUT, exist_ok=True)
log = []
def L(*a):
    s = ' '.join(str(x) for x in a); print(s); log.append(s)

with sync_playwright() as pw:
    b = pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    pg = b.new_page(viewport={'width': 1100, 'height': 760})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/')
    pg.wait_for_function('window.__djfmDbg', timeout=30000); time.sleep(2)
    E = lambda js: pg.evaluate(js)
    def shot(n):
        time.sleep(0.4); pg.locator('canvas').first.screenshot(path=OUT + f'pt_{n}.png')
    def skipvid():
        if E("!!document.querySelector('.cutscene')"):
            L('  ▶', E('window.__djfmAvi')); time.sleep(0.6); pg.keyboard.press('Escape'); time.sleep(0.2)
    def go(s):
        E(f"window.__djfmDbg.applyPack('{s}')"); time.sleep(2.0); skipvid()
        L(f'[{s}] flags={json.dumps(E("window.__djfmDbg.dlg.flags"))} foes={E("window.__djfmDbg.foes.filter(f=>!f.gone&&f.dead<=0).length")} lock={json.dumps(E("window.__djfmDbg.dlg.lockText"))} bld={json.dumps(E("window.__djfmDbg.dlg.bldStatus"))}')
    def talk(e, picks=(), maxn=50):
        E(f"window.__djfmDbg.talk('{e}')"); pk = list(picks)
        for _ in range(maxn):
            d = E("(()=>{const d=window.__djfmDbg.dlg;return {open:d.open,l:d.lines[d.idx],c:d.choices.map(c=>c.label)}})()")
            if not d['open']: break
            if d['c']:
                i = pk.pop(0) if pk else 0
                E(f"window.__djfmDbg.dlg.pick({i})")
            else:
                E("window.__djfmDbg.dlg.advance()")
        E('window.__djfmDbg.sync()')
        L(f'  talk {e} → flags={json.dumps(E("window.__djfmDbg.dlg.flags"))}')
    def fight_all(maxn=80, boss_events=()):
        n = 0
        for _ in range(500):
            alive = E("window.__djfmDbg.foes.filter(f=>f.dead<=0&&!f.gone).length")
            if not alive or n >= maxn: break
            E("""(()=>{const d=window.__djfmDbg,f=d.foes.find(f=>f.dead<=0&&!f.gone);
              if(!f)return; f.x=d.pos.x+1.1; f.y=d.pos.y; f.hx=f.x; f.hy=f.y; f.hitT=0;
              d.stats.hp=d.stats.maxHp;})()""")
            E("window.__djfmDbg.omniAttack()"); time.sleep(0.35); n += 1
        for ev in boss_events:
            E(f"window.__djfmDbg.killFlag({ev!r})")
        L(f'  fight swings={n} left={E("window.__djfmDbg.foes.filter(f=>!f.gone&&f.dead<=0).length")} lv={E("window.__djfmDbg.stats.lvl")} at={E("window.__djfmDbg.stats.at")} flags={json.dumps({k:E(f"window.__djfmDbg.dlg.flags.{k}") for k in ("zhs1","bq2","bq1")})}')
    def pick():
        ok = E("window.__djfmDbg.pickProp()")
        L(f'  pickProp={ok} inv121={E("window.__djfmDbg.inv.qty(121)")} 122={E("window.__djfmDbg.inv.qty(122)")} 123={E("window.__djfmDbg.inv.qty(123)")} 124={E("window.__djfmDbg.inv.qty(124)")}')

    E("""(()=>{const d=window.__djfmDbg;
      d.dlg.flags={sy1:100,cjg1:100,bq:3,bq1:0,tj:1,tj1:100,xss:1};
      d.inv.add(120,1); d.stats.lvl=8; d.stats.at=40+4*7; d.stats.df=30+4*7;
      d.stats.maxHp=800+80*7; d.stats.hp=d.stats.maxHp; d.stats.exp=800;
    })()""")
    L('BOOT sy1=100 soft-lv8', E("window.__djfmDbg.dlg.flags"), E("window.__djfmDbg.stats"))

    go('ren'); shot('01_town_sy100')
    talk('bq'); talk('sws')
    L('  exit 1-4s', E("window.__djfmDbg.dlg.exitText['1-4s']"))

    go('1-4s'); shot('02_1-4s'); talk('sdyx')
    go('ren'); talk('bq')
    L('  bq1', E("window.__djfmDbg.dlg.flags.bq1"), 'exit 1-7as', E("window.__djfmDbg.dlg.exitText['1-7as']"))

    go('1-5s'); shot('03_1-5s')
    E("(()=>{const d=window.__djfmDbg; d.pos.x=185-d.origin().x; d.pos.y=154-d.origin().y;})()")
    time.sleep(0.3); pick(); shot('04_bjsm')

    go('1-7s'); shot('05_1-7s_locked')
    L('  jiutianchi lock', E("window.__djfmDbg.dlg.lockText.jiutianchi"))
    E("(()=>{const d=window.__djfmDbg; d.pos.x=139-d.origin().x; d.pos.y=63-d.origin().y;})()")
    time.sleep(0.3); pick()
    E("(()=>{const d=window.__djfmDbg; d.pos.x=59-d.origin().x; d.pos.y=68-d.origin().y;})()")
    time.sleep(1.2)
    L('  approach jiutianchi scene=', E("window.__djfmDbg.scene()"), 'dialog', E("window.__djfmDbg.dlg.open"))

    go('1-8s'); shot('06_1-8s')
    E("(()=>{const d=window.__djfmDbg; d.pos.x=110-d.origin().x; d.pos.y=68-d.origin().y;})()")
    time.sleep(0.3); pick(); L('  bq1 after tzxs', E("window.__djfmDbg.dlg.flags.bq1"))

    go('ren'); talk('bq')  # expect bq1=50
    L('  after hand 121: bq1', E("window.__djfmDbg.dlg.flags.bq1"))
    go('1-7s'); L('  jiutianchi unlock', E("window.__djfmDbg.dlg.lockText.jiutianchi"))

    talk('bq')  # bq1=60
    go('1-4s'); talk('sdyx')  # 玲珑心
    L('  玲珑心', E("window.__djfmDbg.inv.qty(119)"), 'bq1', E("window.__djfmDbg.dlg.flags.bq1"))
    shot('07_linglong')

    go('ren'); talk('sws'); talk('bq')  # bq2=1
    L('  bq2 start', E("window.__djfmDbg.dlg.flags"), 'exit 1-9s', E("window.__djfmDbg.dlg.exitText['1-9s']"))
    talk('zhs')

    go('1-9s'); shot('08_1-9s')
    talk('bossdaxiang'); time.sleep(0.8); shot('09_daxiang_fight')
    E("(()=>{const d=window.__djfmDbg;d.foes.forEach(f=>{if(f.event!=='bossdaxiang'&&f.name!=='战象')f.gone=true;});})()")
    fight_all(20, boss_events=('bossdaxiang',))
    L('  zhs1', E("window.__djfmDbg.dlg.flags.zhs1")); shot('10_daxiang_dead')

    go('ren'); talk('zs'); L('  zhs1 after zs', E("window.__djfmDbg.dlg.flags.zhs1"))

    go('1-11s'); shot('11_1-11s')
    for xy in [(197,157),(130,70),(186,160)]:
        E(f"(()=>{{const d=window.__djfmDbg; d.pos.x={xy[0]}-d.origin().x; d.pos.y={xy[1]}-d.origin().y;}})()")
        time.sleep(0.2); pick()
    L('  after jiguan', E("window.__djfmDbg.dlg.bldStatus"), '124', E("window.__djfmDbg.inv.qty(124)"), 'bq2', E("window.__djfmDbg.dlg.flags.bq2"))
    skipvid(); shot('12_qiningzhu')

    go('ren'); talk('bq'); talk('sws')

    go('1-10a6s'); shot('13_1-10a6s')
    talk('bosstianji'); time.sleep(0.8); shot('14_tianji')
    E("(()=>{const d=window.__djfmDbg;d.foes.forEach(f=>{if(f.event!=='bosstianji'&&f.event!=='boss'&&f.name!=='天机')f.gone=true;});})()")
    fight_all(25, boss_events=('bosstianji','boss'))
    L('  bq2 after dual', E("window.__djfmDbg.dlg.flags.bq2")); skipvid(); shot('15_tianji_dead')

    go('ren'); talk('bq'); talk('sws'); talk('bq')
    L('  FINAL flags', E("window.__djfmDbg.dlg.flags"), 'scene', E("window.__djfmDbg.scene()"))
    shot('16_final')
    L('page errors', errs[:8])
    b.close()

open(OUT + 'playthrough_log.txt', 'w').write('\n'.join(log))
print('done', len(log))
