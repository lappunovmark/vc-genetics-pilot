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

## Second amendment of 19 November 2026 (after the tables were read and checked, before any model was fitted)

**What was read.** `pilot/ipo_holders.py` read the table of 392 of the 398 IPO prospectuses, and of 344 of the
348 filed under the sponsor's own name. Not read: two plain-text filings (2002 and 2004), whose tables are set
with spaces and wrap names over lines (a first attempt misread them, so they are left out rather than keyed by
hand); two prospectuses without a section the reader finds; two without rows it can read.

**Check by eye.** Twenty prospectuses were drawn at random from the own-name sample (seed 20261119). Each table
was rendered with another parser (BeautifulSoup with lxml) and compared row by row with what the reader gave: 95
holders of 5% or more that are not natural persons, each with the right percentage, none missed and none added
(names compared by their beginning). The first comparison found one name with a line of its address in front of
it; the rule that caused it was removed. The reader changed in other ways after that comparison (it reads only
tables whose heading names owners or holders; plain-text filings are left out), so the 95 holders were written
down (`factcheck/ipo_holders_check.csv`) and the final reader is compared with them by
`factcheck/ipo_holders_check.py`: all 95 agree.

**Definitions fixed here.** The plan left these open; they are set before any model is fitted.
* *Holder counted.* A row with 5.0% or more before the offering, as printed, that is not a natural person. A
  natural person is a name without a word that marks an organisation and with a title or degree, or with the
  first name of a director or officer of some prospectus (`person` in `ipo_holders.csv`).
* *Classes.* `pilot/ipo_holder_classes.tsv` first, then `pilot/investor_classes.tsv`; the kind of a corporate
  investor from the new file where it gives one, otherwise from `pilot/corporate_investors.tsv`. The existing
  files are not changed, so the earlier analyses are not affected. All 445 names the existing rules left
  unclassified were read; where the name did not say what the holder is, the footnote of the table was read.
  In the own-name sample there are 1,520 holdings of 5% or more by holders that are not natural persons, in 334
  prospectuses: 806 venture capital, 154 life-science crossover, 124 corporate, 93 asset manager, 83 private
  equity or holding, 36 hedge fund, 13 foundation, university or hospital, 9 credit or secondaries, and 202
  (13%) left unclassified (vehicles of founders and families, and holders that could not be identified). An
  unclassified holder counts as neither venture nor corporate.
* *Venture fund.* Class "venture capital", which includes the venture arms of companies, as in the existing
  rules. *Venture share* is the sum of the percentages of venture funds, capped at 100 (a percentage counts the
  holder's convertible securities, and two holders can report the same shares, so sums can pass 100; no venture
  share in the sample does). *Venture holder* is a venture share above zero.
* *Corporate holder.* A holder whose kind is "pharma corporate" (large or other): a drug, drug-services or
  medical-technology company or its venture arm. *Venture funds only*: a venture holder and no corporate holder.
* *Specialist share*, an added variant declared here: venture capital plus life-science crossover funds, which
  hold shares at the IPO because they buy the last private round.
* *Sponsor and year.* A prospectus belongs to the sponsor names linked to its registrant whose first word is
  the first word of the filer's name at the time (the own-name rule, applied name by name); a sponsor name
  linked to several prospectuses takes the earliest. The IPO year is the year of the prospectus. A sponsor
  whose table was not read is left out; a sponsor whose table was read and names no venture fund above 5% has
  a venture share of zero. (This point first read "belongs to every sponsor name linked to its registrant".
  It was corrected when the model script was written, before any model was fitted: the other names linked to
  a registrant are companies that merged into it later, such as Oncternal into GTx, and had other investors.)
* *Errors.* The plan clusters errors by drug, as the pilot does. The venture share is the same for every
  programme of a sponsor, so each model is also reported with errors clustered by sponsor; the interval by
  drug stays the one the reading rule is applied to, and the interval by sponsor is reported next to it.

## Note of 19 November 2026, after the models

The check by eye of the second amendment was made while the reader was still being corrected, so it does not
show how the final reader does on prospectuses it was not corrected on. Ten more prospectuses were therefore
drawn at random from the own-name sample (seed 20261120, the first twenty left out) and compared in the same way
after the models were run: 46 holders of 5% or more that are not natural persons, all read with the right
percentage, none missed and none added (one of the ten has no such holder, and the reader gives none). Nothing
in the reader, the rules or the models was changed after this check.
