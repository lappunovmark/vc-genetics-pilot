"""Pilot panel from Open Targets Platform 26.x clinical data (clinical_report + evidence_clinical_precedence),
genetic-support labels re-implemented from Minikel et al. (2024).

Usage: python build_panel26.py OT_DIR MINIKEL_DATA_DIR OUT_DIR

Since release 25.x/26.x Open Targets ships trial-level records (from AACT) with lead sponsor, phase, start date,
overall status and why_stopped, linked to drug, target and disease. One evidence row = target x disease x drug x
clinical report (a trial or a regulatory/label record).

Outputs (OUT_DIR): coverage.json, programmes.csv.gz, phase_entries.csv.gz, sponsors.csv.gz,
h1_selection.csv, h1_by_period.csv, transitions.csv, models.txt
"""

import glob
import json
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gensup
import sponsors

PHASE_MAP = {"PHASE1": 1, "PHASE1/PHASE2": 2, "PHASE2": 2, "PHASE2/PHASE3": 3, "PHASE3": 3, "PHASE4": 4}
MESH_XREF = re.compile(r"^(?:MESH|MSH):\s*([CD]\d{6,9})$", re.I)
SUFFIX = re.compile(
    r"\b(incorporated|inc|ltd|limited|llc|l l c|corp|corporation|co|company|gmbh|ag|sa|s a|plc|bv|b v|"
    r"nv|spa|s p a|kk|k k|pty|srl|ab|as|oy|kg|lp|holdings?|group|international|usa|us|"
    r"pharmaceuticals?|pharma|biopharma(ceuticals?)?|therapeutics|biotherapeutics|biosciences?|"
    r"biotech(nology)?|research|development|commercialization|laboratories|labs|global|america|"
    r"north america|europe|japan|china|the)\b"
)


def read(d, cols=None):
    files = sorted(glob.glob(os.path.join(d, "*.parquet")))
    if not files:
        raise SystemExit(f"no parquet in {d}")
    return pd.concat([pd.read_parquet(f, columns=cols) for f in files], ignore_index=True)


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def norm_sponsor(s):
    if not isinstance(s, str):
        return None
    s = norm(s)
    s = SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip() or None


def mesh_tools(mdir):
    voc = pd.read_csv(f"{mdir}/mesh_all_vocab.tsv.gz", sep="\t", dtype=str).dropna()
    voc = voc[voc.id.str.match(r"^[CD]\d")]
    voc["key"] = voc.labeltext.str.lower().str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip()
    u = voc.drop_duplicates(["key", "id"])
    u = u[u.key.map(u.key.value_counts()) == 1]
    label2id = dict(zip(u.key, u.id))
    scr = pd.read_csv(f"{mdir}/mesh_scr_to_best.tsv.gz", sep="\t", dtype=str)
    scr2d = dict(zip(scr.scr, scr.main))
    rem = pd.read_csv(f"{mdir}/mesh_remappings.tsv", sep="\t", dtype=str)
    remap = dict(zip(rem.old, rem.new))

    def desc(mid):
        if not isinstance(mid, str):
            return None
        mid = remap.get(mid, mid)
        return scr2d.get(mid) if mid.startswith("C") else mid

    return label2id, desc


def disease_to_mesh(dis, label2id, desc):
    """Per ontology disease id: (1) a unique MeSH xref, (2) a unique exact match of name or exact synonym to a MeSH
    label, (3) the nearest ancestor mapped by (1)/(2). Returns DataFrame diseaseId, mesh, method."""
    direct = {}
    meth = {}
    for r in dis.itertuples(index=False):
        ids = set()
        for x in r.dbXRefs if r.dbXRefs is not None else []:
            m = MESH_XREF.match(str(x))
            if m:
                d = desc(m.group(1))
                if d:
                    ids.add(d)
        if len(ids) == 1:
            direct[r.id] = ids.pop()
            meth[r.id] = "xref"
            continue
        cands = [r.name] + list(r.exactSynonyms if r.exactSynonyms is not None else [])
        hits = {desc(label2id.get(norm(c))) for c in cands if c} - {None}
        if len(hits) == 1:
            direct[r.id] = hits.pop()
            meth[r.id] = "name"
    out = dict(direct)
    # ancestors are ordered arbitrarily in OT; use parents breadth-first for the nearest mapped ancestor
    parents = dict(zip(dis.id, dis.parents))
    for did in dis.id:
        if did in out:
            continue
        seen, frontier, hit = {did}, list(parents.get(did) if parents.get(did) is not None else []), None
        depth = 0
        while frontier and hit is None and depth < 6:
            nxt = []
            for p in frontier:
                if p in direct:
                    hit = direct[p]
                    break
                if p not in seen:
                    seen.add(p)
                    nxt += list(parents.get(p) if parents.get(p) is not None else [])
            frontier, depth = nxt, depth + 1
        if hit:
            out[did] = hit
            meth[did] = f"ancestor{depth}"
    return pd.DataFrame(
        {"diseaseId": list(out), "indication_mesh_id": list(out.values()), "map_method": [meth[k] for k in out]}
    )


