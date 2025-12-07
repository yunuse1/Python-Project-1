from __future__ import annotations
import scrapy


class UniversityPriceItem(scrapy.Item):
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
