import urllib.request
from bs4 import BeautifulSoup
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://www.basarisiralamalari.com/istanbul-nisantasi-universitesi-egitim-ucretleri-ve-burslari/"
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

for result in results:
    print(result)
