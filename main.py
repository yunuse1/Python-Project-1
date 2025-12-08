import argparse
import logging
import os

import pandas as pd
from openpyxl.styles import Alignment
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from repository.repository import UniversityPriceRepository
from util.web_scraping import scrape_universities_from_list
from util.school_list import scholarship_rates
from util.notifications import fetch_notifications, print_notifications


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

PDF_FONT = 'Helvetica'
try:
    windows_font_path = os.path.join(
        os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'arial.ttf'
    )
    if os.path.exists(windows_font_path):
        pdfmetrics.registerFont(TTFont('Arial', windows_font_path))
        PDF_FONT = 'Arial'
except (OSError, IOError):
    pass


def convert_to_excel(dataframe: pd.DataFrame, xlsx_file: str) -> None:
    """Convert DataFrame to Excel file with formatting.

    Args:
        dataframe: The pandas DataFrame to export.
        xlsx_file: Output Excel file path.
    """
    with pd.ExcelWriter(xlsx_file, engine='openpyxl') as writer:
        dataframe.to_excel(writer, index=False, sheet_name='Prices')
        worksheet = writer.sheets['Prices']

        column_widths = {
            'A': 40, 'B': 70, 'C': 12, 'D': 12,
            'E': 12, 'F': 12, 'G': 15
        }
        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width

        if len(dataframe.columns) > 7:
            worksheet.column_dimensions['H'].width = 15
            worksheet.column_dimensions['I'].width = 18
            worksheet.column_dimensions['J'].width = 20

        for row in worksheet.iter_rows():
            for cell in row:
                if cell.column == 10:
                    cell.alignment = Alignment(
                        horizontal='center', vertical='center', wrap_text=True
                    )
                else:
                    cell.alignment = Alignment(
                        horizontal='center', vertical='center'
                    )

    logger.info("Excel file created: %s", xlsx_file)


def convert_to_pdf(dataframe: pd.DataFrame, pdf_file: str) -> None:
    """Convert DataFrame to PDF file with table formatting.

    Args:
        dataframe: The pandas DataFrame to export.
        pdf_file: Output PDF file path.
    """
    pdf = SimpleDocTemplate(
        pdf_file,
        pagesize=landscape(A3),
        leftMargin=15,
        rightMargin=15,
        topMargin=15,
        bottomMargin=15
    )
    data = [dataframe.columns.tolist()] + dataframe.values.tolist()

    # Calculate column widths based on number of columns
    num_cols = len(dataframe.columns)
    if num_cols <= 7:
        # Basic export: Uni, Dept, ScoreType, Quota, Score, Ranking, Price
        col_widths = [100, 280, 55, 50, 65, 70, 80]
    else:
        # With discount: 10 columns
        col_widths = [95, 280, 50, 45, 55, 60, 65, 45, 70, 70]

    table = Table(data, colWidths=col_widths[:num_cols])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), PDF_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
    ]))

    pdf.build([table])
    logger.info("PDF file created: %s", pdf_file)


