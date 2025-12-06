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
from models.university_models import UniversityDepartmentPrice
from repository.repository import UniversityPriceRepository

# SSL context for HTTPS requests (disable verification for scraping)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


def parse_price_from_text(price_text: str) -> tuple[float | None, str | None]:
    """Parse a price string and extract numeric value and currency code.
    
    Args:
        price_text: Raw price string (e.g., "₺235.000,00")
    
    Returns:
        Tuple of (price_amount, currency_code)
    """
    if not price_text:
        return None, None
    
    cleaned_text = price_text.replace('\xa0', ' ').strip()
    currency_code = None
    
    # Detect currency
    if '₺' in cleaned_text or 'TL' in cleaned_text.upper():
        currency_code = 'TRY'
    elif '$' in cleaned_text:
        currency_code = 'USD'
    
    # Remove non-numeric characters except comma and period
    numeric_string = re.sub(r"[^0-9,\.]+", "", cleaned_text)
    if not numeric_string:
        return None, currency_code
    
    # Normalize thousand separators and decimal points
    if '.' in numeric_string and ',' in numeric_string:
        numeric_string = numeric_string.replace('.', '').replace(',', '.')
    else:
        if '.' in numeric_string and len(numeric_string.split('.')[-1]) == 3:
            numeric_string = numeric_string.replace('.', '')
        numeric_string = numeric_string.replace(',', '.')
    
    try:
        return float(numeric_string), currency_code
    except ValueError:
        return None, currency_code


def fetch_university_list(base_url: str = "https://www.universitego.com/") -> list[dict]:
    """Fetch list of universities from the main page.
    
    Returns:
        List of dictionaries with 'name' and 'url' keys
    """
    request = urllib.request.Request(base_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, context=ssl_context, timeout=30) as response:
        html_content = response.read()
    
    soup = BeautifulSoup(html_content, "html.parser")
    anchor_tags = soup.find_all("a", href=True)
    
    discovered_universities = {}
    url_pattern = re.compile(r"/([^/]+)-universitesi-ucretleri/?", flags=re.IGNORECASE)
    
    for anchor in anchor_tags:
        href = anchor["href"]
        pattern_match = url_pattern.search(href)
        
        if not pattern_match:
            if 'ücret' in href.lower() and 'universite' in href.lower():
                pass
            else:
                continue
        
        full_url = urllib.parse.urljoin(base_url, href)
        link_text = anchor.get_text(" ", strip=True)
        
        if not link_text:
            university_name = pattern_match.group(1).replace('-', ' ').title() if pattern_match else urllib.parse.urlparse(href).path
        else:
            university_name = link_text
        
        if full_url not in discovered_universities:
            discovered_universities[full_url] = {"name": university_name.strip(), "url": full_url}

    return list(discovered_universities.values())


def find_university_url(university_list: list[dict], search_query: str) -> str | None:
    """Find a university URL by name (exact or partial match).
    
    Args:
        university_list: List of university dictionaries
        search_query: University name to search for
    
    Returns:
        URL string if found, None otherwise
    """
    normalized_query = search_query.strip().lower()
    
    # Try exact match first
    for university in university_list:
        if university["name"].strip().lower() == normalized_query:
            return university["url"]
    
    # Try partial match
    for university in university_list:
        if normalized_query in university["name"].strip().lower():
            return university["url"]
    
    # Try token-based match
    query_tokens = normalized_query.split()
    for university in university_list:
        university_name = university["name"].strip().lower()
        if all(token in university_name for token in query_tokens):
            return university["url"]
    
    return None


def slugify_university_name(name: str) -> str:
    """Convert university name to URL-friendly slug.
    
    Args:
        name: University name in Turkish
    
    Returns:
        URL-friendly slug string
    """
    if not name:
        return ''
    
    slug = name.lower()
    slug = slug.replace('üniversitesi', '').replace('universitesi', '').replace('ücretleri', '').strip()
    
    # Map Turkish characters to ASCII equivalents
    turkish_char_map = str.maketrans({
        'ş': 's', 'Ş': 's',
        'ı': 'i', 'İ': 'i',
        'ğ': 'g', 'Ğ': 'g',
        'ü': 'u', 'Ü': 'u',
        'ö': 'o', 'Ö': 'o',
        'ç': 'c', 'Ç': 'c',
    })
    slug = slug.translate(turkish_char_map)
    slug = unicodedata.normalize('NFKD', slug)
    slug = slug.encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = re.sub(r'-{2,}', '-', slug).strip('-')
    
    return slug


