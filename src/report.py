import sys
from pathlib import Path

import pandas as pd

import quality_checks as qc

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

DESCRIPTIONS = {
    "empty_email": "Contact has no email",
    "bad_email_format": "Email does not look like name@domain.tld",
    "duplicate_email": "Email is already used by an earlier contact",
    "contact_without_company": "Contact is not linked to a company",
    "deal_without_amount": "Deal has no amount (row in deals.csv)",
}


def build_problems(found):
    # contacts and deals have different columns, only these two are common
    df = pd.concat([res[["row", "rule"]] for res in found], ignore_index=True)
    df["description"] = df["rule"].map(DESCRIPTIONS)
    return df


def build_summary(problems):
    counts = problems["rule"].value_counts()
    rows = []
    # every rule gets a line, so a clean report still shows it with 0
    for rule in DESCRIPTIONS:
        rows.append({"rule": rule, "count": int(counts.get(rule, 0))})
    return pd.DataFrame(rows)


def write_report(found, name, folder=REPORTS_DIR):
    problems = build_problems(found)
    summary = build_summary(problems)
    path = Path(folder) / f"quality_{name}.xlsx"
    with pd.ExcelWriter(path) as writer:
        problems.to_excel(writer, sheet_name="problems", index=False)
        summary.to_excel(writer, sheet_name="summary", index=False)
    return path


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "before"
    contacts = qc.read_csv("contacts.csv")
    deals = qc.read_csv("deals.csv")

    found = qc.run_all(contacts, deals)
    path = write_report(found, name)
    total = sum(len(res) for res in found)
    print(f"{total} problems written to {path}")


if __name__ == "__main__":
    main()
