from __future__ import annotations
import os
import ssl
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import datetime
import re
import sys
import unicodedata
import time
import requests

sys.path.insert(0, os.getcwd())
from models.university_models import DepartmentPrice
from repository.repository import UniversityPriceRepository

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def _parse_price_num(price_text: str):
    if not price_text:
        return None, None
    txt = price_text.replace('\xa0', ' ').strip()
    currency = None
    if '₺' in txt or 'TL' in txt.upper():
        currency = 'TRY'
    elif '$' in txt:
        currency = 'USD'
    # remove non-number characters except , and .
    num = re.sub(r"[^0-9,\.]+", "", txt)
    if not num:
        return None, currency
    # normalize thousand separators
    if '.' in num and ',' in num:
        num = num.replace('.', '').replace(',', '.')
    else:
        if '.' in num and len(num.split('.')[-1]) == 3:
            num = num.replace('.', '')
        num = num.replace(',', '.')
    try:
        return float(num), currency
    except Exception:
        return None, currency


def fetch_university_list(base_url: str = "https://www.universitego.com/") -> list:
    req = urllib.request.Request(base_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        html = resp.read()
    soup = BeautifulSoup(html, "html.parser")

    anchors = soup.find_all("a", href=True)
    seen = {}
    pattern = re.compile(r"/([^/]+)-universitesi-ucretleri/?", flags=re.IGNORECASE)
    for a in anchors:
        href = a["href"]
        m = pattern.search(href)
        if not m:
            if 'ücret' in href.lower() and 'universite' in href.lower():
                pass
            else:
                continue
        full = urllib.parse.urljoin(base_url, href)
        text = a.get_text(" ", strip=True)
        if not text:
            name = m.group(1).replace('-', ' ').title() if m else urllib.parse.urlparse(href).path
        else:
            name = text
        if full not in seen:
            seen[full] = {"name": name.strip(), "url": full}

    return list(seen.values())


def find_university_url(universities: list, query: str) -> str | None:
    q = query.strip().lower()
    for u in universities:
        if u["name"].strip().lower() == q:
            return u["url"]
    for u in universities:
        if q in u["name"].strip().lower():
            return u["url"]
    qtokens = q.split()
    for u in universities:
        name = u["name"].strip().lower()
        if all(tok in name for tok in qtokens):
            return u["url"]
    return None


def slugify(name: str) -> str:
    if not name:
        return ''
    s = name.lower()
    s = s.replace('üniversitesi', '').replace('universitesi', '').replace('ücretleri', '').strip()
    # map common Turkish characters to ASCII equivalents
    trans = str.maketrans({
        'ş': 's', 'Ş': 's',
        'ı': 'i', 'İ': 'i',
        'ğ': 'g', 'Ğ': 'g',
        'ü': 'u', 'Ü': 'u',
        'ö': 'o', 'Ö': 'o',
        'ç': 'c', 'Ç': 'c',
    })
    s = s.translate(trans)
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-{2,}', '-', s).strip('-')
    return s


def scrape_universitego_table(url: str, university_name: str | None = None):
    print('Fetching:', url)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        html = resp.read()
    soup = BeautifulSoup(html, 'html.parser')

    # find candidate tables: prefer id 'ozeluni' or table containing header with 'Ücret' or 'Bölüm Adı'
    table = None
    table = soup.find('table', id='ozeluni') or soup.find('table', class_='ozeluni')
    if not table:
        for t in soup.find_all('table'):
            ths = t.find_all(['th'])
            headers = ' '.join([th.get_text(' ', strip=True).lower() for th in ths])
            if 'ücret' in headers or 'bölüm' in headers:
                table = t
                break

    if not table:
        print('No suitable table found on page')
        return 0, 0

    # locate column indices for department and price
    dept_idx = None
    price_idx = None
    header_row = table.find('tr')
    if header_row:
        cols = [c.get_text(' ', strip=True).lower() for c in header_row.find_all(['th', 'td'])]
        for i, h in enumerate(cols):
            if 'bölüm' in h or 'bölüm adı' in h or 'program' in h:
                dept_idx = i
            if 'ücret' in h or 'ücretleri' in h or 'ücret' in h:
                price_idx = i

    # fallback positions
    if dept_idx is None:
        dept_idx = 0
    if price_idx is None:
        price_idx = -1

    rows = []
    for tr in table.find_all('tr'):
        tds = [td.get_text(' ', strip=True) for td in tr.find_all(['td', 'th'])]
        if len(tds) <= 1:
            continue
        # try to guard against header rows
        if any('bölüm' in c.lower() or 'ücret' in c.lower() for c in tds[:3]):
            continue
        try:
            dept = tds[dept_idx]
        except Exception:
            dept = tds[0]
        try:
            price_text = tds[price_idx]
        except Exception:
            price_text = ''
        value, currency = _parse_price_num(price_text)
        rows.append({'department': dept, 'price_text': price_text or '', 'price_value': value, 'currency': currency})

    # save to DB via repository
    repo = UniversityPriceRepository()
    now = datetime.datetime.utcnow()
    uni = university_name or os.environ.get('UNIVERSITY_NAME') or urllib.parse.urlparse(url).path.split('/')[-2].replace('-', ' ').strip()
    inserted = 0
    updated = 0
    for r in rows:
        dept_price = DepartmentPrice(
            university=uni,
            department=r.get('department', ''),
            price_text=r.get('price_text', ''),
            price_value=r.get('price_value'),
            currency=r.get('currency'),
            scraped_at=now,
        )
        ins, upd = repo.upsert_price(dept_price)
        if ins:
            inserted += 1
        elif upd:
            updated += 1

    print(f'Saved {len(rows)} rows – inserted {inserted}, updated {updated}')
    return inserted, updated


if __name__ == '__main__':
    url = os.environ.get('SCRAPER_URL') or 'https://www.universitego.com/istanbul-arel-universitesi-ucretleri/'
    uni = os.environ.get('UNIVERSITY_NAME') or 'Istanbul Arel University'
    scrape_universitego_table(url, uni)


def run_interactive_scrape():
    # Fetch the university list lazily only when the user explicitly asks for it
    universities = None

    print('Type "list" to fetch and show available universities from universitego.com, or type a university name to scrape its page.')
    uni_input = input('University (name or "list"): ').strip()
    if not uni_input:
        print('No input; aborting.')
        return

    if uni_input.lower() == 'list':
        try:
            universities = fetch_university_list()
        except Exception as e:
            print('Failed to fetch university list:', e)
            universities = []

        if not universities:
            print('No universities fetched.')
            return
        for u in universities:
            print('-', u['name'])
        return

    # User provided a name: avoid network calls by default — construct a slug
    # and try the expected universitego URL. This is fast and works for most
    # cases; if you want site-based matching, type "list" instead.
    slug = slugify(uni_input)
    url = f'https://www.universitego.com/{slug}-universitesi-ucretleri/'

    print('Scraping URL:', url)
    try:
        scrape_universitego_table(url, uni_input)
    except Exception as e:
        print('Scrape failed:', e)


def scrape_universities_from_list(save: bool = True, delay: int = 0, start_index: int = 0, stop_index: int | None = None):
    try:
        from util.school_list import universities
    except Exception as e:
        print('Could not import university list:', e)
        return

    total = len(universities)
    stop = stop_index if stop_index is not None else total
    inserted_total = 0
    updated_total = 0
    failed_total = 0
    for idx, name in enumerate(universities[start_index:stop], start=start_index):
        slug = slugify(name)
        url = f'https://www.universitego.com/{slug}-universitesi-ucretleri/'
        print(f'[{idx+1}/{total}] -> {name} -> {url}')
        if save:
            try:
                ins, upd = scrape_universitego_table(url, name)
                try:
                    inserted_total += int(ins or 0)
                except Exception:
                    pass
                try:
                    updated_total += int(upd or 0)
                except Exception:
                    pass
            except Exception as e:
                failed_total += 1
                print(f'Failed to scrape {name}:', e)
        if delay and (idx + 1) < stop:
            time.sleep(delay)

    # send notification if topic provided via environment
    notify_topic = os.environ.get('NOTIFY_TOPIC')
    if save and notify_topic:
        msg = f"Bütün üniversiteler güncellendi. Toplam taranan: {total}, başarılı sayfa içi kayıt: inserted={inserted_total}, updated={updated_total}, failed={failed_total}."
        try:
            send_notification(notify_topic, msg, title='Universiteler Güncellendi')
        except Exception as e:
            print('Notification failed:', e)


def send_notification(topic: str, message: str, title: str | None = None, priority: int = 3):
    """Send a notification using ntfy.sh (simple POST).

    Requires environment variable `NOTIFY_TOPIC` or passing a `topic` value.
    """
    import sys
    if not topic:
        return
    url = f'https://ntfy.sh/{topic}'
    headers = {}
    if title:
        headers['Title'] = title
    headers['Priority'] = str(priority)
    try:
        resp = requests.post(url, data=message.encode('utf-8'), headers=headers, timeout=10)
        resp.raise_for_status()
        # Echo the notification locally so the user sees the exact message
        print('\n' + '='*60)
        print(f'✓ NOTIFICATION SENT to {topic} (HTTP {resp.status_code})')
        print('='*60)
        if title:
            print(f'Title: {title}')
        print(f'Message:\n{message}')
        print('='*60 + '\n')
        sys.stdout.flush()
    except Exception as e:
        print(f'✗ Failed to send notification to {url}: {e}', flush=True)

       