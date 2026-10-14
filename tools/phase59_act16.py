import sys;sys.path.insert(0,'/workspace/djfm-sgcs/tools')
from phase59_pd901 import pm,P,Image,ImageDraw
O=['CA','LE','LA','TK','JQ','RA','RE','RH','HD']
CODE={}
def dirgroups(res):
  m={}
  for i,g in enumerate(pm['CA']):
    fr=g['frames']
    if fr and fr[0]['res'] in (res,res+1) and fr[0]['lib']==3:
      code=g['code']; d=(fr[0]['res']-res)*8+(fr[0]['sub']-1)//code
      m.setdefault(d,i)
  return m
def frame16(res,d,f,order=O,C=(80,120)):
  m=dirgroups(res); code=None
  can=Image.new('RGBA',(160,160))
  gi=m.get(d)
  for p in order:
    if p not in pm: continue
    if gi is not None:
      g=pm[p][gi]; fr=g['frames']
      if not fr: continue
      code=g['code']; x=fr[0] if len(fr)==1 else fr[min(f,len(fr)-1)]
      sub=x['sub']+(f if len(fr)==1 else 0); lib=x['lib']; r=x['res']; ox,oy=x['ox'],x['oy']
      if lib in (0,15): continue
    else:
      continue
    im=P.lep(lib,r,sub)
    if im is None or im.height<=2: continue
    can.alpha_composite(im.convert('RGBA'),(C[0]-ox,C[1]-oy))
  return can
if __name__=='__main__':
  res=int(sys.argv[1]); nf=int(sys.argv[2])
  m=dirgroups(res); print(sorted(m.items()))
  S=Image.new('RGBA',(16*90,nf*130+14),(60,66,52,255)); D=ImageDraw.Draw(S)
  for d in range(16):
    D.text((d*90+40,0),str(d),fill='yellow')
    for f in range(nf): S.alpha_composite(frame16(res,d,f).crop((35,0,125,130)),(d*90,14+f*130))
  S.save(f'/tmp/a16_{res}.png')
