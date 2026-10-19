"""H4, second part: were industry trials stopped for financial or strategic reasons as genetically well supported as
completed ones?

Usage: python h4_biology.py OT_DIR RESULTS_DIR CTGOV_ALL_CSV MINIKEL_DATA_DIR
Unit: an industry Phase 1-3 drug trial on ClinicalTrials.gov that Open Targets links to at least one drug x MeSH
indication with genetic insight, started 2000-2024, with a terminal status (completed, or terminated/withdrawn/
suspended). Support = any linked programme whose target gene has an association with a similar trait
(Minikel definition, MeSH similarity >= 0.8) dated before the trial's start year (OMIM counted as ex ante; a no-OMIM
variant is reported). Stop reasons use the v3 classifier (stopreasons.py); sponsor groups follow rq2_stops.py.
Writes RESULTS_DIR/h4_trials.csv.gz and RESULTS_DIR/h4_biology.txt.
"""
import glob, os, sys
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gensup, rq2_stops, stopreasons

OUT = ['Completed', 'Stopped: financial or strategic', 'Stopped: efficacy', 'Stopped: safety', 'Stopped: enrolment',
       'Stopped: other or no reason']
MOD = {'Small molecule': 'small molecule', 'Antibody': 'antibody', 'Antibody drug conjugate': 'antibody',
       'Protein': 'protein', 'Enzyme': 'protein', 'Oligonucleotide': 'nucleic acid/gene/cell', 'Gene': 'nucleic acid/gene/cell',
       'Cell': 'nucleic acid/gene/cell'}


def read(d, cols):
    return pd.concat([pd.read_parquet(f, columns=cols) for f in sorted(glob.glob(f'{d}/*.parquet'))], ignore_index=True)


def phase_num(p):
    p = p if isinstance(p, str) else ''
    return 3 if 'PHASE3' in p else 2 if 'PHASE2' in p else 1 if 'PHASE1' in p else np.nan


def outcome(r):
    if r.status == 'COMPLETED':
        return 'Completed'
    if not r.stopped:
        return None
    if r.reason in stopreasons.FINANCIAL:
        return OUT[1]
    return {'Efficacy / futility': OUT[2], 'Safety / benefit-risk': OUT[3], 'Enrolment': OUT[4]}.get(r.reason, OUT[5])


def build(ot, R, ctg, mdir):
    ev = read(f'{ot}/evidence_clinical_precedence', ['drugId', 'diseaseId', 'clinicalReportId'])
    ev = ev[ev.clinicalReportId.fillna('').str.startswith('nct')]
    mol = read(f'{ot}/drug_molecule', ['id', 'parentId'])
    parent = dict(zip(mol.id, mol.parentId.where(mol.parentId.notna(), mol.id)))
    ev['drug'] = ev.drugId.map(parent).fillna(ev.drugId)
    dm = pd.read_csv(f'{R}/disease_mesh.csv.gz')[['diseaseId', 'indication_mesh_id']]
    key = ['drug', 'indication_mesh_id']
    links = ev.merge(dm, on='diseaseId')[key + ['clinicalReportId']].drop_duplicates()
    links['nct_id'] = links.clinicalReportId.str.upper()
    P = pd.read_csv(f'{R}/programmes.csv.gz', usecols=key + ['insight', 'area', 'drugType', 'drug_first_year'])
    links = links.merge(P, on=key)
    links = links[links.insight.astype(bool)]

    ct = rq2_stops.load(ctg)  # industry, interventional, drug/biological/genetic, phase 1-3; adds group, reason, stop_year
    ct['phase'] = ct.phases.map(phase_num)
    ct['outcome'] = [outcome(r) for r in ct[['status', 'stopped', 'reason']].itertuples(index=False)]
    end = ct.completion_date.fillna(ct.primary_completion_date)
    ct['end_year'] = np.where(ct.stopped, ct.stop_year, end.dt.year)
    ct = ct[ct.outcome.notna() & ct.start_year.between(2000, 2024)]
    L = links.merge(ct[['nct_id', 'phase', 'start_year', 'end_year', 'outcome', 'reason', 'group', 'lead_sponsor']], on='nct_id')

    genes = pd.read_csv(f'{R}/programme_targets.csv.gz')
    assoc, sim, _ = gensup.load(mdir)
    a = gensup.filter_assoc(assoc)
    simp = gensup.similar_pairs(sim)
    ti = L[key + ['start_year']].drop_duplicates().merge(genes, on=key)
    lab = gensup.label(ti, a, simp, year_col='start_year', omim_mode='always_ante')
    lab2 = gensup.label(ti, a[a.source != 'OMIM'], simp, year_col='start_year')
    k2 = key + ['start_year']
    g = lab.groupby(k2).agg(gs_ante=('gs_ante', 'any'), gs_post=('gs_post', 'any')).reset_index()
    g2 = lab2.groupby(k2).agg(gs_ante_noomim=('gs_ante', 'any')).reset_index()
    L = L.merge(g, on=k2, how='left').merge(g2, on=k2, how='left')
    for c in ('gs_ante', 'gs_post', 'gs_ante_noomim'):
        L[c] = L[c].fillna(False).astype(bool)
    # trial level: support if any linked insight programme is supported
    T = L.sort_values(key).groupby('nct_id').agg(
        drug=('drug', 'first'), n_links=('drug', 'size'), area=('area', lambda s: s.fillna('other').mode().iat[0]),
        drugType=('drugType', 'first'), drug_first_year=('drug_first_year', 'min'), phase=('phase', 'first'), start_year=('start_year', 'first'),
        end_year=('end_year', 'first'), outcome=('outcome', 'first'), reason=('reason', 'first'), group=('group', 'first'),
        gs_ante=('gs_ante', 'any'), gs_post=('gs_post', 'any'), gs_ante_noomim=('gs_ante_noomim', 'any')).reset_index()
    return L, T


