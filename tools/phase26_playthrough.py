"""Phase 26: act-1 end → 2-0s and probe reachable act-2 maps."""
import json, time, os
from playwright.sync_api import sync_playwright
OUT='assets/samples/phase26/'; os.makedirs(OUT, exist_ok=True)
log=[]
def L(*a):
    s=' '.join(str(x) for x in a); print(s); log.append(s)

with sync_playwright() as pw:
    b=pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    pg=b.new_page(viewport={'width':1100,'height':760})
    errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/'); pg.wait_for_function('window.__djfmDbg'); time.sleep(2)
    E=lambda js: pg.evaluate(js)
    def shot(n):
        time.sleep(0.5); pg.locator('canvas').first.screenshot(path=OUT+f'pt_{n}.png')
    def skip():
        if E("!!document.querySelector('.foreword,.cutscene')"):
            L('  overlay', E("document.querySelector('.fore-title,.cut-tip')?.textContent"))
            time.sleep(0.8); pg.keyboard.press('Escape'); time.sleep(0.3)
    def go(s):
        E(f"window.__djfmDbg.applyPack('{s}')"); time.sleep(2.2); skip()
        L(f'[{s}] scene={E("window.__djfmDbg.scene()")} npcs={E("window.__djfmDbg.objects.length")} foes={E("window.__djfmDbg.foes.length")} name={E("window.__djfmDbg.dlg.names && 0")} flags_act={E("window.__djfmDbg.dlg.currentAct")}')
    def talk(e):
        E(f"window.__djfmDbg.talk('{e}')")
        for _ in range(40):
            d=E("(()=>{const d=window.__djfmDbg.dlg;return {open:d.open,c:d.choices.length}})()")
            if not d['open']: break
            if d['c']: E("window.__djfmDbg.dlg.pick(0)")
            else: E("window.__djfmDbg.dlg.advance()")
        E('window.__djfmDbg.sync()'); time.sleep(0.3); skip()
        L(f'  talk {e} → {json.dumps(E("window.__djfmDbg.dlg.flags"))} scene={E("window.__djfmDbg.scene()")}')

    # Jump to act-1 clear state
    E("""(()=>{const d=window.__djfmDbg;
      d.dlg.flags={sy1:100,bq1:100,bq2:99,bq:3,zhs1:100,cjg1:100,act1:1};
      d.stats.lvl=12; d.stats.at=40+4*11; d.stats.df=30+4*11;
      d.stats.maxHp=800+80*11; d.stats.hp=d.stats.maxHp;
    })()""")
    go('ren'); shot('01_town_clear')
    talk('bq')  # bq2>=99 → go 2-0s (line 24) or >=69 (line 13)
    time.sleep(2); skip(); time.sleep(1)
    L('ARRIVE', E("window.__djfmDbg.scene()"), 'act', E("window.__djfmDbg.dlg.currentAct"), 'act2flag', E("window.__djfmDbg.dlg.flags.act2"))
    shot('02_2-0s')
    talk('2bq'); talk('2sws'); talk('2sy'); shot('03_2-0s_talk')

    for s in ['2-1s','2-2s','2-7s','2-3s','2-5s','2-8s','2-13s','2-13as']:
        go(s); shot(f'map_{s}')

    L('page errors', errs[:8])
    b.close()
open(OUT+'playthrough_log.txt','w').write('\n'.join(log))
print('done')
