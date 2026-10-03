"""Apply the 13-place workflow result: stations3.json -> stations4.json, m13_verdicts.json
status 4 = unnamed/illegible station placed from the road layout (no label to read)."""
import sys, json
S, res_fn = sys.argv[1], sys.argv[2]
st = {s['id']: s for s in json.load(open(f'{S}/stations3.json'))}
res = json.load(open(res_fn))
verdicts = {}
for r in res:
    found = {p['id']: p for p in r['found']['places']}
    ver = {v['id']: v for v in r['verify']['verdicts']}
    if r.get('retry') and r['retry'].get('verify'):
        f2 = {p['id']: p for p in r['retry']['found']['places']}
        for v in r['retry']['verify']['verdicts']:
            found[v['id']] = f2.get(v['id'], found.get(v['id'])); ver[v['id']] = v
    for k, v in ver.items():
        f = found.get(k)
        x = v.get('x', f['x'] if f else None); y = v.get('y', f['y'] if f else None)
        verdicts[k] = dict(verdict=v['verdict'], confidence=v['confidence'] if v['verdict'] == 'accept' else (f or {}).get('confidence', 'low'),
                           x=x, y=y, reason=v['reason'], evidence=(f or {}).get('evidence', ''))
for k, v in verdicts.items():
    s = st[k]
    if v['x'] is None: continue
    s['x'], s['y'] = int(v['x']), int(v['y'])
    named = bool(s['n'].strip().strip("'"))
    if v['verdict'] == 'accept':
        s['status'] = 1 if named else 4
    else:
        s['status'] = 2
    s['checked'] = v['verdict'] == 'accept'
    print(k, repr(s['n']), v['verdict'], v['confidence'], (s['x'], s['y']), '|', v['reason'][:90])
json.dump(list(st.values()), open(f'{S}/stations4.json', 'w'), ensure_ascii=False)
json.dump(verdicts, open(f'{S}/m13_verdicts.json', 'w'), ensure_ascii=False, indent=1)
