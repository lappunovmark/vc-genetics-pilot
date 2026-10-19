import pandas as pd, numpy as np, gzip
D = 'data/genetic_support/data/'
a = pd.read_csv(D + 'assoc.tsv.gz', sep='\t', low_memory=False)
print('assoc rows', len(a)); print(a.columns.tolist())
src = a['source'] if 'source' in a else None
print(a.source.value_counts())
for s in a.source.unique():
    y = pd.to_numeric(a.loc[a.source == s, 'year'], errors='coerce')
    print(f'{s:12s} n={int((a.source==s).sum()):7d} year_nonnull={y.notna().mean():.3f} min={y.min()} max={y.max()}')
n = 0
with gzip.open(D + 'sim.tsv.gz', 'rt') as f:
    hdr = f.readline()
    for _ in f:
        n += 1
print('sim pairs', n, 'header', hdr.strip()[:200])
m = pd.read_csv(D + 'merge2.tsv.gz', sep='\t', low_memory=False, nrows=5)
print('merge2 cols', m.columns.tolist())
