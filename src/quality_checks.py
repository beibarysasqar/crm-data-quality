import sys
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# same pattern the loader uses to decide if a contact can go to HubSpot
EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def read_csv(name):
    path = DATA_DIR / name
    if not path.exists():
        sys.exit(f"{path} not found, run generate_data.py first")
    # everything as text, so an empty cell is "" and not NaN
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def problems(df, mask, rule):
    res = df[mask].copy()
    # +2: line 1 of the CSV is the header and the index starts at 0
    res.insert(0, "row", res.index + 2)
    res.insert(1, "rule", rule)
    return res


def empty_email(contacts):
    mask = contacts["email"].str.strip() == ""
    return problems(contacts, mask, "empty_email")


def bad_email_format(contacts):
    email = contacts["email"]
    # empty emails have their own rule
    mask = (email.str.strip() != "") & ~email.str.match(EMAIL_RE)
    return problems(contacts, mask, "bad_email_format")


def duplicate_email(contacts):
    email = contacts["email"].str.strip().str.lower()
    # the first occurrence is the original, only the repeats are problems
    mask = (email != "") & email.duplicated(keep="first")
    return problems(contacts, mask, "duplicate_email")


def contact_without_company(contacts):
    mask = contacts["company_id"].str.strip() == ""
    return problems(contacts, mask, "contact_without_company")


def deal_without_amount(deals):
    mask = deals["amount"].str.strip() == ""
    return problems(deals, mask, "deal_without_amount")


def run_all(contacts, deals):
    return [
        empty_email(contacts),
        bad_email_format(contacts),
        duplicate_email(contacts),
        contact_without_company(contacts),
        deal_without_amount(deals),
    ]


def main():
    contacts = read_csv("contacts.csv")
    deals = read_csv("deals.csv")

    found = run_all(contacts, deals)

    print(f"checked {len(contacts)} contacts and {len(deals)} deals")
    total = 0
    for res in found:
        if len(res) == 0:
            continue
        print(f"  {res['rule'].iloc[0]:<26}{len(res)}")
        total += len(res)
    print(f"  {'total':<26}{total}")


if __name__ == "__main__":
    main()
