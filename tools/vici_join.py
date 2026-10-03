"""Join Vici (via SPARQL results) and Pleiades (bulk CSV) to OmnesViae TPPlace ids -> linked.json"""
import json, csv, gzip, math, collections, re, sys
S = sys.argv[1]
links = collections.defaultdict(lambda: collections.defaultdict(set))
for r in json.load(open(f'{S}/vici_tp.json'))['results']['bindings']:
    k = r['tp']['value'].split('#')[1]; links[k]['vici'].add(r['s']['value'].rsplit('/', 1)[1])
    if 'm' in r:
        m = r['m']['value'].rstrip('/')
        if 'pleiades' in m: links[k]['pleiades'].add(m.rsplit('/', 1)[1])
        elif 'wikidata' in m: links[k]['wikidata'].add(m.rsplit('/', 1)[1])
        elif 'livius' in m: links[k]['livius'].add(m.split('/place/')[1] if '/place/' in m else m)
        elif 'dare' in m: links[k]['dare'].add(m.rsplit('/', 1)[1])
det = collections.defaultdict(dict)
for r in json.load(open(f'{S}/vici_detail.json'))['results']['bindings']:
    k = r['tp']['value'].split('#')[1]; vid = r['s']['value'].rsplit('/', 1)[1]
    d = det[k].setdefault(vid, dict(vis=int(r['vis']['value']), types=set(), temporal=set()))
    if 'wkt' in r:
        xy = re.findall(r'(-?\d+\.?\d*)\s+(-?\d+\.?\d*)', r['wkt']['value'])
        if xy: d['ll'] = [float(xy[0][1]), float(xy[0][0])]
    if 'typeLabel' in r: d['types'].add(r['typeLabel']['value'])
    if 'temporal' in r: d['temporal'].add(r['temporal']['value'])
PL = {}
with gzip.open(f'{S}/pleiades-places.csv.gz', 'rt') as f:
    for row in csv.DictReader(f): PL[row['id']] = row
g = json.load(open(f'{S}/ov.json'))['@graph']
OV = {x['@id'].split('#')[1]: x for x in g if x['@type'] == 'Place'}
def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    return 2 * 6371 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
out = {}; stats = collections.Counter(); far = []
for k, L in links.items():
    o = dict(vici=sorted(L['vici'], key=lambda v: -det[k].get(v, {}).get('vis', 0)))
    for key in ('pleiades', 'wikidata', 'livius', 'dare'):
        if L[key]: o[key] = sorted(L[key])
    vd = det[k].get(o['vici'][0], {})
    if vd.get('types'): o['vtype'] = sorted(vd['types'])[0]
    if vd.get('temporal'): o['vtime'] = sorted(vd['temporal'])[0]
    p = [PL[i] for i in o.get('pleiades', []) if i in PL]
    if p:
        p0 = p[0]; o['ptitle'] = p0['title']; o['pprec'] = p0['locationPrecision'] or 'unlocated'
        if p0['reprLat']: o['pll'] = [round(float(p0['reprLat']), 5), round(float(p0['reprLong']), 5)]
        stats['pleiades ' + o['pprec']] += 1
    ov = OV.get(k, {})
    if 'lat' in ov and 'pll' in o:
        d = km((ov['lat'], ov['lng']), o['pll']); o['dkm'] = round(d, 1)
        stats['ov-pleiades <5km'] += d < 5; stats['5-25km'] += 5 <= d < 25; stats['>=25km'] += d >= 25
        if d >= 25: far.append((k, ov.get('label'), ov.get('modern'), o['ptitle'], round(d)))
    if 'lat' not in ov and 'pll' in o: stats['fills missing coords'] += 1
    out[k] = o
json.dump(out, open(f'{S}/linked.json', 'w'), ensure_ascii=False)
json.dump(far, open(f'{S}/far.json', 'w'), ensure_ascii=False)
print(len(out), dict(stats)); print('far examples', far[:15])
