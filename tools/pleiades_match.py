"""Candidate Pleiades matches for Table places that Vici doesn't link -> pmatch.json"""
import json, csv, gzip, math, re, unicodedata, collections, sys
from rapidfuzz import fuzz
from scipy.spatial import cKDTree
import numpy as np
S = sys.argv[1]
def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = s.translate(str.maketrans('ujyk', 'viic'))
    s = re.sub(r'\b(ad|fl|flumen|fluvius|ins|insula|mons|portus)\b', ' ', s)
    return re.sub(r'[^a-z]', '', s)
PL = {}
with gzip.open(f'{S}/pleiades-places.csv.gz', 'rt') as f:
    for r in csv.DictReader(f):
        if r['reprLat']: PL[r['id']] = dict(title=r['title'], ll=(float(r['reprLat']), float(r['reprLong'])), prec=r['locationPrecision'], names={norm(r['title'])})
with gzip.open(f'{S}/pleiades-names.csv.gz', 'rt') as f:
    for r in csv.DictReader(f):
        pid = r['pid'].rsplit('/', 1)[-1]
        if pid in PL:
            for n in (r['nameAttested'], r['nameTransliterated'], r['title']):
                if n: PL[pid]['names'].add(norm(n))
ids = list(PL); T = cKDTree(np.radians([PL[i]['ll'] for i in ids]))
linked = json.load(open(f'{S}/linked.json'))
onscan = {s['id'] for s in json.load(open(f'{S}/stations4.json'))}
g = json.load(open(f'{S}/ov.json'))['@graph']
OV = {x['@id'].split('#')[1]: x for x in g if x['@type'] == 'Place'}
def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    return 2 * 6371 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
auto, review, none = {}, [], 0
for k, p in OV.items():
    if k in linked or 'lat' not in p: continue
    nm = norm(p.get('label', '')); mod = norm((p.get('modern') or '').split('~')[0])
    if len(nm) < 3: continue
    cand = []
    for j in T.query_ball_point(np.radians([p['lat'], p['lng']]), 30 / 6371):
        q = PL[ids[j]]; sim = max([fuzz.ratio(nm, n) for n in q['names'] if n] or [0])
        d = km((p['lat'], p['lng']), q['ll'])
        if sim >= 70: cand.append(dict(pid=ids[j], title=q['title'], sim=round(sim), km=round(d, 1), prec=q['prec']))
    cand.sort(key=lambda c: (-c['sim'], c['km']))
    if not cand: none += 1; continue
    best = cand[0]; second = cand[1] if len(cand) > 1 else None
    clear = best['sim'] >= 88 and best['km'] <= 8 and (not second or second['sim'] < best['sim'] - 8 or second['pid'] == best['pid'])
    rec = dict(id=k, label=p.get('label'), modern=p.get('modern', ''), ll=[p['lat'], p['lng']], onscan=k in onscan, candidates=cand[:4])
    if clear: auto[k] = best
    else: review.append(rec)
json.dump(dict(auto=auto, review=review), open(f'{S}/pmatch.json', 'w'), ensure_ascii=False, indent=0)
print('auto', len(auto), 'review', len(review), 'no candidate', none)
print([ (OV[k]['label'], v['title'], v['sim'], v['km']) for k, v in list(auto.items())[:8]])
print([(r['label'], r['modern'], [(c['title'], c['sim'], c['km']) for c in r['candidates'][:2]]) for r in review[:6]])
