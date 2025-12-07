"""Scrapy Pipelines for processing scraped university price data.

Pipelines process items after they have been scraped by spiders.
This module contains the MongoDB pipeline for saving items to the database.
"""
from __future__ import annotations
import datetime
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.university_models import UniversityDepartmentPrice
from repository.repository import UniversityPriceRepository

logger = logging.getLogger(__name__)


class MongoDBPipeline:
    """Pipeline that saves scraped items to MongoDB.
    
    This pipeline converts Scrapy items to domain models
    and uses the repository pattern to persist them.
    """
    
    def __init__(self):
        """Initialize the pipeline with counters and repository."""
        self.repository = None
        self.inserted_count = 0
        self.updated_count = 0
        self.failed_count = 0
    
    def open_spider(self, spider):
        """Called when the spider is opened.
        
        Initializes the repository connection.
        """
        self.repository = UniversityPriceRepository()
        self.inserted_count = 0
        self.updated_count = 0
        self.failed_count = 0
        logger.info('MongoDB pipeline opened')
    
    def close_spider(self, spider):
        """Called when the spider is closed.
        
        Logs final statistics and sends notifications.
        """
        logger.info(
            f'MongoDB pipeline closed. '
            f'Inserted: {self.inserted_count}, '
            f'Updated: {self.updated_count}, '
            f'Failed: {self.failed_count}'
        )
        
        # Store stats in spider for later access
        spider.pipeline_stats = {
            'inserted': self.inserted_count,
            'updated': self.updated_count,
            'failed': self.failed_count
        }
        
        # Send notification if topic is configured
        notification_topic = os.environ.get('NOTIFY_TOPIC')
        if notification_topic:
            try:
                from util.notifications import send_notification
                message = (
                    f"Scraping completed. "
                    f"Inserted: {self.inserted_count}, "
                    f"Updated: {self.updated_count}, "
                    f"Failed: {self.failed_count}"
                )
                send_notification(notification_topic, message, title='Universities Updated')
            except Exception as error:
                logger.error(f'Notification failed: {error}')
    
    def process_item(self, item, spider):
        """Process each scraped item.
        
        Converts the Scrapy item to a domain model and saves to MongoDB.
        
        Args:
            item: The scraped UniversityPriceItem
            spider: The spider that scraped the item
            
        Returns:
            The processed item
        """
        try:
            # Convert Scrapy item to domain model
            department_price = UniversityDepartmentPrice(
                university_name=item.get('university_name', ''),
                faculty_name=item.get('faculty_name'),
                department_name=item.get('department_name', ''),
                score_type=item.get('score_type'),
                quota=item.get('quota'),
                score=item.get('score'),
                ranking=item.get('ranking'),
                price_description=item.get('price_description', ''),
                price_amount=item.get('price_amount'),
                currency_code=item.get('currency_code'),
                last_scraped_at=item.get('last_scraped_at', datetime.datetime.utcnow()),
            )
            
            # Save to database using repository
            was_inserted, was_updated = self.repository.upsert(department_price)
            
            if was_inserted:
                self.inserted_count += 1
            elif was_updated:
                self.updated_count += 1
                
        except Exception as error:
            self.failed_count += 1
            logger.error(f'Failed to save item: {error}')
        
        return item


class LoggingPipeline:
    """Pipeline that logs each scraped item for debugging."""
    
    def process_item(self, item, spider):
        """Log the scraped item.
        
        Args:
            item: The scraped item
            spider: The spider that scraped the item
            
        Returns:
            The item unchanged
        """
        logger.debug(
            f"Scraped: {item.get('university_name')} - "
            f"{item.get('department_name')} - "
            f"{item.get('price_amount')}"
        )
        return item
