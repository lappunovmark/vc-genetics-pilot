# Plan: genetic evidence for an unrelated disease as a placebo (written before the run)

Written on 23 November 2026, before advancement was tabulated by the similarity of the genetic evidence.

**Why.** The first result of the paper is that programmes with ex-ante genetic support advance more often. Support
means that the target gene is associated with a trait similar to the indication (similarity of the two MeSH terms
of 0.8 or more on the scale of Minikel et al. 2024). The premium could instead reflect the gene: genes with any
human genetics are better studied, and drugs against them may advance more often whatever the disease. A placebo
separates the two readings: a target with genetic evidence only for traits unrelated to the indication.

**What had been seen.** The advancement models with support at 0.8 and their variants. Advancement has not been
tabulated by lower similarity. The distribution of the similarity scores over all pairs of terms was looked at to
choose the bands (median 0.10, third quartile 0.19).

**Measure.** For each phase entry, over the targets of the programme (`programme_targets.csv.gz`) and over the
associations of each target dated before the entry year (OMIM counted as ex ante, as in the main measure), the
highest similarity between the associated trait and the indication; an identical term counts as 1. Bands:
* **supported**, 0.8 or more (this must reproduce `gs_ante` of the panel, which is checked);
* **0.5 to 0.8** and **0.2 to 0.5**, intermediate;
* **placebo**, below 0.2: the target has ex-ante genetic evidence, all of it for traits unrelated to the indication;
* **none**: no ex-ante association of any target (the reference).

**Model.** The advancement model of the paper (`robust26.py`, "Advance: main effects"): phase entries in indications
with genetic insight, 2000 to six years before the last entry year, no earlier higher phase; sponsor tier, phase,
period, therapeutic area and modality; errors clustered by drug. The support indicator is replaced by the bands.

**Primary estimate.** The odds ratio of advancement for the placebo band against none.

**Secondary.** The other bands against none, and supported against placebo (the premium net of the gene);
the same without OMIM; industry sponsors only; the placebo band cut at 0.1 instead of 0.2.

**Reading rule, fixed in advance.** If the interval of the placebo estimate includes 1, genetic evidence for an
unrelated disease does not predict advancement, and the premium belongs to the link between gene and disease. If
it lies above 1, part of the premium reflects the gene, and the premium should be read as supported against
placebo. If it lies below 1, the placebo group differs from the reference in some other way and the comparison of
supported against placebo is the one to read. All estimates are reported.

**Limits.** Similarity between MeSH terms is a coarse measure of relatedness; pleiotropic genes have real effects
on traits with unrelated names; the none group holds targets without any reported association, which differ from
the others in how much they have been studied.
