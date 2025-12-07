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
        
        table_selector = response.css('table#ozeluni, table.ozeluni')
        
        if not table_selector:
            for table in response.css('table'):
                headers_text = ' '.join(table.css('th::text').getall()).lower()
                if 'ücret' in headers_text or 'bölüm' in headers_text:
                    table_selector = table
                    break
        
        if not table_selector:
            self.logger.warning(f'No price table found for {university_name}')
            self.failed_count += 1
            return
        
        column_indices = {
            'department': 0,
            'score_type': 1,
            'quota': 2,
            'score': 3,
            'ranking': 4,
            'price': 5,
        }
        
        header_row = table_selector.css('tr:first-child th')
        if header_row:
            headers = [th.css('::text').get() or '' for th in header_row]
            headers = [h.strip().lower() for h in headers]
            
            for index, header in enumerate(headers):
                if 'bölüm' in header or 'program' in header:
                    column_indices['department'] = index
                elif 'puan türü' in header or 'puan t' in header:
                    column_indices['score_type'] = index
                elif 'kont' in header or 'yer' in header:
                    column_indices['quota'] = index
                elif header == 'puan':
                    column_indices['score'] = index
                elif 'sıra' in header:
                    column_indices['ranking'] = index
                elif 'ücret' in header:
                    column_indices['price'] = index
        
        current_timestamp = datetime.datetime.utcnow()
        rows_found = 0
        
        for row in table_selector.css('tr')[1:]:
            cells = row.css('td')
            
            if len(cells) < 2:
                continue
            
            def get_cell_text(cell_index: int) -> str:
                if cell_index < len(cells):
                    text = cells[cell_index].css('::text').getall()
                    return ' '.join(t.strip() for t in text if t.strip())
                return ''
            
            department_name = get_cell_text(column_indices['department'])
            score_type = get_cell_text(column_indices['score_type'])
            quota = get_cell_text(column_indices['quota'])
            score_text = get_cell_text(column_indices['score'])
            ranking_text = get_cell_text(column_indices['ranking'])
            price_text = get_cell_text(column_indices['price'])
            
            if not department_name or not department_name.strip():
                continue
            if 'bölüm' in department_name.lower() and 'adı' in department_name.lower():
                continue
            
            score = self._parse_score(score_text)
            ranking = self._parse_ranking(ranking_text)
            price_amount, currency_code = self._parse_price(price_text)
            
            rows_found += 1
            
            yield UniversityPriceItem(
                university_name=university_name,
                faculty_name=None,
                department_name=department_name,
                score_type=score_type if score_type else None,
                quota=quota if quota else None,
                score=score,
                ranking=ranking,
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
        
        if '₺' in cleaned_text or 'TL' in cleaned_text.upper():
            currency_code = 'TRY'
        elif '$' in cleaned_text:
            currency_code = 'USD'
        
        numeric_string = re.sub(r"[^0-9,\.]+", "", cleaned_text)
        if not numeric_string:
            return None, currency_code
        
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
    
    def _parse_score(self, score_text: str) -> float | None:
        """Parse a score string and extract numeric value.
        
        Args:
            score_text: Raw score string (e.g., "239,52" or "Dolmadı")
            
        Returns:
            Float score value or None if not parseable
        """
        if not score_text:
            return None
        
        cleaned_text = score_text.strip().lower()
        
        if 'dolmadı' in cleaned_text or 'dolmadi' in cleaned_text:
            return None
        
        numeric_string = re.sub(r"[^0-9,\.]+", "", score_text)
        if not numeric_string:
            return None
        
        numeric_string = numeric_string.replace(',', '.')
        
        try:
            return float(numeric_string)
        except ValueError:
            return None
    
    def _parse_ranking(self, ranking_text: str) -> int | None:
        """Parse a ranking string and extract integer value.
        
        Args:
            ranking_text: Raw ranking string (e.g., "633.510" or "Dolmadı")
            
        Returns:
            Integer ranking value or None if not parseable
        """
        if not ranking_text:
            return None
        
        cleaned_text = ranking_text.strip().lower()
        
        if 'dolmadı' in cleaned_text or 'dolmadi' in cleaned_text:
            return None
        
        numeric_string = re.sub(r"[^0-9]+", "", ranking_text)
        if not numeric_string:
            return None
        
        try:
            return int(numeric_string)
        except ValueError:
            return None
    
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
