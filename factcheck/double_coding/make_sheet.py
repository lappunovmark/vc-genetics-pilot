"""Build the blind coding sheet for the 200 held-out stop-reason texts.

Usage (from the repository root): python factcheck/double_coding/make_sheet.py
Reads results/rq2_hand_labels.csv (set == 'held-out (labelled blind)'), shuffles the texts with a fixed seed, and
writes factcheck/double_coding/coding_sheet.xlsx (id, text, drop-down label, confidence, note) and key.csv
(id -> nct_id; do not open it before coding). Labels are not written to the sheet.
"""

import os
import sys

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "pilot"))
from stopreasons import CLASSES  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = [k for k, _ in CLASSES] + ["Other"]
SEED = 20261106


def main():
    d = pd.read_csv(os.path.join(ROOT, "results", "rq2_hand_labels.csv"))
    h = d[d.set.str.startswith("held-out")].sample(frac=1, random_state=SEED).reset_index(drop=True)
    h["id"] = range(1, len(h) + 1)
    h[["id", "nct_id"]].to_csv(os.path.join(HERE, "key.csv"), index=False)

    wb = Workbook()
    ws = wb.active
    ws.title = "Coding"
    head = Font(name="Arial", bold=True)
    body = Font(name="Arial")
    fill = PatternFill("solid", fgColor="FFFF00")
    ws.append(["id", "why_stopped (text as registered on ClinicalTrials.gov)", "label", "confidence", "note"])
    for c in ws[1]:
        c.font = head
    for row in h.itertuples(index=False):
        ws.append([int(row.id), row.why_stopped, None, None, None])
    n = len(h) + 1
    dv = DataValidation(type="list", formula1='"' + ",".join(LABELS) + '"', allow_blank=True, showDropDown=False)
    dv.error = "Pick one of the labels in the list"
    dv.errorTitle = "Label"
    ws.add_data_validation(dv)
    dv.add(f"C2:C{n}")
    dv2 = DataValidation(type="list", formula1='"high,low"', allow_blank=True)
    ws.add_data_validation(dv2)
    dv2.add(f"D2:D{n}")
    for r in range(2, n + 1):
        for col in "ABCDE":
            ws[f"{col}{r}"].font = body
        ws[f"B{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws[f"E{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws[f"C{r}"].fill = fill
    for col, width in zip("ABCDE", (6, 90, 30, 12, 40)):
        ws.column_dimensions[get_column_letter("ABCDE".index(col) + 1)].width = width
    ws.freeze_panes = "A2"

    lg = wb.create_sheet("Read me")
    lines = [
        "Blind double-coding of stop reasons (see codebook.md in this folder).",
        "Fill in column C of the sheet 'Coding' (yellow cells) with one label per row from the drop-down list.",
        "Column D: 'low' when unsure (optional). Column E: a short note for ambiguous texts (optional).",
        "Code the reason the sponsor gives; a scientific or operational reason wins over a business one; negated "
        "mentions do not count.",
        "Do not open results/rq2_hand_labels.csv, results/rq2_label_sample.csv or key.csv before you finish.",
        "When done: python factcheck/double_coding/double_coding_eval.py",
        "",
        "Labels: " + "; ".join(LABELS),
        "",
        "Example row (format only): id 0 | 'Sponsor decision due to portfolio prioritization' | Business / strategic "
        "| high | (empty)",
    ]
    for i, line in enumerate(lines, 1):
        lg[f"A{i}"] = line
        lg[f"A{i}"].font = body
    lg.column_dimensions["A"].width = 120
    wb.save(os.path.join(HERE, "coding_sheet.xlsx"))
    print(f"wrote coding_sheet.xlsx with {len(h)} texts and key.csv")


if __name__ == "__main__":
    main()
