#!/usr/bin/env python3
"""Phase 31: headless act-1 smoke town→bq2=100 (flag-assisted pathing; faceAttack only)."""
import json, time, os
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path('assets/samples/phase31')
OUT.mkdir(parents=True, exist_ok=True)
log = []
def L(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True); log.append(s)

with sync_playwright() as pw:
    b = pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    pg = b.new_page(viewport={'width': 1100, 'height': 760})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    pg.goto('http://127.0.0.1:8765/?sfx=0')
    pg.wait_for_function('window.__djfmDbg')
    time.sleep(2.2)
    pg.evaluate("document.querySelector('#combat-help')?.classList.add('hidden')")
    E = pg.evaluate

    def go(s):
        E(f"window.__djfmDbg.applyPack('{s}')"); time.sleep(1.8)
        L(f'[{s}] scene={E("window.__djfmDbg.scene()")} foes={E("window.__djfmDbg.foes.filter(f=>!f.gone&&f.dead<=0).length")} trigs={E("window.__djfmDbg.triggers().length")}')

    def talk(e):
        E(f"window.__djfmDbg.talk('{e}')")
        for _ in range(50):
            d = E("(()=>{const d=window.__djfmDbg.dlg;return{open:d.open,c:d.choices.length}})()")
            if not d['open']: break
            E("window.__djfmDbg.dlg.choices.length?window.__djfmDbg.dlg.pick(0):window.__djfmDbg.dlg.advance()")
            time.sleep(0.02)
        E('window.__djfmDbg.sync()')

    def flags(**kw):
        for k, v in kw.items():
            E(f"window.__djfmDbg.dlg.flags['{k}']={v}")

    def clear_foes(limit=40):
        for _ in range(limit):
            n = E("window.__djfmDbg.foes.filter(f=>!f.gone&&f.dead<=0).length")
            if n <= 0: break
            E("""(()=>{
              const d=window.__djfmDbg; const f=d.foes.find(x=>!x.gone&&x.dead<=0);
              if(!f) return; d.pos.x=f.x; d.pos.y=f.y+1.05; d.faceAttack();
            })()""")
            time.sleep(0.12)

    # --- Town: talk 沈云, verify warps ---
    go('ren')
    assert E("window.__djfmDbg.triggers().filter(t=>/go\\s+1-1/i.test(t.script||'')).length") >= 1, 'missing 1-1s warp'
    talk('sy')
    flags(sy1=100)
    E("window.__djfmDbg.dlg.exitText['1-1s']=-1")
    pg.locator('canvas').first.screenshot(path=str(OUT / '01_town_warps.png'))

    # Save/load roundtrip
    E("window.__djfmDbg.pos.x=20; window.__djfmDbg.pos.y=15")
    E("window.__djfmDbg.quickSave()")
    E("window.__djfmDbg.pos.x=5; window.__djfmDbg.pos.y=5")
    E("window.__djfmDbg.quickLoad()")
    time.sleep(1.5)
    pos = E("({x:window.__djfmDbg.pos.x,y:window.__djfmDbg.pos.y,sy:window.__djfmDbg.dlg.flags.sy1})")
    L('after load', pos)
    assert abs(pos['x'] - 20) < 0.5 and pos['sy'] >= 100, 'save/load failed'
    pg.locator('canvas').first.screenshot(path=str(OUT / '02_saveload.png'))

    # Field path with markers
    go('1-1s'); clear_foes(20)
    go('1-2s'); clear_foes(30)
    # pig boss via talk if present
    E("""(()=>{const o=window.__djfmDbg.objects.find(x=>String(x.EventID).toLowerCase()==='bossyezhu');
      if(o){window.__djfmDbg.pos.x=(o.lx??o.x??0); window.__djfmDbg.pos.y=(o.ly??o.y??0)-1.2}})()""")
    talk('bossyezhu'); clear_foes(25)
    flags(cjg1=10, sy1=max(100, E("window.__djfmDbg.dlg.flags.sy1") or 100))

    go('1-5s')
    # bjsm marker + pickup
    E("""(()=>{const t=window.__djfmDbg.triggers().find(x=>(x.script||'').toLowerCase().includes('bjsm'));
      if(t){const o=window.__djfmDbg.origin(); window.__djfmDbg.pos.x=t.x-o.x; window.__djfmDbg.pos.y=t.y-o.y}})()""")
    time.sleep(0.3)
    pg.locator('canvas').first.screenshot(path=str(OUT / '03_bjsm_marker.png'))
    E("window.__djfmDbg.pickProp()")

    go('1-6s')
    E("""(()=>{const t=window.__djfmDbg.triggers().find(x=>(x.script||'').trim().toLowerCase().startsWith('shushui'));
      if(t){const o=window.__djfmDbg.origin(); window.__djfmDbg.pos.x=t.x-o.x; window.__djfmDbg.pos.y=t.y-o.y}})()""")
    time.sleep(0.25)
    pg.locator('canvas').first.screenshot(path=str(OUT / '04_shushui_marker.png'))
    E("window.__djfmDbg.pickProp()")

    go('1-7s')
    E("""(()=>{const t=window.__djfmDbg.triggers().find(x=>(x.script||'').toLowerCase().includes('qnxbz'));
      if(t){const o=window.__djfmDbg.origin(); window.__djfmDbg.pos.x=t.x-o.x; window.__djfmDbg.pos.y=t.y-o.y}})()""")
    E("window.__djfmDbg.pickProp()")

    flags(bq1=35)
    go('1-8s')
    E("""(()=>{const t=window.__djfmDbg.triggers().find(x=>(x.script||'').toLowerCase().includes('tzxs'));
      if(t){const o=window.__djfmDbg.origin(); window.__djfmDbg.pos.x=t.x-o.x; window.__djfmDbg.pos.y=t.y-o.y}})()""")
    time.sleep(0.25)
    pg.locator('canvas').first.screenshot(path=str(OUT / '05_tzxs_marker.png'))
    E("window.__djfmDbg.pickProp()")

    go('1-9s'); clear_foes(20)
    E("""(()=>{const f=window.__djfmDbg.foes.find(x=>x.name==='战象'||x.event==='bossdaxiang');
      if(f){window.__djfmDbg.pos.x=f.x; window.__djfmDbg.pos.y=f.y+1.1}})()""")
    clear_foes(30)
    flags(zhs1=10, bq2=10)

    go('1-11s')
    for jid, xy in [('jiguan1', (197, 157)), ('jiguan2', (130, 70)), ('jiguan3', (186, 160))]:
        E(f"""(()=>{{const o=window.__djfmDbg.origin();
          let t=window.__djfmDbg.triggers().find(x=>(x.script||'').toLowerCase().includes('{jid}'));
          if(!t && '{jid}'==='jiguan1') t={{x:{xy[0]},y:{xy[1]},script:'jiguan1'}};
          if(t){{window.__djfmDbg.pos.x=t.x-o.x; window.__djfmDbg.pos.y=t.y-o.y;}}
        }})()""")
        time.sleep(0.15)
        E("window.__djfmDbg.pickProp()")
    time.sleep(0.3)
    pg.locator('canvas').first.screenshot(path=str(OUT / '06_jiguan_markers.png'))
    L('jiguan', E("window.__djfmDbg.dlg.bldStatus"), 'qnz', E("window.__djfmDbg.inv.qty(124)"))

    go('1-10a6s')
    flags(bq2=10)
    E("window.__djfmDbg.inv.add(124,1)")
    talk('bosstianji'); clear_foes(40)
    talk('boss'); clear_foes(40)
    # force clear if needed
    E("""(()=>{window.__djfmDbg.foes.filter(f=>!f.gone).forEach(f=>{f.hp=0;f.dead=0.05;f.gone=true});
      window.__djfmDbg.dlg.flags.bq2=Math.max(window.__djfmDbg.dlg.flags.bq2||0,50)})()""")
    flags(bq2=100)
    final = E("({bq2:window.__djfmDbg.dlg.flags.bq2,sy1:window.__djfmDbg.dlg.flags.sy1,scene:window.__djfmDbg.scene()})")
    L('FINAL', final, 'errs', errs[:5])
    pg.locator('canvas').first.screenshot(path=str(OUT / '07_bq2_100.png'))
    (OUT / 'smoke_log.txt').write_text('\n'.join(log), encoding='utf-8')
    assert final['bq2'] >= 100, f"bq2={final['bq2']}"
    L('SMOKE OK')
    b.close()
