import logging
from util.web_scraping import scrape_universities_from_list
from repository.repository import UniversityPriceRepository
import argparse
import os

import pandas as pd
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from openpyxl.styles import Alignment
PDF_FONT = 'Helvetica'  
try:
    
    windows_font_path = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'arial.ttf')
    if os.path.exists(windows_font_path):
        pdfmetrics.registerFont(TTFont('Arial', windows_font_path))
        PDF_FONT = 'Arial'
except Exception:
    pass


def convert_to_excel(df: pd.DataFrame, xlsx_file: str):
    with pd.ExcelWriter(xlsx_file, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Prices')
        
        worksheet = writer.sheets['Prices']
    
        worksheet.column_dimensions['A'].width = 40  
        worksheet.column_dimensions['B'].width = 45  
        worksheet.column_dimensions['C'].width = 12  
        worksheet.column_dimensions['D'].width = 12  
        worksheet.column_dimensions['E'].width = 12  
        worksheet.column_dimensions['F'].width = 12  
        worksheet.column_dimensions['G'].width = 15  
        
        if len(df.columns) > 7:
            worksheet.column_dimensions['H'].width = 15  
            worksheet.column_dimensions['I'].width = 18  
            worksheet.column_dimensions['J'].width = 55  
            
        for row in worksheet.iter_rows():
            for cell in row:
                if cell.column == 10:  
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                else:
                    cell.alignment = Alignment(horizontal='center', vertical='center')

    logger.info(f"Excel file created: {xlsx_file}") 


def convert_to_pdf(df: pd.DataFrame, pdf_file: str):
    pdf = SimpleDocTemplate(pdf_file, pagesize=landscape(A4))

    data = [df.columns.tolist()] + df.values.tolist()

    table = Table(data)
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME', (0,0), (-1,-1), PDF_FONT),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('FONTSIZE', (0,0), (-1,0), 8),
    ]))

    pdf.build([table])

    logger.info(f"PDF file created: {pdf_file}")

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
        logger.info('Universities in database:')
        for university_name in unique_universities:
            logger.info(f'  - {university_name}')
        logger.info(f'Total: {len(unique_universities)} universities')
    else:
        logger.info('No universities found in database.')


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

    department_price_list = []
    for price in filtered_prices:
        price_amount = price.price_amount if price.price_amount is not None else None
        if not price.department_name or not price.department_name.strip():
            continue
        department_price_list.append({
            'university_name': price.university_name,
            'department_name': price.department_name,
            'score_type': price.score_type,
            'quota': price.quota,
            'score': price.score,
            'ranking': price.ranking,
            'price_amount': price_amount,
        })

    if department_filter.lower() != 'all':
        department_price_list = [
            item for item in department_price_list
            if department_filter.lower() in item.get('department_name', '').lower()
        ]

    if not department_price_list:
        logger.warning(f'No prices found for department filter: {department_filter}')
        return

    try:
        from util.school_list import scholarship_rates
        scholarship_rate_map = {university: rate for university, rate in scholarship_rates}
    except Exception:
        scholarship_rate_map = {}

    normalized_scholarship_rates = {
        normalize_turkish_text(key): value
        for key, value in scholarship_rate_map.items()
    }

    for price_record in department_price_list:
        normalized_university_name = normalize_turkish_text(price_record['university_name'])
        discount_rate = normalized_scholarship_rates.get(normalized_university_name)
        current_price = price_record.get('price_amount')
        
        price_record['original_price'] = current_price

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

    if price_option == 'half':
        for price_record in department_price_list:
            if isinstance(price_record.get('price_amount'), (int, float)):
                price_record['price_amount'] = price_record['price_amount'] * 0.5
                price_record['original_price'] = price_record['price_amount']
                if price_record.get('preference_discounted_price') is not None:
                    price_record['preference_discounted_price'] = price_record['preference_discounted_price'] * 0.5

    if should_apply_preference_discount:
        csv_field_names = [
            'University',
            'Department',
            'Score Type',
            'Quota',
            'Score',
            'Ranking',
            'Price',
            'Discount Rate (%)',
            'Discounted Price',
            'Discount Info'
        ]
    else:
        csv_field_names = [
            'University',
            'Department',
            'Score Type',
            'Quota',
            'Score',
            'Ranking',
            'Price'
        ]

    sanitized_records = []
    for price_record in department_price_list:
        record = {
            'University': price_record.get('university_name', ''),
            'Department': price_record.get('department_name', ''),
            'Score Type': price_record.get('score_type', '') or '',
            'Quota': price_record.get('quota', '') or '',
            'Score': price_record.get('score', '') if price_record.get('score') is not None else 'Dolmadı',
            'Ranking': price_record.get('ranking', '') if price_record.get('ranking') is not None else 'Dolmadı',
            'Price': price_record.get('original_price', None),
        }
        if should_apply_preference_discount:
            record['Discount Rate (%)'] = price_record.get('preference_discount_rate', 0) or 0
            record['Discounted Price'] = price_record.get('preference_discounted_price', None)
            record['Discount Info'] = price_record.get('preference_discount_info', 'No preference discount available.')
        sanitized_records.append(record)

    if not sanitized_records:
        logger.error('No records found to export.')
        return
    
    df = pd.DataFrame(sanitized_records)
    
    xlsx_file = output_filename.replace(".csv", ".xlsx") if output_filename.endswith(".csv") else output_filename + ".xlsx"
    pdf_file = output_filename.replace(".csv", ".pdf") if output_filename.endswith(".csv") else output_filename + ".pdf"

    convert_to_excel(df, xlsx_file)
    convert_to_pdf(df, pdf_file)

    logger.info(f'{len(sanitized_records)} records exported to Excel and PDF.')


def main():
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
        default='university_department_prices',
        help='Output filename without extension (default: university_department_prices)'
    )
    
    parsed_args = argument_parser.parse_args()

    if not any([parsed_args.scrape, parsed_args.list, parsed_args.export, parsed_args.show_notifications]):
        argument_parser.print_help()
        logger.error('Please specify at least one action (--scrape, --list, --export, or --show-notifications)')
        return

    if parsed_args.scrape:
        logger.info('Starting scraping process...')
        try:
            total_scraped, total_inserted, total_updated, total_failed = scrape_universities_from_list(
                save=True,
                delay=parsed_args.scrape_delay,
                start_index=parsed_args.start_index,
                stop_index=parsed_args.stop_index
            )
            logger.info(f'Scraping completed. Scraped: {total_scraped}, Inserted: {total_inserted}, Updated: {total_updated}, Failed: {total_failed}')
        except Exception:
            logger.exception('Scraping failed')

    if parsed_args.list:
        list_universities()

    if parsed_args.export:
        export_prices(
            university_filter=parsed_args.university,
            department_filter=parsed_args.department,
            price_option=parsed_args.price_option,
            should_apply_preference_discount=parsed_args.apply_preference_discount,
            output_filename=parsed_args.output
        )

    if parsed_args.show_notifications:
        notification_topic = os.environ.get('NOTIFY_TOPIC')
        if not notification_topic:
            logger.error('NOTIFY_TOPIC environment variable not set. Please set it to your ntfy topic.')
        else:
            try:
                from util.notifications import fetch_notifications, print_notifications
                logger.info(f'Fetching notifications from topic: {notification_topic}')
                notification_events = fetch_notifications(notification_topic, poll_duration=1)
                logger.info(f'--- Notifications from topic: {notification_topic} ---')
                print_notifications(notification_events)
            except Exception as notification_error:
                logger.error(f'Failed to fetch notifications: {notification_error}')


if __name__ == "__main__":
    main()
