"""Scrapy settings for the university price scraper.

These settings configure the Scrapy crawler behavior including
concurrent requests, delays, pipelines, and user agent.
"""
from __future__ import annotations

# Scrapy settings for scraper project
BOT_NAME = 'university_scraper'

SPIDER_MODULES = ['scraper.spiders']
NEWSPIDER_MODULE = 'scraper.spiders'

# Crawl responsibly by identifying yourself
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Obey robots.txt rules (disabled for this educational project)
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 4

# Configure delay between requests (in seconds)
DOWNLOAD_DELAY = 0.5

# Disable cookies (not needed for this scraper)
COOKIES_ENABLED = False

# Configure item pipelines
ITEM_PIPELINES = {
    'scraper.pipelines.LoggingPipeline': 100,
    'scraper.pipelines.MongoDBPipeline': 300,
}

# Enable and configure HTTP caching (disabled by default)
HTTPCACHE_ENABLED = False

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Logging settings
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# Disable Telnet Console
TELNETCONSOLE_ENABLED = False

# Request fingerprinting
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'

# Set settings whose default value is deprecated
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'
FEED_EXPORT_ENCODING = 'utf-8'
