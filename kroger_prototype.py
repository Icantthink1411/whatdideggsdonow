#!/usr/bin/env python3
"""
Kroger API Price Prototype
===========================
Tests pulling live grocery prices from Kroger's public API.
Shows what eggs, milk, beef, etc. actually cost at a nearby Kroger-banner store.

SETUP:
  1. Register a free app at https://developer.kroger.com/manage/apps/register
  2. Get your CLIENT_ID and CLIENT_SECRET
  3. pip install requests

USAGE:
  python kroger_prototype.py --id YOUR_CLIENT_ID --secret YOUR_CLIENT_SECRET --zip 78701
"""

import argparse
import base64
import json
import requests
from datetime import datetime


# Items to look up — tuned to match our site's tracked products
ITEMS = [
    {"label": "Eggs",         "search": "large eggs dozen",        "emoji": "🥚"},
    {"label": "Whole Milk",   "search": "whole milk gallon",        "emoji": "🥛"},
    {"label": "Butter",       "search": "salted butter 1 lb",       "emoji": "🧈"},
    {"label": "White Bread",  "search": "white sandwich bread loaf", "emoji": "🍞"},
    {"label": "Ground Beef",  "search": "ground beef 80/20 1 lb",   "emoji": "🥩"},
    {"label": "Chicken Breast","search": "boneless skinless chicken breast", "emoji": "🍗"},
    {"label": "Bacon",        "search": "bacon sliced 1 lb",        "emoji": "🥓"},
    {"label": "Coffee",       "search": "ground coffee 1 lb",       "emoji": "☕"},
    {"label": "Orange Juice", "search": "orange juice",             "emoji": "🍊"},
]


def get_token(client_id, client_secret):
    """Get an OAuth2 client credentials token."""
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        "https://api.kroger.com/v1/connect/oauth2/token",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {creds}",
        },
        data={"grant_type": "client_credentials", "scope": "product.compact"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def find_store(token, zip_code):
    """Find the nearest Kroger-banner store to a zip code."""
    resp = requests.get(
        "https://api.kroger.com/v1/locations",
        headers={"Authorization": f"Bearer {token}"},
        params={"filter.zipCode.near": zip_code, "filter.radiusInMiles": 25, "filter.limit": 5},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("data"):
        return None
    store = data["data"][0]
    return {
        "locationId": store["locationId"],
        "name": store.get("name", "Kroger"),
        "chain": store.get("chain", ""),
        "address": store.get("address", {}).get("addressLine1", ""),
        "city": store.get("address", {}).get("city", ""),
        "state": store.get("address", {}).get("state", ""),
    }


def search_product_price(token, location_id, search_term, limit=5):
    """Search for a product and return the cheapest priced result."""
    resp = requests.get(
        "https://api.kroger.com/v1/products",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "filter.term": search_term,
            "filter.locationId": location_id,
            "filter.fulfillment": "ais",  # available in store
            "filter.limit": limit,
        },
        timeout=15,
    )
    resp.raise_for_status()
    products = resp.json().get("data", [])

    # Filter to only products with price data
    priced = []
    for p in products:
        items = p.get("items", [])
        for item in items:
            price_info = item.get("price", {})
            regular = price_info.get("regular")
            promo = price_info.get("promo")
            if regular:
                priced.append({
                    "description": p.get("description", ""),
                    "brand": p.get("brand", ""),
                    "size": item.get("size", ""),
                    "regular_price": regular,
                    "promo_price": promo,
                    "upc": p.get("upc", ""),
                })

    if not priced:
        return None

    # Return the lowest regular price result
    return min(priced, key=lambda x: x["regular_price"])


def main():
    parser = argparse.ArgumentParser(description="Kroger API price prototype")
    parser.add_argument("--id",     required=True, help="Kroger API client ID")
    parser.add_argument("--secret", required=True, help="Kroger API client secret")
    parser.add_argument("--zip",    required=True, help="ZIP code to find a nearby store")
    parser.add_argument("--json",   action="store_true", help="Output raw JSON instead of table")
    args = parser.parse_args()

    print("\n🥚  Kroger API Price Prototype")
    print("=" * 52)

    # Step 1: Auth
    print("  Authenticating...", end=" ")
    try:
        token = get_token(args.id, args.secret)
        print("✅")
    except Exception as e:
        print(f"❌  {e}")
        return

    # Step 2: Find store
    print(f"  Finding store near {args.zip}...", end=" ")
    try:
        store = find_store(token, args.zip)
        if not store:
            print("❌  No stores found in that area")
            return
        print(f"✅  {store['name']} — {store['address']}, {store['city']}, {store['state']}")
    except Exception as e:
        print(f"❌  {e}")
        return

    print()
    print(f"  {'Item':<20} {'Best Match':<35} {'Size':<15} {'Regular':>8} {'Sale':>8}")
    print("  " + "-" * 90)

    results = []
    for item in ITEMS:
        try:
            result = search_product_price(token, store["locationId"], item["search"])
            if result:
                sale = f"${result['promo_price']:.2f}" if result["promo_price"] else "  —"
                desc = result["description"][:33]
                size = result["size"][:13] if result["size"] else ""
                print(f"  {item['emoji']} {item['label']:<18} {desc:<35} {size:<15} ${result['regular_price']:>6.2f} {sale:>8}")
                results.append({**item, **result})
            else:
                print(f"  {item['emoji']} {item['label']:<18} {'(no priced results found)':<35}")
                results.append({**item, "error": "no results"})
        except Exception as e:
            print(f"  {item['emoji']} {item['label']:<18} ❌  {e}")
            results.append({**item, "error": str(e)})

    print()
    print(f"  Store: {store['name']}, {store['city']} {store['state']}")
    print(f"  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    if args.json:
        print("\n── Raw JSON output ──")
        print(json.dumps({"store": store, "prices": results}, indent=2))

    print("✅  Done. If prices look right, we can wire this into the site.\n")


if __name__ == "__main__":
    main()
