"""RQ2 pilot: did financially motivated stops of industry drug trials rise after the 2022 biotech funding downturn,
and more for small sponsors than for top-20 pharma?

Usage: python rq2_stops.py CTGOV_ALL_CSV OUT_DIR
Input: all interventional studies (fetch_ctgov.py all).
Sponsor groups (by trial start year): top-20 pharma (acquisition-dated, sponsors.py); other industry split by the
number of interventional drug trials the normalised lead-sponsor name has ever led on ClinicalTrials.gov:
small <= 20, mid 21-200, large > 200.
Outputs in OUT_DIR:
  rq2_stops_by_year.csv   stopped trials by stop year x group x reason class
  rq2_shares.csv          share of stops (with a stated reason) that are financial / no-funding, by year x group
  rq2_rates.csv           stops per 1,000 trials at risk, by year x group
  rq2_did.txt             difference-in-differences and event-study logits
  rq2_label_sample.csv    stratified sample of why_stopped texts for hand-coding validation
"""
import os, re, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sponsors, stopreasons

STOPPED = {'TERMINATED', 'WITHDRAWN', 'SUSPENDED'}
FIN = stopreasons.FINANCIAL  # No funding, M&A / licensing, Business / strategic
SUFFIX = re.compile(r'\b(incorporated|inc|ltd|limited|llc|corp|corporation|co|company|gmbh|ag|sa|plc|bv|nv|spa|kk|pty|'
                    r'srl|ab|as|oy|kg|lp|holdings?|group|international|usa|us|pharmaceuticals?|pharma|'
                    r'biopharma(ceuticals?)?|therapeutics|biosciences?|biotech(nology)?|research|development|the)\b')
GROUPS = ['Top-20 pharma', 'Industry, large (>200 trials)', 'Industry, mid (21-200)', 'Industry, small (<=20)']


def norm_sponsor(s):
    if not isinstance(s, str):
        return None
    s = re.sub(r'[^a-z0-9]+', ' ', s.lower())
    return re.sub(r'\s+', ' ', SUFFIX.sub(' ', s)).strip() or None


def load(path):
    ct = pd.read_csv(path, dtype=str)
    ct = ct[ct.study_type.eq('INTERVENTIONAL') & ct.lead_class.eq('INDUSTRY')]
    ct = ct[ct.intervention_types.fillna('').str.contains('DRUG|BIOLOGICAL|GENETIC')]
    ct = ct[ct.phases.fillna('').str.contains('PHASE1|PHASE2|PHASE3')].copy()
    for c in ('start_date', 'completion_date', 'primary_completion_date', 'last_update'):
        ct[c] = pd.to_datetime(ct[c], errors='coerce')
    ct['start_year'] = ct.start_date.dt.year
    ct['top20'] = [sponsors.top20_parent(n, y) for n, y in zip(ct.lead_sponsor, ct.start_year)]
    ct['sponsor_norm'] = ct.lead_sponsor.map(norm_sponsor)
    n = ct.groupby('sponsor_norm').nct_id.nunique()
    ct['sponsor_n_trials'] = ct.sponsor_norm.map(n)
    k = ct.sponsor_n_trials
    ct['group'] = np.select([ct.top20.notna(), k > 200, k > 20], GROUPS[:3], GROUPS[3])
    ct['stopped'] = ct.status.isin(STOPPED)
    end = ct.completion_date.fillna(ct.primary_completion_date)
    ct['stop_date'] = end.fillna(ct.last_update).where(ct.stopped)
    ct['stop_year'] = ct.stop_date.dt.year
    ct['reason'] = ct.why_stopped.map(stopreasons.classify).where(ct.stopped)
    ct['fin'] = ct.reason.isin(FIN)
    ct['nofund'] = ct.reason.eq('No funding')
    return ct


