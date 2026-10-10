"""res00 building lep: row RLE  [skip_bytes] ([count_bytes][pix...][skip_bytes])* , row sums to W px."""
import struct
from PIL import Image
import leyilib as L

def _parse(blob, start, W, end):
    p=start; rows=[]
    while p+2<=end:
        x=0; spans=[]
        while True:
            if p+2>end: return rows,p
            s=struct.unpack_from('<H',blob,p)[0]; p+=2
            if s%2: return rows,p-2
            x+=s//2
            if x==W: break
            if x>W: return rows,p-2
            c=struct.unpack_from('<H',blob,p)[0]
            if c==0 or c%2 or x+c//2>W or p+2+c>end: return rows,p-2
            n=c//2; spans.append((x,struct.unpack_from(f'<{n}H',blob,p+2))); p+=2+c; x+=n
            if x==W: break   # run reaches edge: no trailing skip
        rows.append(spans)
    return rows,p

def best_parse(blob):
    h=L.parse_lep_header(blob); first=h['first_off']
    sec,sec_end=L._get_sec_table(blob,first)
    start=sec_end; end=len(blob)
    best=None
    for W in range(8,2048):
        rows,p=_parse(blob,start,W,end)
        sc=p-start
        if best is None or sc>best[0]: best=(sc,W,rows,p)
    return best,start,end

def decode(blob):
    (sc,W,rows,p),start,end=best_parse(blob)
    if not rows: return None
    im=Image.new('RGBA',(W,len(rows)),(0,0,0,0)); px=im.load()
    for y,spans in enumerate(rows):
        for x,pix in spans:
            for j,v in enumerate(pix):
                if v!=L.COLOR_KEY: px[x+j,y]=L._sprite_rgba_exact(v)
    return im
