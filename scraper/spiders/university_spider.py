"""Scrapy Spider for scraping university tuition prices.

This spider crawls universitego.com to extract department prices
for Turkish universities. It uses CSS selectors and XPath for
efficient data extraction.
"""
from __future__ import annotations
import datetime
import re
import unicodedata
import os
import sys
from typing import Generator, Any

import scrapy
from scrapy.http import Response

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scraper.items import UniversityPriceItem


class UniversityPriceSpider(scrapy.Spider):
    """Spider that scrapes university department prices from universitego.com.
    
    This spider generates URLs for all universities in the predefined list
    and extracts price tables from each page.
    
    Attributes:
        name: Spider identifier used by Scrapy
        allowed_domains: List of domains the spider is allowed to crawl
        custom_settings: Spider-specific settings
    """
    
    name = 'university_prices'
    allowed_domains = ['universitego.com']
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
    }
    
    def __init__(self, universities: list[str] | None = None, *args, **kwargs):
        """Initialize the spider with optional university list.
        
        Args:
            universities: Optional list of university names to scrape.
                         If not provided, uses the default list from school_list.py
        """
        super().__init__(*args, **kwargs)
        
        if universities:
            self.university_list = universities
        else:
            try:
                from util.school_list import universities as default_universities
                self.university_list = default_universities
            except ImportError:
                self.university_list = []
                self.logger.error('Could not import university list from util.school_list')
        
        # Statistics tracking
        self.scraped_count = 0
        self.failed_count = 0
        self.pipeline_stats = {}
    
    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """Generate initial requests for all universities.
        
        Yields:
            Scrapy Request objects for each university URL
        """
        for university_name in self.university_list:
            slug = self._slugify_university_name(university_name)
            url = f'https://www.universitego.com/{slug}-universitesi-ucretleri/'
            
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={'university_name': university_name},
                errback=self.handle_error,
            )
    
    def parse(self, response: Response) -> Generator[UniversityPriceItem, None, None]:
        """Parse the university price page and extract department prices.
        
        Args:
            response: The HTTP response from the university page
            
        Yields:
            UniversityPriceItem objects for each department price found
        """
        university_name = response.meta.get('university_name', 'Unknown')
        self.logger.info(f'Parsing: {university_name} ({response.url})')
        
        # Find the price table using CSS selectors
        price_table = response.css('table#ozeluni, table.ozeluni').get()
        
        if not price_table:
            # Try alternative table detection
            for table in response.css('table'):
                headers_text = ' '.join(table.css('th::text').getall()).lower()
                if 'ücret' in headers_text or 'bölüm' in headers_text:
                    price_table = table.get()
                    break
        
        if not price_table:
            self.logger.warning(f'No price table found for {university_name}')
            self.failed_count += 1
            return
        
        # Re-select the table for proper parsing
        table_selector = response.css('table#ozeluni, table.ozeluni')
        if not table_selector:
            table_selector = response.css('table')
        
        # Determine column indices from headers
        department_col_index = 0
        price_col_index = -1
        
        headers = table_selector.css('tr:first-child th::text, tr:first-child td::text').getall()
        headers = [h.strip().lower() for h in headers]
        
        for index, header in enumerate(headers):
            if 'bölüm' in header or 'program' in header:
                department_col_index = index
            if 'ücret' in header:
                price_col_index = index
        
        # Extract rows
        current_timestamp = datetime.datetime.utcnow()
        rows_found = 0
        
        for row in table_selector.css('tr'):
            cells = row.css('td::text, td *::text').getall()
            cells = [c.strip() for c in cells if c.strip()]
            
            if len(cells) <= 1:
                continue
            
            # Skip header rows
            if any('bölüm' in cell.lower() or 'ücret' in cell.lower() for cell in cells[:3]):
                continue
            
            # Extract department name and price
            try:
                department_name = cells[department_col_index] if department_col_index < len(cells) else cells[0]
            except IndexError:
                continue
            
            try:
                price_text = cells[price_col_index] if price_col_index < len(cells) else ''
            except IndexError:
                price_text = ''
            
            # Skip empty department names
            if not department_name or not department_name.strip():
                continue
            
            # Parse price
            price_amount, currency_code = self._parse_price(price_text)
            
            rows_found += 1
            
            yield UniversityPriceItem(
                university_name=university_name,
                faculty_name=None,
                department_name=department_name,
                price_description=price_text,
                price_amount=price_amount,
                currency_code=currency_code,
                last_scraped_at=current_timestamp,
            )
        
        if rows_found > 0:
            self.scraped_count += 1
            self.logger.info(f'Extracted {rows_found} departments from {university_name}')
        else:
            self.failed_count += 1
            self.logger.warning(f'No departments extracted from {university_name}')
    
    def handle_error(self, failure):
        """Handle request failures.
        
        Args:
            failure: The Twisted Failure object containing error details
        """
        university_name = failure.request.meta.get('university_name', 'Unknown')
        self.logger.error(f'Failed to scrape {university_name}: {failure.value}')
        self.failed_count += 1
    
    def _slugify_university_name(self, name: str) -> str:
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
    
    def _parse_price(self, price_text: str) -> tuple[float | None, str | None]:
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
    
    def closed(self, reason: str):
        """Called when the spider is closed.
        
        Args:
            reason: The reason the spider was closed
        """
        self.logger.info(
            f'Spider closed: {reason}. '
            f'Universities scraped: {self.scraped_count}, '
            f'Failed: {self.failed_count}'
        )
