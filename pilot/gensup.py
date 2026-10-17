"""Genetic support labelling, re-implemented from Minikel et al. (2024) definitions.
support(T, I) = exists association (gene T, trait A) with MeSH similarity(I, A) >= 0.8,
sources OMIM + GWAS (OTG with L2G share >= 0.5 and year 2005-2022, PICCOLO, Genebass).
ex-ante variant: only associations with year < cutoff year (OMIM handled by `omim_mode`)."""
import pandas as pd, numpy as np

def load(repo='/tmp/genetic_support/data'):
    assoc = pd.read_csv(f'{repo}/assoc.tsv.gz', sep='\t', low_memory=False)
    sim = pd.read_csv(f'{repo}/sim.tsv.gz', sep='\t')
    indic = pd.read_csv(f'{repo}/indic.tsv', sep='\t')
    return assoc, sim, indic

def filter_assoc(assoc, sources=('OMIM','OTG','PICCOLO','Genebass'), min_l2g=0.5):
    a = assoc[assoc.source.isin(sources)].copy()
    otg = a.source.eq('OTG')
    a = a[~otg | ((a.l2g_share >= min_l2g) & a.year.between(2005, 2022))]
    return a[['gene','mesh_id','source','year']].drop_duplicates()

def similar_pairs(sim, threshold=0.8):
    s = sim[sim.comb_norm >= threshold][['meshcode_a','meshcode_b']]
    s = pd.concat([s, s.rename(columns={'meshcode_a':'meshcode_b','meshcode_b':'meshcode_a'})])
    return s.drop_duplicates()

def label(ti, a, simpairs, year_col=None, omim_mode='always_ante'):
    """ti: DataFrame with gene, indication_mesh_id (+ optional year_col).
    Returns ti with gs_post (any support) and, if year_col, gs_ante."""
    # self-similarity: identical MeSH counts as similar
    selfp = pd.DataFrame({'meshcode_a': ti.indication_mesh_id.unique(), 'meshcode_b': ti.indication_mesh_id.unique()})
    sp = pd.concat([simpairs, selfp]).drop_duplicates()
    m = ti[['gene','indication_mesh_id'] + ([year_col] if year_col else [])].drop_duplicates() \
        .merge(sp, left_on='indication_mesh_id', right_on='meshcode_a') \
        .merge(a, left_on=['gene','meshcode_b'], right_on=['gene','mesh_id'])
    key = ['gene','indication_mesh_id']
    post = m[key].drop_duplicates().assign(gs_post=True)
    out = ti.merge(post, on=key, how='left')
    out['gs_post'] = out.gs_post.fillna(False).astype(bool)
    if year_col:
        k2 = key + [year_col]
        ok = (m.year < m[year_col]) | (m.year.isna() & m.source.eq('OMIM') & (omim_mode == 'always_ante'))
        ante = m[ok][k2].drop_duplicates().assign(gs_ante=True)
        out = out.merge(ante, on=k2, how='left')
        out['gs_ante'] = out.gs_ante.fillna(False).astype(bool)
    return out
