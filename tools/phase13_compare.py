"""Offline compose web model (ground x2 + BLD parts at iso(cell)+(ox,oy)) at a Wine camera; side-by-side."""
import json, sys
from PIL import Image
def compose(shot, cell, anchor, out):
    d=json.load(open('web/public/game/map/meta.json')); g=d['ground_full']
    G=Image.open('web/public/game/map/'+g['file']).convert('RGBA')
    (cx,cy),(ax,ay)=cell,anchor
    ox0=ax-((cx-cy)*16-g['min_sx'])*2; oy0=ay-((cx+cy)*8-g['min_sy'])*2
    C=G.crop((int(-ox0/2),int(-oy0/2),int((800-ox0)/2),int((600-oy0)/2))).resize((800,600),Image.NEAREST)
    for b in sorted(d['buildings'],key=lambda b:b['x']+b['y']):
        sx=ax+((b['x']-b['y'])-(cx-cy))*32; sy=ay+((b['x']+b['y'])-(cx+cy))*16
        for q in b['parts']:
            x,y=int(sx+q['ox']),int(sy+q['oy'])
            if x>800 or y>600 or x+q['w']<0 or y+q['h']<0: continue
            im=Image.open('web/public/game/map/props/'+q['file']).convert('RGBA')
            L=Image.new('RGBA',(800,600),(0,0,0,0)); L.paste(im,(x,y),im); C.alpha_composite(L)
    W=Image.open(shot).convert('RGB').crop((0,0,800,600))
    s=Image.new('RGB',(1600,600)); s.paste(W,(0,0)); s.paste(C.convert('RGB'),(800,0)); s.save(out)
if __name__=='__main__':
    compose('assets/samples/xp_compare/orig_wadang/01_gate_rain.png',(70,55),(560,156),'assets/samples/phase13/wine_vs_model_arch.png')
    compose('assets/samples/xp_compare/orig_wadang/10_pavilion_tower.png',(84,78),(258,500),'assets/samples/phase13/wine_vs_model_pavilion_ground.png')
