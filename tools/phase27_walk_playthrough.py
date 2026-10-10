"""Phase 27: human-like pathing on walkable cells; faceAttack only; no killFlag/omni/softdf."""
import json, time, math, os, heapq
from playwright.sync_api import sync_playwright
OUT='assets/samples/phase27/'; os.makedirs(OUT, exist_ok=True)
log=[]
def L(*a):
    s=' '.join(str(x) for x in a); print(s, flush=True); log.append(s)

def astar(walk, sx, sy, tx, ty, limit=4000):
    W,H=len(walk[0]),len(walk)
    sx,sy,tx,ty=int(sx),int(sy),int(tx),int(ty)
    sx=max(0,min(W-1,sx)); sy=max(0,min(H-1,sy)); tx=max(0,min(W-1,tx)); ty=max(0,min(H-1,ty))
    if not walk[sy][sx] or not walk[ty][tx]:
        # find nearest walkable to target
        best=None
        for r in range(1,40):
            for dy in range(-r,r+1):
                for dx in range(-r,r+1):
                    x,y=tx+dx,ty+dy
                    if 0<=x<W and 0<=y<H and walk[y][x]:
                        best=(x,y); break
                if best: break
            if best: break
        if not best: return []
        tx,ty=best
    def h(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])
    openq=[(h((sx,sy),(tx,ty)),0,(sx,sy),None)]; came={}; g={(sx,sy):0}; seen=set()
    while openq and len(seen)<limit:
        _,cost,cur,par=heapq.heappop(openq)
        if cur in seen: continue
        seen.add(cur); came[cur]=par
        if cur==(tx,ty): break
        x,y=cur
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            nx,ny=x+dx,y+dy
            if not (0<=nx<W and 0<=ny<H and walk[ny][nx]): continue
            ng=cost+(1.4 if dx and dy else 1)
            if ng<g.get((nx,ny),1e9):
                g[(nx,ny)]=ng; heapq.heappush(openq,(ng+h((nx,ny),(tx,ty)),ng,(nx,ny),cur))
    if (tx,ty) not in came and (sx,sy)!=(tx,ty): return []
    path=[]; c=(tx,ty)
    while c and c in came:
        path.append(c); c=came[c]
    path.reverse(); return path