def scrape_university_prices(url: str, university_name: str | None = None) -> tuple[int, int]:
    """Scrape department prices from a university page.
    
    Args:
        url: URL of the university prices page
        university_name: Name of the university (optional, will be extracted from URL if not provided)
    
    Returns:
        Tuple of (inserted_count, updated_count)
    """
    print(f'Fetching: {url}')
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with urllib.request.urlopen(request, context=ssl_context, timeout=30) as response:
            html_content = response.read()
    except urllib.error.HTTPError as http_error:
        if http_error.code == 404:
            fallback_urls = []
            
            if '-universitesi-ucretleri' in url:
                fallback_urls.append(url.replace('-universitesi-ucretleri/', '-ucretleri/'))
                fallback_urls.append(url.replace('-universitesi-ucretleri/', '-universitesi/'))
            
            if 'yuksekokulu' in url and 'yusekokulu' not in url:
                fallback_urls.append(url.replace('yuksekokulu', 'yusekokulu'))
            
            page_fetched = False
            for fallback_url in fallback_urls:
                try:
                    print(f'Got 404, trying fallback URL: {fallback_url}')
                    request = urllib.request.Request(fallback_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(request, context=ssl_context, timeout=30) as response:
                        html_content = response.read()
                    page_fetched = True
                    break
                except urllib.error.HTTPError:
                    continue
            
            if not page_fetched:
                raise http_error
        else:
            raise
    
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the price table
    price_table = soup.find('table', id='ozeluni') or soup.find('table', class_='ozeluni')
    
    if not price_table:
        for table in soup.find_all('table'):
            table_headers = table.find_all(['th'])
            headers_text = ' '.join([th.get_text(' ', strip=True).lower() for th in table_headers])
            if 'ücret' in headers_text or 'bölüm' in headers_text:
                price_table = table
                break

    if not price_table:
        print('No suitable table found on page')
        return 0, 0

    # Determine column indices
    department_column_index = None
    price_column_index = None
    
    header_row = price_table.find('tr')
    if header_row:
        column_headers = [cell.get_text(' ', strip=True).lower() for cell in header_row.find_all(['th', 'td'])]
        for index, header in enumerate(column_headers):
            if 'bölüm' in header or 'bölüm adı' in header or 'program' in header:
                department_column_index = index
            if 'ücret' in header or 'ücretleri' in header:
                price_column_index = index

    if department_column_index is None:
        department_column_index = 0
    if price_column_index is None:
        price_column_index = -1

    # Extract rows
    extracted_rows = []
    for table_row in price_table.find_all('tr'):
        cells = [cell.get_text(' ', strip=True) for cell in table_row.find_all(['td', 'th'])]
        
        if len(cells) <= 1:
            continue
        
        # Skip header rows
        if any('bölüm' in cell.lower() or 'ücret' in cell.lower() for cell in cells[:3]):
            continue
        
        try:
            department_name = cells[department_column_index]
        except IndexError:
            department_name = cells[0]
        
        try:
            price_text = cells[price_column_index]
        except IndexError:
            price_text = ''
        
        price_amount, currency_code = parse_price_from_text(price_text)
        extracted_rows.append({
            'department_name': department_name,
            'price_description': price_text or '',
            'price_amount': price_amount,
            'currency_code': currency_code
        })

    # Save to database
    repository = UniversityPriceRepository()
    current_timestamp = datetime.datetime.utcnow()
    
    resolved_university_name = university_name or os.environ.get('UNIVERSITY_NAME') or urllib.parse.urlparse(url).path.split('/')[-2].replace('-', ' ').strip()
    
    inserted_count = 0
    updated_count = 0
    
    for row in extracted_rows:
        department_price = UniversityDepartmentPrice(
            university_name=resolved_university_name,
            department_name=row.get('department_name', ''),
            price_description=row.get('price_description', ''),
            price_amount=row.get('price_amount'),
            currency_code=row.get('currency_code'),
            last_scraped_at=current_timestamp,
        )
        was_inserted, was_updated = repository.upsert_department_price(department_price)
        
        if was_inserted:
            inserted_count += 1
        elif was_updated:
            updated_count += 1

    return inserted_count, updated_count


def run_interactive_scrape():
    """Run an interactive scraping session."""
    university_list = None

    user_input = input('University (name or "list"): ').strip()
    if not user_input:
        print('No input; aborting.')
        return

    if user_input.lower() == 'list':
        try:
            university_list = fetch_university_list()
        except Exception:
            university_list = []

        if not university_list:
            print('No universities fetched.')
            return
        
        for university in university_list:
            print('-', university['name'])
        return

    slug = slugify_university_name(user_input)
    url = f'https://www.universitego.com/{slug}-universitesi-ucretleri/'

    print(f'Scraping URL: {url}')
    try:
        scrape_university_prices(url, user_input)
    except Exception as error:
        print(f'Scrape failed: {error}')


def scrape_universities_from_list(save: bool = True, delay: float = 0, start_index: int = 0, stop_index: int | None = None):
    """Scrape prices for all universities in the predefined list.
    
    Args:
        save: Whether to save results to database
        delay: Delay in seconds between requests
        start_index: Starting index in the university list
        stop_index: Ending index (exclusive) in the university list
    """
    try:
        from util.school_list import universities as university_list
    except Exception as import_error:
        print(f'Could not import university list: {import_error}')
        return

    total_universities = len(university_list)
    end_index = stop_index if stop_index is not None else total_universities
    
    total_inserted = 0
    total_updated = 0
    total_failed = 0
    
    for index, university_name in enumerate(university_list[start_index:end_index], start=start_index + 1):
        slug = slugify_university_name(university_name)
        url = f'https://www.universitego.com/{slug}-universitesi-ucretleri/'
        print(f'[{index}/{total_universities}] -> {university_name} -> {url}')
        
        if save:
            try:
                inserted, updated = scrape_university_prices(url, university_name)
                total_inserted += int(inserted or 0)
                total_updated += int(updated or 0)
            except Exception as scrape_error:
                total_failed += 1
                print(f'Failed to scrape {university_name}: {scrape_error}')
        
        if delay and (index + 1) < end_index:
            time.sleep(delay)

    # Send notification if topic is configured
    notification_topic = os.environ.get('NOTIFY_TOPIC')
    if save and notification_topic:
        notification_message = (
            f"All universities have been updated. "
            f"Total scraped: {total_universities}, "
            f"inserted: {total_inserted}, "
            f"updated: {total_updated}, "
            f"failed: {total_failed}."
        )
        try:
            send_scrape_notification(notification_topic, notification_message, title='Universities Updated')
        except Exception as notification_error:
            print(f'Notification failed: {notification_error}')


def send_scrape_notification(topic: str, message: str, title: str | None = None, priority: int = 3):
    """Send a notification via ntfy.sh.
    
    Args:
        topic: ntfy topic name
        message: Notification message body
        title: Optional notification title
        priority: Priority level (1-5)
    """
    if not topic:
        return
    
    url = f'https://ntfy.sh/{topic}'
    headers = {}
    
    if title:
        headers['Title'] = title
    headers['Priority'] = str(priority)
    
    try:
        response = requests.post(url, data=message.encode('utf-8'), headers=headers, timeout=10)
        response.raise_for_status()
        
        print('\n' + '=' * 60)
        print(f'[OK] NOTIFICATION SENT to {topic} (HTTP {response.status_code})')
        print('=' * 60)
        if title:
            print(f'Title: {title}')
        print(f'Message:\n{message}')
        print('=' * 60 + '\n')
        sys.stdout.flush()
    except Exception as request_error:
        print(f'[FAILED] Notification to {url}: {request_error}', flush=True)


if __name__ == '__main__':
    scraper_url = os.environ.get('SCRAPER_URL') or 'https://www.universitego.com/istanbul-arel-universitesi-ucretleri/'
    university_name = os.environ.get('UNIVERSITY_NAME') or 'Istanbul Arel University'
    scrape_university_prices(scraper_url, university_name)