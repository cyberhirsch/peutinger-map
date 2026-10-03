"""Confidence rating (0-100 + reasons) for every place's position on the scan.
usage: confidence.py <scratch> <stations_final.json> [m13_result.json]
writes <scratch>/confidence.json  {id: {"s": score, "r": [reasons]}}"""
import sys, json, math, re, unicodedata
from rapidfuzz import fuzz
from scipy.spatial import cKDTree
import networkx as nx
S, fn = sys.argv[1], sys.argv[2]
sys.path.insert(0, S)
from grid import EDGES
ROWS = {'A': (330, 740), 'B': (740, 1165), 'C': (1165, 1620)}

def box(sq):
    seg, row, col = int(sq[:-2]), sq[-2], int(sq[-1]); a, b = EDGES[seg - 1], EDGES[seg]; w = (b - a) / 5
    return (a + (col - 1) * w, ROWS[row][0], a + col * w, ROWS[row][1])

def boxdist(x, y, sqs):
    best = 1e9
    for b in map(box, sqs):
        best = min(best, math.hypot(max(b[0] - x, 0, x - b[2]), max(b[1] - y, 0, y - b[3])))
    return best

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z]', '', s.translate(str.maketrans('ujfyk', 'visic')))

orig = {s['id']: s for s in json.load(open(f'{S}/stations2.json'))}     # method + OCR score
final = {s['id']: s for s in json.load(open(f'{S}/{fn}'))}
grid = json.load(open(f'{S}/talbert_grid.json'))['grid']
res = json.load(open(f'{S}/review_result.json'))
m13 = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}

# review path per place
path, note = {}, {}
for r in res:
    seg, rev, ver = r['seg'], r['review'], r['verify']
    L = json.load(open(f'{S}/review/seg{seg:02d}/legend.json')); by = {p['num']: p['id'] for p in L['places']}
    acc = {a['num'] for a in ver['accepted']}; okc = set(ver['ok_confirmed']); okr = {a['num']: a for a in ver['ok_refuted']}
    for n in rev['ok']:
        k = by[n]; est = orig[k]['c'] in ('interp', 'grid')
        path[k] = ('ok' if not est else 'ok-est-confirmed' if n in okc else
                   'ok-est-moved' if n in okr and okr[n].get('found') else 'ok-est-unconfirmed')
    for f in rev['fixes']:
        k = by[f['num']]; path[k] = 'fix-accepted' if f['num'] in acc else 'fix-rejected'; note[k] = f.get('note', '')
    for n in rev['not_found']: path[by[n]] = 'not-found'
# left-edge places outside every segment's crops, checked by hand on a contact sheet
for k in ('TPPlace80', 'TPPlace697', 'TPPlace550', 'TPPlace540'): path[k] = 'ok'

g = json.load(open(f'{S}/ov.json'))['@graph']
O = nx.Graph()
for e in g:
    if e['@type'] == 'TravelAction':
        O.add_edge(e['from'][0]['@id'].split('#')[1], e['to'][0]['@id'].split('#')[1])
P = list(final); T = cKDTree([(final[k]['x'], final[k]['y']) for k in P])
dups = {P[i] for pair in T.query_pairs(8) for i in pair}

out = {}
for k, s in final.items():
    o = orig.get(k, {}); method = o.get('c'); p = path.get(k); R = []
    if k in m13:
        v = m13[k]; acc = v['verdict'] == 'accept'; named = bool(s['n'].strip().strip("'"))
        if k == 'TPPlace1260':      # Portus: Talbert's unnamed symbol no. 34, the harbour drawing below Rome
            sc = 90 if acc else 30; R.append('unnamed symbol: placed on the harbour drawing')
        elif named:
            sc = {'high': 88, 'medium': 75, 'low': 55}[v['confidence']] if acc else 30
            R.append('faint label: found by comparing with the manuscript photo')
        else:
            sc = {'high': 75, 'medium': 60, 'low': 45}[v['confidence']] if acc else 30
            R.append('no readable label: placed from the road layout and the manuscript photo')
        R.append(f"checker {'accepted' if acc else 'rejected'} ({v['confidence']} confidence)")
    elif method == 'anchor' and p in ('ok', 'fix-accepted'):
        sc = 95; R += ['placed by hand', 'confirmed in visual review' if p == 'ok' else 'moved to its label in review, checked independently']
    elif p == 'ok':
        ocr = o.get('sc') or 0
        sc = 95 if ocr >= 95 else 92 if ocr >= 85 else 88   # audit: 18/18 low-match confirmations were right
        R += [f'name read on the scan (match {round(ocr)}%)', 'confirmed in visual review']
    elif p == 'fix-accepted':
        txt = norm(re.split(r'[.(]', note.get(k, ''))[0]); ratio = fuzz.partial_ratio(norm(s['n']), txt) if txt else 0
        sc = 93 if ratio >= 80 else 86 if ratio >= 55 else 76
        R += ['label found in visual review, checked independently']
        if ratio < 55: R.append(f"spelling on Miller's copy differs from Talbert's reading ({note.get(k, '')[:40]})")
    elif p == 'ok-est-confirmed':
        sc = 85; R += ['estimated position confirmed by reviewer and checker']
    elif p == 'ok-est-moved':
        sc = 82; R += ['moved to its label by the checker']
    elif s.get('status') == 2:
        sc = 30; R += ['label not found: estimated along the road between neighbours']
    else:
        sc = 15; R += ['label not found: somewhere in its grid square']
    sq = grid.get(k)
    if sq:
        d = boxdist(s['x'], s['y'], sq)
        if d == 0: R.append(f"inside Talbert grid square {', '.join(sq)}")
        elif d <= 90: sc -= 3; R.append(f"just outside Talbert grid square {', '.join(sq)} (sheet edges are fuzzy)")
        else: sc -= 15; R.append(f"{round(d)} px outside Talbert grid square {', '.join(sq)}")
    nb = [final[n] for n in (O[k] if k in O else []) if n in final]
    if nb:
        dmin = min(math.dist((s['x'], s['y']), (t['x'], t['y'])) for t in nb)
        if dmin > 900: sc -= 10; R.append(f'far from its road neighbours ({round(dmin)} px)')
    if k in dups: sc -= 10; R.append('shares its spot with another place')
    out[k] = dict(s=max(5, min(99, sc)), r=R)
json.dump(out, open(f'{S}/confidence.json', 'w'), ensure_ascii=False)
from collections import Counter
band = lambda v: 'high' if v >= 85 else 'medium' if v >= 65 else 'low' if v >= 40 else 'very low'
print(Counter(band(v['s']) for v in out.values()))
