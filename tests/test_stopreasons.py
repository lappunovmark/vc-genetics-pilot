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


def test_financial_group():
    assert FINANCIAL == {"No funding", "M&A / licensing", "Business / strategic"}
    assert classify("Business decision") in FINANCIAL
    assert classify("Safety concerns") not in FINANCIAL
