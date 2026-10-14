import sys;sys.path.insert(0,'/workspace/djfm-sgcs/tools')
import phase24_paperdoll as P
from PIL import Image,ImageDraw
pm={p:P.groups(s) for p,s in P.parts('901').items()}
import re
print({p:s for p,s in P.parts('901').items()})
def frame(gi,f,parts=None,order=None):
  can=Image.new('RGBA',(160,160))
  seq=order or ['RH','CA','JQ','LA','RA','TK','LE','RE','HD']
  for p in seq:
    if p not in pm or (parts and p not in parts): continue
    gs=pm[p]
    if gi>=len(gs) or not gs[gi]['frames']: continue
    fr=gs[gi]['frames']; x=fr[min(f,len(fr)-1)]
    sub=x['sub']+(f if len(fr)==1 else 0)
    if x['lib'] in (0,15): continue
    im=P.lep(x['lib'],x['res'],sub)
    if im is None or im.height<=2: continue
    can.alpha_composite(im.convert('RGBA'),(80-x['ox'],120-x['oy']))
  return can
if __name__=='__main__':
  S=Image.new('RGBA',(16*90,9*130),(60,66,52,255)); D=ImageDraw.Draw(S)
  for k,p in enumerate(['CA','HD','TK','JQ','LA','RA','LE','RE','RH']):
    for j,gi in enumerate(range(18,34)):
      S.alpha_composite(frame(gi,0,parts=[p]).crop((35,0,125,130)),(j*90,k*130))
    D.text((2,k*130+2),p,fill='yellow')
  S.save('/tmp/pd_parts.png')
