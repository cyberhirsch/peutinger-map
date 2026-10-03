"""Route every Table connection along the Itiner-e road network -> routes.json

For each road [a, b, dist] in places.json: snap both places to the nearest Itiner-e vertex,
take the shortest path along the network, and store the simplified line, its length (km),
the straight-line distance (km) and the mix of Itiner-e certainty along the way.

Itiner-e static version 2024 (de Soto et al. 2025, doi:10.5281/zenodo.17122148), CC BY 4.0.
Usage: python itinere_routes.py <itinere_roads.geojson> <places.json> <routes.json>
"""
import json, math, sys
from collections import defaultdict
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

SRC, PLACES, OUT = sys.argv[1:4]
A, E = 6378137.0, 0.0818191908426
R = 6371.0088
SNAP_MAX = 10.0        # km: a place farther than this from any Itiner-e road is off the network
JOIN = 0.15            # km: line ends within this of another line's vertex are joined to it
CERT = {'Certain': 0, 'Conjectured': 1, 'Hypothetical': 2}


def unproject(x, y):
    """EPSG:3395 (ellipsoidal World Mercator) -> lat, lon in degrees"""
    lon = np.degrees(x / A)
    t = np.exp(-y / A)
    phi = np.pi / 2 - 2 * np.arctan(t)
    for _ in range(6):
        es = E * np.sin(phi)
        phi = np.pi / 2 - 2 * np.arctan(t * ((1 - es) / (1 + es)) ** (E / 2))
    return np.degrees(phi), lon


def xyz(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], -1)


def chord_km(c):  # chord length on the unit sphere -> great-circle km
    return 2 * R * np.arcsin(np.clip(c / 2, 0, 1))


