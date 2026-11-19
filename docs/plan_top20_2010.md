# Plan: the top-20 group defined by 2010 sales (written before the run)

Written on 19 November 2026, before any model with this group was fitted.

**Why.** The pilot's top-20 group is fixed by prescription-drug sales in 2023, after the programmes studied. A
company is in that list partly because its programmes of the years before succeeded, so a group defined this way
will look as if it had been where the successful targets were. This matters most for the second result of the
pilot: after GWAS evidence for a target–indication pair is published, top-20 pharma start more programmes on it
and other industry sponsors do not (ratio of the two responses 0.54, 0.34–0.84).

**The list.** The Pharm Exec 50 of May 2011 (Cacciotti and Clinton, *Pharmaceutical Executive*) ranks companies
by global prescription-drug sales in 2010. Its first twenty are taken as they stand: Pfizer, Novartis,
Sanofi-Aventis, Merck & Co, Roche, GlaxoSmithKline, AstraZeneca, Johnson & Johnson, Eli Lilly, Abbott,
Bristol-Myers Squibb, Teva, Amgen, Bayer, Takeda, Boehringer Ingelheim, Novo Nordisk, Astellas, Daiichi Sankyo and
Eisai. Eighteen are also in the pilot's list (Abbott's drug business is AbbVie from 2013). Teva and Eisai come in;
Gilead (22nd in 2010) and Merck KGaA (21st) go out. The pilot's list left generics companies out by judgement;
this one makes no such choice, so Teva is in it, and one variant leaves Teva out.

**Typing.** The rule of the pilot is unchanged: a sponsor name is typed by its own leading name, and an acquired
company counts as its parent from the year of the acquisition. Entries are added for Teva and Eisai and for the
companies they acquired that appear in the programme table (Cephalon from 2011, Barr and Duramed from 2008,
NuPathe from 2014, the Actavis generics business from 2016; Morphotek from 2007). A sponsor that leaves the group
is typed by the size of its portfolio like any other industry sponsor. Before this plan was written the programme
table was read only for the names and numbers of programmes that move (about 290 programmes leave the group and
about 130 enter, of 5,873); no outcome was looked at.

**Primary analysis.** The contrast D1 of `evidence_arrival.py` on GWAS credible sets (other industry sponsors
against top-20 pharma after the evidence year), with the top-20 group of 2010 and only pairs whose evidence year is
2010 or later, so that every programme start counted as following the evidence is later than the year that
defines the group. Everything else as in `docs/plan_evidence_arrival_ot.md`.

**Secondary.** (a) The 2010 group on all pairs, which is the planned run of 18 November with only the group
changed. (b) The pilot's group on pairs with an evidence year of 2010 or later, to tell the effect of the list
from that of the sample. (c) All germline sources. (d) The checks that the script adds to every run (gene × year
effects, the target as the unit, placebo). (e) The 2010 group without Teva. (f) The selection model of the pilot
(small sponsors against top-20 pharma, `robust26.py`) with the 2010 group.

**Reading rule, fixed in advance.** If the primary contrast is below 1 with an interval that excludes 1, the
second result does not depend on defining the group by later sales. If the interval includes 1, the result is
reported as not holding for a group fixed in 2010, whatever the point estimate. All estimates are reported.

**Known limits.** A list fixed in 2010 still reflects success before 2010. Companies acquired after 2010 still
enter the group from the year of their acquisition, as in the pilot. A list fixed year by year, with licensing
followed, is left for the full design.
