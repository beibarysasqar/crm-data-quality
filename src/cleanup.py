import re
import sys

import hubspot_client as hs
import load_to_hubspot as loader
import quality_checks as qc
import report

CLEAN_DIR = qc.DATA_DIR / "clean"
PERSON = ["firstname", "lastname", "email", "company_id"]


def is_valid(email):
    return re.match(qc.EMAIL_RE, email) is not None


def strip_all(df):
    df = df.copy()
    for col in df.columns:
        df[col] = df[col].str.strip()
    return df


def fix_email_spaces(contacts):
    contacts = contacts.copy()
    email = contacts["email"].str.lower()
    contacts["email"] = email.str.replace(r"\s+", "", regex=True)
    return contacts


def drop_repeats(contacts):
    was = len(contacts)
    df = contacts.drop_duplicates()
    # same person entered twice: only the id, job title or phone differ
    same = df.duplicated(PERSON, keep="first") & (df["email"] != "")
    df = df[~same].reset_index(drop=True)
    return df, was - len(df)


def cycle1(contacts, deals):
    contacts = fix_email_spaces(strip_all(contacts))
    contacts, dropped = drop_repeats(contacts)
    return contacts, strip_all(deals), dropped


def repair_email(email, domain):
    if email == "" or domain == "" or is_valid(email):
        return email
    if "@" not in email:
        user = email[:-len(domain)]
        if email.endswith(domain) and user:
            return user + "@" + domain
        return email
    user, part = email.split("@", 1)
    # "user@" or a domain cut before the dot, e.g. user@cole-walton
    if user and (part == "" or domain.startswith(part + ".")):
        return user + "@" + domain
    return email


def repair_emails(contacts, companies):
    domains = dict(zip(companies["company_id"], companies["domain"].str.lower()))
    contacts = contacts.copy()
    fixed = []
    for row in contacts.to_dict("records"):
        fixed.append(repair_email(row["email"], domains.get(row["company_id"], "")))
    contacts["email"] = fixed
    return contacts


def contact_note(row):
    notes = []
    if row["email"] == "":
        notes.append("no email")
    elif not is_valid(row["email"]):
        notes.append("bad email")
    if row["company_id"] == "":
        notes.append("no company")
    return "; ".join(notes)


def add_notes(contacts, deals):
    contacts = contacts.copy()
    deals = deals.copy()
    contacts["review_note"] = [contact_note(r) for r in contacts.to_dict("records")]
    # the amount stays empty, a person has to look it up
    deals["review_note"] = ["no amount" if a == "" else "" for a in deals["amount"]]
    return contacts, deals


def cycle2(contacts, deals, companies):
    contacts = repair_emails(contacts, companies)
    return add_notes(contacts, deals)


def save_clean(contacts, deals):
    CLEAN_DIR.mkdir(exist_ok=True)
    contacts.to_csv(CLEAN_DIR / "contacts.csv", index=False)
    deals.to_csv(CLEAN_DIR / "deals.csv", index=False)


def save_report(contacts, deals, name):
    found = qc.run_all(contacts, deals)
    path = report.write_report(found, name)
    for res in found:
        if len(res) > 0:
            print(f"  {res['rule'].iloc[0]:<26}{len(res)}")
    print(f"  {'total':<26}{sum(len(res) for res in found)}")
    print(f"  report: {path}")


def fixed_contacts(original, cleaned):
    old = dict(zip(original["contact_id"], original["email"]))
    rows = []
    for row in cleaned.to_dict("records"):
        before = old[row["contact_id"]]
        if before != "" and not is_valid(before) and is_valid(row["email"]):
            rows.append(row)
    return rows


def push_fixed(rows, companies):
    in_crm = {c["properties"].get("email") for c in hs.get_contacts()}
    hs_ids = {}
    for c in hs.get_companies():
        if c["properties"].get("domain"):
            hs_ids[c["properties"]["domain"].lower()] = c["id"]
    domains = dict(zip(companies["company_id"], companies["domain"].str.lower()))

    created = 0
    for row in rows:
        if row["email"] in in_crm:
            print("already in HubSpot:", row["email"])
            continue
        props = loader.pick(row, ["firstname", "lastname", "email", "jobtitle", "phone"])
        company = hs_ids.get(domains.get(row["company_id"]))
        if loader.create("contacts", props, company, loader.CONTACT_TO_COMPANY):
            created += 1
    print(f"created {created} contacts in HubSpot")


def main():
    apply = "--apply" in sys.argv
    original = qc.read_csv("contacts.csv")
    deals = qc.read_csv("deals.csv")
    companies = qc.read_csv("companies.csv")

    contacts, deals, dropped = cycle1(original, deals)
    save_clean(contacts, deals)
    print(f"cycle 1: dropped {dropped} repeated contacts, {len(contacts)} left")
    save_report(contacts, deals, "after_cycle1")

    contacts, deals = cycle2(contacts, deals, companies)
    save_clean(contacts, deals)
    marked = (contacts["review_note"] != "").sum() + (deals["review_note"] != "").sum()
    print(f"\ncycle 2: {marked} rows marked in review_note")
    save_report(contacts, deals, "after_cycle2")
    print(f"\nclean copies saved to {CLEAN_DIR}")

    rows = fixed_contacts(original, contacts)
    if apply:
        push_fixed(rows, companies)
        return
    print(f"\nDRY RUN, nothing is written to HubSpot. Use --apply to create "
          f"{len(rows)} contacts with a repaired email:")
    for row in rows:
        print(" ", row["contact_id"], row["email"])


if __name__ == "__main__":
    main()