def hav(p, q):
    la1, lo1, la2, lo2 = map(math.radians, (p[0], p[1], q[0], q[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def simplify(pts, tol):
    """Douglas-Peucker on lat/lon, tolerance in km (local equirectangular)"""
    if len(pts) < 3: return pts
    P = np.array(pts); k = math.cos(math.radians(P[:, 0].mean()))
    Q = np.c_[P[:, 0] * 111.2, P[:, 1] * 111.2 * k]
    keep = np.zeros(len(P), bool); keep[[0, -1]] = True; st = [(0, len(P) - 1)]
    while st:
        i, j = st.pop()
        if j <= i + 1: continue
        d = Q[j] - Q[i]; n = np.hypot(*d)
        seg = Q[i + 1:j] - Q[i]
        dist = np.abs(seg[:, 0] * d[1] - seg[:, 1] * d[0]) / n if n else np.hypot(seg[:, 0], seg[:, 1])
        m = int(dist.argmax())
        if dist[m] > tol: keep[i + 1 + m] = True; st += [(i, i + 1 + m), (i + 1 + m, j)]
    return [pts[i] for i in np.flatnonzero(keep)]


def encode(pts):
    """Google encoded polyline, precision 5"""
    out, pl, pn = [], 0, 0
    for la, lo in pts:
        a, b = round(la * 1e5), round(lo * 1e5)
        for v in (a - pl, b - pn):
            v = ~(v << 1) if v < 0 else v << 1
            while v >= 0x20: out.append(chr((0x20 | (v & 0x1f)) + 63)); v >>= 5
            out.append(chr(v + 63))
        pl, pn = a, b
    return ''.join(out)


# --- network: every vertex is a node, consecutive vertices are edges
feats = json.load(open(SRC, encoding='utf-8'))['features']
lines, fcert, fid = [], [], []
for i, f in enumerate(feats):
    for part in f['geometry']['coordinates']:
        c = np.array(part)[:, :2]
        if len(c) >= 2:
            lines.append(c); fcert.append(CERT.get(f['properties'].get('Segment_s'), 1)); fid.append(i)
allxy = np.concatenate(lines)
lat, lon = unproject(allxy[:, 0], allxy[:, 1])
P3 = xyz(lat, lon)

# merge coincident vertices (rounded to ~1 m)
key = np.round(P3 * R * 1000).astype(np.int64)
_, node, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
inv = inv.ravel()
N = len(node); NLAT, NLON, N3 = lat[node], lon[node], P3[node]
print(len(feats), 'features', len(lines), 'lines', len(allxy), 'vertices ->', N, 'nodes')

src, dst, w, ecert = [], [], [], []
off = 0
ends = []
for c, cert in zip(lines, fcert):
    ids = inv[off:off + len(c)]; off += len(c)
    a, b = ids[:-1], ids[1:]
    src.append(a); dst.append(b); w.append(chord_km(np.linalg.norm(N3[a] - N3[b], axis=1))); ecert.append(np.full(len(a), cert))
    ends += [ids[0], ids[-1]]
src, dst, w, ecert = map(np.concatenate, (src, dst, w, ecert))

# join loose line ends to the nearest vertex of another line (T-junctions, small digitising gaps)
tree = cKDTree(N3)
ends = np.unique(ends)
d, j = tree.query(N3[ends], k=8)
J = [(e, t, chord_km(dist)) for e, dd, jj in zip(ends, d, j) for dist, t in zip(dd[1:], jj[1:]) if chord_km(dist) <= JOIN]
if J:
    je, jt, jw = map(np.array, zip(*J))
    src, dst, w, ecert = np.r_[src, je], np.r_[dst, jt], np.r_[w, jw], np.r_[ecert, np.ones(len(J), int)]
print('joined', len(J), 'line-end links')

keep = src != dst
src, dst, w, ecert = src[keep], dst[keep], np.maximum(w[keep], 1e-6), ecert[keep]
# deduplicate parallel edges by keeping the shortest
order = np.lexsort((np.r_[w, w], np.r_[dst, src], np.r_[src, dst]))
S, D, W, C = np.r_[src, dst][order], np.r_[dst, src][order], np.r_[w, w][order], np.r_[ecert, ecert][order]
first = np.r_[True, (S[1:] != S[:-1]) | (D[1:] != D[:-1])]
S, D, W, C = S[first], D[first], W[first], C[first]
# --- places become extra nodes, linked to a few nearby road vertices (lets the route pick the right road)
data = json.load(open(PLACES, encoding='utf-8'))
places, roads = data['places'], data['roads']
pn, pv, pw = [], [], []
for i, p in enumerate(places):
    if not p.get('ll'): continue
    dd, tt = tree.query(xyz(*p['ll']), k=40)
    km = chord_km(dd)
    if km[0] > SNAP_MAX: continue
    seen = set()
    for k, t in zip(km, tt):
        if k > max(km[0] * 1.5, km[0] + 2): break
        if t in seen: continue
        seen.add(t); pn.append(N + i); pv.append(t); pw.append(max(k, 1e-6))
    if len(seen) == 0: pn.append(N + i); pv.append(tt[0]); pw.append(max(km[0], 1e-6))
on_net = set(pn)
S, D = np.r_[S, pn, pv], np.r_[D, pv, pn]
W, C = np.r_[W, pw, pw], np.r_[C, np.full(2 * len(pn), 3)]
M = N + len(places)
G = coo_matrix((W, (S, D)), shape=(M, M)).tocsr()
EC = {(int(s), int(t)): int(c) for s, t, c in zip(S, D, C)}
print(len(on_net), 'places within', SNAP_MAX, 'km of an Itiner-e road')

# --- units: Gallic leagues in Gaul north of Narbonensis and in the Germanies, Roman miles elsewhere
MILE, LEAGUE = 1.48, 2.22
GAUL = [(43.3, -1.9), (43.1, 0.6), (43.9, 1.1), (44.6, 2.4), (45.2, 3.7), (45.7, 4.6), (45.9, 5.6),
        (46.3, 6.1), (46.8, 7.0), (47.6, 7.6), (49.0, 8.3), (50.0, 8.4), (50.8, 7.2), (51.9, 6.4),
        (53.5, 6.6), (53.5, 4.0), (51.2, 1.6), (50.0, 1.2), (49.7, -2.0), (48.6, -5.5), (47.0, -3.0), (45.0, -1.5)]


def inside(pt, poly):
    y, x = pt; c = False
    for (y1, x1), (y2, x2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1): c = not c
    return c


routes = [None] * len(roads)
by_src = defaultdict(list)
for r, (a, b, d) in enumerate(roads):
    la, lb = places[a].get('ll'), places[b].get('ll')
    if not (la and lb): continue
    mid = ((la[0] + lb[0]) / 2, (la[1] + lb[1]) / 2)
    unit = 'league' if inside(mid, GAUL) else 'mile'
    routes[r] = x = dict(sk=round(hav(la, lb), 1), u=unit[0])
    if mid[1] > 39: x['uq'] = 1  # beyond the Euphrates the Table's unit is uncertain
    if d: x['rk'] = round(d * (LEAGUE if unit == 'league' else MILE), 1)
    if N + a in on_net and N + b in on_net: by_src[a].append(r)

for a, rs in by_src.items():
    lim = max(max(routes[r]['sk'] for r in rs) * 4 + 50, 100)
    dist, pred = dijkstra(G, indices=N + a, return_predecessors=True, limit=lim)
    for r in rs:
        b = roads[r][0] if roads[r][1] == a else roads[r][1]
        if not np.isfinite(dist[N + b]): continue
        path = [N + b]
        while path[-1] != N + a: path.append(int(pred[path[-1]]))
        path.reverse()
        mix = [0.0] * 4
        for u, v in zip(path[:-1], path[1:]): mix[EC[(u, v)]] += G[u, v]
        tot = sum(mix) or 1
        ll = [tuple(places[n - N]['ll']) if n >= N else (float(NLAT[n]), float(NLON[n])) for n in path]
        # 2-bit confidence per vertex, for the segment that starts there (the last vertex repeats the one before):
        # 3 certain, 2 conjectured, 1 hypothetical, 0 off-road. Each run is simplified on its own so the switches survive.
        lvl = [3 - EC[(u, v)] for u, v in zip(path[:-1], path[1:])]
        pts, cs, i = [], [], 0
        while i < len(lvl):
            j = i
            while j < len(lvl) and lvl[j] == lvl[i]: j += 1
            run = simplify(ll[i:j + 1], 0.1)
            if pts: cs[-1] = lvl[i]; run = run[1:]  # the shared vertex starts this run's segment
            pts += run; cs += [lvl[i]] * len(run)
            i = j
        cs[-1] = cs[-2]
        x = routes[r]
        x.update(km=round(float(dist[N + b]), 1), cert=[round(m / tot, 2) for m in mix],
                 g=encode([(round(p, 5), round(q, 5)) for p, q in pts]), c=''.join(map(str, cs)))
        if roads[r][1] == a: x['rev'] = 1  # geometry runs b -> a
        if x['km'] > 2 * x['sk'] + 10: x['dt'] = 1  # long detour: probably a gap in Itiner-e or a sea crossing

json.dump(dict(source='Itiner-e static version 2024, doi:10.5281/zenodo.17122148, CC BY 4.0', routes=routes),
          open(OUT, 'w', encoding='utf-8'), separators=(',', ':'))
print(len(roads), 'roads;', sum(1 for x in routes if x and 'km' in x), 'routed on Itiner-e;',
      sum(1 for x in routes if x and 'km' not in x), 'straight line only;', sum(1 for x in routes if not x), 'no coordinates')