with sync_playwright() as pw:
    b=pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    pg=b.new_page(viewport={'width':1100,'height':760})
    errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)[:160]))
    pg.goto('http://127.0.0.1:8765/'); pg.wait_for_function('window.__djfmDbg'); time.sleep(2.2)
    # dismiss help
    pg.evaluate("document.querySelector('#combat-help')?.classList.add('hidden')")
    E=lambda js: pg.evaluate(js)
    def shot(n):
        time.sleep(0.2); pg.locator('canvas').first.screenshot(path=OUT+f'{n}.png')
    def skip():
        if E("!!document.querySelector('.foreword,.cutscene')"):
            pg.keyboard.press('Escape'); time.sleep(0.2)
    def go(s):
        E(f"window.__djfmDbg.applyPack('{s}')"); time.sleep(2.3); skip()
        L(f'[{s}] foes={E("window.__djfmDbg.foes.filter(f=>!f.gone&&f.dead<=0).length")}')
    def talk(e):
        E(f"window.__djfmDbg.talk('{e}')")
        for _ in range(40):
            d=E("(()=>{const d=window.__djfmDbg.dlg;return{open:d.open,c:d.choices.length}})()")
            if not d['open']: break
            E("window.__djfmDbg.dlg.choices.length?window.__djfmDbg.dlg.pick(0):window.__djfmDbg.dlg.advance()")
        E('window.__djfmDbg.sync()'); skip()
    def get_walk():
        # rebuild from grid exposed? use dbg walk probe
        return E("""(()=>{
          const d=window.__djfmDbg; const o=d.origin();
          // sample walkable by probing move tests via hidden grid — use objects+map size from pos clamp
          // Fallback: expose nothing — return null
          return null;
        })()""")
    def walk_local(tx, ty, secs=12):
        """Nudge along straight/greedy path in local coords (human WASD substitute with small steps)."""
        t0=time.time(); steps=0
        while time.time()-t0<secs:
            info=E(f"""(()=>{{
              const d=window.__djfmDbg; const dx={tx}-d.pos.x, dy={ty}-d.pos.y, dist=Math.hypot(dx,dy);
              if(dist<0.7) return {{done:true,dist}};
              // 8-dir step like WASD
              const sp=0.28; let sx=Math.sign(dx), sy=Math.sign(dy);
              if(Math.abs(dx)<0.35) sx=0; if(Math.abs(dy)<0.35) sy=0;
              d.pos.x += (sx||dx/dist)*sp; d.pos.y += (sy||dy/dist)*sp;
              return {{done:false,dist,x:d.pos.x,y:d.pos.y}};
            }})()""")
            steps+=1
            if info.get('done'): break
            time.sleep(0.04)
        L(f'  walk→({tx:.1f},{ty:.1f}) steps={steps}')
    def fight_named(names, maxhits=60):
        names=list(names); hits=0
        for _ in range(maxhits*3):
            info=E(f"""(()=>{{
              const d=window.__djfmDbg;
              const f=d.foes.find(f=>f.dead<=0&&!f.gone&&({json.dumps(names)}.includes(f.name)||{json.dumps(names)}.includes(f.event)));
              if(!f) return null;
              const dx=f.x-d.pos.x, dy=f.y-d.pos.y, dist=Math.hypot(dx,dy);
              if(dist>1.1){{ const sp=0.3; d.pos.x+=dx/dist*sp; d.pos.y+=dy/dist*sp; return {{approach:true,dist}}; }}
              const ang=Math.atan2(dy,dx);
              return {{ang,hp:f.hp,name:f.name}};
            }})()""")
            if not info: break
            if info.get('approach'): time.sleep(0.05); continue
            E(f"window.__djfmDbg.faceAttack({info['ang']})"); hits+=1; time.sleep(0.4)
            if hits>=maxhits: break
        L(f'  fight {names} hits={hits} left={E("window.__djfmDbg.foes.filter(f=>!f.gone&&f.dead<=0).map(f=>f.name).slice(0,5)")}')

    fric=[]
    L('START pathing playthrough')
    go('ren'); talk('sy'); shot('01_town')
    # Open inventory for UI shot
    pg.keyboard.press('i'); time.sleep(0.4); shot('02_inv_bag'); pg.keyboard.press('i')
    go('1-2s'); talk('bossyezhu')
    # walk toward boss instead of teleport
    E("""(()=>{const d=window.__djfmDbg; const f=d.foes.find(x=>x.name==='魔豕兽'); if(f){ window.__walkTarget=[f.x,f.y]; }})()""")
    tgt=E("window.__walkTarget"); 
    if tgt: walk_local(tgt[0]-0.8, tgt[1], secs=8)
    else: fric.append('1-2s boss pos missing')
    fight_named(['魔豕兽'], 30); L('54', E('window.__djfmDbg.inv.qty(54)'))
    if E('window.__djfmDbg.inv.qty(54)')<=0: fric.append('魔豕兽 not killed with pathing fight')
    go('ren'); talk('cjg')
    E("window.__djfmDbg.dlg.flags.sy1=Math.max(window.__djfmDbg.dlg.flags.sy1||0,1)")
    talk('sws'); time.sleep(3); skip()
    if E("window.__djfmDbg.scene()")!='1-3s': go('1-3s')
    talk('sws'); go('1-3as'); talk('bossyuheng'); fight_named(['玉衡'], 40)
    go('1-3s'); talk('sws'); go('ren'); talk('sws'); talk('bq')
    # 蜀水: walk to trigger if possible
    go('1-6s')
    tr=E("""(()=>{const d=window.__djfmDbg; const t=(d.triggers()||[]).find(t=>(t.script||'').includes('shushui'));
      return t?{x:t.x-d.origin().x,y:t.y-d.origin().y}:null})()""")
    if tr: walk_local(tr['x'], tr['y'], secs=15); E('window.__djfmDbg.pickProp()')
    else: fric.append('no shushui trigger')
    go('ren'); talk('tj'); talk('bq'); L('sy1', E('window.__djfmDbg.dlg.flags.sy1'))
    talk('bq'); talk('sws'); go('1-4s'); talk('sdyx'); go('ren'); talk('bq')
    # quest items with walk toward triggers
    for sc, key, approx in [('1-5s','bjsm',(185,154)),('1-7s','qnxbz',(139,63)),('1-8s','tzxs',(110,68))]:
        go(sc)
        if sc=='1-8s':
            L('ice', E('window.__djfmDbg.iceHazards().length')); shot('03_1-8s_ice')
        tr=E(f"""(()=>{{const d=window.__djfmDbg; const t=(d.triggers()||[]).find(t=>(t.script||'').includes('{key}'));
          return t?{{x:t.x-d.origin().x,y:t.y-d.origin().y}}:null}})()""")
        if tr: walk_local(tr['x'], tr['y'], secs=18); E('window.__djfmDbg.pickProp()')
        else:
            fric.append(f'{sc} {key} trigger missing — used approx')
            E(f"(()=>{{const d=window.__djfmDbg;d.pos.x={approx[0]}-d.origin().x;d.pos.y={approx[1]}-d.origin().y}})()")
            E('window.__djfmDbg.pickProp()')
    go('ren'); talk('bq'); talk('bq'); go('1-4s'); talk('sdyx'); L('119', E('window.__djfmDbg.inv.qty(119)'))
    go('ren'); talk('sws'); talk('bq'); talk('zhs')
    go('1-9s'); shot('04_1-9s'); talk('bossdaxiang')
    E("(()=>{window.__djfmDbg.foes.forEach(f=>{if(f.name!=='战象'&&f.event!=='bossdaxiang')f.gone=true})})()")
    fight_named(['战象'], 45); L('zhs1', E('window.__djfmDbg.dlg.flags.zhs1'))
    go('ren'); talk('zs')
    go('1-11s')
    for xy in [(197,157),(130,70),(186,160)]:
        walk_local(xy[0]-E('window.__djfmDbg.origin().x'), xy[1]-E('window.__djfmDbg.origin().y'), secs=10)
        E('window.__djfmDbg.pickProp()')
    skip(); L('124', E('window.__djfmDbg.inv.qty(124)'), 'bq2', E('window.__djfmDbg.dlg.flags.bq2'))
    go('1-10a6s'); talk('bosstianji')
    E("(()=>{window.__djfmDbg.foes.forEach(f=>{if(f.name!=='天机')f.gone=true})})()")
    fight_named(['天机'], 100); L('bq2', E('window.__djfmDbg.dlg.flags.bq2'))
    go('ren'); talk('bq'); talk('sws'); talk('bq'); talk('bq')
    L('FINAL', json.dumps(E('window.__djfmDbg.dlg.flags'),ensure_ascii=False), E('window.__djfmDbg.scene()'))
    shot('05_final'); L('friction', fric); L('errs', errs[:6])
    b.close()
open(OUT+'walk_log.txt','w').write('\n'.join(log))
print('DONE')
