import json, re, math, sys, unicodedata, numpy as np, networkx as nx, os
from rapidfuzz import fuzz, process
from scipy.spatial import cKDTree
S=sys.argv[1]; sys.path.insert(0,S)
from grid import EDGES, col_of
ROW_AB, ROW_BC = 740, 1165
ROWS={'A':(330,ROW_AB),'B':(ROW_AB,ROW_BC),'C':(ROW_BC,1620)}
def box(sq):
    seg,row,col=int(sq[:-2]),sq[-2],int(sq[-1])
    a,b=EDGES[seg-1],EDGES[seg]; w=(b-a)/5
    return (a+(col-1)*w, ROWS[row][0], a+col*w, ROWS[row][1])
def inbox(x,y,sqs,mx=70,my=90):
    return any(b[0]-mx<=x<=b[2]+mx and b[1]-my<=y<=b[3]+my for b in map(box,sqs))
def boxdist(x,y,sqs):
    best=1e9
    for b in map(box,sqs):
        dx=max(b[0]-x,0,x-b[2]); dy=max(b[1]-y,0,y-b[3]); best=min(best,math.hypot(dx,dy))
    return best
# ---- grid data
GRID=json.load(open(f'{S}/talbert_grid.json'))['grid']
for k,v in json.load(open(f'{S}/grid_from_index.json')).items(): GRID[k]=sorted(set(GRID.get(k,[]))|set(v))
ON_TABLE=set(GRID)
html=open('/Users/sebhirsch/Documents/Misc/peutinger/index.html').read()
cand=json.load(open(f'{S}/cand.json'))
OVID={k:v[0][0] for k,v in cand.items()}; OVID['Babylonia']='TPPlace2702'; OVID['Muziris']='TPPlace2797'
PXA=json.load(open(f'{S}/anchors.json'))
def norm(s):
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
    s=s.translate(str.maketrans('ujfyk','visic'))
    return re.sub(r'[^a-z ]','',s).strip()
ROMAN=re.compile(r'^[ivxlcdmn]{1,6}$')
phr=[]
for fn in ('ocr_all.json','ocr_all2.json'):
    for o in json.load(open(f'{S}/{fn}')):
        raw=o['t']; toks=[(m.start(),norm(m.group()).replace(' ','')) for m in re.finditer(r'\S+',raw)]
        toks=[(i,t) for i,t in toks if len(t)>=3 and not ROMAN.match(t)]
        n=max(len(raw),1)
        for k,(i,t) in enumerate(toks):
            for span in (1,2,3):
                if k+span>len(toks): break
                txt=''.join(x[1] for x in toks[k:k+span])
                phr.append(dict(t=txt,x=o['x']+o['w']*i/n,y=o['y']+o['h']/2,h=o['h'],c=o['c']))
seen=set(); P2=[]
for p in phr:
    key=(p['t'],round(p['x']/30),round(p['y']/30))
    if key in seen: continue
    seen.add(key); P2.append(p)
phr=P2; texts=[p['t'] for p in phr]
g=json.load(open(f'{S}/ov.json'))['@graph']
PL={x['@id'].split('#')[1]:x for x in g if x['@type']=='Place'}
O=nx.Graph(); O.add_nodes_from(PL)
for e in g:
    if e['@type']=='TravelAction':
        O.add_edge(e['from'][0]['@id'].split('#')[1], e['to'][0]['@id'].split('#')[1], d=e.get('dist') or 0)
roads=json.load(open(f'{S}/roads.json'))
pts=[]
for r in roads:
    for a,b in zip(r,r[1:]):
        n=max(1,int(math.dist(a,b)/4))
        for t in range(n): pts.append((a[0]+(b[0]-a[0])*t/n, a[1]+(b[1]-a[1])*t/n))
RT=cKDTree(pts)
def station(p):
    d,j=RT.query((p['x']-4, p['y']+p['h']*0.6))
    return (round(pts[j][0]),round(pts[j][1])) if d<30 else (round(p['x']),round(p['y']))
placed={OVID[n]:(x,y,'anchor',100) for n,(x,y) in PXA.items()}
used=set()
# ---- candidate lists
C={}
for k,p in PL.items():
    if k in placed or k not in ON_TABLE: continue
    nm=norm(p.get('label','')).replace(' ','')
    if len(nm)<3: continue
    sq=GRID.get(k)
    th=(92 if len(nm)<=4 else 85 if len(nm)==5 else 75) if sq else (93 if len(nm)<=5 else 82)
    res=process.extract(nm,texts,scorer=fuzz.ratio,score_cutoff=th,limit=60)
    # partial match for long names split across lines
    if len(nm)>=8:
        res+= [(a,b*0.95,i) for a,b,i in process.extract(nm,texts,scorer=fuzz.partial_ratio,score_cutoff=92,limit=30) if len(texts[i])>=6]
    cs=[]
    for _,sc,i in res:
        q=phr[i]
        if sq and not inbox(q['x'],q['y'],sq): continue
        cs.append((sc,i))
    if cs: C[k]=sorted(set(cs),reverse=True)
