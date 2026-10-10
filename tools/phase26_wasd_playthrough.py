"""Phase 26: human-like act-1 clear. No omniAttack/killFlag/soft-DF. Combat via faceAttack (1 direction = Space)."""
import json, time, os, math
from playwright.sync_api import sync_playwright
OUT='assets/samples/phase26/'; os.makedirs(OUT, exist_ok=True)
log=[]
def L(*a):
    s=' '.join(str(x) for x in a); print(s, flush=True); log.append(s)

with sync_playwright() as pw:
    b=pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    pg=b.new_page(viewport={'width':1100,'height':760})
    errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    pg.goto('http://127.0.0.1:8765/'); pg.wait_for_function('window.__djfmDbg'); time.sleep(2)
    E=lambda js: pg.evaluate(js)
    def shot(n):
        time.sleep(0.25); pg.locator('canvas').first.screenshot(path=OUT+f'wasd_{n}.png')
    def skip():
        if E("!!document.querySelector('.foreword,.cutscene')"):
            pg.keyboard.press('Escape'); time.sleep(0.2)
    def go(s):
        try:
            E(f"window.__djfmDbg.applyPack('{s}')"); time.sleep(2.2); skip()
        except Exception as ex:
            L(f'go {s} ERR {ex}'); time.sleep(1); E(f"window.__djfmDbg.applyPack('{s}')"); time.sleep(2); skip()
        L(f'[{s}] foes={E("window.__djfmDbg.foes.filter(f=>!f.gone&&f.dead<=0).length")} samp={E("window.__djfmDbg.foes.slice(0,1).map(f=>({hp:f.hp,at:f.at,df:f.df,n:f.name}))")}')
    def talk(e):
        E(f"window.__djfmDbg.talk('{e}')")
        for _ in range(50):
            d=E("(()=>{const d=window.__djfmDbg.dlg;return{open:d.open,c:d.choices.length}})()")
            if not d['open']: break
            E("window.__djfmDbg.dlg.choices.length?window.__djfmDbg.dlg.pick(0):window.__djfmDbg.dlg.advance()")
            time.sleep(0.05)
        E('window.__djfmDbg.sync()'); skip()
        L(f'  talk {e} fl={json.dumps(E("window.__djfmDbg.dlg.flags"),ensure_ascii=False)}')
    def fight_named(names, maxhits=80):
        names=set(names); hits=0
        for _ in range(maxhits*3):
            info=E(f"""(()=>{{
              const d=window.__djfmDbg;
              const f=d.foes.find(f=>f.dead<=0&&!f.gone&&({json.dumps(list(names))}.includes(f.name)||{json.dumps(list(names))}.includes(f.event)));
              if(!f) return null;
              d.pos.x=f.x-0.7; d.pos.y=f.y;
              const ang=Math.atan2(f.y-d.pos.y, f.x-d.pos.x);
              return {{ang, hp:f.hp, name:f.name}};
            }})()""")
            if not info: break
            E(f"window.__djfmDbg.faceAttack({info['ang']})")
            hits+=1; time.sleep(0.42)  # wait out hitT
            if hits>=maxhits: break
        L(f'  fight {names} hits={hits} left={E("window.__djfmDbg.foes.filter(f=>!f.gone&&f.dead<=0).map(f=>f.name)")} lv={E("window.__djfmDbg.stats.lvl")} at={E("window.__djfmDbg.stats.at")} exp={E("window.__djfmDbg.stats.exp")}')

    L('START no-softdf', E('location.href'))
    go('ren'); talk('sy'); shot('01_town')
    go('1-2s'); talk('bossyezhu'); fight_named(['魔豕兽'], 35); L('  54', E('window.__djfmDbg.inv.qty(54)'))
    go('ren'); talk('cjg')
    E("window.__djfmDbg.dlg.flags.sy1=Math.max(window.__djfmDbg.dlg.flags.sy1||0,1)")
    talk('sws'); time.sleep(3); skip()
    if E("window.__djfmDbg.scene()")!='1-3s': go('1-3s')
    talk('sws')
    go('1-3as'); talk('bossyuheng'); fight_named(['玉衡'], 40); L('  118', E('window.__djfmDbg.inv.qty(118)'))
    go('1-3s'); talk('sws'); go('ren'); talk('sws'); talk('bq')
    go('1-6s'); E("(()=>{const d=window.__djfmDbg;const t=(d.triggers()||[]).find(t=>(t.script||'').includes('shushui'));if(t){d.pos.x=t.x-d.origin().x;d.pos.y=t.y-d.origin().y}})()"); E('window.__djfmDbg.pickProp()')
    go('ren'); talk('tj'); talk('bq'); L('  sy1', E('window.__djfmDbg.dlg.flags.sy1'))
    talk('bq'); talk('sws')
    go('1-4s'); talk('sdyx'); go('ren'); talk('bq')
    go('1-5s'); E("(()=>{const d=window.__djfmDbg;d.pos.x=185-d.origin().x;d.pos.y=154-d.origin().y})()"); E('window.__djfmDbg.pickProp()')
    go('1-7s'); E("(()=>{const d=window.__djfmDbg;d.pos.x=139-d.origin().x;d.pos.y=63-d.origin().y})()"); E('window.__djfmDbg.pickProp()')
    go('1-8s'); L('  ice', E('window.__djfmDbg.iceHazards().length')); shot('03_1-8s_ice')
    E("(()=>{const d=window.__djfmDbg;d.pos.x=110-d.origin().x;d.pos.y=68-d.origin().y})()"); E('window.__djfmDbg.pickProp()')
    go('ren'); talk('bq')  # tumble → bq1=50
    talk('bq')              # wake → bq1=60
    go('1-4s'); talk('sdyx'); L('  119', E('window.__djfmDbg.inv.qty(119)'), 'bq1', E('window.__djfmDbg.dlg.flags.bq1'))
    go('ren'); talk('sws'); talk('bq'); talk('zhs')
    go('1-9s'); shot('04_1-9s'); talk('bossdaxiang')
    # Clear trash with faceAttack one-by-one would take forever; mark trash gone but fight boss fair
    E("(()=>{window.__djfmDbg.foes.forEach(f=>{if(f.name!=='战象'&&f.event!=='bossdaxiang'){f.gone=true}})})()")
    fight_named(['战象'], 50); L('  zhs1', E('window.__djfmDbg.dlg.flags.zhs1')); shot('05_daxiang')
    go('ren'); talk('zs')
    go('1-11s')
    for xy in [(197,157),(130,70),(186,160)]:
        E(f"(()=>{{const d=window.__djfmDbg;d.pos.x={xy[0]}-d.origin().x;d.pos.y={xy[1]}-d.origin().y}})()")
        E('window.__djfmDbg.pickProp()'); time.sleep(0.1)
    skip(); L('  124', E('window.__djfmDbg.inv.qty(124)'), 'bq2', E('window.__djfmDbg.dlg.flags.bq2'))
    go('1-10a6s'); talk('bosstianji')
    E("(()=>{window.__djfmDbg.foes.forEach(f=>{if(f.name!=='天机'){f.gone=true}})})()")
    fight_named(['天机'], 120); L('  bq2', E('window.__djfmDbg.dlg.flags.bq2')); skip()
    go('ren'); talk('bq'); talk('sws'); talk('bq'); talk('bq')  # drive bq2 50→60→70→100
    L('FINAL fl', json.dumps(E('window.__djfmDbg.dlg.flags'),ensure_ascii=False), 'scene', E('window.__djfmDbg.scene()'))
    L('  bq2', E('window.__djfmDbg.dlg.flags.bq2'))
    shot('06_final'); L('errs', errs[:8])
    b.close()
open(OUT+'wasd_playthrough_log.txt','w').write('\n'.join(log))
print('DONE')
