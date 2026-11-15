import re
import sys
from pathlib import Path

import pandas as pd

import hubspot_client as hs

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SHOW = 3

# HubSpot industry is a dropdown with fixed internal values
INDUSTRY_MAP = {
    "Software": "COMPUTER_SOFTWARE",
    "Finance": "FINANCIAL_SERVICES",
    "Healthcare": "HOSPITAL_HEALTH_CARE",
    "Retail": "RETAIL",
    "Manufacturing": "MACHINERY",
    "Marketing": "MARKETING_AND_ADVERTISING",
}

# association type ids defined by HubSpot
CONTACT_TO_COMPANY = 279
DEAL_TO_COMPANY = 341

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def read_csv(name):
    path = DATA_DIR / name
    if not path.exists():
        sys.exit(f"{path} not found, run generate_data.py first")
    # everything as text, so ids and amounts go to HubSpot exactly as in the file
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def pick(row, cols):
    return {c: row[c] for c in cols if row[c]}


def link_to(company_hs_id, type_id):
    return [{
        "to": {"id": company_hs_id},
        "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": type_id}],
    }]


def create(obj_type, props, company_hs_id=None, type_id=None):
    body = {"properties": props}
    if company_hs_id:
        body["associations"] = link_to(company_hs_id, type_id)
    return hs.request("POST", f"/crm/v3/objects/{obj_type}", body=body)


def load_companies(df, apply):
    existing = {}
    for c in hs.get_companies():
        domain = c["properties"].get("domain")
        if domain:
            existing[domain.lower()] = c["id"]

    # CSV company_id -> HubSpot id
    ids = {}
    created = skipped = 0
    for row in df.to_dict("records"):
        if row["domain"].lower() in existing:
            ids[row["company_id"]] = existing[row["domain"].lower()]
            skipped += 1
            continue
        props = pick(row, ["name", "domain", "numberofemployees", "annualrevenue", "city", "country"])
        if row["industry"] in INDUSTRY_MAP:
            props["industry"] = INDUSTRY_MAP[row["industry"]]
        hs_id = None
        if apply:
            res = create("companies", props)
            if res is None:
                skipped += 1
                continue
            hs_id = res["id"]
        elif created < SHOW:
            print("would create company:", props)
        ids[row["company_id"]] = hs_id
        created += 1
    return ids, created, skipped


def load_contacts(df, company_ids, apply):
    seen = set()
    for c in hs.get_contacts():
        email = c["properties"].get("email")
        if email:
            seen.add(email.lower())

    res = {"created": 0, "skipped": 0, "no_email": 0, "linked": 0}
    for row in df.to_dict("records"):
        email = row["email"].lower()
        if not EMAIL_RE.match(email):
            res["no_email"] += 1
            continue
        if email in seen:
            res["skipped"] += 1
            continue
        props = pick(row, ["firstname", "lastname", "email", "jobtitle", "phone"])
        if apply:
            hs_id = company_ids.get(row["company_id"])
            if create("contacts", props, hs_id, CONTACT_TO_COMPANY) is None:
                res["skipped"] += 1
                continue
        elif res["created"] < SHOW:
            print("would create contact:", props, "company:", row["company_id"] or "-")
        seen.add(email)
        res["created"] += 1
        if row["company_id"] in company_ids:
            res["linked"] += 1
    return res


def load_deals(df, company_ids, apply):
    existing = {d["properties"].get("dealname") for d in hs.get_deals()}
    created = skipped = 0
    for row in df.to_dict("records"):
        if row["dealname"] in existing:
            skipped += 1
            continue
        props = pick(row, ["dealname", "amount", "dealstage", "closedate"])
        props["pipeline"] = "default"
        if apply:
            hs_id = company_ids.get(row["company_id"])
            if create("deals", props, hs_id, DEAL_TO_COMPANY) is None:
                skipped += 1
                continue
        elif created < SHOW:
            print("would create deal:", props, "company:", row["company_id"])
        existing.add(row["dealname"])
        created += 1
    return created, skipped


def main():
    apply = "--apply" in sys.argv
    companies = read_csv("companies.csv")
    contacts = read_csv("contacts.csv")
    deals = read_csv("deals.csv")

    word = "created" if apply else "would create"
    if not apply:
        print("DRY RUN, nothing is written to HubSpot. Use --apply to write.\n")

    company_ids, c_new, c_skip = load_companies(companies, apply)
    print(f"companies: {word} {c_new}, skipped {c_skip}\n")

    res = load_contacts(contacts, company_ids, apply)
    print(f"contacts: {word} {res['created']}, skipped {res['skipped']}, "
          f"not loaded (no valid email) {res['no_email']}")
    print(f"  linked to a company: {res['linked']}\n")

    d_new, d_skip = load_deals(deals, company_ids, apply)
    print(f"deals: {word} {d_new}, skipped {d_skip}")


if __name__ == "__main__":
    main()
