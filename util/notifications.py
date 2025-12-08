"""Notification utilities for ntfy.sh integration.

This module provides functions for fetching and sending
notifications via the ntfy.sh service.
"""
from __future__ import annotations

import argparse
import logging
from typing import List

import requests

logger = logging.getLogger(__name__)


def fetch_notifications(
    topic: str,
    poll_duration: int = 1,
    timeout_seconds: int = 30
) -> List[dict]:
    """Fetch notifications from an ntfy topic.

    Args:
        topic: The ntfy topic name to fetch from.
        poll_duration: Poll duration parameter for the API.
        timeout_seconds: Request timeout in seconds.

    Returns:
        List of notification event dictionaries.

    Raises:
        ValueError: If topic is not provided.
    """
    if not topic:
        raise ValueError('topic is required')

    request_url = f'https://ntfy.sh/{topic}/json?poll={poll_duration}'
    response = requests.get(request_url, timeout=timeout_seconds)
    response.raise_for_status()

    try:
        response_data = response.json()
    except ValueError:
        raw_text = response.text
        return [{'raw': raw_text}]

    if isinstance(response_data, list):
        return response_data

    if isinstance(response_data, dict) and 'events' in response_data:
        return response_data.get('events') or []

    return [response_data]


def print_notifications(notification_events: List[dict]) -> None:
    """Pretty-print a list of ntfy notification events.

    Args:
        notification_events: List of notification event dictionaries.
    """
    if not notification_events:
        logger.info('No notifications found')
        return

    for event in notification_events:
        event_id = event.get('id')
        event_title = event.get('title')
        event_message = (
            event.get('message') or event.get('msg') or
            event.get('raw') or event.get('body')
        )
        event_topic = event.get('topic')
        event_time = event.get('time')
        event_priority = event.get('priority')

        logger.info('---')
        if event_id:
            logger.info('id: %s', event_id)
        if event_title:
            logger.info('title: %s', event_title)
        if event_topic:
            logger.info('topic: %s', event_topic)
        if event_time:
            logger.info('time: %s', event_time)
        if event_priority is not None:
            logger.info('priority: %s', event_priority)
        logger.info('message:')
        logger.info('%s', event_message)


def send_notification(
    topic: str,
    message: str,
    title: str = None,
    priority: int = 3,
    tags: List[str] = None,
    timeout_seconds: int = 30
) -> bool:
    """Send a notification to an ntfy topic.

    Args:
        topic: The ntfy topic to send to.
        message: The notification message body.
        title: Optional title for the notification.
        priority: Priority level (1-5, default 3).
        tags: Optional list of tags/emojis.
        timeout_seconds: Request timeout in seconds.

    Returns:
        True if notification was sent successfully, False otherwise.

    Raises:
        ValueError: If topic or message is not provided.
    """
    if not topic:
        raise ValueError('topic is required')
    if not message:
        raise ValueError('message is required')

    request_url = f'https://ntfy.sh/{topic}'
    request_headers = {}

    if title:
        request_headers['Title'] = title
    if priority:
        request_headers['Priority'] = str(priority)
    if tags:
        request_headers['Tags'] = ','.join(tags)

    try:
        response = requests.post(
            request_url,
            data=message.encode('utf-8'),
            headers=request_headers,
            timeout=timeout_seconds
        )
        response.raise_for_status()
        logger.info('Notification sent to topic: %s', topic)
        return True
    except requests.exceptions.RequestException as request_error:
        logger.error('Failed to send notification: %s', request_error)
        return False


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    arg_parser = argparse.ArgumentParser(
        description='Fetch and print ntfy notifications for a topic'
    )
    arg_parser.add_argument('topic', help='ntfy topic name')
    arg_parser.add_argument(
        '--poll', type=int, default=1, help='Poll duration parameter'
    )

    parsed_args = arg_parser.parse_args()
    fetched_events = fetch_notifications(
        parsed_args.topic, poll_duration=parsed_args.poll
    )
    print_notifications(fetched_events)
