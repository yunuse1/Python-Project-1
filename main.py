import csv
import logging
from util.web_scraping import scrape_universities_from_list
from repository.repository import UniversityPriceRepository
import argparse
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def normalize_turkish_text(text: str) -> str:
    """Normalize Turkish text for case-insensitive comparison.
    
    Handles Turkish-specific characters like İ, ı, Ş, ş, Ğ, ğ, Ü, ü, Ö, ö, Ç, ç.
    
    Args:
        text: Input text to normalize
    
    Returns:
        Lowercase normalized text
    """
    if not text:
        return ''
    
    text = text.strip()
    turkish_uppercase = 'ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ'
    turkish_lowercase = 'abcçdefgğhıijklmnoöprsştuüvyz'
    
    result = ''
    for character in text:
        if character in turkish_uppercase:
            result += turkish_lowercase[turkish_uppercase.index(character)]
        else:
            result += character.lower()
    return result


def list_universities():
    """List all universities in the database."""
    repository = UniversityPriceRepository()
    all_prices = repository.get_all_prices()
    unique_universities = sorted({price.university_name for price in all_prices})
    
    if unique_universities:
        print('Universities in database:')
        for university_name in unique_universities:
            print(f'  - {university_name}')
        print(f'\nTotal: {len(unique_universities)} universities')
    else:
        print('No universities found in database.')


def export_prices(
    university_filter: str,
    department_filter: str,
    price_option: str,
    should_apply_preference_discount: bool,
    output_filename: str
):
    """Export university prices to CSV file.
    
    Args:
        university_filter: University name to filter (or 'all')
        department_filter: Department name to filter (or 'all')
        price_option: 'full' or 'half' scholarship price
        should_apply_preference_discount: Whether to apply preference discount
        output_filename: Output CSV filename
    """
    repository = UniversityPriceRepository()

    # Fetch prices from database with optional filtering
    if university_filter.lower() != 'all':
        all_prices = repository.get_all_prices()
        search_query = university_filter.strip().lower()
        filtered_prices = [
            price for price in all_prices 
            if search_query in (price.university_name or '').lower()
        ]
    else:
        filtered_prices = repository.get_all_prices()

    if not filtered_prices:
        logger.warning(f'No prices found for university filter: {university_filter}')
        return

    # Convert price models to dictionaries for processing
    department_price_list = []
    for price in filtered_prices:
        price_amount = price.price_amount if price.price_amount is not None else None
        # Skip records with empty department names
        if not price.department_name or not price.department_name.strip():
            continue
        department_price_list.append({
            'university_name': price.university_name,
            'faculty_name': price.faculty_name or '',
            'department_name': price.department_name,
            'price_amount': price_amount,
        })

    # Filter by department if requested
    if department_filter.lower() != 'all':
        department_price_list = [
            item for item in department_price_list
            if department_filter.lower() in item.get('department_name', '').lower()
        ]

    if not department_price_list:
        logger.warning(f'No prices found for department filter: {department_filter}')
        return

    # Load scholarship rates for preference discount calculation
    try:
        from util.school_list import scholarship_rates
        scholarship_rate_map = {university: rate for university, rate in scholarship_rates}
    except Exception:
        scholarship_rate_map = {}

    # Normalize scholarship rate map keys for case-insensitive matching
    normalized_scholarship_rates = {
        normalize_turkish_text(key): value
        for key, value in scholarship_rate_map.items()
    }

    # Calculate and attach preference discount information
    for price_record in department_price_list:
        normalized_university_name = normalize_turkish_text(price_record['university_name'])
        discount_rate = normalized_scholarship_rates.get(normalized_university_name)
        current_price = price_record.get('price_amount')

        if discount_rate and isinstance(current_price, (int, float)):
            discounted_price = round(current_price * (1 - discount_rate / 100), 2)
            price_record['has_preference_discount'] = True
            price_record['preference_discount_rate'] = discount_rate
            price_record['preference_discounted_price'] = discounted_price
            price_record['preference_discount_info'] = f"A preference discount of {discount_rate}% is available (price after discount: {discounted_price})."
        elif discount_rate:
            price_record['has_preference_discount'] = True
            price_record['preference_discount_rate'] = discount_rate
            price_record['preference_discounted_price'] = None
            price_record['preference_discount_info'] = f"A preference discount of {discount_rate}% is available."
        else:
            price_record['has_preference_discount'] = False
            price_record['preference_discount_rate'] = 0
            price_record['preference_discounted_price'] = None
            price_record['preference_discount_info'] = "No preference discount available."

    # Apply half scholarship price if requested
    if price_option == 'half':
        for price_record in department_price_list:
            if isinstance(price_record.get('price_amount'), (int, float)):
                price_record['price_amount'] = price_record['price_amount'] * 0.5

    # Apply preference discount to price if requested
    if should_apply_preference_discount:
        for price_record in department_price_list:
            discount_rate = price_record.get('preference_discount_rate', 0) or 0
            if isinstance(price_record.get('price_amount'), (int, float)) and discount_rate:
                price_record['price_amount'] = round(price_record['price_amount'] * (1 - discount_rate / 100), 2)

    # Prepare CSV output - only include discount columns if discount is applied
    if should_apply_preference_discount:
        csv_field_names = [
            'university_name',
            'faculty_name',
            'department_name',
            'price_amount',
            'preference_discount_rate',
            'preference_discounted_price',
            'preference_discount_info'
        ]
    else:
        csv_field_names = [
            'university_name',
            'faculty_name',
            'department_name',
            'price_amount'
        ]

    # Sanitize records for CSV output
    sanitized_records = []
    for price_record in department_price_list:
        record = {
            'university_name': price_record.get('university_name', ''),
            'faculty_name': price_record.get('faculty_name', ''),
            'department_name': price_record.get('department_name', ''),
            'price_amount': price_record.get('price_amount', None),
        }
        # Only add discount fields if applying preference discount
        if should_apply_preference_discount:
            record['preference_discount_rate'] = price_record.get('preference_discount_rate', 0) or 0
            record['preference_discounted_price'] = price_record.get('preference_discounted_price', None)
            record['preference_discount_info'] = price_record.get('preference_discount_info', 'No preference discount available.')
        sanitized_records.append(record)

    # Write to CSV file
    with open(output_filename, 'w', newline='', encoding='utf-8-sig') as csv_file:
        if sanitized_records:
            csv_writer = csv.DictWriter(csv_file, fieldnames=csv_field_names, delimiter=';')
            csv_writer.writeheader()
            csv_writer.writerows(sanitized_records)
            logger.info(f'{len(sanitized_records)} records saved to: {output_filename}')
        else:
            logger.error('No records found to export.')


