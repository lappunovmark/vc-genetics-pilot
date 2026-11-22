# Plan: the sponsor's financing stage in the year of the trial (written before the run)

Written on 23 November 2026, before the grouping below was built or any outcome was tabulated by it.

**Why.** The hypotheses were written for venture-backed private companies as a type of sponsor. The venture markers
of the repository do not give that type: the flag from four sources is a property of the sponsor and is not dated
to the trial, and the holders named in IPO prospectuses describe one date. The sources already linked carry
dates, so each programme of a non-top-20 industry sponsor can be placed by what the sponsor was in the year of the
programme's first trial: private and venture-backed, public after venture backing, public without a venture
marker, or none of these.

**What had been seen when this was written.** The related comparisons were run earlier and showed no link between
venture backing and ex-ante genetic support (the undated flag, venture rounds in Crunchbase, Form D, the venture
share at the IPO; in `ipo_models.py` the venture share was fitted separately on programmes first tried no later
than the IPO year and after it). Ex-ante support has not been tabulated by the stage defined here. To write the
plan, the number of sponsors covered by each source was counted, without outcomes.

**Definitions.** *t* is the year of a programme's first trial (of the entry trial for phase entries).
* *IPO year*: the earlier of the IPO year in the prospectus read for the sponsor (`ipo_sponsors.csv`) and in Jay
  Ritter's list (`ritter_sponsors.csv`).
* *Public at t*: *t* is later than the IPO year; for a sponsor without an IPO year, *t* is later than its first
  year as an EDGAR registrant (`owners_sponsors.csv`), and a first year of 2001, where the index begins, means
  public throughout. A trial in the IPO year counts as private, as in the plan for the prospectuses.
* *Venture-backed at the IPO*: a venture-capital fund holds 5% or more in the prospectus, or Ritter's list marks
  the IPO as venture-backed.
* *Dated venture marker before t*: a venture round in the Crunchbase export, or a Form D filing with a venture
  investor on the board, in a year before *t*.

**Groups of non-top-20 industry sponsors, per programme.**
* **A, private and venture-backed**: not public at *t*, and either (i) venture-backed at an IPO that is still
  ahead (*t* no later than the IPO year) or (ii) a dated venture marker before *t*.
* **B, public, venture-backed before**: public at *t*, and venture-backed at the IPO, or a dated venture marker
  before *t*, or a venture-capital fund among its owners in a Schedule 13D or 13G first filed before *t*.
* **C, public, no venture marker**: public at *t*, none of the markers of B.
* **D, the rest**: not known to be public at *t* and no venture marker before *t*. This group mixes companies
  without venture money, companies outside the United States and companies no source shows.

Top-20 pharma is the reference group.

**Model.** The selection model of the pilot on programmes in indications with genetic insight, first trial in 2001
or later, industry sponsors: ex-ante support on the groups A–D (top-20 as reference), first-trial period,
therapeutic area and modality; errors clustered by drug and, as a second reading, by sponsor.

**Primary estimate.** The odds ratio of ex-ante support for group A against top-20 pharma.

**Secondary.**
(a) A against B, and A against D, as contrasts in the same model.
(b) Among non-top-20 sponsors only, A against all others, with the sponsor-size band in the model.
(c) A strict variant of A: only (ii), a dated marker before *t*.
(d) First trials from 2010, when the Form D markers exist.
(e) Within sponsor: for sponsors venture-backed at their IPO, programmes first tried after the IPO year against
    those no later than it, in a conditional logit with the sponsor as stratum and first-trial period as control.
(f) The primary model with the dated Open Targets measure, where `gs_ot_programmes.csv.gz` is present.
(g) Advancement of phase entries (2001 to six years before the last entry year, no earlier higher phase): ex-ante
    support, the groups and their interactions with support, phase, period, area and modality.

**Reading rule, fixed in advance.** If the interval of the primary estimate excludes 1, private venture-backed
companies started programmes with more (above 1) or less (below 1) genetic support than top-20 pharma. If it
includes 1, the data do not show a difference. If A does not differ from D, a gap between A and top-20 pharma is
not specific to venture backing. No adjustment for multiple testing; all estimates are reported whatever they
show.

**Known limits.** Part (i) of group A is assigned backwards from an IPO, so it holds only companies that later
went public, and it assumes that a company venture-held at its IPO was venture-backed at its earlier trials; the
date of the first sale of preferred stock has not been read from the prospectuses. For companies that never went
public the markers are Crunchbase rounds to 2015 and Form D filings from 2009, both centred on the United States.
A listing outside the United States is not seen, so some sponsors in A and D were public at *t*. Trial stops by
stage are not part of this plan.
