import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.hubapi.com"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def get_token():
    load_dotenv(ENV_FILE)
    token = os.getenv("HUBSPOT_TOKEN")
    if not token:
        sys.exit("HUBSPOT_TOKEN is missing, add it to .env")
    return token


def request(method, path, body=None, params=None):
    headers = {"Authorization": f"Bearer {get_token()}"}
    for attempt in range(4):
        # free plan allows about 100 requests per 10 seconds
        time.sleep(0.1)
        res = requests.request(method, BASE_URL + path, headers=headers,
                               json=body, params=params, timeout=30)
        if res.status_code != 429:
            break
        wait = int(res.headers.get("Retry-After", 10))
        print(f"rate limit hit, waiting {wait}s (attempt {attempt + 1})")
        time.sleep(wait)

    if res.status_code == 409:
        print("already exists:", error_message(res))
        return None
    if not res.ok:
        print(f"HubSpot error {res.status_code}: {error_message(res)}")
        res.raise_for_status()
    if not res.content:
        return None
    return res.json()


def error_message(res):
    try:
        return res.json().get("message", res.text)
    except ValueError:
        return res.text


def get_objects(obj_type, props):
    results = []
    params = {"limit": 100, "properties": ",".join(props)}
    while True:
        data = request("GET", f"/crm/v3/objects/{obj_type}", params=params)
        results.extend(data["results"])
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            return results
        params["after"] = after


def get_contacts(props=("email", "firstname", "lastname")):
    return get_objects("contacts", props)


def get_companies(props=("name", "domain")):
    return get_objects("companies", props)


def get_deals(props=("dealname", "amount", "dealstage")):
    return get_objects("deals", props)


def count_contacts():
    data = request("POST", "/crm/v3/objects/contacts/search", body={"limit": 1})
    return data["total"]


if __name__ == "__main__":
    print("contacts in HubSpot:", count_contacts())
