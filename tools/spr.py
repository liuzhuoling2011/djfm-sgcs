"""Spr.lib graph descriptor: groups (action_code, 4, 7, 0, nframes) + nframes×7 i32:
packed=(frame_no<<24)|(lib<<20? byte)|(res_index u16), ?, ?, ox, oy, ?, ?. frame_no = dir*10 + k (1-based)."""
import struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import leyilib as L
Z = Path('/workspace/djfm-sgcs/extract/Blade And Sword 2 Ancient Legend/zy')
LIBS = ['Spr.lib','res00.Lib','ResPrior.lib','ResPlayer1.lib','ResBoss.lib','ResNpc2.lib','ResJM.Lib.chs','ResPlayer2.Lib','ResPlayer3.lib','ResNpc3.lib','ResExNpc1.lib','ResExPlayer1.lib','ResExPlayer2.Lib','ResEx01.Lib']
_spr = None
def spr_groups(g):
    global _spr
    _spr = _spr or L.LeyiLib.open(Z/'Spr.lib')
    b = _spr.entry_bytes(g); v = struct.unpack_from('<%di' % (len(b)//4), b)
    groups = []; i = 1
    while i < len(v) - 5:
        if v[i+1] == 4 and v[i+2] == 7 and v[i+3] == 0 and 0 < v[i+4] < 64:
            n = v[i+4]; fr = []; j = i + 5
            for _ in range(n):
                if j + 5 > len(v): break
                p = v[j] & 0xffffffff
                fr.append(dict(frame=p >> 24, lib=(p >> 16) & 0xff, res=p & 0xffff, ox=v[j+3], oy=v[j+4])); j += 7
            groups.append(dict(code=v[i], frames=fr)); i = j
        else:
            i += 1
    return groups
if __name__ == '__main__':
    from collections import Counter
    gs = spr_groups(int(sys.argv[1]))
    print(Counter((g['code'], f['lib'], f['res']) for g in gs for f in g['frames'][:1]))
