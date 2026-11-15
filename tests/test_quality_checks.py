import pandas as pd

import quality_checks as qc


def make_contacts(emails, company_ids=None):
    if company_ids is None:
        company_ids = ["C001"] * len(emails)
    return pd.DataFrame({
        "contact_id": [f"P{i:03d}" for i in range(1, len(emails) + 1)],
        "email": emails,
        "company_id": company_ids,
    })


def make_deals(amounts):
    return pd.DataFrame({
        "deal_id": [f"D{i:03d}" for i in range(1, len(amounts) + 1)],
        "amount": amounts,
    })


def test_empty_email_found():
    df = make_contacts(["a@x.com", "", "b@x.com", "   "])
    res = qc.empty_email(df)
    assert list(res["contact_id"]) == ["P002", "P004"]


def test_empty_email_row_and_rule():
    df = make_contacts(["a@x.com", "", "b@x.com"])
    res = qc.empty_email(df)
    # second record of the file is line 3, because line 1 is the header
    assert list(res["row"]) == [3]
    assert list(res["rule"]) == ["empty_email"]


def test_empty_email_clean_data():
    df = make_contacts(["a@x.com", "b@x.com"])
    assert len(qc.empty_email(df)) == 0


def test_bad_email_format_found():
    df = make_contacts(["userx.com", "user@", "user@domain", "user @x.com"])
    res = qc.bad_email_format(df)
    assert list(res["row"]) == [2, 3, 4, 5]
    assert set(res["rule"]) == {"bad_email_format"}


def test_bad_email_format_valid_is_ok():
    df = make_contacts(["anna.lee@x.com", "bob99@my-shop.co.uk"])
    assert len(qc.bad_email_format(df)) == 0


def test_bad_email_format_skips_empty():
    df = make_contacts(["", "a@x.com"])
    assert len(qc.bad_email_format(df)) == 0


def test_duplicate_email_only_second_copy():
    df = make_contacts(["a@x.com", "b@x.com", "a@x.com", "a@x.com"])
    res = qc.duplicate_email(df)
    assert list(res["contact_id"]) == ["P003", "P004"]
    assert list(res["row"]) == [4, 5]
    assert set(res["rule"]) == {"duplicate_email"}


def test_duplicate_email_ignores_case():
    df = make_contacts(["Anna@X.com", "anna@x.com"])
    res = qc.duplicate_email(df)
    assert list(res["contact_id"]) == ["P002"]


def test_duplicate_email_empty_is_not_duplicate():
    df = make_contacts(["", "", "a@x.com"])
    assert len(qc.duplicate_email(df)) == 0


def test_contact_without_company_found():
    df = make_contacts(["a@x.com", "b@x.com", "c@x.com"], ["C001", "", "C002"])
    res = qc.contact_without_company(df)
    assert list(res["contact_id"]) == ["P002"]
    assert list(res["row"]) == [3]
    assert list(res["rule"]) == ["contact_without_company"]


def test_contact_without_company_clean_data():
    df = make_contacts(["a@x.com", "b@x.com"])
    assert len(qc.contact_without_company(df)) == 0


def test_deal_without_amount_found():
    df = make_deals(["5000", "", "12000", ""])
    res = qc.deal_without_amount(df)
    assert list(res["deal_id"]) == ["D002", "D004"]
    assert list(res["row"]) == [3, 5]
    assert set(res["rule"]) == {"deal_without_amount"}


def test_deal_without_amount_clean_data():
    df = make_deals(["5000", "12000"])
    assert len(qc.deal_without_amount(df)) == 0
