import sys
from pathlib import Path

import pandas as pd

import hubspot_client as hs

REPORT = Path(__file__).resolve().parent.parent / "reports" / "abm_tiers.xlsx"
PROP = "abm_tier"
TIERS = ["Tier 1", "Tier 2", "Tier 3"]

# score is 0..8: contacts 0-3, deals 0-3, domain 1, industry 1
TIER1_FROM = 7
TIER2_FROM = 5


def get_with_companies(obj_type, props):
    results = []
    params = {"limit": 100, "properties": ",".join(props), "associations": "companies"}
    while True:
        data = hs.request("GET", f"/crm/v3/objects/{obj_type}", params=params)
        results.extend(data["results"])
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            return results
        params["after"] = after


def company_ids(obj):
    links = obj.get("associations", {}).get("companies", {}).get("results", [])
    # HubSpot can list one company twice, as a primary and as a plain link
    return {link["id"] for link in links}


def build_table(companies, contacts, deals):
    n_contacts = {}
    for c in contacts:
        for cid in company_ids(c):
            n_contacts[cid] = n_contacts.get(cid, 0) + 1

    sums = {}
    for d in deals:
        amount = d["properties"].get("amount")
        # a lost deal says nothing good about the account
        if not amount or d["properties"].get("dealstage") == "closedlost":
            continue
        for cid in company_ids(d):
            sums[cid] = sums.get(cid, 0) + float(amount)

    rows = []
    for c in companies:
        p = c["properties"]
        rows.append({
            "id": c["id"],
            "name": p.get("name") or "",
            "domain": p.get("domain") or "",
            "industry": p.get("industry") or "",
            "contacts": n_contacts.get(c["id"], 0),
            "deal_sum": sums.get(c["id"], 0),
            "current_tier": p.get(PROP) or "",
        })
    return pd.DataFrame(rows)


def contact_points(n):
    if n >= 7:
        return 3
    if n >= 4:
        return 2
    if n >= 1:
        return 1
    return 0


def deal_points(total):
    if total >= 100000:
        return 3
    if total >= 50000:
        return 2
    if total > 0:
        return 1
    return 0


def score_row(row):
    score = contact_points(row["contacts"]) + deal_points(row["deal_sum"])
    if row["domain"]:
        score += 1
    if row["industry"]:
        score += 1
    return score


def tier(score):
    if score >= TIER1_FROM:
        return "Tier 1"
    if score >= TIER2_FROM:
        return "Tier 2"
    return "Tier 3"


def add_scores(df):
    df = df.copy()
    df["score"] = [score_row(row) for row in df.to_dict("records")]
    df["tier"] = [tier(s) for s in df["score"]]
    return df.sort_values(["score", "deal_sum"], ascending=False).reset_index(drop=True)


def property_exists():
    data = hs.request("GET", "/crm/v3/properties/companies")
    return PROP in [p["name"] for p in data["results"]]


def create_property():
    options = [{"label": t, "value": t, "displayOrder": i} for i, t in enumerate(TIERS)]
    body = {
        "name": PROP,
        "label": "ABM tier",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": "companyinformation",
        "options": options,
    }
    hs.request("POST", "/crm/v3/properties/companies", body=body)
    print(f"created company property {PROP}")


def write_tiers(df):
    inputs = [{"id": row["id"], "properties": {PROP: row["tier"]}}
              for row in df.to_dict("records")]
    # the batch endpoint takes at most 100 records per call
    for i in range(0, len(inputs), 100):
        hs.request("POST", "/crm/v3/objects/companies/batch/update",
                   body={"inputs": inputs[i:i + 100]})
    print(f"updated {len(inputs)} companies in HubSpot")


def save_report(df):
    cols = ["name", "domain", "industry", "contacts", "deal_sum", "score", "tier"]
    df[cols].to_excel(REPORT, sheet_name="abm_tiers", index=False)
    print(f"report: {REPORT}")


def print_result(df):
    for t in TIERS:
        print(f"  {t}: {(df['tier'] == t).sum()}")
    print("\ntop 5:")
    for row in df.head(5).to_dict("records"):
        print(f"  {row['score']}  {row['name']} ({row['contacts']} contacts, "
              f"deals {row['deal_sum']:.0f})")


def main():
    apply = "--apply" in sys.argv
    companies = hs.get_companies(props=("name", "domain", "industry", PROP))
    contacts = get_with_companies("contacts", ["email"])
    deals = get_with_companies("deals", ["amount", "dealstage"])

    df = add_scores(build_table(companies, contacts, deals))
    print(f"scored {len(df)} companies ({len(contacts)} contacts, {len(deals)} deals)")
    print_result(df)
    save_report(df)

    exists = property_exists()
    changed = df[df["current_tier"] != df["tier"]]
    if not apply:
        print("\nDRY RUN, nothing is written to HubSpot. Use --apply to write.")
        if not exists:
            print(f"would create company property {PROP}")
        print(f"would update {len(changed)} companies")
        return
    if not exists:
        create_property()
    write_tiers(changed)


if __name__ == "__main__":
    main()
