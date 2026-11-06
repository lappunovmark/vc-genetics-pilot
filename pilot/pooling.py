"""Pool sparse control categories before a logit, so that the fit converges.

A control category with no (or almost no) events makes a logit quasi-separated: the coefficient of that category
drifts towards minus infinity and Newton's method never reports convergence, although the coefficients of interest
are stable to three or four decimals (checked for every model of this pipeline with factcheck/convergence_audit.py).
Nominal controls (area, modality, group, phase) with fewer than `min_events` events are merged into 'other' when that
level has events of its own, else into the largest level with enough events (a fresh 'other' made only of sparse levels
would have no events and separate again); sparse levels of ordered controls (start period bins, start year, drug age)
are merged into the next non-sparse level (the last one at the top end). Only
columns that appear as C(col) in the formula are touched; exposures of interest are never pooled.
"""

NOMINAL = ("area", "modality", "group", "phase")
ORDERED = ("yb", "start_year", "drug_age")


def pool_sparse(d, formula, y=None, nominal=NOMINAL, ordered=ORDERED, min_events=3):
    y = y or formula.split("~")[0].strip()
    d = d.copy()
    for col in nominal:
        if f"C({col})" in formula:
            ev = d.groupby(col)[y].sum()
            sparse = ev[ev < min_events].index
            if len(sparse):
                # merge into 'other' when it has events of its own, else into the largest non-sparse level: a fresh
                # 'other' made only of sparse levels would still have no events and would separate again
                dense = ev[ev >= min_events].index
                if "other" in dense:
                    target = "other"
                elif len(dense):
                    target = d[col][d[col].isin(dense)].value_counts().idxmax()
                else:
                    target = None  # no level has enough events: leave the column alone
                if target is not None:
                    d[col] = d[col].where(~d[col].isin(sparse), target)
    for col in ordered:
        if f"C({col})" in formula:
            ev = d.groupby(col)[y].sum().sort_index()
            levels, remap, carry = list(ev.index), {}, []
            for lv in levels:
                if ev[lv] + sum(ev[c] for c in carry) < min_events:
                    carry.append(lv)
                else:
                    for c in carry:
                        remap[c] = lv
                    carry = []
            if carry:  # sparse levels at the top end go to the last non-sparse level
                last = [lv for lv in levels if lv not in carry and lv not in remap]
                for c in carry:
                    remap[c] = last[-1] if last else c
            if remap:
                d[col] = d[col].map(lambda x: remap.get(x, x))
    return d