def fit(f, d, out, title, keep=('fin',)):
    try:
        r = smf.logit(f, d).fit(disp=0, cov_type='cluster', cov_kwds={'groups': pd.factorize(d.drug)[0]})
        t = r.summary2().tables[1]
        t = t.loc[[i for i in t.index if i.startswith('C(outcome') or i in keep], ['Coef.', 'Std.Err.', 'P>|z|', '[0.025', '0.975]']]
        t['OR'] = np.exp(t['Coef.']); t['OR_lo'] = np.exp(t['[0.025']); t['OR_hi'] = np.exp(t['0.975]'])
        out.extend(['=' * 100, title, f, f'N={int(r.nobs)}; clusters (drugs)={d.drug.nunique()}', t.round(4).to_string()])
        return t
    except Exception as e:
        out.extend(['=' * 100, title, f, f'failed: {e!r}'])


def tost(d, ctrl, out, title, margin=0.02):
    """Equivalence of ex-ante support between financial stops and completed trials: linear probability model,
    90% CI of the difference against +/- margin (two one-sided tests at 5%)."""
    r = smf.ols(f'y ~ fin + {ctrl}', d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.drug)[0]})
    b, se = r.params['fin'], r.bse['fin']
    lo, hi = b - 1.645 * se, b + 1.645 * se
    out.extend(['=' * 100, f'Equivalence (TOST, margin +/- {margin}): {title}',
                f'diff={b:.4f} se={se:.4f} 90% CI=({lo:.4f}, {hi:.4f}) equivalent={bool(lo > -margin and hi < margin)}; '
                f'share among completed={d.loc[d.fin.eq(0), "y"].mean():.4f}; among financial stops={d.loc[d.fin.eq(1), "y"].mean():.4f}; '
                f'N={int(r.nobs)}'])


def prep(T):
    T = T.copy()
    T['outcome'] = pd.Categorical(T.outcome, categories=OUT).remove_unused_categories()
    T['modality'] = T.drugType.map(MOD).fillna('other')
    T['area'] = T.area.fillna('other')
    T['yb'] = pd.cut(T.start_year, [1999, 2005, 2010, 2015, 2025]).astype(str)
    T['small'] = T.group.eq('Industry, small (<=20)').astype(int)
    T['post22'] = (T.end_year >= 2022).astype(int)
    T['drug_age'] = pd.cut(T.start_year - T.drug_first_year, [-100, 0, 3, 8, 100], labels=['0', '1-3', '4-8', '9+']).astype(str)
    return T


