import json, time, urllib.parse, requests, sys
UA = {'User-Agent': 'vc-genetics-thesis-factcheck/1.0 (UCL MSc dissertation)'}
dois = json.load(open('dois.json'))
out = {}
for d in dois:
    rec = {'doi': d}
    try:
        r = requests.get('https://api.crossref.org/works/' + urllib.parse.quote(d), headers=UA, timeout=30)
        if r.ok:
            m = r.json()['message']
            rec['crossref'] = {k: m.get(k) for k in ['title', 'container-title', 'volume', 'issue', 'page', 'article-number',
                                                     'published', 'published-print', 'published-online', 'issued', 'type', 'publisher']}
            rec['crossref']['authors'] = [(a.get('family'), a.get('given')) for a in m.get('author', [])]
        else:
            rec['crossref_status'] = r.status_code
    except Exception as e:
        rec['crossref_err'] = repr(e)
    try:
        q = 'DOI:"%s"' % d
        r = requests.get('https://www.ebi.ac.uk/europepmc/webservices/rest/search',
                         params={'query': q, 'format': 'json', 'resultType': 'core'}, headers=UA, timeout=30)
        if r.ok and r.json().get('resultList', {}).get('result'):
            x = r.json()['resultList']['result'][0]
            rec['epmc'] = {k: x.get(k) for k in ['pmid', 'pmcid', 'isOpenAccess', 'inEPMC', 'abstractText', 'journalInfo', 'pubYear', 'source', 'id']}
    except Exception as e:
        rec['epmc_err'] = repr(e)
    out[d] = rec
    time.sleep(0.3)
    print(d, 'crossref' in rec, 'epmc' in rec, flush=True)
json.dump(out, open('meta.json', 'w'), indent=1)
