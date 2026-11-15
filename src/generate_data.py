import random
import re
from pathlib import Path

import pandas as pd
from faker import Faker

SEED = 42
N_COMPANIES = 50
N_CONTACTS = 300
N_DEALS = 30

N_EMPTY_EMAIL = 10
N_BAD_EMAIL = 10
N_DUP_EMAIL = 10
N_NO_COMPANY = 15
N_NO_AMOUNT = 5

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

INDUSTRIES = ["Software", "Finance", "Healthcare", "Retail", "Manufacturing", "Marketing"]
EMPLOYEES = [10, 25, 50, 120, 300, 800, 2000, 5000]
STAGES = ["appointmentscheduled", "qualifiedtobuy", "presentationscheduled",
          "decisionmakerboughtin", "contractsent", "closedwon", "closedlost"]

fake = Faker("en_US")
Faker.seed(SEED)
random.seed(SEED)


def make_companies(n):
    rows = []
    for i in range(1, n + 1):
        employees = random.choice(EMPLOYEES)
        rows.append({
            "company_id": f"C{i:03d}",
            "name": fake.unique.company(),
            "domain": fake.unique.domain_name(),
            "industry": random.choice(INDUSTRIES),
            "numberofemployees": employees,
            "annualrevenue": employees * random.randint(80, 250) * 1000,
            "city": fake.city(),
            "country": "United States",
        })
    return pd.DataFrame(rows)


def clean_name(s):
    return re.sub(r"[^a-z]", "", s.lower())


def make_contacts(companies, n):
    comps = companies.to_dict("records")
    seen = set()
    rows = []
    for i in range(1, n + 1):
        comp = random.choice(comps)
        first, last = fake.first_name(), fake.last_name()
        user = f"{clean_name(first)}.{clean_name(last)}"
        email = f"{user}@{comp['domain']}"
        while email in seen:
            email = f"{user}{random.randint(2, 99)}@{comp['domain']}"
        seen.add(email)
        rows.append({
            "contact_id": f"P{i:03d}",
            "firstname": first,
            "lastname": last,
            "email": email,
            "jobtitle": fake.job(),
            "phone": fake.phone_number(),
            "company_id": comp["company_id"],
        })
    return pd.DataFrame(rows)


def break_email(email):
    user, domain = email.split("@")
    options = [
        user + domain,
        user + "@",
        user + "@" + domain.split(".")[0],
        user + " @" + domain,
    ]
    return random.choice(options)


def add_contact_errors(df):
    total = N_EMPTY_EMAIL + N_BAD_EMAIL + N_DUP_EMAIL + N_NO_COMPANY
    idx = random.sample(range(len(df)), total)
    empty = idx[:N_EMPTY_EMAIL]
    bad = idx[N_EMPTY_EMAIL:N_EMPTY_EMAIL + N_BAD_EMAIL]
    dup = idx[N_EMPTY_EMAIL + N_BAD_EMAIL:N_EMPTY_EMAIL + N_BAD_EMAIL + N_DUP_EMAIL]
    no_company = idx[N_EMPTY_EMAIL + N_BAD_EMAIL + N_DUP_EMAIL:]

    df.loc[empty, "email"] = ""
    df.loc[bad, "email"] = [break_email(e) for e in df.loc[bad, "email"]]
    df.loc[no_company, "company_id"] = ""

    # copy the whole person, so the duplicate looks like the same contact entered twice
    good = [i for i in range(len(df)) if i not in idx]
    sources = random.sample(good, N_DUP_EMAIL)
    cols = ["firstname", "lastname", "email", "company_id"]
    df.loc[dup, cols] = df.loc[sources, cols].values
    return df


def make_deals(companies, n):
    rows = []
    for i in range(1, n + 1):
        comp = companies.iloc[random.randrange(len(companies))]
        rows.append({
            "deal_id": f"D{i:03d}",
            "dealname": f"{comp['name']} deal {i:03d}",
            "amount": random.randint(5, 150) * 1000,
            "dealstage": random.choice(STAGES),
            "closedate": fake.date_between("-6M", "+6M").isoformat(),
            "company_id": comp["company_id"],
        })
    df = pd.DataFrame(rows)
    # Int64 keeps amounts as whole numbers in the CSV even with empty cells
    df["amount"] = df["amount"].astype("Int64")
    no_amount = random.sample(range(n), N_NO_AMOUNT)
    df.loc[no_amount, "amount"] = pd.NA
    return df


def main():
    companies = make_companies(N_COMPANIES)
    contacts = add_contact_errors(make_contacts(companies, N_CONTACTS))
    deals = make_deals(companies, N_DEALS)

    DATA_DIR.mkdir(exist_ok=True)
    companies.to_csv(DATA_DIR / "companies.csv", index=False)
    contacts.to_csv(DATA_DIR / "contacts.csv", index=False)
    deals.to_csv(DATA_DIR / "deals.csv", index=False)

    print(f"companies: {len(companies)}, contacts: {len(contacts)}, deals: {len(deals)}")
    print("deliberate errors:")
    print(f"  empty emails:          {N_EMPTY_EMAIL}")
    print(f"  bad email format:      {N_BAD_EMAIL}")
    print(f"  duplicate emails:      {N_DUP_EMAIL}")
    print(f"  contacts w/o company:  {N_NO_COMPANY}")
    print(f"  deals w/o amount:      {N_NO_AMOUNT}")
    print(f"saved to {DATA_DIR}")


if __name__ == "__main__":
    main()
