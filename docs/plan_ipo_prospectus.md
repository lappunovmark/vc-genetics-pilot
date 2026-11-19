# Plan: investors named in IPO prospectuses (written before the prospectuses were downloaded)

Written on 19 November 2026, before any prospectus was downloaded or read.

**Why.** The pilot names a sponsor's investors only where an open source does: owners above 5% in Schedules 13D and
13G (filed after a company is public, undated to the IPO), and venture rounds in a Crunchbase export that ends in
December 2015. A licensed deal database is not available to the author. The final prospectus of an initial public
offering (form 424B4) lists every holder of more than 5% of the company just before the offering, with the
percentage held. For sponsors that went public this gives the investors by name at a known date, including the
IPOs of 2016–2026 that the Crunchbase export does not cover.

**Sample.** Non-top-20 industry sponsors with an EDGAR registrant (`owners_link.py`). The IPO prospectus of a
registrant is its first 424B4 filed on or after its first S-1 or F-1, if the registrant filed no annual report
(10-K, 20-F, 40-F) before that registration. The EDGAR index (2001–2026) gives 426 such filings. The primary sample
is the filings whose filer name at the time is the sponsor's own name (same first word of the normalised name):
371 by a count made from the index alone. The other 55 are later renamings or companies that merged into a listed
company; they are downloaded but set aside, because telling the two apart needs a decision case by case.

**What is read from a prospectus.** The table of principal stockholders: each holder of more than 5% that is not a
natural person, and the percentage of shares it held before the offering. A parser extracts the table; a prospectus
whose table cannot be read is counted and left out, and a random sample of 20 parsed prospectuses is compared with
the document by eye before any model is fitted.

**Classes of holder.** The rules already in the repository (`pilot/investor_classes.tsv`,
`pilot/corporate_investors.tsv`) are applied first. Names they leave unclassified are read by frequency and the
rules extended, as was done for Schedules 13D and 13G. The extended rules are committed before any model with them
is fitted, and are not changed afterwards.

**Measures, per sponsor at its IPO.**
* *venture holder*: at least one venture-capital fund among the holders above 5%;
* *venture share*: the sum of the percentages held by venture-capital funds before the offering;
* *corporate holder*: a drug or medical-technology company (or its venture arm) among the holders above 5%.

**Outcome and models.** The selection model of the pilot (ex-ante genetic support of a programme at its first
trial; first-trial period, therapeutic area, modality and sponsor size; errors clustered by drug), on programmes of
the sponsors in the sample. Programmes first tried no later than the year of the IPO are the main set, because the
investors named in the prospectus were there when those programmes were chosen; all programmes are the second set.

**Primary estimate.** The odds ratio of ex-ante support per 10 percentage points of *venture share*, on programmes
first tried no later than the IPO year. A continuous measure is primary because nearly all sponsors that went
public have a venture holder, so a yes/no comparison rests on very few sponsors without one.

**Secondary.** *Venture holder* yes against no; *corporate holder* against venture funds only; the same on all
programmes; the same with the dated Open Targets measure; IPOs of 2016–2026 alone; advancement to the next phase
with ex-ante support in the model. Agreement of *venture holder* with the venture flag of Jay Ritter's IPO list and
with the owners in Schedules 13D and 13G is reported as a check of the measure, not as a result.

**Reading rule, fixed in advance.** If the interval of the primary estimate excludes 1, the share of a sponsor
held by venture funds at its IPO goes with more (above 1) or less (below 1) genetic support. If it includes 1, the
data do not show a link. The comparison of corporate holders with venture funds only is read the same way. All
estimates are reported whatever they show.

**Known limits.** Only sponsors that went public, and only holders above 5% at the IPO, so early investors who
were diluted below 5% are not seen; the prospectus shows who held shares at the IPO, not who invested in which
round or when; IPOs before 2001 and IPOs registered on other forms are not covered; a sponsor that reached the
market through a merger with a listed company has no prospectus of its own.

## Amendment of 19 November 2026 (after the download, before any table was read in bulk or any model fitted)

The first prospectus opened to write the parser, of The Medicines Company (March 2003), is a follow-on offering:
the company went public in 2000, and the EDGAR index used here starts in January 2001, so its first registration
in the index precedes its first annual report in the index. The rule for an IPO prospectus is therefore tightened:
the registrant filed no annual report before the *prospectus* either, and its first registration in the index is
dated 1 April 2001 or later (by then a company that went public in 2000 has filed an annual report). The counts
under the amended rule are written by `fetch_ipo_prospectus.py`; the filings it no longer keeps stay downloaded
and are not used. Nothing else in the plan changes.
