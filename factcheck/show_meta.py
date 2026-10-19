import json
M = json.load(open('meta.json'))
for d, r in M.items():
    c = r.get('crossref')
    if not c:
        print('##', d, 'NO CROSSREF', r.get('crossref_status')); continue
    yr = None
    for k in ('published-print', 'issued', 'published-online', 'published'):
        if c.get(k) and c[k].get('date-parts'):
            yr = c[k]['date-parts'][0]; break
    au = '; '.join(f'{a[0]}, {a[1]}' for a in c['authors'][:8]) + (' ...' if len(c['authors']) > 8 else '')
    t = (c.get('title') or [''])[0]
    j = (c.get('container-title') or [''])[0]
    pr = c.get('published-print', {}) or {}
    po = c.get('published-online', {}) or {}
    print(f"## {d} | {au} | n_auth={len(c['authors'])}\n   {t}\n   {j} vol={c.get('volume')} iss={c.get('issue')} pages={c.get('page')} art={c.get('article-number')} "
          f"print={pr.get('date-parts')} online={po.get('date-parts')} issued={c.get('issued', {}).get('date-parts')} type={c.get('type')}")
    e = r.get('epmc')
    if e:
        print(f"   EPMC pmid={e.get('pmid')} pmcid={e.get('pmcid')} OA={e.get('isOpenAccess')}")