def insight_flags(ids, assoc, sim, indic):
    ids = pd.Series(sorted(set(pd.Series(ids).dropna())))
    sp = sim[sim.comb_norm >= 0.8][["meshcode_a", "meshcode_b"]]
    sp = sp[sp.meshcode_a.isin(set(ids))]
    g = assoc[assoc.source.isin(["OTG", "PICCOLO", "Genebass"])]
    g = g[(g.source != "OTG") | ((g.l2g_share >= 0.5) & g.year.between(2005, 2022))]
    o = assoc[assoc.source.isin(["OMIM", "intOGen"])]

    def n_genes(x):
        x = x[["mesh_id", "gene"]].drop_duplicates()
        m = sp.merge(x, left_on="meshcode_b", right_on="mesh_id")[["meshcode_a", "gene"]].drop_duplicates()
        return m.groupby("meshcode_a").gene.size()

    n_o, n_g = n_genes(o), n_genes(g)
    in_sim = set(sim.meshcode_a.unique())
    approx = ((ids.map(n_o).fillna(0) >= 1) | (ids.map(n_g).fillna(0) >= 3)) & ids.isin(in_sim)
    own = ids.map(dict(zip(indic.indication_mesh_id, indic.genetic_insight.ne("none"))))
    return pd.DataFrame(
        {
            "indication_mesh_id": ids,
            "insight": own.fillna(approx).astype(bool),
            "insight_source": np.where(own.notna(), "minikel", "approx"),
            "in_sim": ids.isin(in_sim),
        }
    )


def mesh_area(mdir):
    """MeSH descriptor -> one therapeutic area (Minikel et al. areas.tsv over MeSH tree top levels). A term in several
    areas gets the first in the row order of areas.tsv (infection, oncology, musculoskeletal, ...)."""
    tree = pd.read_csv(f"{mdir}/mesh_tree.tsv", sep=" ", header=None, names=["id", "tree"], dtype=str)
    areas = pd.read_csv(f"{mdir}/areas.tsv", sep="\t", dtype=str)
    order = {a: i for i, a in enumerate(areas.area)}
    tree["topl"] = tree.tree.str[:3]
    m = tree.merge(areas[["topl", "area"]], on="topl")
    m["o"] = m.area.map(order)
    return m.sort_values("o").drop_duplicates("id").set_index("id").area.to_dict()


def similar_advance(ent, tr, ev, simp, key, chunk=300):
    """Advancement that tolerates indication granularity: a later higher-phase trial, or an approval, of the same drug
    in the same indication or one with MeSH similarity >= 0.8 (Minikel et al. matrix). Returns per entry
    prior_higher_sim (a similar-indication higher-phase trial started before entry) and advanced_sim."""
    ids = pd.Index(sorted(set(tr.indication_mesh_id) | set(ev.indication_mesh_id)))
    code = {m: i for i, m in enumerate(ids)}
    sp = simp[simp.meshcode_a.isin(code) & simp.meshcode_b.isin(code)]
    pairs = pd.DataFrame(
        {
            "m1": np.r_[sp.meshcode_a.map(code).values, np.arange(len(ids))],
            "m2": np.r_[sp.meshcode_b.map(code).values, np.arange(len(ids))],
        }
    ).drop_duplicates()
    e = ent[key + ["phase", "entry_start"]].copy()
    e["m1"] = e.indication_mesh_id.map(code)
    t = tr[["drug", "indication_mesh_id", "phase_num", "start"]].copy()
    t["m2"] = t.indication_mesh_id.map(code)
    ap = ev[ev.clinicalStage.eq("APPROVAL")][["drug", "indication_mesh_id"]].drop_duplicates()
    ap["m2"] = ap.indication_mesh_id.map(code)
    drugs = e.drug.unique()
    res = []
    for i in range(0, len(drugs), chunk):
        dd = set(drugs[i : i + chunk])
        x = e[e.drug.isin(dd)].merge(t[t.drug.isin(dd)][["drug", "m2", "phase_num", "start"]], on="drug")
        x = x[x.phase_num > x.phase].merge(pairs, on=["m1", "m2"])
        pr = x[x.start < x.entry_start].groupby(key + ["phase"]).size().rename("n_prior")
        la = x[x.start >= x.entry_start].groupby(key + ["phase"]).size().rename("n_later")
        y = e[e.drug.isin(dd)].merge(ap[ap.drug.isin(dd)][["drug", "m2"]], on="drug").merge(pairs, on=["m1", "m2"])
        apr = y.groupby(key + ["phase"]).size().rename("n_appr")
        res.append(pd.concat([pr, la, apr], axis=1))
    r = pd.concat(res).fillna(0)
    out = pd.DataFrame({"prior_higher_sim": r.n_prior > 0, "advanced_sim": (r.n_later > 0) | (r.n_appr > 0)})
    return out.reset_index()


