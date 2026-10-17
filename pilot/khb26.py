"""H2 pilot: how much of the sponsor-tier gap in advancement runs through ex-ante genetic support?
Karlson-Holm-Breen decomposition for logit (Karlson, Holm and Breen, 2012): the reduced model replaces the mediator
by its residual from a linear regression on tier and controls, so both models share one scale.
Usage: python khb26.py RESULTS_DIR [SUPPORT_COLUMN] [ENTRIES_FILE]
"""
import sys, numpy as np, pandas as pd
import statsmodels.formula.api as smf

R = sys.argv[1]
col = sys.argv[2] if len(sys.argv) > 2 else 'gs_ante'
E = pd.read_csv(f'{R}/' + (sys.argv[3] if len(sys.argv) > 3 else 'phase_entries.csv.gz'))
TIERS = ['Top-20 pharma', 'Industry, large (>30)', 'Industry, mid (6-30)', 'Industry, small (<=5 drugs)', 'Academic/other', 'Government']
MOD = {'Small molecule': 'small molecule', 'Antibody': 'antibody', 'Antibody drug conjugate': 'antibody', 'Protein': 'protein',
       'Enzyme': 'protein', 'Oligonucleotide': 'nucleic acid/gene/cell', 'Gene': 'nucleic acid/gene/cell', 'Cell': 'nucleic acid/gene/cell'}
end_year = int(E.entry_year.max())
T = E[E.insight & ~E.prior_higher & E.sponsor_tier.isin(TIERS) & E.entry_year.between(2000, end_year - 6)].copy()
T['tier'] = pd.Categorical(T.sponsor_tier, categories=TIERS)
T['modality'] = T.drugType.map(MOD).fillna('other'); T['area'] = T.area.fillna('other')
T['yb'] = pd.cut(T.entry_year, [1999, 2005, 2010, 2015, 2030]).astype(str)
T['adv'] = T.advanced.astype(int); T['gs'] = T[col].fillna(False).astype(int)
ctrl = 'C(phase) + C(yb) + C(area) + C(modality)'
T['gs_res'] = smf.ols(f'gs ~ C(tier) + {ctrl}', T).fit().resid
g = pd.factorize(T.drug)[0]
fit = lambda f: smf.logit(f, T).fit(disp=0, cov_type='cluster', cov_kwds={'groups': g})
full = fit(f'adv ~ C(tier) + gs + {ctrl}')
red = fit(f'adv ~ C(tier) + gs_res + {ctrl}')
naive = fit(f'adv ~ C(tier) + {ctrl}')
rows = []
for t in TIERS[1:]:
    k = f'C(tier)[T.{t}]'
    tot, direct = red.params[k], full.params[k]
    rows.append({'tier vs top-20': t, 'total (KHB reduced)': tot, 'direct (full)': direct, 'indirect via support': tot - direct,
                 'share mediated %': 100 * (tot - direct) / tot if tot else np.nan, 'naive (no support)': naive.params[k],
                 'support share in tier': T.loc[T.tier == t, 'gs'].mean()})
out = pd.DataFrame(rows)
print(f'support column: {col}; N = {int(full.nobs)}; support share top-20 = {T.loc[T.tier == TIERS[0], "gs"].mean():.4f}')
print(out.round(4).to_string(index=False))