def main(path, out):
    os.makedirs(out, exist_ok=True)
    ct = load(path)
    today = pd.Timestamp.today()
    s = ct[ct.stopped & ct.stop_year.between(2012, today.year)]
    tab = s.groupby(['stop_year', 'group', 'reason']).size().rename('n').reset_index()
    tab.to_csv(f'{out}/rq2_stops_by_year.csv', index=False)
    r = s[s.reason.ne('No reason')]
    sh = r.groupby(['stop_year', 'group']).agg(n_with_reason=('nct_id', 'size'), share_fin=('fin', 'mean'),
                                               share_nofund=('nofund', 'mean'),
                                               share_strategic=('reason', lambda x: x.eq('Business / strategic').mean()),
                                               share_unspecified=('reason', lambda x: x.eq('Sponsor decision, unspecified').mean()),
                                               share_enrol=('reason', lambda x: x.eq('Enrolment').mean())).reset_index()
    sh.to_csv(f'{out}/rq2_shares.csv', index=False)

    rows = []
    ended = ct.stop_date.fillna(ct.completion_date).fillna(ct.primary_completion_date)
    for t in range(2012, today.year + 1):
        a, b = pd.Timestamp(t, 1, 1), pd.Timestamp(t, 12, 31)
        risk = ct[(ct.start_date <= b) & (ended.isna() | (ended >= a))]
        for g, d in risk.groupby('group'):
            st = d[d.stopped & (d.stop_year == t)]
            rows.append({'year': t, 'group': g, 'at_risk': len(d), 'stops_all': len(st), 'stops_fin': int(st.fin.sum()),
                         'stops_nofund': int(st.nofund.sum()),
                         'rate_all_per_1000': 1000 * len(st) / len(d), 'rate_fin_per_1000': 1000 * st.fin.sum() / len(d),
                         'rate_nofund_per_1000': 1000 * st.nofund.sum() / len(d)})
    rates = pd.DataFrame(rows)
    rates.to_csv(f'{out}/rq2_rates.csv', index=False)

    lines = []
    try:
        import statsmodels.formula.api as smf
        d = r[r.stop_year.between(2016, today.year - 1)].copy()
        d['grp'] = pd.Categorical(d.group, categories=[g for g in GROUPS if g in set(d.group)])
        d['post'] = (d.stop_year >= 2022).astype(int)
        d['small'] = d.group.eq(GROUPS[3]).astype(int)
        present = list(d.grp.cat.categories)
        inter = []
        for i, g in enumerate(present[1:], 1):  # differential post-2022 change relative to the first group (top-20)
            d[f'post_x_g{i}'] = (d.group.eq(g) & d.post.eq(1)).astype(int); inter.append(f'post_x_g{i}')
        lines.append('groups: ' + '; '.join(f'g{i}={g}' for i, g in enumerate(present)))
        for y in ('fin', 'nofund'):
            d['y'] = d[y].astype(int)
            f = 'y ~ C(grp) + C(stop_year)' + ''.join(f' + {c}' for c in inter)
            try:
                res = smf.logit(f, d).fit(disp=0, cov_type='HC1')
                lines += ['=' * 90, f'outcome={y} among stops with a stated reason, 2016-{today.year - 1}', f,
                          f'N={int(res.nobs)}', res.summary2().tables[1].to_string()]
            except Exception as ex:
                lines += ['=' * 90, f, f'failed: {ex!r}']
            if GROUPS[3] not in present:
                continue
            # event study: small vs top-20, year-specific gaps relative to 2021
            e = d[d.group.isin([GROUPS[0], GROUPS[3]])].copy()
            for yr in sorted(e.stop_year.unique()):
                if yr != 2021:
                    e[f'sm_{int(yr)}'] = ((e.stop_year == yr) & (e.small == 1)).astype(int)
            terms = ' + '.join(c for c in e.columns if c.startswith('sm_'))
            res = smf.logit(f'y ~ small + C(stop_year) + {terms}', e).fit(disp=0, cov_type='HC1')
            es = res.summary2().tables[1].loc[[c for c in res.params.index if c.startswith('sm_')]]
            lines += ['=' * 90, f'event study ({y}): small (<=20 trials) vs top-20, gap by year relative to 2021',
                      f'N={int(res.nobs)}', es.to_string()]
    except Exception as ex:
        lines.append(f'models failed: {ex!r}')
    open(f'{out}/rq2_did.txt', 'w').write('\n'.join(lines))

    w = s[s.why_stopped.notna()].copy()
    w['period'] = np.where(w.stop_year >= 2022, '2022+', '<2022')
    smp = w.sample(frac=1, random_state=42).groupby(['group', 'period']).head(50)
    smp[['nct_id', 'lead_sponsor', 'group', 'stop_year', 'status', 'why_stopped', 'reason']].rename(
        columns={'reason': 'keyword_class'}).assign(hand_label='').to_csv(f'{out}/rq2_label_sample.csv', index=False)
    print(ct.drop_duplicates('sponsor_norm').group.value_counts().to_string())
    print(sh.pivot(index='stop_year', columns='group', values='share_fin').round(3).to_string())
    print('\n'.join(lines))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
