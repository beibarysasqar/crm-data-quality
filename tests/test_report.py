import pandas as pd

import quality_checks as qc
import report


def make_found(emails, amounts):
    contacts = pd.DataFrame({
        "contact_id": [f"P{i:03d}" for i in range(1, len(emails) + 1)],
        "email": emails,
        "company_id": ["C001"] * len(emails),
    })
    deals = pd.DataFrame({
        "deal_id": [f"D{i:03d}" for i in range(1, len(amounts) + 1)],
        "amount": amounts,
    })
    return qc.run_all(contacts, deals)


def test_build_problems_columns():
    found = make_found(["a@x.com", "", "bad"], ["100", ""])
    df = report.build_problems(found)
    assert list(df.columns) == ["row", "rule", "description"]
    assert list(df["rule"]) == ["empty_email", "bad_email_format", "deal_without_amount"]
    assert list(df["row"]) == [3, 4, 3]


def test_build_problems_has_description():
    found = make_found(["", "a@x.com"], ["100"])
    df = report.build_problems(found)
    assert list(df["description"]) == [report.DESCRIPTIONS["empty_email"]]


def test_build_summary_counts():
    found = make_found(["", "", "a@x.com", "a@x.com"], ["", "5"])
    summary = report.build_summary(report.build_problems(found))
    counts = dict(zip(summary["rule"], summary["count"]))
    assert counts["empty_email"] == 2
    assert counts["duplicate_email"] == 1
    assert counts["deal_without_amount"] == 1
    # rules with nothing found stay in the summary
    assert counts["bad_email_format"] == 0
    assert len(summary) == len(report.DESCRIPTIONS)


def test_write_report_sheets(tmp_path):
    found = make_found(["", "a@x.com"], ["", ""])
    path = report.write_report(found, "test", tmp_path)
    assert path.name == "quality_test.xlsx"
    sheets = pd.read_excel(path, sheet_name=None)
    assert list(sheets) == ["problems", "summary"]
    assert len(sheets["problems"]) == 3
    assert list(sheets["summary"].columns) == ["rule", "count"]


def test_write_report_clean_data(tmp_path):
    found = make_found(["a@x.com", "b@x.com"], ["100"])
    path = report.write_report(found, "clean", tmp_path)
    sheets = pd.read_excel(path, sheet_name=None)
    assert len(sheets["problems"]) == 0
    assert sheets["summary"]["count"].sum() == 0
