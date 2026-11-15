import pandas as pd

import cleanup


def make_contacts(rows):
    cols = ["contact_id", "firstname", "lastname", "email", "phone", "company_id"]
    return pd.DataFrame(rows, columns=cols)


def test_strip_all():
    df = make_contacts([["P001", " Ann ", "Lee", "ann@x.com  ", "111", " C001"]])
    res = cleanup.strip_all(df)
    assert list(res.iloc[0]) == ["P001", "Ann", "Lee", "ann@x.com", "111", "C001"]
    # the input frame is not touched
    assert df["firstname"][0] == " Ann "


def test_strip_all_clean_data():
    df = make_contacts([["P001", "Ann", "Lee", "ann@x.com", "111", "C001"]])
    assert cleanup.strip_all(df).equals(df)


def test_fix_email_spaces():
    df = make_contacts([
        ["P001", "Ann", "Lee", "Ann.Lee@X.com", "1", "C001"],
        ["P002", "Bob", "Ray", "bob.ray @x.com", "2", "C001"],
        ["P003", "Cat", "Fox", "", "3", "C001"],
    ])
    res = cleanup.fix_email_spaces(df)
    assert list(res["email"]) == ["ann.lee@x.com", "bob.ray@x.com", ""]


def test_drop_repeats_same_person():
    df = make_contacts([
        ["P001", "Ann", "Lee", "ann@x.com", "111", "C001"],
        ["P002", "Bob", "Ray", "bob@x.com", "222", "C001"],
        ["P003", "Ann", "Lee", "ann@x.com", "999", "C001"],
    ])
    res, dropped = cleanup.drop_repeats(df)
    assert dropped == 1
    assert list(res["contact_id"]) == ["P001", "P002"]
    assert list(res.index) == [0, 1]


def test_drop_repeats_identical_row():
    row = ["P001", "Ann", "Lee", "ann@x.com", "111", "C001"]
    res, dropped = cleanup.drop_repeats(make_contacts([row, row]))
    assert dropped == 1
    assert len(res) == 1


def test_drop_repeats_keeps_other_people():
    df = make_contacts([
        ["P001", "Ann", "Lee", "info@x.com", "111", "C001"],
        ["P002", "Bob", "Ray", "info@x.com", "222", "C001"],
        ["P003", "Cat", "Fox", "", "333", "C002"],
        ["P004", "Cat", "Fox", "", "444", "C002"],
    ])
    res, dropped = cleanup.drop_repeats(df)
    # same email but another name is not the same person, empty emails are not compared
    assert dropped == 0
    assert len(res) == 4


def test_repair_email_fixes():
    assert cleanup.repair_email("larry.hunter@", "russell.com") == "larry.hunter@russell.com"
    assert cleanup.repair_email("mia.rivera@cole-walton", "cole-walton.com") == "mia.rivera@cole-walton.com"
    assert cleanup.repair_email("susan.hallriley.org", "riley.org") == "susan.hall@riley.org"


def test_repair_email_leaves_unclear():
    assert cleanup.repair_email("ann@x.com", "other.com") == "ann@x.com"
    assert cleanup.repair_email("ann@", "") == "ann@"
    assert cleanup.repair_email("ann@xyz", "other.com") == "ann@xyz"
    assert cleanup.repair_email("annother.net", "other.com") == "annother.net"
    # nothing would be left before the @
    assert cleanup.repair_email("other.com", "other.com") == "other.com"
    assert cleanup.repair_email("", "other.com") == ""


def test_repair_emails_uses_company_domain():
    contacts = make_contacts([
        ["P001", "Ann", "Lee", "ann.lee@", "1", "C001"],
        ["P002", "Bob", "Ray", "bob.ray@", "2", ""],
    ])
    companies = pd.DataFrame({"company_id": ["C001"], "domain": ["x.com"]})
    res = cleanup.repair_emails(contacts, companies)
    assert list(res["email"]) == ["ann.lee@x.com", "bob.ray@"]


def test_add_notes():
    contacts = make_contacts([
        ["P001", "Ann", "Lee", "ann@x.com", "1", "C001"],
        ["P002", "Bob", "Ray", "", "2", "C001"],
        ["P003", "Cat", "Fox", "cat@x", "3", ""],
        ["P004", "Dan", "Orr", "dan@x.com", "4", ""],
    ])
    deals = pd.DataFrame({"deal_id": ["D001", "D002"], "amount": ["5000", ""]})
    contacts, deals = cleanup.add_notes(contacts, deals)
    assert list(contacts["review_note"]) == ["", "no email", "bad email; no company", "no company"]
    assert list(deals["review_note"]) == ["", "no amount"]
    assert list(deals["amount"]) == ["5000", ""]


def test_fixed_contacts():
    original = make_contacts([
        ["P001", "Ann", "Lee", "ann@x.com", "1", "C001"],
        ["P002", "Bob", "Ray", "bob@", "2", "C001"],
        ["P003", "Cat", "Fox", "", "3", "C001"],
        ["P004", "Dan", "Orr", "danx.com", "4", ""],
    ])
    cleaned = original.copy()
    cleaned["email"] = ["ann@x.com", "bob@x.com", "", "danx.com"]
    rows = cleanup.fixed_contacts(original, cleaned)
    assert [r["contact_id"] for r in rows] == ["P002"]
