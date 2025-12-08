"""Web scraping utilities using Scrapy framework.

This module provides functions for scraping university tuition prices
using Scrapy, a powerful and modern web scraping framework.
"""
from __future__ import annotations

import logging
import os
import re
import sys
import unicodedata

from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings

sys.path.insert(0, os.getcwd())

from scraper.spiders.university_spider import UniversityPriceSpider

logger = logging.getLogger(__name__)


def slugify_university_name(name: str) -> str:
    """Convert university name to URL-friendly slug.

    Args:
        name: University name in Turkish.

    Returns:
        URL-friendly slug string.
    """
    if not name:
        return ''

    slug = name.lower()
    slug = slug.replace('üniversitesi', '')
    slug = slug.replace('universitesi', '')
    slug = slug.replace('ücretleri', '').strip()

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


def scrape_universities_from_list(
    save: bool = True,
    delay: float = 0.5,
    start_index: int = 0,
    stop_index: int | None = None
) -> tuple[int, int, int, int]:
    """Scrape prices for all universities using Scrapy framework.

    Args:
        save: Whether to save results to database (always True for Scrapy).
        delay: Delay in seconds between requests.
        start_index: Starting index in the university list.
        stop_index: Ending index (exclusive) in the university list.

    Returns:
        Tuple of (total_scraped, total_inserted, total_updated, total_failed).
    """
    try:
        from util.school_list import universities as university_list
    except (ImportError, AttributeError) as import_error:
        logger.error('Could not import university list: %s', import_error)
        return 0, 0, 0, 0

    total_universities = len(university_list)
    end_index = stop_index if stop_index is not None else total_universities

    universities_to_scrape = university_list[start_index:end_index]

    if not universities_to_scrape:
        logger.warning('No universities to scrape')
        return 0, 0, 0, 0

    logger.info(
        'Starting Scrapy crawler for %d universities...',
        len(universities_to_scrape)
    )

    settings = Settings()
    settings.setmodule('scraper.settings')

    if delay:
        settings.set('DOWNLOAD_DELAY', delay)

    process = CrawlerProcess(settings)

    stats = {'inserted': 0, 'updated': 0, 'failed': 0, 'scraped': 0}

    def spider_closed(spider, reason):
        stats['scraped'] = spider.scraped_count
        stats['failed'] = spider.failed_count
        if hasattr(spider, 'pipeline_stats'):
            stats['inserted'] = spider.pipeline_stats.get('inserted', 0)
            stats['updated'] = spider.pipeline_stats.get('updated', 0)
            stats['failed'] = spider.pipeline_stats.get('failed', 0)

    crawler = process.create_crawler(UniversityPriceSpider)
    crawler.signals.connect(spider_closed, signal=signals.spider_closed)

    process.crawl(crawler, universities=universities_to_scrape)
    process.start()

    notification_message = (
        f"Scrapy scraping completed. "
        f"Universities: {len(universities_to_scrape)}, "
        f"Inserted: {stats['inserted']}, "
        f"Updated: {stats['updated']}, "
        f"Failed: {stats['failed']}."
    )
    logger.info('%s', notification_message)

    notification_topic = os.environ.get('NOTIFY_TOPIC')
    if save and notification_topic:
        try:
            send_scrape_notification(
                notification_topic,
                notification_message,
                title='Universities Updated'
            )
        except (ImportError, ConnectionError) as notification_error:
            logger.error('Notification failed: %s', notification_error)

    return (
        len(universities_to_scrape),
        stats['inserted'],
        stats['updated'],
        stats['failed']
    )


def send_scrape_notification(
    topic: str,
    message: str,
    title: str | None = None,
    priority: int = 3
) -> None:
    """Send a notification via ntfy.sh.

    Args:
        topic: ntfy topic name.
        message: Notification message body.
        title: Optional notification title.
        priority: Priority level (1-5).
    """
    if not topic:
        return

    try:
        from util.notifications import send_notification
        send_notification(topic, message, title=title, priority=priority)
    except (ImportError, ConnectionError) as error:
        logger.error('Notification failed: %s', error)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    scrape_universities_from_list()
