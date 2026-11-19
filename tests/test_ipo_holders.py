"""ipo_holders: the principal stockholders table of a prospectus is read in the layouts met in the filings."""

import gzip
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pilot"))
import ipo_holders as h  # noqa: E402

INTRO = (
    "<p>PRINCIPAL STOCKHOLDERS</p><p>The following table sets forth the beneficial ownership of our common stock.</p>"
)
END = "<p>DESCRIPTION OF CAPITAL STOCK</p><p>General</p>"


def row(*cells):
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def read(body):
    lines, kind = h.to_lines("<html><body><p>Summary</p>" + body + "</body></html>")
    assert kind == "html"
    sec, rows = h.best(lines)
    return {r[0]: r for r in rows}


def modern():
    """Sub-headings, an options column of dashes before the percentage, the sign in a cell of its own."""
    t = "<table>"
    t += row("", "", "Number of shares", "", "Percentage owned", "", "")
    t += row("Name of beneficial owner", "", "Stock", "Options", "Before the offering", "", "After the offering")
    t += row("5% and Greater Stockholders:", "", "", "", "", "", "")
    t += row("Entities affiliated with Third Rock Ventures<sup>(1)</sup>", "", "12,353,248", "—", "28.8", "%", "21.7%")
    t += row("Alpha Venture Fund II, L.P.(2)<br>25 First Street, Suite 303<br>Cambridge, MA 02141", "", "2,005,578", "—", "12.5", "", "9.3")  # fmt: skip
    t += row("Named Executive Officers and Directors:", "", "", "", "", "", "")
    t += row("Jane A. Doe, M.D., Ph.D.(3)", "", "—", "279,835", "1.9", "", "1.4")
    t += row("John Roe", "", "117,104", "—", "*", "", "*")
    t += row("Mary Major", "", "—", "—", "—", "", "—")
    t += row(
        "All executive officers and directors as a group (3 persons)", "", "117,104", "279,835", "2.6", "%", "2.0%"
    )
    return t + "</table>"


def test_percentage_before_the_offering_is_the_first_percentage_column():
    r = read(INTRO + modern() + END)
    assert r["Entities affiliated with Third Rock Ventures"][1:3] == (28.8, "holders")
    assert r["Alpha Venture Fund II, L.P"][1] == 12.5  # address and footnote mark are not part of the name
    assert r["Jane A. Doe, M.D., Ph.D"][1:4] == (1.9, "insiders", False)
    assert r["John Roe"][1] == 0.0 and r["Mary Major"][1] == 0.0  # a star and a dash are read as 0
    assert not any("group" in n for n in r)  # the row for all directors and officers together is left out
    assert r["Entities affiliated with Third Rock Ventures"][3] and not r["John Roe"][3]


def test_name_on_a_row_of_its_own_above_the_address():
    t = "<table>" + row("Name and Address of Beneficial Owner", "", "Shares", "Before Offering", "After Offering")
    t += row("5% Stockholders", "", "", "", "")
    t += row("Entities affiliated with Sevin Rosen Funds(2)", "", "", "", "")
    t += row("", "Two Galleria Tower", "", "", "")
    t += row("", "Dallas, TX 75240", "3,167,694", "16.2%", "11.7%")
    t += row("Glaxo Group Limited", "", "", "", "")
    t += row("", "Greenford", "", "", "")
    t += row("", "UB6 0NN", "1,504,149", "7.7%", "7.6%")
    t += row("Directors", "", "", "", "")
    t += row("Stephen Dow(10)", "", "", "", "")
    t += row("", "Dallas, TX 75240", "3,167,694", "16.2%", "11.7%")
    t += row("Ann Smith", "", "5,000", "*", "*") + "</table>"
    r = read(INTRO + t + END)
    assert r["Entities affiliated with Sevin Rosen Funds"][1:3] == (16.2, "holders")
    assert r["Glaxo Group Limited"][1] == 7.7
    assert r["Stephen Dow"][1:3] == (16.2, "insiders")  # the footnote number is not taken for an address
    assert not any("Dallas" in n or "UB6" in n for n in r)


def test_address_rows_under_a_name_are_not_joined_to_the_next_name():
    t = "<table>" + row("Name of Beneficial Owner", "Shares", "Before Offering", "After Offering")
    t += row("Funds affiliated with Domain Associates, L.L.C.(1)", "4,023,807", "21.3%", "15.6%")
    t += row("One Palmer Square, Suite 515<br>Princeton, NJ 08542", "", "", "")
    t += row("KPCB Holdings, Inc.(3)", "3,763,807", "20.0", "14.6")
    t += row("2750 Sand Hill Road<br>Menlo Park, CA 94025", "", "", "")
    t += row("Scale Venture Partners II, LP(5)", "2,797,424", "14.8", "10.8") + "</table>"
    r = read(INTRO + t + END)
    assert set(r) == {"Funds affiliated with Domain Associates, L.L.C", "KPCB Holdings, Inc", "Scale Venture Partners II, LP"}  # fmt: skip
    assert r["KPCB Holdings, Inc"][1] == 20.0


