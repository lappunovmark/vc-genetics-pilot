"""Keyword classifier for ClinicalTrials.gov why_stopped text (pilot).

v4 (7 Nov 2026): v3 plus patterns for business stops that v3 left in 'Other', found by cross-checking v3 against the
Open Targets StopReasons predictions (factcheck/stopreasons_crosscheck.py): management or company decisions, programmes
discontinued (noun first), company focus or goals, withdrawn support, wind-downs, expired grants, and a catch-all for a
bare decision or cancellation in the last class. v3 was revised after hand-labelling 400 texts (a stratified sample of
stopped industry drug trials, 2012-2026).
Rule for every pattern: it must match at least one text outside the 200 held-out texts (in the 400 tuning texts or in
the StopReasons file), so that the held-out score is not tuned to the held-out set. factcheck/stopreasons_support.py
checks this (the StopReasons file is read without the 97 held-out trials it contains); two v4 patterns that failed it
("cessation of activities", "project adjustment": one held-out text each, nothing else) were removed on 7 Nov 2026
before any number built on them reached the paper, the README or the public repository. The same day two v3
patterns were narrowed after reading the texts they matched in the StopReasons file (held-out trials excluded):
"no longer required/needed/relevant" fired on regulatory or data-no-longer-needed stops and now needs a strategic or
commercial context, and "other studies" fired on stops explained by the results of other studies and is dropped
("other projects", "broader programme objectives" and "focus on other ..." remain).
One label per text, first match in priority order. A scientific or operational reason stated alongside a business
one wins, so a stop is called financial/strategic only when nothing scientific or operational is given.
Negated or neutral mentions ("not due to safety", "no safety concerns", "the safety profile remained unchanged",
"safety committee") are removed before matching; v1 had no negation handling and labelled about 8% of texts
Safety wrongly.
"""

import re

