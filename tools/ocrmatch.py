import json, re, math, sys, unicodedata, numpy as np, networkx as nx
from rapidfuzz import fuzz, process
from scipy.spatial import cKDTree
S=sys.argv[1]
html=open('/Users/sebhirsch/Documents/Misc/peutinger/index.html').read()
PX=json.loads(re.search(r'const PX = (\{.*\});',html).group(1))
cand=json.load(open(f'{S}/cand.json'))
OVID={k:v[0][0] for k,v in cand.items()}; OVID['Babylonia']='TPPlace2702'; OVID['Muziris']='TPPlace2797'
def norm(s):
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
    s=s.translate(str.maketrans('ujfyk','visic'))
    return re.sub(r'[^a-z ]','',s).strip()
ROMAN=re.compile(r'^[ivxlcdmn]{1,6}$')
# ---- OCR phrases
ocr=json.load(open(f'{S}/ocr_all.json'))
phr=[]
for o in ocr:
    if o['c']<0.3: continue
    raw=o['t']; toks=[(m.start(),m.group()) for m in re.finditer(r'\S+',raw)]
    toks=[(i,norm(t).replace(' ','')) for i,t in toks]
    toks=[(i,t) for i,t in toks if len(t)>=3 and not ROMAN.match(t)]
    n=max(len(raw),1)
    for k,(i,t) in enumerate(toks):
        for span in (1,2,3):
            if k+span>len(toks): break
            txt=''.join(x[1] for x in toks[k:k+span])
            x=o['x']+o['w']*i/n
            phr.append(dict(t=txt,x=x,y=o['y']+o['h']/2,h=o['h']))
# dedupe overlapping tiles
seen={}; P2=[]
for p in phr:
    key=(p['t'],round(p['x']/25),round(p['y']/25))
    if key in seen: continue
    seen[key]=1; P2.append(p)
phr=P2; texts=[p['t'] for p in phr]
print('phrases',len(phr))
# ---- OV
g=json.load(open(f'{S}/ov.json'))['@graph']
PL={x['@id'].split('#')[1]:x for x in g if x['@type']=='Place'}
O=nx.Graph(); O.add_nodes_from(PL)
for e in g:
    if e['@type']=='TravelAction':
        O.add_edge(e['from'][0]['@id'].split('#')[1], e['to'][0]['@id'].split('#')[1], d=e.get('dist') or 0)
cands={}
for k,p in PL.items():
    nm=norm(p.get('label','')).replace(' ','')
    if len(nm)<4: continue
    th=93 if len(nm)<=5 else 82
    res=process.extract(nm,texts,scorer=fuzz.ratio,score_cutoff=th,limit=40)
    if res: cands[k]=[(sc,phr[i]) for _,sc,i in res]
print('places with ocr candidates',len(cands))
# ---- road points for snapping
roads=json.load(open(f'{S}/roads.json'))
pts=[]
for r in roads:
    for a,b in zip(r,r[1:]):
        n=max(1,int(math.dist(a,b)/4))
        for t in range(n): pts.append((a[0]+(b[0]-a[0])*t/n, a[1]+(b[1]-a[1])*t/n))
RT=cKDTree(pts)
def station(p):
    q=(p['x']-4, p['y']+p['h']*0.6)
    d,j=RT.query(q)
    return (round(pts[j][0]),round(pts[j][1])) if d<30 else (round(p['x']),round(p['y']))
placed={OVID[n]:(x,y,'anchor',100) for n,(x,y) in PX.items()}
# longitude -> x sanity band from anchors
an=sorted((PL[OVID[n]]['lng'],x) for n,(x,y) in PX.items() if 'lng' in PL[OVID[n]])
def xband(lng): return np.interp(lng,[a for a,_ in an],[b for _,b in an])
changed=True; rnd=0
while changed:
    changed=False; rnd+=1
    for k,cs in cands.items():
        if k in placed or k not in O: continue
        lengths=nx.single_source_shortest_path_length(O,k,cutoff=4)
        nbrs=[(placed[n],h) for n,h in lengths.items() if n in placed and h>0]
        if not nbrs: continue
        best=None
        for sc,p in cs:
            sup=sum(1 for (x,y,_,_),h in nbrs if abs(x-p['x'])<260*h+150 and abs(y-p['y'])<700)
            if sup and (best is None or (sup,sc)>(best[0],best[1])): best=(sup,sc,p)
        if best:
            x,y=station(best[2]); placed[k]=(x,y,'ocr',best[1]); changed=True
    print('round',rnd,len(placed))
# strong unique matches not connected yet
for k,cs in cands.items():
    if k in placed: continue
    strong=[(sc,p) for sc,p in cs if sc>=90]
    nm=norm(PL[k].get('label','')).replace(' ','')
    if len(strong)==1 and len(nm)>=6 and 'lng' in PL[k] and abs(xband(PL[k]['lng'])-strong[0][1]['x'])<2500:
        x,y=station(strong[0][1]); placed[k]=(x,y,'ocr-unique',strong[0][0])
print('after unique',len(placed))
# rerun neighbour rounds with new seeds
changed=True
while changed:
    changed=False
    for k,cs in cands.items():
        if k in placed or k not in O: continue
        lengths=nx.single_source_shortest_path_length(O,k,cutoff=4)
        nbrs=[(placed[n],h) for n,h in lengths.items() if n in placed and h>0]
        best=None
        for sc,p in cs:
            sup=sum(1 for (x,y,_,_),h in nbrs if abs(x-p['x'])<260*h+150 and abs(y-p['y'])<700)
            if sup and (best is None or (sup,sc)>(best[0],best[1])): best=(sup,sc,p)
        if best: x,y=station(best[2]); placed[k]=(x,y,'ocr',best[1]); changed=True
print('ocr total',len(placed))
# ---- interpolate short gaps along OV chains between placed points (straight line)
added=1
while added:
    added=0
    for k in PL:
        if k in placed or k not in O: continue
        # find chain through k: walk both directions through unplaced degree-2 nodes
        if O.degree(k)!=2: continue
        ends=[]; 
        for start in O[k]:
            prev,cur,steps,dist=k,start,1,O[k][start]['d'] or 1
            while cur not in placed and O.degree(cur)==2 and steps<6:
                nxt=[n for n in O[cur] if n!=prev][0]; dist+=O[cur][nxt]['d'] or 1; prev,cur=cur,nxt; steps+=1
            ends.append((cur,dist) if cur in placed else None)
        if None in ends: continue
        (a,da),(b,db)=ends; A,B=placed[a],placed[b]
        if math.dist(A[:2],B[:2])>900: continue
        f=da/(da+db); x=A[0]+f*(B[0]-A[0]); y=A[1]+f*(B[1]-A[1])
        d,j=RT.query((x,y)); 
        if d<25: x,y=pts[j]
        placed[k]=(round(x),round(y),'interp',0); added+=1
from collections import Counter
print('final',len(placed),Counter(v[2] for v in placed.values()))
out=[dict(id=k,n=PL[k].get('label',k),m=PL[k].get('modern',''),lat=PL[k].get('lat'),lng=PL[k].get('lng'),x=v[0],y=v[1],c=v[2]) for k,v in placed.items()]
json.dump(out,open(f'{S}/stations.json','w'),ensure_ascii=False)
json.dump(dict(roads=roads,stations=[dict(n=o['n']+('*' if o['c']=='interp' else ''),x=o['x'],y=o['y']) for o in out]),open(f'{S}/viz_data.json','w'))
