import pandas as pd
D = 'data/genetic_support/data/'
m = pd.read_csv(D + 'merge2.tsv.gz', sep='\t', low_memory=False)
s = m[(m.comb_norm >= 0.8) & m.assoc_source.notna()]
s = s[~((s.assoc_source == 'OTG') & (s.l2g_share < 0.5))]
for excl in (False, True):
    t = s[s.assoc_source != 'intOGen'] if excl else s
    g = t.groupby('ti_uid').assoc_source.agg(lambda x: set(x))
    omim_only = g.apply(lambda x: x == {'OMIM'})
    print(f'exclude intOGen={excl}: supported T-I pairs={len(g)}, OMIM-only={omim_only.sum()} ({omim_only.mean():.3f}), any OMIM={g.apply(lambda x: "OMIM" in x).mean():.3f}')
# analytic set: indications with genetic insight
try:
    pp = pd.read_csv(D + 'pp.tsv', sep='\t', low_memory=False)
    print('pp cols', [c for c in pp.columns][:40])
except Exception as e:
    print('pp', e)
