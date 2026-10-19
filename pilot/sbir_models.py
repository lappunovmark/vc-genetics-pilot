"""Does prior NIH SBIR/STTR funding of the sponsor go with genetically supported programmes, and with advancement?

Usage: python sbir_models.py RESULTS_DIR   (after build_panel26.py and sbir_link.py)
Sample: programmes and phase entries whose first (entry) trial was led by a non-top-20 industry sponsor.
sbir = the sponsor had an NIH SBIR/STTR award in a fiscal year before the trial's start year.
Writes RESULTS_DIR/sbir_models.txt.
"""
import sys
import numpy as np, pandas as pd
import statsmodels.formula.api as smf

R = sys.argv[1]
IND = ['Industry, large (>30)', 'Industry, mid (6-30)', 'Industry, small (<=5 drugs)']
MOD = {'Small molecule': 'small molecule', 'Antibody': 'antibody', 'Antibody drug conjugate': 'antibody', 'Protein': 'protein',
       'Enzyme': 'protein', 'Oligonucleotide': 'nucleic acid/gene/cell', 'Gene': 'nucleic acid/gene/cell', 'Cell': 'nucleic acid/gene/cell'}
s = pd.read_csv(f'{R}/sbir_trials.csv.gz')
s['trial'] = s.nct_id.str.lower()
sb = dict(zip(s.trial, s.sbir_before.fillna(False).astype(bool)))
out = []


def fit(f, d, title, keep):
    try:
        r = smf.logit(f, d).fit(disp=0, cov_type='cluster', cov_kwds={'groups': pd.factorize(d.drug)[0]})
        t = r.summary2().tables[1]
        t = t.loc[[i for i in t.index if i in keep], ['Coef.', 'Std.Err.', 'P>|z|', '[0.025', '0.975]']]
        t['OR'] = np.exp(t['Coef.']); t['OR_lo'] = np.exp(t['[0.025']); t['OR_hi'] = np.exp(t['0.975]'])
        out.extend(['=' * 100, title, f, f'N={int(r.nobs)}; clusters (drugs)={d.drug.nunique()}; sbir share={d.sbir.mean():.4f}',
                    t.round(4).to_string()])
    except Exception as e:
        out.extend(['=' * 100, title, f, f'failed: {e!r}'])


P = pd.read_csv(f'{R}/programmes.csv.gz')
P = P[P.insight & P.first_sponsor_tier.isin(IND)].copy()
P['sbir'] = P.first_trial.map(sb).fillna(False).astype(int)
P['tier'] = pd.Categorical(P.first_sponsor_tier, categories=IND)
P['modality'] = P.drugType.map(MOD).fillna('other'); P['area'] = P.area.fillna('other')
P['yb'] = pd.cut(P.first_year, [0, 2004, 2009, 2014, 2019, 2100]).astype(str)
out.append('Programmes (insight indications, first trial by non-top-20 industry): '
           + P.groupby('tier', observed=True).agg(n=('drug', 'size'), sbir=('sbir', 'mean'),
                                                  gs_ante=('gs_ante_first', 'mean')).round(4).to_string())
out.append(P.groupby('sbir').agg(n=('drug', 'size'), gs_ante=('gs_ante_first', 'mean'), gs_post=('gs_post', 'mean')).round(4).to_string())
P['y'] = P.gs_ante_first.fillna(False).astype(int)
fit('y ~ sbir + C(tier) + C(yb) + C(area) + C(modality)', P, 'H1: ex-ante support at first trial ~ prior SBIR/STTR', ('sbir',))

E = pd.read_csv(f'{R}/phase_entries.csv.gz')
end_year = int(E.entry_year.max())
E = E[E.insight & ~E.prior_higher & E.sponsor_tier.isin(IND) & E.entry_year.between(2000, end_year - 6)].copy()
E['sbir'] = E.entry_trial.map(sb).fillna(False).astype(int)
E['tier'] = pd.Categorical(E.sponsor_tier, categories=IND)
E['modality'] = E.drugType.map(MOD).fillna('other'); E['area'] = E.area.fillna('other')
E['yb'] = pd.cut(E.entry_year, [1999, 2005, 2010, 2015, 2030]).astype(str)
E['gs'] = E.gs_ante.fillna(False).astype(int); E['adv'] = E.advanced.astype(int)
out.append(E.groupby('sbir').agg(n=('drug', 'size'), adv=('adv', 'mean'), gs=('gs', 'mean')).round(4).to_string())
base = 'C(phase) + C(tier) + C(yb) + C(area) + C(modality)'
fit(f'adv ~ sbir + gs + {base}', E, 'Advancement ~ prior SBIR/STTR + ex-ante support', ('sbir', 'gs'))
fit(f'adv ~ sbir * gs + {base}', E, 'Advancement ~ prior SBIR/STTR x ex-ante support', ('sbir', 'gs', 'sbir:gs'))
open(f'{R}/sbir_models.txt', 'w').write('\n'.join(out))
print('\n'.join(out))