def test_table_that_runs_over_a_page_and_a_financial_table_after_it():
    first = "<table>" + row("Name of beneficial owner", "Number", "Percentage", "Number", "Percentage")
    first += row("5% shareholders", "", "", "", "")
    first += row("TOLEFI SA(1)", "2,267,844", "28.90%", "2,267,844", "24.6%")
    first += row("Medisun Ltd", "568,180", "7.24%", "568,180", "6.2%")
    first += row("SRIW SA(2)", "400,000", "5.10%", "400,000", "4.3%") + "</table>"
    second = "<p>165</p><p>Principal shareholders</p><table>"
    second += row("Name of beneficial owner", "Number", "Percentage", "Number", "Percentage")
    second += row("Directors and Members of Executive Management Team", "", "", "", "")
    second += row("Michel Lussier", "162,370", "2.07%", "162,370", "1.76%")
    second += row("William Wijns", "4,079", "*", "4,079", "*")
    second += row("Patrick Jeanmart", "13,924", "*", "13,924", "*") + "</table>"
    money = "<p>LEGAL MATTERS</p><table>" + row("", "Year ended December 31,", "") + row("", "2014", "2013")
    money += row("Revenue", "1,200", "900") + row("Net loss per share", "0.76", "0.52")
    money += row("Effective tax rate", "22.0%", "21.0%") + row("Total assets", "5,000", "4,000") + "</table>"
    r = read("<p>Principal shareholders</p><p>The beneficial ownership of our shares.</p>" + first + second + money)
    assert r["TOLEFI SA"][1:3] == (28.9, "holders") and r["Michel Lussier"][1:3] == (2.07, "insiders")
    assert not any(n in r for n in ("Revenue", "Net loss per share", "Effective tax rate", "Total assets"))


def test_section_found_by_the_heading_row_of_the_table():
    t = "<p>SHARE OWNERSHIP</p><table>" + row("Name of Beneficial Owner", "Shares", "Percent before", "Percent after")
    t += row("Roivant Sciences Ltd.(1)", "20,025,098", "100", "%", "76", "%")
    t += row("Keith Katkin", "—", "—", "—") + row("Myrtle Potter", "—", "—", "—") + "</table>"
    r = read(t + END)
    assert r["Roivant Sciences Ltd"][1] == 100.0  # a whole number is a percentage where the sign follows it


def test_cells():
    assert h.token("12,345")[2] == "big" and h.token("17.6 %") == (17.6, True, "num")
    assert h.token("—")[2] == "dash" and h.token("*")[2] == "star" and h.token("(3)")[2] == "skip"
    assert h.token("Less than 1%")[2] == "star" and h.token("Stock")[2] == "text"
    assert (
        h.name_of("S.L.A. Pharma AG" + h.INNER + "Rebgasse 2" + h.INNER + "Liestal, Switzerland") == "S.L.A. Pharma AG"
    )
    assert h.name_of("Hillel Gross" + h.MARK + "(9)" + h.MARK + h.INNER + "c/o AmTrust Financial") == "Hillel Gross"
    assert (
        h.is_address("82 Devonshire St.") and h.is_address("Boston, MA 02109") and not h.is_address("Stephen Dow(10)")
    )
    assert not h.is_address("New Enterprise Associates 14, L.P.")


def test_natural_persons_are_told_from_funds(tmp_path):
    os.makedirs(tmp_path / "docs")
    docs = {"1_a": INTRO + modern() + END}
    t = "<table>" + row("Name of Beneficial Owner", "Shares", "Before Offering", "After Offering")
    t += row("5% Stockholders", "", "", "") + row("Jane Smith", "900,000", "9.0%", "7.0%")
    t += row("Entities affiliated with SR One", "800,000", "8.0%", "6.0%") + row("Venrock", "700,000", "7.0%", "5.0%")
    t += row("Lakeview EyeTech", "600,000", "6.0%", "4.0%") + "</table>"
    docs["2_b"] = INTRO + t + END
    for k, v in docs.items():
        with gzip.open(tmp_path / "docs" / f"{k}.htm.gz", "wt", encoding="utf-8") as fh:
            fh.write("<html><body>" + v + "</body></html>")
    idx = pd.DataFrame({"cik": ["1", "2"], "accession": ["a", "b"], "name": ["A", "B"], "date": ["2015-01-01"] * 2})
    idx.to_csv(tmp_path / "ipo_prospectus_index.csv", index=False)
    h.main(str(tmp_path), str(tmp_path))
    d = pd.read_csv(tmp_path / "ipo_holders.csv").set_index("holder")
    assert d.loc["Jane Smith", "person"] == 1  # "Jane" is the first name of a director in the other prospectus
    assert d.loc[["Entities affiliated with SR One", "Venrock", "Lakeview EyeTech"], "person"].sum() == 0
    log = pd.read_csv(tmp_path / "ipo_holders_log.csv").set_index("accession")
    assert log.loc["b", "holders_5pct"] == 3 and log.loc["a", "status"] == "read"