CTRL0 = 'C(phase) + C(yb) + C(area) + C(modality)'
CTRL = CTRL0 + ' + C(group)'


def financial_models(F, out, unit):
    F = F[F.outcome.isin([OUT[0], OUT[1]])].copy()
    F['fin'] = F.outcome.eq(OUT[1]).astype(int)
    F['y'] = F.gs_ante.astype(int)
    fit(f'y ~ fin + {CTRL}', F, out, f'[{unit}] Financial/strategic stop vs completed')
    fit(f'y ~ fin * post22 + {CTRL}', F, out, f'[{unit}] ... x ended 2022 or later', keep=('fin', 'post22', 'fin:post22'))
    for lab, sub in (('ended before 2022', F[F.post22.eq(0)]), ('ended 2022 or later', F[F.post22.eq(1)])):
        fit(f'y ~ fin + {CTRL}', sub, out, f'[{unit}] Financial/strategic stop vs completed, trials that {lab}')
        tost(sub, CTRL, out, f'[{unit}] trials that {lab}')
    fit(f'y ~ fin * small + {CTRL0}', F, out, f'[{unit}] ... x small sponsor (<=20 trials)', keep=('fin', 'small', 'fin:small'))
    fit(f'y ~ fin + {CTRL0}', F[F.small.eq(1)], out, f'[{unit}] Small sponsors only')
    tost(F, CTRL, out, f'[{unit}] all years')
    if unit == 'trial':
        rob = 'C(phase) + C(start_year) + C(area) + C(modality) + C(group)'
        fit(f'y ~ fin * post22 + {rob}', F, out, '[trial] robustness: start-year fixed effects', keep=('fin', 'post22', 'fin:post22'))
        fit(f'y ~ fin * post22 + {rob} + C(drug_age)', F, out, '[trial] robustness: + years since the drug\'s first trial',
            keep=('fin', 'post22', 'fin:post22'))


def analyse(T, L, out):
    T = prep(T)
    tab = T.groupby('outcome', observed=True).agg(trials=('nct_id', 'size'), drugs=('drug', 'nunique'),
                                                  gs_ante=('gs_ante', 'mean'), gs_post=('gs_post', 'mean'),
                                                  gs_ante_noomim=('gs_ante_noomim', 'mean'))
    out.extend(['Trials by outcome (industry, Phase 1-3, start 2000-2024, indications with genetic insight):', tab.round(4).to_string()])
    tab2 = T.groupby(['outcome', 'group'], observed=True).agg(trials=('nct_id', 'size'), gs_ante=('gs_ante', 'mean')).unstack()
    out.extend(['', 'Ex-ante support by outcome x sponsor group:', tab2.round(4).to_string()])
    tab3 = T.groupby(['outcome', 'post22'], observed=True).agg(trials=('nct_id', 'size'), gs_ante=('gs_ante', 'mean')).unstack()
    out.extend(['', 'Ex-ante support by outcome x ended 2022 or later:', tab3.round(4).to_string()])
    ref = "C(outcome, Treatment(reference='Completed'))"
    for y in ('gs_ante', 'gs_post', 'gs_ante_noomim'):
        T['y'] = T[y].astype(int)
        fit(f'y ~ {ref} + {CTRL}', T, out, f'{y} ~ outcome (reference: completed) + phase, start period, area, modality, sponsor group')
    financial_models(T, out, 'trial')
    financial_models(prep(L), out, 'trial x indication link')
    return T


def main(ot, R, ctg, mdir):
    L, T = build(ot, R, ctg, mdir)
    out = [f'links={len(L)} trials={len(T)} drugs={T.drug.nunique()}']
    analyse(T, L, out)
    T.to_csv(f'{R}/h4_trials.csv.gz', index=False)
    open(f'{R}/h4_biology.txt', 'w').write('\n'.join(out))
    print('\n'.join(out))


if __name__ == '__main__':
    main(*sys.argv[1:5])
