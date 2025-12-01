import urllib.request
from bs4 import BeautifulSoup
import ssl
import os
import requests

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def _parse_page(url: str) -> list:
    page = urllib.request.urlopen(url, context=ctx).read()
    soup = BeautifulSoup(page, "html.parser")

    old_section = False
    results = []

    for tag in soup.find_all(["strong", "li", "table"]):

        if tag.name == "strong":
            strong_text = tag.get_text(strip=True)

            if "2024" in strong_text:
                old_section = True
                continue

        if old_section:
            continue

        if tag.name == "li":
            text = tag.get_text(" ", strip=True)
            if "₺" in text or "TL" in text:
                results.append(text)

        if tag.name == "table":
            for row in tag.find_all("tr"):
                cols = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
                if len(cols) >= 2:
                    price = cols[1]
                    if "₺" in price or "TL" in price:
                        results.append(f"{cols[0]} → {cols[1]}")

    return results

def _parse_price_text(price_text: str) -> tuple:
    if not price_text:
        return None, None
    txt = price_text.replace("\xa0", " ").strip()
    currency = None
    if "₺" in txt:
        currency = "TRY"
    elif "TL" in txt.upper():
        currency = "TRY"
    elif "$" in txt:
        currency = "USD"
    cleaned = txt
    cleaned = ''.join(ch for ch in cleaned if ch.isdigit() or ch in ",.\s")
    parts = [p for p in cleaned.split() if any(c.isdigit() for c in p)]
    if not parts:
        return None, currency
    num = parts[-1]
    if "." in num and "," in num:
        num = num.replace('.', '').replace(',', '.')
    else:
        if '.' in num and len(num.split('.')[-1]) == 3:
            num = num.replace('.', '')
        if ',' in num and len(num.split(',')[-1]) == 3:
            num = num.replace(',', '')
        else:
            num = num.replace(',', '.')
    try:
        value = float(num)
    except Exception:
        value = None
    return value, currency


def _format_prices(results_list):
    import re

    def find_price_matches(text: str):
        patterns = [r'₺\s?[\d\.,]+', r'[\d\.,]+\s?TL\b', r'\$\s?[\d\.,]+']
        matches = []
        for pat in patterns:
            for m in re.finditer(pat, text, flags=re.IGNORECASE):
                matches.append((m.start(), m.end(), m.group().strip()))
        matches.sort(key=lambda x: x[0])
        return matches

    def split_programs(left_text: str):
        import re
        parts = [p.strip(" .–—()\n\t") for p in re.split(r'[;,]', left_text) if p.strip()]
        return parts if parts else [left_text.strip()]

    prices = []
    for r in results_list:
        if "→" in r:
            parts = [p.strip() for p in r.split("→", 1)]
            left = parts[0]
            price_part = parts[1]
            price_matches = find_price_matches(price_part) or find_price_matches(r)
        else:
            price_matches = find_price_matches(r)
            if price_matches:
                first = price_matches[0]
                left = r[: first[0]]
            else:
                left = r

        programs = split_programs(left)

        price_chunks = []
        if price_matches:
            start = price_matches[0][0]
            price_area = r[start:]
            for chunk in price_area.split('/'):
                chunk = chunk.strip(' ;,')
                pm = find_price_matches(chunk)
                if pm:
                    price_chunks.append(pm[0][2])
                else:
                    price_chunks.append(chunk)
        else:
            price_chunks = [""]

        if len(programs) == 1 and len(price_chunks) > 1:
            targets = [(programs[0], pc) for pc in price_chunks]
        elif len(programs) > 1 and len(price_chunks) == 1:
            targets = [(p, price_chunks[0]) for p in programs]
        elif len(programs) == len(price_chunks):
            targets = list(zip(programs, price_chunks))
        else:
            combined_price = ' / '.join(price_chunks) if price_chunks else ''
            targets = [(left.strip(), combined_price)]

        for prog, price_text in targets:
            value, currency = _parse_price_text(price_text)
            prices.append({
                "item": prog,
                "price_text": price_text or "",
                "price_value": value,
                "currency": currency,
            })

    return prices


def run_scraper(url: str | None = None, university_name: str | None = None, department: str | None = None, save: bool = True):

    url = url or os.environ.get("SCRAPER_URL") or "https://www.basarisiralamalari.com/istanbul-nisantasi-universitesi-egitim-ucretleri-ve-burslari/"
    raw = _parse_page(url)
    prices = _format_prices(raw)

    for p in prices:
        print(p)

    if save:
        try:
            from util.connect import get_db
            import datetime

            UNIVERSITY_NAME = university_name or os.environ.get("UNIVERSITY_NAME", "Istanbul Nisantasi University")
            DEPARTMENT = department or os.environ.get("DEPARTMENT", "Unknown Department")

            db = get_db()
            coll = db["university_prices"]
            now = datetime.datetime.utcnow()
            for p in prices:
                prog = p.get("item")
                price_text = p.get("price_text", "")
                doc = {
                    "university_name": UNIVERSITY_NAME,
                    "department": prog,
                    "price_text": price_text,
                    "price_value": p.get("price_value"),
                    "currency": p.get("currency"),
                    "scraped_at": now,
                }
                q = {"university_name": UNIVERSITY_NAME, "department": prog, "price_text": price_text}
                res = coll.update_one(q, {"$set": doc}, upsert=True)
                if getattr(res, "upserted_id", None):
                    print("Inserted:", prog)
                else:
                    print("Updated:", prog)
        except Exception as e:
            print("Failed to save to DB:", e)

    return prices

## sonra ilgileneceğim burayla dokunmayın
##try:
##    import json
##    resp = requests.get('https://ntfy.sh/AlSweigartZPgxBQ42/json?poll=1')
##    notifications = []
##    for json_text in resp.text.splitlines():
##        notifications.append(json.loads(json_text))
##        
##    notifications[0]['message']
##
##    notifications[1]['message']
##except Exception:
##    pass