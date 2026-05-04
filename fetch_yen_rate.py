#!/usr/bin/env python3
"""
Fetch BOC Bank JPY (Japanese Yen) exchange rates and save to a CSV file.
Running on the same day overwrites the existing entry for that day.
"""

import csv
import os
import re
import sys
import time
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
MAX_RETRIES = 5
RETRY_DELAYS = [5, 15, 30, 60, 120]  # seconds between retries


def fetch_jpy_rates():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    session = requests.Session()
    session.headers.update(headers)

    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(URL, timeout=30)
            resp.raise_for_status()
            break
        except requests.exceptions.HTTPError as e:
            last_exc = e
            if resp.status_code == 403 and attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                print(f"Got 403, retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})...")
                time.sleep(delay)
            else:
                raise
        except requests.exceptions.RequestException as e:
            last_exc = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                print(f"Request failed ({e}), retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})...")
                time.sleep(delay)
            else:
                raise

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