def main():
    # Set up argument parser
    argument_parser = argparse.ArgumentParser(
        description='Scrape university tuition prices and export to CSV.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape all universities and export to CSV
  python main.py --scrape --export

  # List all universities in database
  python main.py --list

  # Export specific university
  python main.py --export --university "İstinye Üniversitesi"

  # Export with half scholarship price
  python main.py --export --university "all" --price-option half

  # Export with preference discount applied
  python main.py --export --university "İstinye Üniversitesi" --apply-preference-discount

  # Show notifications
  python main.py --show-notifications
        """
    )
    
    # Action arguments (mutually exclusive main actions)
    action_group = argument_parser.add_argument_group('Actions')
    action_group.add_argument(
        '--scrape',
        action='store_true',
        help='Run the scraping step to fetch prices from web'
    )
    action_group.add_argument(
        '--list',
        action='store_true',
        help='List all universities in the database'
    )
    action_group.add_argument(
        '--export',
        action='store_true',
        help='Export prices to CSV file'
    )
    action_group.add_argument(
        '--show-notifications',
        action='store_true',
        help='Fetch and display notifications from NOTIFY_TOPIC'
    )
    
    # Scraping options
    scrape_group = argument_parser.add_argument_group('Scraping Options')
    scrape_group.add_argument(
        '--scrape-delay',
        type=float,
        default=0.0,
        help='Delay between scrape requests in seconds (default: 0.0)'
    )
    scrape_group.add_argument(
        '--start-index',
        type=int,
        default=0,
        help='Start index when scraping the universities list (default: 0)'
    )
    scrape_group.add_argument(
        '--stop-index',
        type=int,
        default=None,
        help='Stop index (exclusive) when scraping the universities list'
    )
    
    # Export/Filter options
    export_group = argument_parser.add_argument_group('Export Options')
    export_group.add_argument(
        '--university',
        type=str,
        default='all',
        help='University name to filter, use "all" for all universities (default: all)'
    )
    export_group.add_argument(
        '--department',
        type=str,
        default='all',
        help='Department name to filter, use "all" for all departments (default: all)'
    )
    export_group.add_argument(
        '--price-option',
        choices=['full', 'half'],
        default='full',
        help='Price option: "full" for full price, "half" for 50%% scholarship (default: full)'
    )
    export_group.add_argument(
        '--apply-preference-discount',
        action='store_true',
        help='Apply preference discount to prices when available'
    )
    export_group.add_argument(
        '--output',
        type=str,
        default='university_department_prices.csv',
        help='Output CSV filename (default: university_department_prices.csv)'
    )
    
    parsed_args = argument_parser.parse_args()

    # Check if no action specified
    if not any([parsed_args.scrape, parsed_args.list, parsed_args.export, parsed_args.show_notifications]):
        argument_parser.print_help()
        print('\nError: Please specify at least one action (--scrape, --list, --export, or --show-notifications)')
        return

    # Handle scraping
    if parsed_args.scrape:
        logger.info('Starting scraping process...')
        try:
            scrape_universities_from_list(
                save=True,
                delay=parsed_args.scrape_delay,
                start_index=parsed_args.start_index,
                stop_index=parsed_args.stop_index
            )
            logger.info('Scraping completed successfully.')
        except Exception:
            logger.exception('Scraping failed')

    # Handle list universities
    if parsed_args.list:
        list_universities()

    # Handle export
    if parsed_args.export:
        export_prices(
            university_filter=parsed_args.university,
            department_filter=parsed_args.department,
            price_option=parsed_args.price_option,
            should_apply_preference_discount=parsed_args.apply_preference_discount,
            output_filename=parsed_args.output
        )

    # Handle notifications
    if parsed_args.show_notifications:
        notification_topic = os.environ.get('NOTIFY_TOPIC')
        if not notification_topic:
            logger.error('NOTIFY_TOPIC environment variable not set. Please set it to your ntfy topic.')
        else:
            try:
                from util.notifications import fetch_notifications, print_notifications
                logger.info(f'Fetching notifications from topic: {notification_topic}')
                notification_events = fetch_notifications(notification_topic, poll_duration=1)
                print(f'\n--- Notifications from topic: {notification_topic} ---')
                print_notifications(notification_events)
            except Exception as notification_error:
                logger.error(f'Failed to fetch notifications: {notification_error}')


if __name__ == "__main__":
    main()
