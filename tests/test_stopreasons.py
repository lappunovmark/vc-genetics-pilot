"""Unit tests for the ClinicalTrials.gov why_stopped classifier (pilot/stopreasons.py)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pilot"))
from stopreasons import FINANCIAL, classify  # noqa: E402


@pytest.mark.parametrize(
    "text, label",
    [
        ("Terminated due to lack of funding", "No funding"),
        ("The sponsor ran out of money", "No funding"),
        ("Study stopped for safety reasons", "Safety / benefit-risk"),
        ("Futility at interim analysis", "Efficacy / futility"),
        ("Slow enrollment", "Enrolment"),
        ("Study halted due to COVID-19 pandemic", "COVID-19"),
        ("Company acquired; program discontinued", "M&A / licensing"),
        ("Strategic portfolio prioritization", "Business / strategic"),
        ("", "No reason"),
    ],
)
def test_basic_labels(text, label):
    assert classify(text) == label


@pytest.mark.parametrize(
    "text, label",
    [
        # negated or neutral safety mentions must not trigger the safety class
        ("Not due to safety concerns; business decision", "Business / strategic"),
        ("Data safety monitoring board recommended stopping for futility", "Efficacy / futility"),
        ("The safety profile remained unchanged; sponsor decision", "Sponsor decision, unspecified"),
    ],
)
def test_negation_handling(text, label):
    assert classify(text) == label


@pytest.mark.parametrize(
    "text, label",
    [
        # v4: business stops that v3 left in Other
        ("Management decision", "Business / strategic"),
        ("The development program has been terminated", "Business / strategic"),
        ("Company focus on other projects", "Business / strategic"),
        ("Pharmaceutical sponsor withdrew financial support", "No funding"),
        ("Grant was not renewed", "No funding"),
        ("Sponsor is winding down business operations", "No funding"),
        ("Insys Therapeutics filed Chapter 11 and terminated all studies", "No funding"),
        ("The applicant decided to close the study", "Sponsor decision, unspecified"),
        ("No longer pursued for strategic reasons", "Business / strategic"),
        # v4 narrowing: a regulatory or data-no-longer-needed stop is not a business decision ...
        ("FDA advised that study is no longer required", "Other"),
        ("Study data no longer needed", "Other"),
        # ... and a stop explained by other studies' results is not one either
        ("Results from other studies did not support continuation of this trial", "Other"),
        ("Increased risk of PML associated with raptiva in other studies", "Other"),
        # patterns removed on 7 Nov 2026 because their only support was a held-out text
        ("Project adjustment", "Other"),
        ("Closed due to cessation of activities", "Other"),
        # a scientific or operational reason stated with a business one still wins
        ("Program discontinued after slow enrollment", "Enrolment"),
        ("Development halted following safety findings", "Safety / benefit-risk"),
    ],
)
def test_v4_patterns(text, label):
    assert classify(text) == label


def test_financial_group():
    assert FINANCIAL == {"No funding", "M&A / licensing", "Business / strategic"}
    assert classify("Business decision") in FINANCIAL
    assert classify("Safety concerns") not in FINANCIAL
