#!/usr/bin/env python3
"""
Fetch BOC Bank JPY (Japanese Yen) exchange rates and save to a CSV file.
Running on the same day overwrites the existing entry for that day.
"""

import csv
import os
import re
import sys
from datetime import date

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing dependencies. Run: pip install requests beautifulsoup4")
    sys.exit(1)

URL = "https://www.boc.lk/rates-tariff"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yen_rates.csv")
FIELDNAMES = ["date", "buying_rate", "selling_rate"]


def fetch_jpy_rates():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(URL, headers=headers, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find the row containing "JPY" or "JAPANESE YEN"
    buying = None
    selling = None

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        row_text = row.get_text(" ", strip=True).upper()

        if "JPY" not in row_text and "JAPANESE" not in row_text:
            continue

        # Extract all numeric values from the row
        numbers = []
        for cell in cells:
            text = cell.get_text(strip=True)
            if re.match(r"^\d+(\.\d+)?$", text):
                numbers.append(float(text))

        if len(numbers) >= 2:
            # Telegraphic/TT rates are typically the last pair of buy/sell
            # The page shows: [drafts buy, drafts sell, TT buy, TT sell] or similar
            # Use last two as buying/selling (TT rates)
            buying = numbers[-2]
            selling = numbers[-1]
            break

    if buying is None or selling is None:
        raise ValueError("Could not find JPY rates on the page. The site structure may have changed.")

    return buying, selling


def load_existing_rates():
    rows = {}
    if not os.path.exists(OUTPUT_FILE):
        return rows
    with open(OUTPUT_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows[row["date"]] = row
    return rows


def save_rates(rows):
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for key in sorted(rows.keys()):
            writer.writerow(rows[key])


def main():
    today = date.today().isoformat()  # YYYY-MM-DD

    print(f"Fetching JPY rates from BOC bank...")
    buying, selling = fetch_jpy_rates()
    print(f"Date:         {today}")
    print(f"Buying rate:  {buying}")
    print(f"Selling rate: {selling}")

    rows = load_existing_rates()
    action = "Updated" if today in rows else "Added"
    rows[today] = {"date": today, "buying_rate": buying, "selling_rate": selling}
    save_rates(rows)

    print(f"{action} entry in {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
