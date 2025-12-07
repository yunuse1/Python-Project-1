from __future__ import annotations

BOT_NAME = 'university_scraper'

SPIDER_MODULES = ['scraper.spiders']
NEWSPIDER_MODULE = 'scraper.spiders'

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

ROBOTSTXT_OBEY = False

CONCURRENT_REQUESTS = 4

DOWNLOAD_DELAY = 0.5

COOKIES_ENABLED = False

ITEM_PIPELINES = {
    'scraper.pipelines.LoggingPipeline': 100,
    'scraper.pipelines.MongoDBPipeline': 300,
}

HTTPCACHE_ENABLED = False

RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

TELNETCONSOLE_ENABLED = False

REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'

TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'
FEED_EXPORT_ENCODING = 'utf-8'
