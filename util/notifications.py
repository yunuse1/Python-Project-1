from __future__ import annotations
import requests
import typing as t
import logging

# Configure logging
logger = logging.getLogger(__name__)


def fetch_notifications(topic: str, poll_duration: int = 1, timeout_seconds: int = 30) -> t.List[dict]:
    """Fetch notifications from an ntfy topic.
    
    Args:
        topic: The ntfy topic name to fetch from
        poll_duration: Poll duration parameter for the API
        timeout_seconds: Request timeout in seconds
    
    Returns:
        List of notification event dictionaries
    
    Raises:
        ValueError: If topic is not provided
    """
    if not topic:
        raise ValueError('topic is required')
    
    request_url = f'https://ntfy.sh/{topic}/json?poll={poll_duration}'
    response = requests.get(request_url, timeout=timeout_seconds)
    response.raise_for_status()
    
    try:
        response_data = response.json()
    except Exception:
        # Fallback: return raw text if JSON parsing fails
        raw_text = response.text
        return [{'raw': raw_text}]
    
    if isinstance(response_data, list):
        return response_data
    
    # Sometimes the API returns an object with 'events' key
    if isinstance(response_data, dict) and 'events' in response_data:
        return response_data.get('events') or []
    
    return [response_data]


def print_notifications(notification_events: t.List[dict]) -> None:
    """Pretty-print a list of ntfy notification events.
    
    Args:
        notification_events: List of notification event dictionaries
    """
    if not notification_events:
        logger.info('No notifications found')
        return
    
    for event in notification_events:
        event_id = event.get('id')
        event_title = event.get('title')
        event_message = event.get('message') or event.get('msg') or event.get('raw') or event.get('body')
        event_topic = event.get('topic')
        event_time = event.get('time')
        event_priority = event.get('priority')
        
        logger.info('---')
        if event_id:
            logger.info(f'id: {event_id}')
        if event_title:
            logger.info(f'title: {event_title}')
        if event_topic:
            logger.info(f'topic: {event_topic}')
        if event_time:
            logger.info(f'time: {event_time}')
        if event_priority is not None:
            logger.info(f'priority: {event_priority}')
        logger.info('message:')
        logger.info(event_message)


def send_notification(
    topic: str,
    message: str,
    title: str = None,
    priority: int = 3,
    tags: t.List[str] = None,
    timeout_seconds: int = 30
) -> bool:
    """Send a notification to an ntfy topic.
    
    Args:
        topic: The ntfy topic to send to
        message: The notification message body
        title: Optional title for the notification
        priority: Priority level (1-5, default 3)
        tags: Optional list of tags/emojis
        timeout_seconds: Request timeout in seconds
    
    Returns:
        True if notification was sent successfully, False otherwise
    
    Raises:
        ValueError: If topic or message is not provided
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
        logger.info(f'Notification sent to topic: {topic}')
        return True
    except requests.exceptions.RequestException as request_error:
        logger.error(f'Failed to send notification: {request_error}')
        return False


if __name__ == '__main__':
    import argparse

    argument_parser = argparse.ArgumentParser(description='Fetch and print ntfy notifications for a topic')
    argument_parser.add_argument('topic', help='ntfy topic name')
    argument_parser.add_argument('--poll', type=int, default=1, help='Poll duration parameter')
    
    parsed_args = argument_parser.parse_args()
    fetched_events = fetch_notifications(parsed_args.topic, poll_duration=parsed_args.poll)
    print_notifications(fetched_events)
