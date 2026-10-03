"""Merge Vici links, Pleiades name matches and the verified identifier review -> ids_final.json
usage: merge_ids.py <scratch> <workflow_result.json>"""
import sys, json, csv, gzip, math, collections
S, res_fn = sys.argv[1], sys.argv[2]
PL = {}
with gzip.open(f'{S}/pleiades-places.csv.gz', 'rt') as f:
    for r in csv.DictReader(f):
        PL[r['id']] = dict(title=r['title'], prec=r['locationPrecision'] or 'unlocated',
                           ll=[round(float(r['reprLat']), 5), round(float(r['reprLong']), 5)] if r['reprLat'] else None)
g = json.load(open(f'{S}/ov.json'))['@graph']
OV = {x['@id'].split('#')[1]: x for x in g if x['@type'] == 'Place'}
def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    return 2 * 6371 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))

out = {}
for k, o in json.load(open(f'{S}/linked.json')).items():
    out[k] = dict(v=o['vici'][0], p=(o.get('pleiades') or [None])[0], w=(o.get('wikidata') or [None])[0],
                  l=(o.get('livius') or [None])[0], d=(o.get('dare') or [None])[0], vt=o.get('vtype'), src='vici', use='omnesviae')
for k, m in json.load(open(f'{S}/pmatch.json'))['auto'].items():
    out.setdefault(k, dict(src='name match', use='omnesviae'))['p'] = m['pid']

log = collections.Counter()
for r in json.load(open(res_fn)):
    kind = r['b']['kind']; sk = {c['id']: c['upheld'] for c in ((r.get('skeptic') or {}).get('checks') or [])}
    for d in r['dec']['decisions']:
        k, v = d['id'], d['verdict']; up = sk.get(k)
        if kind == 'review':
            if v == 'match' and d.get('pid') and up:
                e = out.setdefault(k, dict(src='reviewed match', use='omnesviae')); e['p'] = d['pid']
                if d.get('use_coords') == 'pleiades': e['use'] = 'pleiades'
                log['review match kept'] += 1
            else: log[f'review {v}{"" if up is None else " (skeptic " + ("upheld" if up else "refuted") + ")"}'] += 1
        elif kind == 'conflict':
            e = out[k]
            if up:
                if v == 'pleiades_correct': e['use'] = 'pleiades'
                elif v in ('ov_correct', 'wrong_link'):
                    # the linked Pleiades place is a different place: swap in the judge's id if it named a new one
                    e['p'] = d['pid'] if d.get('pid') and d['pid'] != e.get('p') else None; e['use'] = 'omnesviae'
            log[f'conflict {v} {"upheld" if up else "not upheld" if up is not None else ""}'] += 1
        elif kind == 'audit':
            if v == 'wrong' and up:
                out[k]['p'] = d.get('pid') or None; log['audit wrong -> fixed/removed'] += 1
            else: log[f'audit {v}'] += 1

# Pleiades' own citations of Talbert's database are authoritative where they exist
cite = json.load(open(f'{S}/pleiades_tp.json'))
for k, pids in cite.items():
    if k not in OV: continue
    pids = [p for p in pids if p in PL]
    if not pids: continue
    if 'lat' in OV[k] and len(pids) > 1:
        pids.sort(key=lambda p: km((OV[k]['lat'], OV[k]['lng']), PL[p]['ll']) if PL[p]['ll'] else 1e9)
    e = out.setdefault(k, dict(src='pleiades citation', use='omnesviae'))
    if e.get('p') and e['p'] not in pids:
        log['replaced by pleiades citation'] += 1; e['use'] = 'omnesviae'
    elif not e.get('p'): log['added from pleiades citation'] += 1
    else: log['confirmed by pleiades citation'] += 1
    if e.get('p') not in pids: e['p'] = pids[0]
    e['cited'] = True

# Vici records reached through the Pleiades id: fill missing Vici ids, and prefer a curated (visible) record
p2v = json.load(open(f'{S}/vici_by_pleiades.json'))
for k, e in out.items():
    recs = p2v.get(e.get('p') or '', {})
    if not recs: continue
    vis = sorted((v for v, r in recs.items() if r['vis']), key=int)
    best = vis[0] if vis else sorted(recs, key=int)[0]
    if not e.get('v') or (vis and e['v'] not in vis):
        log['vici via pleiades' if not e.get('v') else 'vici swapped to curated record'] += 1
        e['v'] = best
    r = recs.get(e['v'], {})
    if r.get('type') and not e.get('vt'): e['vt'] = r['type']
    if r.get('wd') and not e.get('w'): e['w'] = r['wd']

final = {}
for k, e in out.items():
    e = {a: b for a, b in e.items() if b is not None}
    p = PL.get(e.get('p'))
    if p:
        e['pt'] = p['title']; e['pprec'] = p['prec']
        if p['ll']: e['pll'] = p['ll']
        if 'lat' in OV.get(k, {}) and p['ll']: e['dkm'] = round(km((OV[k]['lat'], OV[k]['lng']), p['ll']), 1)
    final[k] = e
json.dump(final, open(f'{S}/ids_final.json', 'w'), ensure_ascii=False)
print(dict(log))
print('places with ids', len(final), 'pleiades', sum('p' in e for e in final.values()), 'vici', sum('v' in e for e in final.values()),
      'use pleiades coords', sum(e.get('use') == 'pleiades' for e in final.values()))
