"""Phase 14: MAP per-cell record = 5×u16 {ground_tid, deco_tid, flags(FF00/FF01), level, CDCD}.
deco_tid (col1) is a map_ren decal layer (pebbles/rubble/grass) drawn over ground; compose it into ground_full."""
import json, sys, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from leyilib import LeyiLib
from phase10_run_export import compose_iso_ground
from PIL import Image
ROOT=Path('/workspace/djfm-sgcs'); WEB=ROOT/'web/public/game/map'
d=(ROOT/'assets/samples/phase9/fol_extract/cj/1-0s.MAP').read_bytes()
u=np.frombuffer(d[346+32768:][:167972],dtype='<u2'); R=u[2066:2066+81920].reshape(128,128,5)
mapren=LeyiLib.open(ROOT/'extract/Blade And Sword 2 Ancient Legend/zy/map_ren.lib')
from leyilib import decode_lep_diamond
import numpy as _np
cov={}
for v in set(R[:,:,1].ravel().tolist()):
    if v==65535 or v>=mapren.count: continue
    im=decode_lep_diamond(mapren.entry_bytes(v))
    cov[v]=(_np.array(im)[:,:,3]>0).mean() if im is not None else 1
# keep sparse decals (pebbles/rubble/grass); full diamonds in col1 are not drawn opaque in Wine
# Phase 16c: Wine pixel test (tools/phase16_overlay_blend.py) → ALL col1 tiles are plain colour-key alpha-over
deco=R[:,:,1].tolist()
print('deco ids',len(cov),'kept',sum(1 for c in cov.values() if c<0.45))
img,orig,ok,miss,_=compose_iso_ground(deco,mapren,scale=0.5)
meta=json.loads((WEB/'meta.json').read_text()); gm=meta['ground_full']
print('deco ok',ok,'origin',orig,'ground',gm['min_sx'],gm['min_sy'])
base=Image.open(ROOT/'assets/samples/review/ground_after_full.png').convert('RGBA')
lay=Image.new('RGBA',base.size,(0,0,0,0))
A=_np.array(img);lum=A[:,:,:3].astype(int).sum(2)/3
img=Image.fromarray(A)  # no dark-pixel drop (Phase 16c)
lay.paste(img,(int(orig['min_sx']-gm['min_sx']),int(orig['min_sy']-gm['min_sy'])),img)
base.alpha_composite(lay); base.save(WEB/'ground_full.png',optimize=True)
lay.save(ROOT/'assets/samples/phase14_ground_deco.png')
meta['map_cell_record']='5×u16: ground_tid, deco_tid, flags FF00/FF01, level 0-3, CDCD (Phase 14)'
(WEB/'meta.json').write_text(json.dumps(meta,ensure_ascii=False))
