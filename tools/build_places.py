"""Build peutinger/places.json from OmnesViae + reviewed scan positions.
usage: build_places.py <scratch> <stations.json>"""
import sys, json, re
S, fn = sys.argv[1], sys.argv[2]
OUT = '/Users/sebhirsch/Documents/Misc/peutinger/places.json'
old = {p.get('k'): p for p in json.load(open(OUT))['places'] if p.get('k')}   # curated names + notes
cand = json.load(open(f'{S}/cand.json'))
OVID = {k: v[0][0] for k, v in cand.items()}; OVID['Babylonia'] = 'TPPlace2702'; OVID['Muziris'] = 'TPPlace2797'
cur = {OVID[k]: (k, p) for k, p in old.items()}
st = {s['id']: s for s in json.load(open(f'{S}/{fn}'))}
grid = json.load(open(f'{S}/talbert_grid.json'))['grid']
g = json.load(open(f'{S}/ov.json'))['@graph']
ids, out = {}, []
for p in g:
    if p['@type'] != 'Place': continue
    k = p['@id'].split('#')[1]; s = st.get(k)
    if 'lat' not in p and not s: continue
    o = dict(n=p.get('label', '').strip().strip("'").strip() or '(unnamed)')
    if p.get('modern'): o['m'] = p['modern']
    if 'lat' in p: o['ll'] = [round(p['lat'], 4), round(p['lng'], 4)]
    if s:
        o['xy'] = [s['x'], s['y']]; o['c'] = s.get('status', 0)
        if o['n'] == '(unnamed)' and o['c'] == 1: o['c'] = 2   # no label to confirm
    if k in grid: o['g'] = grid[k]
    if k in cur:
        name, prev = cur[k]; o['k'] = name; o['m'] = prev.get('m', o.get('m'))
        if prev.get('note'): o['note'] = prev['note']
    ids[k] = len(out); out.append(o)
roads = []
for e in g:
    if e['@type'] == 'TravelAction':
        a = e['from'][0]['@id'].split('#')[1]; b = e['to'][0]['@id'].split('#')[1]
        if a in ids and b in ids: roads.append([ids[a], ids[b], e.get('dist') or 0])
json.dump(dict(places=out, roads=roads), open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
from collections import Counter
print(len(out), 'places;', sum('xy' in o for o in out), 'on scan;', Counter(o.get('c') for o in out if 'xy' in o), len(roads), 'roads')
