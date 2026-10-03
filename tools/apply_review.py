"""Apply the verified review to stations2.json -> stations3.json
usage: apply_review.py <scratch> <workflow_result.json>
Status codes: 0 hand-placed, 1 label located and checked, 2 estimated along road, 3 grid square only."""
import sys, json, math
from collections import Counter
from scipy.spatial import cKDTree
S, res_fn = sys.argv[1], sys.argv[2]
st = {s['id']: s for s in json.load(open(f'{S}/stations2.json'))}
results = json.load(open(res_fn))
roads = json.load(open(f'{S}/roads.json'))
pts = []
for r in roads:
    for a, b in zip(r, r[1:]):
        n = max(1, int(math.dist(a, b) / 4))
        for t in range(n): pts.append((a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n))
RT = cKDTree(pts)

def snap(x, y):
    # keep the reviewer's label-start position: snapping to the road collapsed stacked labels onto one point
    return (round(x), round(y))

BASE = {'anchor': 0, 'ocr-grid': 1, 'ocr': 1, 'interp': 2, 'grid': 3}
for s in st.values(): s['status'] = BASE[s['c']]; s['checked'] = False
log = Counter()
for r in results:
    seg, rev, ver = r['seg'], r['review'], r.get('verify') or {}
    L = json.load(open(f'{S}/review/seg{seg:02d}/legend.json'))
    by = {p['num']: p['id'] for p in L['places']}
    method = {p['num']: p['method'] for p in L['places']}
    est = lambda n: method.get(n) in ('interp', 'grid')
    acc = {a['num']: a for a in ver.get('accepted', [])}
    ok_conf = set(ver.get('ok_confirmed', []))
    ok_ref = {a['num']: a for a in ver.get('ok_refuted', [])}
    for n in rev['ok']:
        s = st[by[n]]
        if not est(n):
            s['checked'] = True; log['ok green'] += 1
        elif n in ok_conf:
            s['status'] = 1; s['checked'] = True; log['ok estimate confirmed'] += 1
        elif n in ok_ref and ok_ref[n].get('found') and 'x' in ok_ref[n]:
            s['x'], s['y'] = snap(ok_ref[n]['x'], ok_ref[n]['y']); s['status'] = 1; s['checked'] = True; log['ok estimate moved by verifier'] += 1
        else:
            log['ok estimate not confirmed'] += 1
    for f in rev['fixes']:
        s = st[by[f['num']]]
        if f['num'] in acc:
            a = acc[f['num']]; s['x'], s['y'] = snap(a['x'], a['y']); s['status'] = 1; s['checked'] = True; log['fix accepted'] += 1
        else:
            if s['status'] == 1: s['status'] = 2   # disputed OCR match -> approximate
            log['fix rejected'] += 1
    for n in rev['not_found']:
        s = st[by[n]]
        if s['status'] == 1: s['status'] = 2; log['green not found -> approx'] += 1
        else: log['estimate not found'] += 1
# duplicate positions (two places on one label)
P = [(s['x'], s['y']) for s in st.values()]; ids = list(st)
dup = [(ids[i], ids[j]) for i, j in cKDTree(P).query_pairs(8)]
print(dict(log)); print('status', Counter(s['status'] for s in st.values()), 'checked', sum(s['checked'] for s in st.values()))
print('near-duplicate pairs', len(dup), [(st[a]['n'], st[b]['n']) for a, b in dup[:15]])
json.dump(list(st.values()), open(f'{S}/stations3.json', 'w'), ensure_ascii=False)
