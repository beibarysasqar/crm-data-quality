import pandas as pd

import abm_scoring as abm


def linked(props, ids):
    results = [{"id": i, "type": "x"} for i in ids]
    return {"properties": props, "associations": {"companies": {"results": results}}}


def test_contact_points():
    assert abm.contact_points(0) == 0
    assert abm.contact_points(1) == 1
    assert abm.contact_points(3) == 1
    assert abm.contact_points(4) == 2
    assert abm.contact_points(7) == 3


def test_deal_points():
    assert abm.deal_points(0) == 0
    assert abm.deal_points(5000) == 1
    assert abm.deal_points(50000) == 2
    assert abm.deal_points(99999) == 2
    assert abm.deal_points(100000) == 3


def test_tier():
    assert abm.tier(4) == "Tier 3"
    assert abm.tier(5) == "Tier 2"
    assert abm.tier(6) == "Tier 2"
    assert abm.tier(7) == "Tier 1"


def test_score_row():
    row = {"contacts": 8, "deal_sum": 120000, "domain": "x.com", "industry": "RETAIL"}
    assert abm.score_row(row) == 8
    row = {"contacts": 2, "deal_sum": 0, "domain": "", "industry": ""}
    assert abm.score_row(row) == 1
    row = {"contacts": 0, "deal_sum": 0, "domain": "x.com", "industry": ""}
    assert abm.score_row(row) == 1


def test_build_table():
    companies = [
        {"id": "1", "properties": {"name": "A", "domain": "a.com", "industry": "RETAIL"}},
        {"id": "2", "properties": {"name": "B", "domain": None, "industry": None,
                                   "abm_tier": "Tier 3"}},
    ]
    contacts = [
        linked({"email": "ann@a.com"}, ["1"]),
        # the same company listed twice counts once
        linked({"email": "bob@a.com"}, ["1", "1"]),
        {"properties": {"email": "nobody@x.com"}},
    ]
    deals = [
        linked({"amount": "40000", "dealstage": "closedwon"}, ["1"]),
        linked({"amount": "20000", "dealstage": "contractsent"}, ["1"]),
        linked({"amount": "90000", "dealstage": "closedlost"}, ["1"]),
        linked({"amount": None, "dealstage": "contractsent"}, ["2"]),
    ]
    df = abm.build_table(companies, contacts, deals)
    assert list(df["contacts"]) == [2, 0]
    assert list(df["deal_sum"]) == [60000, 0]
    assert list(df["domain"]) == ["a.com", ""]
    assert list(df["current_tier"]) == ["", "Tier 3"]


def test_add_scores():
    df = pd.DataFrame([
        {"id": "1", "contacts": 1, "deal_sum": 0, "domain": "a.com", "industry": ""},
        {"id": "2", "contacts": 9, "deal_sum": 150000, "domain": "b.com", "industry": "RETAIL"},
    ])
    res = abm.add_scores(df)
    assert list(res["id"]) == ["2", "1"]
    assert list(res["tier"]) == ["Tier 1", "Tier 3"]