def normalize_turkish_text(text: str) -> str:
    """Normalize Turkish text for case-insensitive comparison.

    Handles Turkish-specific characters like İ, ı, Ş, ş, Ğ, ğ, Ü, ü, Ö, ö, Ç, ç.

    Args:
        text: Input text to normalize.

    Returns:
        Lowercase normalized text.
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


def list_universities() -> None:
    """List all universities in the database."""
    repository = UniversityPriceRepository()
    all_prices = repository.get_all_prices()
    unique_universities = sorted({price.university_name for price in all_prices})

    if unique_universities:
        logger.info('Universities in database:')
        for university_name in unique_universities:
            logger.info('  - %s', university_name)
        logger.info('Total: %d universities', len(unique_universities))
    else:
        logger.info('No universities found in database.')


def _load_scholarship_rates() -> dict:
    """Load scholarship rates from school_list module.

    Returns:
        Dictionary mapping normalized university names to discount rates.
    """
    try:

        scholarship_map = dict(scholarship_rates)
    except (ImportError, AttributeError):
        scholarship_map = {}

    return {
        normalize_turkish_text(key): value
        for key, value in scholarship_map.items()
    }


def _build_price_records(filtered_prices: list) -> list:
    """Build price records from filtered price data.

    Args:
        filtered_prices: List of price objects from repository.

    Returns:
        List of price record dictionaries.
    """
    records = []
    for price in filtered_prices:
        if not price.department_name or not price.department_name.strip():
            continue
        records.append({
            'university_name': price.university_name,
            'department_name': price.department_name,
            'score_type': price.score_type,
            'quota': price.quota,
            'score': price.score,
            'ranking': price.ranking,
            'price_amount': price.price_amount,
        })
    return records


def _apply_discounts(price_list: list, scholarship_rate: dict) -> None:
    """Apply preference discounts to price records.

    Args:
        price_list: List of price record dictionaries.
        scholarship_rates: Dictionary of normalized names to discount rates.
    """
    for record in price_list:
        normalized_name = normalize_turkish_text(record['university_name'])
        discount_rate = scholarship_rate.get(normalized_name)
        current_price = record.get('price_amount')
        record['original_price'] = current_price

        if discount_rate and isinstance(current_price, (int, float)):
            discounted = round(current_price * (1 - discount_rate / 100), 2)
            record['has_preference_discount'] = True
            record['preference_discount_rate'] = discount_rate
            record['preference_discounted_price'] = discounted
            record['preference_discount_info'] = f"{discount_rate}% available"
        elif discount_rate:
            record['has_preference_discount'] = True
            record['preference_discount_rate'] = discount_rate
            record['preference_discounted_price'] = None
            record['preference_discount_info'] = f"{discount_rate}% available"
        else:
            record['has_preference_discount'] = False
            record['preference_discount_rate'] = 0
            record['preference_discounted_price'] = None
            record['preference_discount_info'] = "-"


def _apply_half_price(price_list: list) -> None:
    """Apply 50% scholarship to price records.

    Args:
        price_list: List of price record dictionaries.
    """
    for record in price_list:
        if isinstance(record.get('price_amount'), (int, float)):
            record['price_amount'] = record['price_amount'] * 0.5
            record['original_price'] = record['price_amount']
            if record.get('preference_discounted_price') is not None:
                record['preference_discounted_price'] *= 0.5


def _create_export_records(price_list: list, include_discount: bool) -> list:
    """Create sanitized records for export.

    Args:
        price_list: List of price record dictionaries.
        include_discount: Whether to include discount columns.

    Returns:
        List of sanitized record dictionaries for export.
    """
    records = []
    for price_record in price_list:
        score_val = price_record.get('score')
        ranking_val = price_record.get('ranking')
        record = {
            'University': price_record.get('university_name', ''),
            'Department': price_record.get('department_name', ''),
            'Score Type': price_record.get('score_type', '') or '',
            'Quota': price_record.get('quota', '') or '',
            'Score': score_val if score_val else 'Not Filled',
            'Ranking': ranking_val if ranking_val else 'Not Filled',
            'Price': price_record.get('original_price'),
        }
        if include_discount:
            discount_rate = price_record.get('preference_discount_rate', 0) or 0
            record['Discount %'] = discount_rate if discount_rate else '-'
            record['Discounted Price'] = price_record.get(
                'preference_discounted_price'
            ) or '-'
            record['Discount Info'] = price_record.get(
                'preference_discount_info', '-'
            )
        records.append(record)
    return records


def export_prices(
    university_filter: str,
    department_filter: str,
    price_option: str,
    should_apply_preference_discount: bool,
    output_filename: str
) -> None:
    """Export university prices to Excel and PDF files.

    Args:
        university_filter: University name to filter (or 'all').
        department_filter: Department name to filter (or 'all').
        price_option: 'full' or 'half' scholarship price.
        should_apply_preference_discount: Whether to include discount columns.
        output_filename: Output filename without extension.
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
        logger.warning('No prices found for university filter: %s', university_filter)
        return

    price_list = _build_price_records(filtered_prices)

    if department_filter.lower() != 'all':
        price_list = [
            item for item in price_list
            if department_filter.lower() in item.get('department_name', '').lower()
        ]

    if not price_list:
        logger.warning('No prices found for department filter: %s', department_filter)
        return

    scholarship_rate = _load_scholarship_rates()
    _apply_discounts(price_list, scholarship_rate)

    if price_option == 'half':
        _apply_half_price(price_list)

    export_records = _create_export_records(price_list, should_apply_preference_discount)

    if not export_records:
        logger.error('No records found to export.')
        return

    dataframe = pd.DataFrame(export_records)

    if output_filename.endswith(".csv"):
        xlsx_file = output_filename.replace(".csv", ".xlsx")
        pdf_file = output_filename.replace(".csv", ".pdf")
    else:
        xlsx_file = output_filename + ".xlsx"
        pdf_file = output_filename + ".pdf"

    convert_to_excel(dataframe, xlsx_file)
    convert_to_pdf(dataframe, pdf_file)

    logger.info('%d records exported to Excel and PDF.', len(export_records))


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description='Scrape university tuition prices and export to Excel/PDF.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --scrape --export
  python main.py --list
  python main.py --export --university "İstinye Üniversitesi"
  python main.py --export --university "all" --price-option half
  python main.py --export --university "İstinye Üniversitesi" --apply-preference-discount
  python main.py --show-notifications
        """
    )

    action_group = parser.add_argument_group('Actions')
    action_group.add_argument(
        '--scrape', action='store_true',
        help='Run the scraping step to fetch prices from web'
    )
    action_group.add_argument(
        '--list', action='store_true',
        help='List all universities in the database'
    )
    action_group.add_argument(
        '--export', action='store_true',
        help='Export prices to Excel/PDF files'
    )
    action_group.add_argument(
        '--show-notifications', action='store_true',
        help='Fetch and display notifications from NOTIFY_TOPIC'
    )

    scrape_group = parser.add_argument_group('Scraping Options')
    scrape_group.add_argument(
        '--scrape-delay', type=float, default=0.0,
        help='Delay between scrape requests in seconds (default: 0.0)'
    )
    scrape_group.add_argument(
        '--start-index', type=int, default=0,
        help='Start index when scraping the universities list (default: 0)'
    )
    scrape_group.add_argument(
        '--stop-index', type=int, default=None,
        help='Stop index (exclusive) when scraping the universities list'
    )

    export_group = parser.add_argument_group('Export Options')
    export_group.add_argument(
        '--university', type=str, default='all',
        help='University name to filter, use "all" for all (default: all)'
    )
    export_group.add_argument(
        '--department', type=str, default='all',
        help='Department name to filter, use "all" for all (default: all)'
    )
    export_group.add_argument(
        '--price-option', choices=['full', 'half'], default='full',
        help='Price option: "full" or "half" for 50%% scholarship (default: full)'
    )
    export_group.add_argument(
        '--apply-preference-discount', action='store_true',
        help='Include preference discount columns in export'
    )
    export_group.add_argument(
        '--output', type=str, default='university_department_prices',
        help='Output filename without extension'
    )

    return parser


def _handle_scrape(args: argparse.Namespace) -> None:
    """Handle the scrape action.

    Args:
        args: Parsed command line arguments.
    """
    logger.info('Starting scraping process...')
    try:
        total, inserted, updated, failed = scrape_universities_from_list(
            save=True,
            delay=args.scrape_delay,
            start_index=args.start_index,
            stop_index=args.stop_index
        )
        logger.info(
            'Scraping completed. Scraped: %d, Inserted: %d, Updated: %d, Failed: %d',
            total, inserted, updated, failed
        )
    except (ConnectionError, TimeoutError):
        logger.exception('Scraping failed due to connection error')


def _handle_notifications() -> None:
    """Handle the show-notifications action."""
    notification_topic = os.environ.get('NOTIFY_TOPIC')
    if not notification_topic:
        logger.error(
            'NOTIFY_TOPIC environment variable not set. '
            'Please set it to your ntfy topic.'
        )
        return

    try:
        logger.info('Fetching notifications from topic: %s', notification_topic)
        events = fetch_notifications(notification_topic, poll_duration=1)
        logger.info('--- Notifications from topic: %s ---', notification_topic)
        print_notifications(events)
    except (ImportError, ConnectionError) as err:
        logger.error('Failed to fetch notifications: %s', err)


def main() -> None:
    """Main entry point for the CLI application."""
    parser = _create_argument_parser()
    args = parser.parse_args()

    has_action = any([
        args.scrape, args.list, args.export, args.show_notifications
    ])

    if not has_action:
        parser.print_help()
        logger.error(
            'Please specify at least one action '
            '(--scrape, --list, --export, or --show-notifications)'
        )
        return

    if args.scrape:
        _handle_scrape(args)

    if args.list:
        list_universities()

    if args.export:
        export_prices(
            university_filter=args.university,
            department_filter=args.department,
            price_option=args.price_option,
            should_apply_preference_discount=args.apply_preference_discount,
            output_filename=args.output
        )

    if args.show_notifications:
        _handle_notifications()


if __name__ == "__main__":
    main()
