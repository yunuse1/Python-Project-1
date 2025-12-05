import csv
import logging
from util.web_scraping import scrape_universities_from_list
from repository.repository import UniversityPriceRepository
import argparse
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Scrape university prices and export CSV.')
    parser.add_argument('--no-scrape', dest='scrape', action='store_false', help='Skip scraping step')
    parser.add_argument('--scrape-delay', type=float, default=0.0, help='Delay between scrape requests in seconds')
    parser.add_argument('--start-index', type=int, default=0, help='Start index when scraping the universities list')
    parser.add_argument('--stop-index', type=int, default=None, help='Stop index (exclusive) when scraping the universities list')
    parser.add_argument('--university', type=str, default='all', help='University name to filter (default: all)')
    parser.add_argument('--department', type=str, default='all', help='Department name to filter (default: all)')
    parser.add_argument('--price-option', choices=['full', 'half'], default='full', help='full or half scholarship price')
    parser.add_argument('--preference-discount', dest='preference_discount', action='store_true', help='Show preference discount when available')
    parser.add_argument('--output', type=str, default='university_department_prices.csv', help='CSV output filename')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode and ask user what to export')
    parser.add_argument('--show-notifications', action='store_true', help='Fetch and print ntfy notifications for NOTIFY_TOPIC after run')
    args = parser.parse_args()

    # Optionally run scraper (keeps all scraping logic inside util/web_scraping)
    if args.interactive:
        do_scrape = False
        resp = input('Do you want to run the scraping step now? (y/n): ').strip().lower()
        if resp in ('y', 'yes'):
            do_scrape = True
        if do_scrape and args.scrape:
            try:
                scrape_universities_from_list(save=True, delay=args.scrape_delay, start_index=args.start_index, stop_index=args.stop_index)
            except Exception:
                logger.exception('Scraping failed; continuing with DB queries')
    else:
        if args.scrape:
            try:
                scrape_universities_from_list(save=True, delay=args.scrape_delay, start_index=args.start_index, stop_index=args.stop_index)
            except Exception:
                # don't fail the entire program if scraping has a problem
                logger.exception('Scraping failed; continuing with DB queries')

    # After scraping (or skipping it), optionally fetch notifications and print them
    if args.show_notifications:
        notify_topic = os.environ.get('NOTIFY_TOPIC')
        if not notify_topic:
            print('NOTIFY_TOPIC not set; cannot fetch notifications. Set NOTIFY_TOPIC environment variable to your topic.')
        else:
            try:
                from util.notifications import fetch_notifications, print_notifications
                events = fetch_notifications(notify_topic, poll=1)
                print('\n--- Notifications from topic:', notify_topic, '---')
                print_notifications(events)
            except Exception as e:
                print('Failed to fetch/print notifications:', e)

    university = args.university
    department = args.department
    price_option = args.price_option
    apply_preference_discount = bool(args.preference_discount)

    # Interactive flow: ask user whether to list all universities or select specific
    if args.interactive:
        repo = UniversityPriceRepository()
        while True:
            raw = input("Type 'list' to show all universities, 'specific' to choose a university, 'all' to export everything, or type a university name directly: ").strip()
            choice = raw.lower()
            if choice == 'list':
                # print distinct university names from DB
                prices = repo.get_all_prices()
                universities = sorted({p.university for p in prices})
                if universities:
                    print('Universities:')
                    for u in universities:
                        print('-', u)
                else:
                    print('No universities found in DB.')
                return
            if choice == 'specific':
                u = input('Enter university name (exact or partial): ').strip()
                d = input('Enter department name (leave empty for all departments): ').strip()
                university = u if u else 'all'
                department = d if d else 'all'
                break
            if choice == 'all':
                university = 'all'
                department = 'all'
                break
            # If user typed a non-keyword, treat it as a direct university name
            if raw:
                university = raw
                d = input('Enter department name (leave empty for all departments): ').strip()
                department = d if d else 'all'
                break
            print("Unknown option. Please type 'list', 'specific', 'all', or a university name.")

    repo = UniversityPriceRepository()

    # Fetch rows from DB — use flexible matching for university (case-insensitive substring)
    if university.lower() != 'all':
        all_prices = repo.get_all_prices()
        q = university.strip().lower()
        prices = [p for p in all_prices if q in (p.university or '').lower()]
    else:
        prices = repo.get_all_prices()

    # convert DepartmentPrice dataclass instances to dicts for CSV
    schools_list = []
    for p in prices:
        price_val = p.price_value if p.price_value is not None else None
        schools_list.append({
            'university': p.university,
            'faculty': p.faculty or '',
            'department': p.department,
            'price': price_val,
        })

    # filter by department if requested
    if department.lower() != 'all':
        schools_list = [s for s in schools_list if department.lower() in s.get('department', '').lower()]

    # attach preference discount info (if available in util.school_list)
    try:
        from util.school_list import scholarship_rates
        rate_map = {u: r for u, r in scholarship_rates}
    except Exception:
        rate_map = {}
    for rec in schools_list:
        rate = rate_map.get(rec['university'])
        price_val = rec.get('price')
        if rate and isinstance(price_val, (int, float)):
            pref_price = round(price_val * (1 - rate / 100), 2)
            rec['preference_applicable'] = True
            rec['preference_discount'] = rate
            rec['preference_price'] = pref_price
            rec['preference_info'] = f"A preference discount of {rate}% is available (price after discount: {pref_price})."
        elif rate:
            # rate exists but price not numeric
            rec['preference_applicable'] = True
            rec['preference_discount'] = rate
            rec['preference_price'] = None
            rec['preference_info'] = f"A preference discount of {rate}% is available."
        else:
            rec['preference_applicable'] = False
            rec['preference_discount'] = 0
            rec['preference_price'] = None
            rec['preference_info'] = "No preference discount available."

    # apply half scholarship price if requested
    if price_option == 'half':
        for rec in schools_list:
            if isinstance(rec.get('price'), (int, float)):
                rec['price'] = rec['price'] * 0.5

    # apply preference discount to price if requested
    if apply_preference_discount:
        for rec in schools_list:
            rate = rec.get('preference_discount', 0) or 0
            if isinstance(rec.get('price'), (int, float)) and rate:
                rec['price'] = round(rec['price'] * (1 - rate / 100), 2)

    csv_filename = args.output

    # Ensure CSV rows only contain the expected fields — construct sanitized rows
    fieldnames = ['university', 'faculty', 'department', 'price', 'preference_discount', 'preference_price', 'preference_info']
    sanitized = []
    for rec in schools_list:
        sanitized.append({
            'university': rec.get('university', ''),
            'faculty': rec.get('faculty', ''),
            'department': rec.get('department', ''),
            'price': rec.get('price', None),
            'preference_discount': rec.get('preference_discount', 0) or 0,
            'preference_price': rec.get('preference_price', None),
            'preference_info': rec.get('preference_info', 'No preference discount available.'),
        })

    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as f:
        if sanitized:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(sanitized)
            logger.info(f' {len(sanitized)} recorded: {csv_filename}')
        else:
            logger.error('There is not found record.')

if __name__ == "__main__":
    main()
