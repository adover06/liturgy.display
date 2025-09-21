#!/usr/bin/env python3
import re
import csv
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup, Tag, NavigableString

URL = "https://sjsuparkingstatus.sjsu.edu/"
HEADERS = {"User-Agent": "sjsu-parking-scraper/1.0 (+you@example.com)"}

PERCENT_RX = re.compile(r"\b(\d{1,3})\s*%\b")
GARAGE_NAME_RX = re.compile(r"\b([A-Z][\w .'-]+?\sGarage)\b", re.I)
UPDATED_RX = re.compile(r"Last updated\s*(.*)", re.I)

def fetch_html(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text

def text_of(node) -> str:
    if isinstance(node, NavigableString):
        return str(node)
    if isinstance(node, Tag):
        return node.get_text(" ", strip=True)
    return ""

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def nearest_garage_name(from_node: Tag) -> Optional[str]:
    """Walk backwards from the % node to find the closest preceding '... Garage' text."""
    # 1) check previous siblings in same container
    sib = from_node.previous_sibling
    while sib:
        t = clean(text_of(sib))
        m = GARAGE_NAME_RX.search(t)
        if m and "Parking Garage Fullness" not in t:
            return clean(m.group(1))
        sib = sib.previous_sibling

    # 2) climb up a few ancestors; scan their previous siblings
    cur = from_node
    for _ in range(6):
        cur = cur.parent
        if not cur:
            break
        sib = cur.previous_sibling
        while sib:
            t = clean(text_of(sib))
            m = GARAGE_NAME_RX.search(t)
            if m and "Parking Garage Fullness" not in t:
                return clean(m.group(1))
            sib = sib.previous_sibling

    # 3) global fallback: nearest previous text that ends with 'Garage'
    prev_text = from_node.find_previous(string=lambda s: bool(s) and GARAGE_NAME_RX.search(str(s)))
    if prev_text:
        m = GARAGE_NAME_RX.search(str(prev_text))
        if m and "Parking Garage Fullness" not in prev_text:
            return clean(m.group(1))
    return None

def parse(html: str) -> Dict[str, List[Dict]]:
    soup = BeautifulSoup(html, "html.parser")

    # last updated
    updated = None
    upd_el = soup.find(string=UPDATED_RX)
    if upd_el:
        m = UPDATED_RX.search(str(upd_el))
        if m:
            updated = clean(m.group(1))

    # find all percentage text nodes like "25 %"
    rows = []
    seen = set()
    for s in soup.find_all(string=PERCENT_RX):
        m = PERCENT_RX.search(str(s))
        if not m:
            continue
        pct = int(m.group(1))
        node = s.parent if isinstance(s, NavigableString) else s
        name = nearest_garage_name(node)
        if name and name.lower() not in seen:
            rows.append({"name": name, "percent_full": pct})
            seen.add(name.lower())

    # If nothing matched (layout changed), fall back: list any lines with "... Garage"
    if not rows:
        for el in soup.find_all(text=GARAGE_NAME_RX):
            m = GARAGE_NAME_RX.search(str(el))
            if m:
                name = clean(m.group(1))
                if name.lower() not in seen:
                    rows.append({"name": name, "percent_full": None})
                    seen.add(name.lower())

    return {"updated": updated, "rows": rows}

def main():
    html = fetch_html(URL)
    result = parse(html)

    if result["updated"]:
        print(f"Last updated: {result['updated']}\n")

    rows = result["rows"]
    if not rows:
        print("No garages found (the page may be JS-rendered now).")
        return

    for i, r in enumerate(rows, 1):
        pct = f"{r['percent_full']}% FULL" if r["percent_full"] is not None else "N/A"
        print(f"{i}. {r['name']} — {pct}")

    with open("sjsu_parking.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "percent_full"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved {len(rows)} rows to sjsu_parking.csv")

if __name__ == "__main__":
    main()