print('places with candidates',len(C),'with grid',sum(1 for k in C if k in GRID))
def support(k,q):
    lengths=nx.single_source_shortest_path_length(O,k,cutoff=4) if k in O else {}
    return sum(1 for n,h in lengths.items() if n in placed and h>0 and abs(placed[n][0]-q['x'])<260*h+150 and abs(placed[n][1]-q['y'])<700)
# pass 1: grid-constrained, greedy by score; ambiguous ones wait for support
changed=True; rnd=0
while changed:
    changed=False; rnd+=1
    order=sorted(C.items(), key=lambda kv:-kv[1][0][0])
    for k,cs in order:
        if k in placed: continue
        cs=[(sc,i) for sc,i in cs if i not in used]
        if not cs: continue
        has_grid=k in GRID
        top=cs[0][0]; close=[(sc,i) for sc,i in cs if sc>=top-6]
        if has_grid and len(close)==1:
            pick=close[0]
        else:
            sup=[(support(k,phr[i]),sc,i) for sc,i in close]
            sup.sort(reverse=True)
            if sup[0][0]==0 or (len(sup)>1 and sup[0][0]==sup[1][0] and sup[0][1]==sup[1][1]): continue
            pick=(sup[0][1],sup[0][2])
        sc,i=pick; x,y=station(phr[i]); used.add(i)
        placed[k]=(x,y,'ocr-grid' if has_grid else 'ocr',sc); changed=True
    print('round',rnd,len(placed))
# ---- interpolation along OV chains
added=1
while added:
    added=0
    for k in PL:
        if k in placed or k not in O or O.degree(k)!=2 or k not in ON_TABLE: continue
        ends=[]
        for start in O[k]:
            prev,cur,steps,dist=k,start,1,O[k][start]['d'] or 1
            while cur not in placed and O.degree(cur)==2 and steps<8:
                nxt=[n for n in O[cur] if n!=prev][0]; dist+=O[cur][nxt]['d'] or 1; prev,cur=cur,nxt; steps+=1
            ends.append((cur,dist) if cur in placed else None)
        if None in ends: continue
        (a,da),(b,db)=ends; A,B=placed[a],placed[b]
        if math.dist(A[:2],B[:2])>1200: continue
        f=da/(da+db); x=A[0]+f*(B[0]-A[0]); y=A[1]+f*(B[1]-A[1])
        d,j=RT.query((x,y))
        if d<25: x,y=pts[j]
        if k in GRID and not inbox(x,y,GRID[k],120,140): continue
        placed[k]=(round(x),round(y),'interp',0); added+=1
# ---- grid-only fallback: place inside the square, near placed neighbours if any
for k,sq in GRID.items():
    if k in placed or k not in PL: continue
    b=box(sq[0]); cx,cy=(b[0]+b[2])/2,(b[1]+b[3])/2
    nb=[placed[n] for n in (O[k] if k in O else []) if n in placed]
    if nb:
        cx=min(max(np.mean([p[0] for p in nb]),b[0]+20),b[2]-20); cy=min(max(np.mean([p[1] for p in nb]),b[1]+20),b[3]-20)
    placed[k]=(round(cx),round(cy),'grid',0)
from collections import Counter
print('final',len(placed),Counter(v[2] for v in placed.values()))
# grid agreement report
ok=Counter()
for k,v in placed.items():
    if k in GRID: ok[(v[2], inbox(v[0],v[1],GRID[k],0,0), inbox(v[0],v[1],GRID[k]))]+=1
for kk,n in sorted(ok.items()): print(kk,n)
out=[dict(id=k,n=PL[k].get('label',k) if k in PL else k,m=PL.get(k,{}).get('modern',''),x=v[0],y=v[1],c=v[2],sc=v[3],grid=GRID.get(k,[])) for k,v in placed.items()]
json.dump(out,open(f'{S}/stations2.json','w'),ensure_ascii=False)
json.dump(dict(roads=roads,stations=[dict(n=o['n']+{'interp':'*','grid':'#'}.get(o['c'],''),x=o['x'],y=o['y']) for o in out]),open(f'{S}/viz_data.json','w'))