def wilson(x, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = x / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def portfolio_size(trials, parent):
    """Distinct parent drugs per normalised industry lead-sponsor name across ALL OT trial reports."""
    t = trials[trials.lead_class.eq("INDUSTRY")][["lead_sponsor", "drugs"]].explode("drugs").dropna()
    t["drug"] = t.drugs.map(lambda d: d.get("drugId") if isinstance(d, dict) else None)
    t = t.dropna(subset=["drug"])
    t["drug"] = t.drug.map(parent).fillna(t.drug)
    t["sponsor_norm"] = t.lead_sponsor.map(norm_sponsor)
    return t.groupby("sponsor_norm").drug.nunique()


def sponsor_tiers(tr, size):
    """Sponsor typing for the pilot: top-20 parent by regex; other industry split by portfolio size (distinct parent
    drugs the normalised sponsor name leads across all OT trial reports); academic/other; government."""
    tr = tr.copy()
    tr["sponsor_norm"] = tr.lead_sponsor.map(norm_sponsor)
    tr["top20_parent"] = [sponsors.top20_parent(n, y) for n, y in zip(tr.lead_sponsor, tr.start_year)]
    tr["sponsor_n_drugs"] = tr.sponsor_norm.map(size)

    def tier(r):
        if isinstance(r.top20_parent, str):
            return "Top-20 pharma"
        if r.lead_class == "INDUSTRY":
            n = r.sponsor_n_drugs
            if not n == n or n is None:
                return "Industry, size unknown"
            return (
                "Industry, small (<=5 drugs)"
                if n <= 5
                else ("Industry, mid (6-30)" if n <= 30 else "Industry, large (>30)")
            )
        if r.lead_class in ("NIH", "FED", "OTHER_GOV"):
            return "Government"
        if r.lead_class in ("OTHER", "NETWORK", "INDIV"):
            return "Academic/other"
        return "Unknown"

    tr["sponsor_tier"] = [
        tier(r) for r in tr[["top20_parent", "lead_class", "sponsor_n_drugs"]].itertuples(index=False)
    ]
    return tr


def main(ot, mdir, out):
    os.makedirs(out, exist_ok=True)
    cov = {"ot_release": open(f"{ot}/RELEASE").read().strip() if os.path.exists(f"{ot}/RELEASE") else None}
    ev = read(
        f"{ot}/evidence_clinical_precedence",
        ["targetId", "diseaseId", "drugId", "clinicalReportId", "clinicalStage", "studyStartDate", "diseaseFromSource"],
    )
    cov["evidence_rows"] = len(ev)
    tgt = read(f"{ot}/target", ["id", "approvedSymbol"]).rename(columns={"id": "targetId", "approvedSymbol": "gene"})
    mol = read(f"{ot}/drug_molecule", ["id", "parentId", "name", "drugType"])
    parent = dict(zip(mol.id, mol.parentId.where(mol.parentId.notna(), mol.id)))
    dis = read(f"{ot}/disease", ["id", "name", "dbXRefs", "exactSynonyms", "parents"])
    cr = read(
        f"{ot}/clinical_report",
        [
            "id",
            "clinicalStage",
            "origin",
            "type",
            "source",
            "trialPhase",
            "trialStudyType",
            "drugs",
            "trialStartDate",
            "trialSponsor",
            "trialOverallStatus",
            "trialWhyStopped",
            "trialStopReasonCategories",
            "year",
        ],
    )
    ev = ev.merge(tgt, on="targetId", how="left")
    ev["drug"] = ev.drugId.map(parent).fillna(ev.drugId)
    label2id, desc = mesh_tools(mdir)
    dm = disease_to_mesh(dis, label2id, desc)
    ev = ev.merge(dm, on="diseaseId", how="left")
    cov["evidence_rows_by_mesh_method"] = ev.map_method.fillna("unmapped").value_counts().to_dict()
    cov["evidence_rows_with_gene"] = int(ev.gene.notna().sum())
    ev = ev[ev.gene.notna() & ev.indication_mesh_id.notna()]
    key = ["drug", "indication_mesh_id"]

    # trials
    sp = pd.json_normalize(
        cr.trialSponsor.where(cr.trialSponsor.notna(), None).map(lambda x: x if isinstance(x, dict) else {}).tolist()
    )
    cr["lead_sponsor"] = sp.get("name")
    cr["lead_class"] = sp.get("agencyClass")
    cr["phase_num"] = cr.trialPhase.map(PHASE_MAP)
    cr["start"] = pd.to_datetime(cr.trialStartDate, errors="coerce")
    trials = cr[
        cr.origin.eq("CLINICAL_TRIAL")
        & cr.type.eq("INDICATION")
        & cr.trialStudyType.eq("INTERVENTIONAL")
        & cr.phase_num.notna()
        & cr.start.notna()
        & (cr.start <= pd.Timestamp.today())
    ]
    cov["trial_reports_usable"] = len(trials)
    cov["trial_reports_all"] = int(cr.origin.eq("CLINICAL_TRIAL").sum())
    tr = (
        ev[key + ["clinicalReportId"]]
        .drop_duplicates()
        .merge(
            trials[["id", "phase_num", "start", "lead_sponsor", "lead_class", "trialOverallStatus", "trialWhyStopped"]],
            left_on="clinicalReportId",
            right_on="id",
        )
    )
    tr["start_year"] = tr.start.dt.year
    size = portfolio_size(cr[cr.origin.eq("CLINICAL_TRIAL")], parent)
    tr = sponsor_tiers(tr, size)
    cov["programme_trial_links"] = len(tr)
    approved = ev[ev.clinicalStage.eq("APPROVAL")][key].drop_duplicates().assign(approved=True)
    targets = ev[key + ["gene"]].drop_duplicates()

    first = tr.sort_values(["start", "clinicalReportId"]).groupby(key).first().reset_index()
    prog = first[
        key + ["clinicalReportId", "start_year", "phase_num", "sponsor_tier", "lead_sponsor", "lead_class"]
    ].rename(
        columns={
            "clinicalReportId": "first_trial",
            "start_year": "first_year",
            "phase_num": "first_phase",
            "sponsor_tier": "first_sponsor_tier",
            "lead_sponsor": "first_sponsor",
            "lead_class": "first_class",
        }
    )
    prog = prog.merge(tr.groupby(key).phase_num.max().rename("max_trial_phase").reset_index(), on=key)
    prog = prog.merge(approved, on=key, how="left")
    prog["approved"] = prog.approved.fillna(False).astype(bool)
    cov["programmes_with_trials"] = len(prog)
    # drug-level origin: the drug's earliest trial in ANY indication, and who ran it
    dfirst = tr.sort_values(["start", "clinicalReportId"]).groupby("drug").first()[["start_year", "sponsor_tier"]]
    prog = prog.join(
        dfirst.rename(columns={"start_year": "drug_first_year", "sponsor_tier": "drug_first_tier"}), on="drug"
    )
    prog["is_drug_first_indication"] = prog.first_year.eq(prog.drug_first_year)
    prog = prog.merge(
        mol.drop_duplicates("id").rename(columns={"id": "drug"})[["drug", "drugType"]], on="drug", how="left"
    )
    mm = (
        ev.groupby(key)
        .map_method.agg(lambda x: "direct" if x.isin(["xref", "name"]).any() else "ancestor")
        .rename("mesh_map")
    )
    prog = prog.join(mm, on=key)
    prog["area"] = prog.indication_mesh_id.map(mesh_area(mdir))

    assoc, sim, indic = gensup.load(mdir)
    a = gensup.filter_assoc(assoc)
    simp = gensup.similar_pairs(sim)
    ins = insight_flags(prog.indication_mesh_id, assoc, sim, indic)
    prog = prog.merge(ins, on="indication_mesh_id", how="left")
    pt = prog[key + ["first_year"]].merge(targets, on=key)
    pl = gensup.label(pt, a, simp, year_col="first_year", omim_mode="always_ante")
    pl2 = gensup.label(pt, a[a.source != "OMIM"], simp, year_col="first_year")
    prog = prog.merge(
        pl.groupby(key)
        .agg(gs_post=("gs_post", "any"), gs_ante_first=("gs_ante", "any"), n_targets=("gene", "nunique"))
        .reset_index(),
        on=key,
        how="left",
    )
    prog = prog.merge(pl2.groupby(key).agg(gs_post_noomim=("gs_post", "any")).reset_index(), on=key, how="left")
    cov["programmes_in_sim"] = int(prog.in_sim.sum())
    cov["programmes_with_insight"] = int(prog.insight.sum())
    cov["programmes_insight_source"] = prog.loc[prog.insight, "insight_source"].value_counts().to_dict()

    # phase entries
    ent = (
        tr[tr.phase_num.isin([1, 2, 3])]
        .sort_values(["start", "clinicalReportId"])
        .groupby(key + ["phase_num"])
        .first()
        .reset_index()
    )
    ent = ent[
        key
        + [
            "phase_num",
            "clinicalReportId",
            "start",
            "start_year",
            "sponsor_tier",
            "lead_sponsor",
            "lead_class",
            "sponsor_n_drugs",
        ]
    ].rename(
        columns={
            "phase_num": "phase",
            "clinicalReportId": "entry_trial",
            "start": "entry_start",
            "start_year": "entry_year",
        }
    )
    ent = ent.join(
        prog.set_index(key)[
            [
                "approved",
                "insight",
                "drugType",
                "mesh_map",
                "area",
                "drug_first_year",
                "drug_first_tier",
                "is_drug_first_indication",
            ]
        ],
        on=key,
    )
    hk = ent[key + ["phase", "entry_start"]].merge(tr[key + ["phase_num", "start"]], on=key)
    hk = hk[hk.phase_num > hk.phase]
    idx = key + ["phase"]
    prior = hk[hk.start < hk.entry_start][idx].drop_duplicates().assign(prior_higher=True)
    later = hk[hk.start >= hk.entry_start].groupby(idx).start.min().rename("next_start").reset_index()
    ent = ent.merge(prior, on=idx, how="left").merge(later, on=idx, how="left")
    ent["prior_higher"] = ent.prior_higher.fillna(False).astype(bool)
    ent["advanced"] = ent.next_start.notna() | ent.approved
    ent["advanced_trial_only"] = ent.next_start.notna()
    ent = ent.merge(similar_advance(ent, tr, ev, gensup.similar_pairs(sim), key), on=idx, how="left")
    for c in ("prior_higher_sim", "advanced_sim"):
        ent[c] = ent[c].fillna(False).astype(bool)
    ti = ent[key + ["phase", "entry_year"]].merge(targets, on=key).rename(columns={"entry_year": "yr"})
    lab = gensup.label(ti, a, simp, year_col="yr", omim_mode="always_ante")
    lab2 = gensup.label(ti, a[a.source != "OMIM"], simp, year_col="yr")
    ent = ent.merge(
        lab.groupby(idx).agg(gs_post=("gs_post", "any"), gs_ante=("gs_ante", "any")).reset_index(), on=idx, how="left"
    )
    ent = ent.merge(lab2.groupby(idx).agg(gs_ante_noomim=("gs_ante", "any")).reset_index(), on=idx, how="left")
    cov["phase_entries"] = {int(k): int(v) for k, v in ent.phase.value_counts().sort_index().items()}
    cov["phase_entries_prior_higher"] = int(ent.prior_higher.sum())

    prog.to_csv(f"{out}/programmes.csv.gz", index=False)
    ent.to_csv(f"{out}/phase_entries.csv.gz", index=False)
    targets.to_csv(f"{out}/programme_targets.csv.gz", index=False)
    dm.to_csv(f"{out}/disease_mesh.csv.gz", index=False)
    tr.drop_duplicates("clinicalReportId")[
        [
            "clinicalReportId",
            "lead_sponsor",
            "sponsor_norm",
            "lead_class",
            "top20_parent",
            "sponsor_n_drugs",
            "sponsor_tier",
        ]
    ].to_csv(f"{out}/sponsors.csv.gz", index=False)

    # H1 selection
    rows = []
    P = prog[prog.insight]
    for grp, d in [("All", P)] + list(P.groupby("first_sponsor_tier")):
        r = {"sponsor_tier": grp, "n_programmes": len(d)}
        for c in ("gs_post", "gs_ante_first", "gs_post_noomim"):
            x = int(d[c].fillna(False).sum())
            lo, hi = wilson(x, len(d))
            r.update({f"{c}_n": x, f"{c}_share": x / len(d) if len(d) else np.nan, f"{c}_lo": lo, f"{c}_hi": hi})
        rows.append(r)
    pd.DataFrame(rows).to_csv(f"{out}/h1_selection.csv", index=False)
    P = P.assign(
        period=pd.cut(
            P.first_year, [0, 2004, 2009, 2014, 2019, 2100], labels=["<=2004", "2005-09", "2010-14", "2015-19", "2020+"]
        )
    )
    t = (
        P.groupby(["period", "first_sponsor_tier"], observed=True)
        .agg(n=("gs_post", "size"), gs_post=("gs_post", "mean"), gs_ante=("gs_ante_first", "mean"))
        .reset_index()
    )
    t.to_csv(f"{out}/h1_by_period.csv", index=False)

    # transitions
    end_year = int(min(tr.start_year.max(), pd.Timestamp.today().year))
    rows = []
    E = ent[ent.insight & ~ent.prior_higher]
    for k in (1, 2, 3):
        cutoff = end_year - (6 if k < 3 else 8)
        d0 = E[(E.phase == k) & E.entry_year.between(2000, cutoff)]
        for st, d in [("All", d0)] + list(d0.groupby("sponsor_tier")):
            r = {"phase": k, "entry_years": f"2000-{cutoff}", "sponsor_tier": st}
            g = d.gs_ante.fillna(False)
            for lbl, s in (("gs", d[g]), ("nogs", d[~g])):
                r[f"n_{lbl}"] = len(s)
                r[f"x_{lbl}"] = int(s.advanced.sum())
                r[f"p_{lbl}"] = s.advanced.mean() if len(s) else np.nan
            r["rs"] = r["p_gs"] / r["p_nogs"] if r["p_nogs"] else np.nan
            rows.append(r)
    pd.DataFrame(rows).to_csv(f"{out}/transitions.csv", index=False)

    lines = []
    try:
        import statsmodels.formula.api as smf

        M = E[E.entry_year.between(2000, end_year - 6)].copy()
        M["gs"] = M.gs_ante.fillna(False).astype(int)
        M["adv"] = M.advanced.astype(int)
        M["yb"] = pd.cut(M.entry_year, [1999, 2005, 2010, 2015, 2030]).astype(str)
        M["tier"] = M.sponsor_tier.where(M.sponsor_tier.ne("Unknown"))
        M = M[M.tier.notna()]
        M["tier"] = pd.Categorical(M.tier, categories=["Top-20 pharma"] + sorted(set(M.tier) - {"Top-20 pharma"}))
        groups = pd.factorize(M.drug)[0]
        for f in [
            "adv ~ gs + C(phase) + C(yb)",
            "adv ~ gs + C(tier) + C(phase) + C(yb)",
            "adv ~ gs * C(tier) + C(phase) + C(yb)",
        ]:
            try:
                res = smf.logit(f, M).fit(disp=0, cov_type="cluster", cov_kwds={"groups": groups})
                lines += [
                    "=" * 90,
                    f,
                    f"N={int(res.nobs)}; clusters (drugs)={len(set(groups))}",
                    res.summary2().tables[1].to_string(),
                ]
            except Exception as e:
                lines += ["=" * 90, f, f"failed: {e!r}"]
    except Exception as e:
        lines.append(f"models failed: {e!r}")
    open(f"{out}/models.txt", "w").write("\n".join(lines))
    cov["end_year"] = end_year
    json.dump(cov, open(f"{out}/coverage.json", "w"), indent=2, default=str)
    print(json.dumps(cov, indent=2, default=str))


if __name__ == "__main__":
    main(*sys.argv[1:4])
