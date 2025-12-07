"""Scrapy Item definitions for university price data.

Items are containers that will be loaded with the scraped data.
They provide a convenient API for declaring available fields.
"""
from __future__ import annotations
import scrapy


class UniversityPriceItem(scrapy.Item):
    """Scrapy Item representing a university department price.
    
    This item maps to the UniversityDepartmentPrice model
    and will be processed by the MongoDB pipeline.
    """
    university_name = scrapy.Field()
    faculty_name = scrapy.Field()
    department_name = scrapy.Field()
    score_type = scrapy.Field()
    quota = scrapy.Field()
    score = scrapy.Field()
    ranking = scrapy.Field()
    price_description = scrapy.Field()
    price_amount = scrapy.Field()
    currency_code = scrapy.Field()
    last_scraped_at = scrapy.Field()
