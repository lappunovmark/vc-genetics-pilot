"""List supplementary / figure links on a publisher page. Usage: links.py URL [regex]"""
import re, sys, warnings
warnings.filterwarnings('ignore')
from bs4 import BeautifulSoup
from fetch_texts import get
u = sys.argv[1]
pat = re.compile(sys.argv[2] if len(sys.argv) > 2 else r'static-content|MediaObjects|\.pptx?|\.pdf|figures/|suppl', re.I)
r = get(u)
s = BeautifulSoup(r.content, 'lxml')
seen = set()
for a in s.find_all(['a', 'img', 'source', 'meta']):
    for attr in ('href', 'src', 'content', 'srcset'):
        v = a.get(attr)
        if v and pat.search(v) and v not in seen:
            seen.add(v)
            print(attr, v[:220], '|', (a.get_text(' ', strip=True) or a.get('alt') or '')[:80])
