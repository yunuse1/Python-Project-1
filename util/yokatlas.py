
import os
import ssl
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

# disable SSL verification for quick scraping (matches util/web_scraping.py behavior)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch_onlisans_programs(url: str) -> list:
    """Fetch a YokAtlas page and return a list of önlisans program names.

    The selector/structure on YokAtlas varies; this function uses simple
    heuristics: it collects text from <li>, <td> and <p> elements and
    splits comma/semicolon-separated lists into program names.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        html = resp.read()
    soup = BeautifulSoup(html, "html.parser")

    import re

    # Prefer content under a header containing 'Önlisans'
    programs = []
    header = None
    for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        if 'önlisans' in h.get_text(' ', strip=True).lower():
            header = h
            break

    def collect(node):
        out = []
        if not node:
            return out
        if node.name in ('ul', 'ol'):
            for li in node.find_all('li'):
                out.append(li.get_text(' ', strip=True))
            return out
        if node.name == 'table':
            for tr in node.find_all('tr'):
                cols = [c.get_text(' ', strip=True) for c in tr.find_all(['td','th'])]
                if cols:
                    out.append(' '.join(cols))
            return out
        text = node.get_text('\n', strip=True)
        for line in text.splitlines():
            if line.strip():
                out.append(line.strip())
        return out

    if header:
        for sib in header.find_next_siblings():
            if sib.name and sib.name.startswith('h'):
                break
            programs.extend(collect(sib))

    # fallback: collect from common containers if header-based empty
    if not programs:
        scope = soup
        for tag in scope.find_all(['ul','ol','table','li','p']):
            programs.extend(collect(tag))

    # split compound lines into separate program entries (handle cases like
    # 'Bilgisayar Programcılığı (İÖ) (Ücretli), Yazılım Mühendisliği ...')
    split_re = re.compile(r"\)\s*,\s*|\)\s*/\s*|;\s+|/\s+|\s*\|\s*|(?<=\w),\s+(?=[A-ZÇĞİİÖŞÜ])")
    expanded = []
    for p in programs:
        # remove leading/trailing bullets or arrows
        p = p.strip(' \t\n\r\u2022→-–—')
        parts = split_re.split(p)
        for part in parts:
            part = part.strip(' .;\n\t')
            if not part:
                continue
            expanded.append(part)

    # dedupe while preserving order
    seen = set()
    out = []
    for p in expanded:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)

    # Merge standalone parenthetical lines into previous item
    merged = []
    for item in out:
        s = item.strip()
        if re.match(r'^\(.*\)$', s) and merged:
            merged[-1] = merged[-1] + ' ' + s
        else:
            merged.append(item)

    # Filter out obvious header/menu lines
    headers = ['üniversite', 'tüm önlisans', 'alfabetik', 'tüm bölümler', 'program atlası', 'yokatlas', 'tercih sihirbazı', 'mezun başarı', 'net sihirbazı']
    filtered = [m for m in merged if not any(h in m.lower() for h in headers) and len(m.strip()) > 2]

    # final dedupe preserving order
    final = []
    seenf = set()
    for item in filtered:
        k = item.lower()
        if k in seenf:
            continue
        seenf.add(k)
        final.append(item)

    out = final

    # if nothing found inside the detected container, try a broader fallback
    if not out:
        programs2 = []
        for tag in soup.find_all(["li", "td", "p"]):
            txt = tag.get_text(" ", strip=True)
            if not txt or len(txt) < 4 or len(txt) > 500:
                continue
            if any(sk.lower() in txt.lower() for sk in stop_keywords):
                continue
            if "," in txt or ";" in txt:
                parts = [p.strip(" .–—()\n\t") for p in re.split(r'[;,]', txt) if p.strip()]
                for p in parts:
                    p = re.sub(r'[₺\$].*$', '', p).strip()
                    if len(p) > 1 and len(p) < 200:
                        programs2.append(p)
            else:
                line = re.sub(r'[₺\$].*$', '', txt).strip()
                if len(line.split()) <= 12:
                    programs2.append(line)

        seen2 = set()
        out2 = []
        for p in programs2:
            k = p.lower()
            if k in seen2:
                continue
            seen2.add(k)
            out2.append(p)
        if out2:
            return out2

    # Final broad fallback: split entire page text into lines and filter
    text = soup.get_text("\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    skip = ["atlas", "tercih", "üniversitelerimiz", "yokatlas", "mailto", "http", "©", "tercih sihirbazı", "mezun başarı", "net sihirbazı"]
    candidates = []
    for line in lines:
        low = line.lower()
        if any(s in low for s in skip):
            continue
        # ignore short tokens and pure numbers
        if len(line) < 5:
            continue
        words = line.split()
        if len(words) < 2:
            continue
        # remove trailing price fragments
        import re
        clean = re.sub(r'[₺\$].*$', '', line).strip()
        if len(clean) < 3:
            continue
        candidates.append(clean)

    # dedupe and return
    seen3 = set()
    out3 = []
    for c in candidates:
        k = c.lower()
        if k in seen3:
            continue
        seen3.add(k)
        out3.append(c)

    # also try to find a generic "diğer ön lisans" price on the page
    full_text = soup.get_text(" ", strip=True)
    gen_price = None
    m = re.search(r"diğer\s+ön\s+lisans[^\d\n\r]{0,40}([₺\$]\s?[\d\.,]+(?:\s*TL)?)", full_text, flags=re.I)
    if not m:
        m = re.search(r"diğer[^\n]{0,60}([₺\$]\s?[\d\.,]+(?:\s*TL)?)", full_text, flags=re.I)
    if m:
        gen_price = m.group(1).strip()

    return out3, gen_price


def resolve_yokatlas_url_from_query(query: str) -> str | None:
    """Use DuckDuckGo HTML search to find the first yokatlas onlisans page for query.

    Returns a full URL string or None if not found.
    """
    try:
        # try Google first (simple GET, parse first yokatlas link)
        gq = urllib.parse.urlencode({"q": query + " yokatlas nişantaşı önlisans"})
        gurl = "https://www.google.com/search?" + gq
        req = urllib.request.Request(gurl, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            html = resp.read()
        s = BeautifulSoup(html, "html.parser")
        for a in s.find_all("a", href=True):
            href = a["href"]
            if "/url?q=" in href and "yokatlas.yok.gov.tr/onlisans-univ.php?u=" in href:
                real = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get('q')
                if real:
                    return real[0]
            if "yokatlas.yok.gov.tr/onlisans-univ.php?u=" in href:
                return href if href.startswith('http') else urllib.parse.urljoin('https://yokatlas.yok.gov.tr/', href)
    except Exception:
        pass
    # fallback: try duckduckgo minimal approach
    try:
        q = f"site:yokatlas.yok.gov.tr {query}"
        url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": q})
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            html = resp.read()
        s = BeautifulSoup(html, "html.parser")
        for a in s.find_all("a", href=True):
            href = a["href"]
            if "yokatlas.yok.gov.tr/onlisans-univ.php?u=" in href:
                if href.startswith("/l/?") and "uddg=" in href:
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    enc = parsed.get("uddg")
                    if enc:
                        return urllib.parse.unquote(enc[0])
                if href.startswith("http"):
                    return href
                return urllib.parse.urljoin("https://yokatlas.yok.gov.tr/", href)
    except Exception:
        return None



def _parse_price_text(price_text: str):
    if not price_text:
        return None, None
    txt = price_text.replace("\xa0", " ").strip()
    currency = None
    if "₺" in txt or "TL" in txt.upper():
        currency = "TRY"
    elif "$" in txt:
        currency = "USD"
    cleaned = ''.join(ch for ch in txt if ch.isdigit() or ch in ',. ')
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


def save_programs_to_db(programs: list, university_name: str, mongo_collection, generic_price_text: str | None = None):
    import datetime

    now = datetime.datetime.utcnow()
    import re
    # filter out non-department lines
    headers = ['üniversite', 'tüm önlisans', 'alfabetik', 'tüm bölümler', 'program atlası', 'yokatlas', 'tercih sihirbazı', 'mezun başarı', 'net sihirbazı', 'bize öneri']
    to_save = []
    for prog in programs:
        if not prog or len(prog.strip()) < 3:
            continue
        if re.match(r'^\(.*\)$', prog.strip()):
            continue
        low = prog.lower()
        if any(h in low for h in headers):
            continue
        to_save.append(prog)

    # First pass: extract inline prices and clean department names
    import re
    rows = []
    price_pat = re.compile(r'(₺\s?[\d\.,]+(?:\s*TL)?|[\d\.,]+\s?TL\b|\$\s?[\d\.,]+)')
    for prog in to_save:
        prog_name = prog
        price_text = ""
        price_value = None
        currency = None
        pm = price_pat.search(prog_name)
        if pm:
            price_text = pm.group(0).strip()
            price_value, currency = _parse_price_text(price_text)
            prog_name = (prog_name[:pm.start()] + prog_name[pm.end():]).strip(' ,;')
        rows.append({
            'orig': prog,
            'name': prog_name,
            'price_text': price_text,
            'price_value': price_value,
            'currency': currency,
        })

    # Helper to compute base program name by removing common variant markers
    def _base_name(name: str) -> str:
        if not name:
            return name
        s = name
        # remove parenthetical variant strings like (Burslu), (Ücretli), (İÖ), (%50 İndirimli)
        s = re.sub(r"\s*\([^)]*(Burslu|Ücretli|İÖ|I\.Ö|İndirimli|%\s*\d+)[^)]*\)", "", s, flags=re.IGNORECASE)
        # remove trailing discount tokens
        s = re.sub(r"%\s*\d+\s*İndirimli", "", s, flags=re.IGNORECASE)
        s = s.replace('  ', ' ').strip(' ,;-')
        return s.strip()

    # Build a map of base_name -> first seen price (from inline extraction)
    base_price_map = {}
    for r in rows:
        if r['price_text']:
            base = _base_name(r['name'])
            if base and base not in base_price_map:
                base_price_map[base] = {
                    'price_text': r['price_text'],
                    'price_value': r['price_value'],
                    'currency': r['currency'],
                }

    # Second pass: upsert rows, inheriting base price when row has no inline price
    for r in rows:
        name = r['name']
        price_text = r['price_text']
        price_value = r['price_value']
        currency = r['currency']

        if not price_text:
            base = _base_name(name)
            if base and base in base_price_map:
                price_text = base_price_map[base]['price_text']
                price_value = base_price_map[base]['price_value']
                currency = base_price_map[base]['currency']

        # fallback to generic price if still missing
        q = {"university_name": university_name, "department": name}
        existing = mongo_collection.find_one(q)
        if not price_text and generic_price_text and (not existing or not existing.get('price_text')):
            price_text = generic_price_text
            price_value, currency = _parse_price_text(generic_price_text)

        doc = {
            "university_name": university_name,
            "department": name,
            "price_text": price_text,
            "price_value": price_value,
            "currency": currency,
            "scraped_at": now,
        }
        mongo_collection.update_one(q, {"$set": doc}, upsert=True)

    # After upserting parsed rows, aggressively copy base prices into variant documents
    # across the collection when a variant lacks a price.
    variant_updated = 0
    all_docs = list(mongo_collection.find({'university_name': university_name}))
    for d in all_docs:
        dept = d.get('department') or ''
        if d.get('price_text'):
            continue
        if '(' not in dept:
            continue
        base = _base_name(dept)
        if not base:
            continue
        # try same-university base first, then any department fallback
        base_doc = mongo_collection.find_one({'university_name': university_name, 'department': base}) or mongo_collection.find_one({'department': base})
        if base_doc and base_doc.get('price_text'):
            mongo_collection.update_one({'_id': d['_id']}, {'$set': {
                'price_text': base_doc.get('price_text'),
                'price_value': base_doc.get('price_value'),
                'currency': base_doc.get('currency'),
                'scraped_at': now,
            }})
            variant_updated += 1

    if variant_updated:
        print(f'Updated {variant_updated} variant documents by inheriting base prices.')

    # Now: if there's a DB record whose department mentions 'diğer ön lisans',
    # take its price and assign it to any documents for this university that
    # currently have no price_text.
    try:
        gen_doc = mongo_collection.find_one({
            'university_name': university_name,
            'department': {'$regex': r"diğer\s*ön\s*lisans", '$options': 'i'}
        })
        if not gen_doc:
            # try a more permissive match
            gen_doc = mongo_collection.find_one({
                'university_name': university_name,
                'department': {'$regex': r"diğer", '$options': 'i'}
            })

        if gen_doc and gen_doc.get('price_text'):
            g_price_text = gen_doc.get('price_text')
            g_value = gen_doc.get('price_value')
            g_currency = gen_doc.get('currency')
            # update any docs for this university missing a price_text
            res = mongo_collection.update_many(
                {
                    'university_name': university_name,
                    '$or': [
                        {'price_text': {'$exists': False}},
                        {'price_text': ''},
                        {'price_text': None},
                    ]
                },
                {'$set': {'price_text': g_price_text, 'price_value': g_value, 'currency': g_currency, 'scraped_at': now}}
            )
            print(f"Propagated generic DB price from '{gen_doc.get('department')}' to {res.modified_count} records.")
        else:
            print("No 'diğer ön lisans' price found in DB to propagate.")
    except Exception as e:
        print('Generic-price propagation failed:', e)

if __name__ == "__main__":
    # support: SCRAPER_YOKATLAS_URL, SCRAPER_YOKATLAS_ID, or SCRAPER_QUERY (search term)
    raw_url = os.environ.get("SCRAPER_YOKATLAS_URL")
    raw_id = os.environ.get("SCRAPER_YOKATLAS_ID")
    query = os.environ.get("SCRAPER_QUERY")
    url = None
    if raw_url:
        url = raw_url
    elif raw_id and raw_id.isdigit():
        url = f"https://yokatlas.yok.gov.tr/onlisans-univ.php?u={raw_id}"
    elif query:
        resolved = resolve_yokatlas_url_from_query(query)
        url = resolved or f"https://yokatlas.yok.gov.tr/onlisans-univ.php?u=2104"
    else:
        url = f"https://yokatlas.yok.gov.tr/onlisans-univ.php?u=2104"
    university = os.environ.get("UNIVERSITY_NAME") or "Istanbul Nisantasi University"
    try:
        print("Using URL:", url)
        progs, gen_price = fetch_onlisans_programs(url)
        # filter for display: remove parenthetical-only and header/menu lines
        import re
        headers = ['üniversite', 'tüm önlisans', 'alfabetik', 'tüm bölümler', 'program atlası', 'yokatlas', 'tercih sihirbazı', 'mezun başarı', 'net sihirbazı', 'bize öneri']
        display = []
        for p in progs:
            if not p or len(p.strip()) < 3:
                continue
            if re.match(r'^\(.*\)$', p.strip()):
                continue
            low = p.lower()
            if any(h in low for h in headers):
                continue
            display.append(p)

        print(f"Found {len(display)} programs (filtered display)")
        if gen_price:
            print("Generic price found:", gen_price)
        for p in display[:40]:
            print(p)
        # try saving if mongo is available
        try:
            import sys
            sys.path.insert(0, os.getcwd())
            from util.connect import get_db
            db = get_db()
            coll = db["university_prices"]
            save_programs_to_db(progs, university, coll, generic_price_text=gen_price)
            print("Saved to DB (upsert per program)")
        except Exception as e:
            print("DB save skipped/failed:", e)
    except Exception as e:
        print("Failed to fetch/parse YokAtlas:", e)
