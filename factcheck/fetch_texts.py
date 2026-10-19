"""Fetch full texts / abstracts of every cited source into texts/<key>.txt for personal fact-checking.
Sources: Europe PMC full-text XML (OA), Europe PMC + OpenAlex abstracts, OA PDFs, and a list of grey-literature URLs.
No personal data is sent; generic User-Agent.
"""
import json, os, re, sys, time, io
import requests
from bs4 import BeautifulSoup
import pypdf

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'}
os.makedirs('texts', exist_ok=True)
M = json.load(open('meta.json'))
log = open('fetch_texts.log', 'a')


def say(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True); log.write(s + '\n'); log.flush()


def key(doi):
    return re.sub(r'[^A-Za-z0-9]+', '_', doi)


def get(url, **kw):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=60, allow_redirects=True, **kw)
            if r.status_code == 429:
                time.sleep(5 * (i + 1)); continue
            return r
        except Exception as e:
            say('  ERR', url, repr(e)[:120]); time.sleep(3)
    return None


def pdf_text(b):
    try:
        rd = pypdf.PdfReader(io.BytesIO(b))
        return '\n'.join((p.extract_text() or '') for p in rd.pages)
    except Exception as e:
        return ''


def html_text(h):
    s = BeautifulSoup(h, 'lxml')
    for t in s(['script', 'style', 'nav', 'footer', 'header', 'noscript']):
        t.decompose()
    return re.sub(r'\n\s*\n+', '\n\n', s.get_text('\n'))


def save(name, txt, src):
    with open(f'texts/{name}.txt', 'w') as f:
        f.write(f'SOURCE: {src}\n\n{txt}')
    say('  saved', name, len(txt), src[:100])


def openalex(doi):
    r = get(f'https://api.openalex.org/works/doi:{doi}')
    if r is None or r.status_code != 200:
        return None, None
    j = r.json()
    ab = None
    inv = j.get('abstract_inverted_index')
    if inv:
        pos = {}
        for w, ps in inv.items():
            for p in ps:
                pos[p] = w
        ab = ' '.join(pos[i] for i in sorted(pos))
    urls = []
    for loc in [j.get('best_oa_location')] + (j.get('locations') or []):
        if loc and loc.get('pdf_url'):
            urls.append(loc['pdf_url'])
    return ab, urls


def main():
  only = set(sys.argv[1:])
  for doi, rec in M.items():
    k = key(doi)
    if only and k not in only and doi not in only:
        continue
    say('##', doi)
    e = rec.get('epmc') or {}
    parts = []
    if e.get('abstractText'):
        parts.append('ABSTRACT (Europe PMC):\n' + BeautifulSoup(e['abstractText'], 'lxml').get_text(' '))
    ab, pdfs = openalex(doi)
    if ab:
        parts.append('ABSTRACT (OpenAlex):\n' + ab)
    full = None
    if e.get('pmcid'):
        r = get(f'https://www.ebi.ac.uk/europepmc/webservices/rest/{e["pmcid"]}/fullTextXML')
        if r is not None and r.status_code == 200 and len(r.content) > 2000:
            s = BeautifulSoup(r.content, 'lxml-xml')
            full = ('EPMC fullTextXML ' + e['pmcid'], re.sub(r'\n\s*\n+', '\n\n', s.get_text('\n')))
    if full is None and pdfs:
        for u in pdfs[:3]:
            r = get(u)
            if r is not None and r.status_code == 200 and r.content[:4] == b'%PDF':
                t = pdf_text(r.content)
                if len(t) > 3000:
                    full = ('OA PDF ' + u, t); break
    if full:
        parts.append('FULL TEXT (' + full[0] + '):\n' + full[1])
    save(k, '\n\n'.join(parts) if parts else '(nothing retrieved)', doi)
    time.sleep(0.5)


if __name__ == '__main__':
    main()
