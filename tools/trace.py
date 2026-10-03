import numpy as np, json, sys
from skimage.morphology import skeletonize, binary_closing, disk
from skimage.measure import label, regionprops, approximate_polygon
from scipy import ndimage as ndi
S=sys.argv[1]
m=np.load(f'{S}/red.npy')
m=binary_closing(m, disk(1))
lab=label(m, connectivity=2)
keep=np.zeros(lab.max()+1,bool)
for rp in regionprops(lab):
    h=rp.bbox[2]-rp.bbox[0]; w=rp.bbox[3]-rp.bbox[1]
    if max(h,w)>=70 and rp.area/(h*w) < 0.35: keep[rp.label]=True
m=keep[lab]
sk=skeletonize(m)
# neighbour count
nb=ndi.convolve(sk.astype(np.uint8), np.ones((3,3),np.uint8), mode='constant')-1
nb[~sk]=0
node=sk&(nb!=2)
ys,xs=np.nonzero(sk)
idx={}
# trace edges
visited=set()
H,W=sk.shape
def nbrs(y,x):
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            if (dy or dx) and 0<=y+dy<H and 0<=x+dx<W and sk[y+dy,x+dx]: yield (y+dy,x+dx)
paths=[]
nys,nxs=np.nonzero(node)
for y,x in zip(nys,nxs):
    for n in nbrs(y,x):
        if ((y,x),n) in visited: continue
        path=[(y,x),n]; visited.add(((y,x),n)); prev=(y,x); cur=n
        while not node[cur]:
            nxt=[q for q in nbrs(*cur) if q!=prev and q not in path[-3:]]
            if not nxt: break
            prev,cur=cur,nxt[0]; path.append(cur)
        visited.add((path[-1],path[-2]))
        if len(path)>=25: paths.append(path)
out=[]
for p in paths:
    a=np.array(p)[:,::-1].astype(float)  # x,y
    s=approximate_polygon(a, tolerance=2.5)
    out.append(s.round().astype(int).tolist())
json.dump(out, open(f'{S}/roads.json','w'))
print(len(out), sum(len(s) for s in out))