_T = r"(safety|efficacy|tolerability|regulatory|benefit\W{0,3}risk|risk\W{0,3}benefit)"
_CONJ = r"((\s*(and/or|and|or|/|nor|,)\s*(any\s+|the\s+|\w+'s\s+)?" + _T + r")*)"
_NOUN = (
    r"(\s+(concerns?|issues?|reasons?|signals?|findings?|profile|data|considerations?|decision|related|assessment))?"
)
NEG = [
    re.compile(p, re.I)
    for p in [
        r"\bno\s+(\w+\s+){0,3}?(changes?)\s+(of|to|in)\s+the\s+(\w+\s+)?" + _T + _CONJ + _NOUN,
        r"\b(not|n't)\s+(\w+\s+){0,3}?(due to|related to|based on|linked to|prompted by|driven by|for|because of|caused by|"
        r"a result of|the result of|in response to|connected to|associated with)\b[^.;:]{0,50}?\b" + _T + _CONJ + _NOUN,
        r"\b(unrelated to|neither|nor|none of)\s+(\w+\s+){0,3}?" + _T + _CONJ + _NOUN,
        r"\bno\s+(\w+\s+){0,3}?" + _T + _CONJ + r"\s+(\w+\s+){0,2}?(concerns?|issues?|reasons?|signals?|findings?|"
        r"considerations?|data|problems?)",
        r"\bno\s+concerns?\s+(with|about|regarding|over)\s+(\w+\s+)?" + _T,
        r"\bnot\s+an?\s+" + _T + r"\s+(decision|issue|concern|reason)",
        r"\b(known\s+|established\s+)?safety\s+profile\s+(of\s+\S+\s+)?(\w+\s+){0,2}?(remained|remains|is|was|being)\s+"
        r"(\w+\s+)?(unchanged|benign|favou?rable|acceptable|good|consistent)",
        r"\b(data\s+)?safety\s+(monitoring\s+|review\s+)?(committee|board)\b",
    ]
]
CLASSES = [
    (
        "No funding",
        r"fund|financ|budget|insolven|bankrupt|cash|capital|money|liquidat|ceased operations|"
        r"lack of resources|resource (constraints?|limitations?)|limited resources|"
        # v4: wind-downs, withdrawn support, expired grants, cost
        r"wind(ing)? down|chapter (7|11)|receivership|"
        r"ceased (its |all |to )?(support|operat)|withdr(ew|awn|awal of|aw) (its |their |all |the )?(financial )?support|"
        r"grant (expired|ended|has ended|was not renewed|funding)|cost constraints?|seeking (research )?(grant|funding)",
    ),
    (
        "Safety / benefit-risk",
        r"safety|adverse|toxic|death|died|side[- ]effect|tolerab|clinical hold|hepatotox|"
        r"transaminase|agranulocyt|\bsaes?\b|serious adverse|benefit\W{0,3}risk|risk\W{0,3}benefit|"
        r"risk profile|\bhold\b.*\b(fda|ansm|ema|authorit)|(fda|ansm|authorit).*\bhold\b",
    ),
    (
        "Efficacy / futility",
        r"futil|efficac|lack of (\w+ )?(clinical )?(evidence|benefit|activity|effect|response)|"
        r"no (clinical )?(benefit|effect)|superiority|interim analys|sufficiently encouraging|"
        r"(end ?points?|objectives?|goals?|criteria|response)\b[^.;]{0,30}\b(not (met|achieved)|did not)|"
        r"did not (meet|achieve|demonstrate|show) (the |its |a |any |sufficient )?(primary|pre-?specified|"
        r"co-primary|study'?s|targeted|statistical|efficacy|clinical|endpoint)|"
        r"failed to (meet|demonstrate|show)|insufficient (evidence|data|activity|response)|modest activity|"
        r"based on (the )?(overall |available |emerging |interim |new |current )?(data|results?|analysis)|"
        r"statistical significance|absence of encouraging|data (do|does|did) not support",
    ),
    ("COVID-19", r"covid|sars-cov|coronavirus|pandemic"),
    (
        "Enrolment",
        r"(?<!before )(?<!prior to )(enrol|enroll)|recruit|accru|screen|patient population|identifiable patients|"
        r"eligible (subjects|patients)|feasibility|no (patients|participants|subjects)|insufficient interest",
    ),
    (
        "M&A / licensing",
        r"acqui|merger|divest|licens|rights\b[^.;]{0,30}\breturned|transferred to|partner|change of sponsor",
    ),
    (
        "Business / strategic",
        r"business|strateg|portfolio|priorit|commercial(?!ly available)|corporate|r ?\\? ?& ?d|"
        r"development (plan|strategy|program|focus|goals)|realloc|realign|refocus|"
        r"market (conditions|dynamics|landscape|environment)|landscape|competitive|"
        r"(research|development) status|status of the same target|"
        r"no longer (pursu|of (strategic |commercial |business )?interest)|not required for development|"
        r"(stop|ceas|halt|end|discontinu|terminat)\w*\s+(\w+\s+){0,3}?(develop\w*|program(me)?)\b|"
        r"development discontinued|not (to )?pursue|did not continue with development|"
        # v4: programme or development stopped (noun first), no-go decisions, company focus or goals, resources
        # moved to other projects, reassessed need, marketing discontinued
        r"(develop\w*|program(me)?s?|project)\s+(\w+\s+){0,2}?(halted|terminated|discontinued|cancell?ed|ceased|stopped|ended)|"
        r"no[- ]go\b|management decision|company (focus|policy|goals?|re-?evaluation|shifted|has decided|decided)|"
        r"(focus|redirect\w*|allocat\w*)\s+(\w+\s+){0,2}?(resources|on other|to other|other projects)|"
        r"\b(other|broader) (projects?|program(me)? objectives)\b|reassess\w* of the (medical|commercial|clinical) need|"
        r"marketing of (this|the) product|scope of the program|development timelines?|"
        r"not (critical|needed|necessary) (to|for) (the )?(continued |further )?(evaluation|development)",
    ),
    (
        "Sponsor decision, unspecified",
        r"sponsor|sponser|company decision|internal decision|administrative|voluntar|"
        r"decision from the sponsor|at .*discretion|"
        # v4: a decision, cancellation or withdrawal by the company or its team with no reason given (last class, so
        # it fires only when no reason above matched)
        r"\bdecision\b|\bdecided\b|\bcancel|withdrawn by (industry|the company)|"
        r"(closed|halted|stopped|terminated|discontinued) by (the )?(company|industry|\w+ pharma\w*|\w+ therapeutics)|"
        r"company (has )?(withdr|discontinu|terminat|stopp)",
    ),
]
_RX = [(k, re.compile(v, re.I)) for k, v in CLASSES]
FINANCIAL = {"No funding", "M&A / licensing", "Business / strategic"}


def clean(text):
    for rx in NEG:
        text = rx.sub(" ", text)
    return text


def classify(text):
    if not isinstance(text, str) or not text.strip():
        return "No reason"
    t = clean(text)
    for k, rx in _RX:
        if rx.search(t):
            return k
    return "Other"
