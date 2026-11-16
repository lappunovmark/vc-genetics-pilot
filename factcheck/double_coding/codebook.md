# Codebook for the blind double-coding of stop reasons

Why this exists: the 200 held-out `why_stopped` texts that validate the stop-reason classifier (83.0% agreement,
κ 0.79) were first labelled by an AI research assistant. The author codes the same texts blind
([roadmap](../../docs/roadmap.md)), so that the validation rests on human labels. This folder holds the sheet to fill in and the script that scores it.

## How to code

1. Open `coding_sheet.xlsx`. Do not open `results/rq2_hand_labels.csv` or `results/rq2_label_sample.csv` until you
   have finished: the sheet is blind on purpose (texts shuffled, trial ids removed).
2. For every row, pick exactly one label in column C from the drop-down list. Use column D for doubts (`low`) and
   column E for a note when the text is ambiguous; both are optional.
3. Code the reason the sponsor **gives**, not what you suspect behind it. A stated lack of funding comes first
   ("lack of funding and slow accrual" → No funding). Otherwise, if a text gives a scientific or operational reason
   together with a business one ("portfolio prioritisation following interim efficacy data"), the scientific or
   operational reason wins. These are the rules the classifier follows, so the comparison is fair.
4. Negated mentions do not count: "terminated by the sponsor, not due to safety concerns" is *not* a safety stop.
5. When you are done, run from the repository root:
   `python factcheck/double_coding/double_coding_eval.py` — it writes `results/double_coding.txt` with the
   agreement between your labels, the first-pass labels and the classifier, Cohen's κ, precision and recall of the
   financial-or-strategic class, and the list of disagreements for adjudication.

## Labels (one per text, in the classifier's order of priority)

| Label | Use when the text says… | Typical wording |
|---|---|---|
| No funding | the sponsor ran out of money or could not finance the trial | funding, financing, budget, insolvency, bankruptcy, cash, ceased operations, lack of resources |
| Safety / benefit-risk | a safety signal, adverse events, toxicity, a clinical hold, or an unfavourable benefit–risk assessment | safety, adverse events, toxicity, deaths, tolerability, clinical hold, benefit/risk |
| Efficacy / futility | the drug did not work, or an interim or external analysis made success unlikely | futility, lack of efficacy, endpoint not met, interim analysis, insufficient activity, based on the data |
| COVID-19 | the pandemic | COVID-19, pandemic, SARS-CoV-2 |
| Enrolment | too few or no patients could be enrolled or recruited, or the study was not feasible | enrolment, recruitment, accrual, feasibility, no eligible patients |
| M&A / licensing | an acquisition, merger, divestment, licence or transfer of the asset or the sponsor | acquired, merger, licensed, rights returned, transferred to, change of sponsor |
| Business / strategic | a business, strategic, portfolio, commercial or development-plan decision; the programme was discontinued; the market or competitive landscape changed | business decision, strategic, portfolio prioritisation, commercial reasons, refocus, development discontinued, no longer pursued |
| Sponsor decision, unspecified | the sponsor decided to stop and gives no reason beyond that | sponsor decision, company decision, administrative reasons, voluntarily withdrawn |
| Other | none of the above: supply or manufacturing problems, site or investigator issues, regulatory requests without a safety or efficacy content, study design changes, "study replaced by another study", unclear text | drug supply, manufacturing, investigator left, protocol redesign, regulatory request |

Notes on borderline cases:

* "Terminated by the sponsor for business reasons" → Business / strategic (a reason is given).
  "Terminated by the sponsor" alone → Sponsor decision, unspecified.
* "Strategic decision following the acquisition of X" → M&A / licensing (the event named is the acquisition).
* "Lack of funding due to the company's strategic refocus" → No funding (money is the stated reason).
* "Slow enrolment and change in development strategy" → Enrolment (operational reason wins).
* Regulatory: a hold or request tied to safety → Safety / benefit-risk; a regulatory request about the design or
  the programme with no safety or efficacy content → Other.
* "Study replaced by a new protocol" or "merged into another study" → Other.

The financial-or-strategic class used in the analysis is the union of No funding, M&A / licensing and
Business / strategic. Sponsor decision, unspecified is kept apart because it gives no reason.
