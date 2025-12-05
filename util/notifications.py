from __future__ import annotations
import requests
import typing as t


def fetch_notifications(topic: str, poll: int = 1, timeout: int = 30) -> t.List[dict]:
    """Fetch notifications for a given ntfy topic using the JSON poll endpoint.

    Args:
        topic: ntfy topic name (e.g. 'mytopic123')
        poll: poll parameter (1 for immediate poll)
        timeout: HTTP timeout in seconds

    Returns:
        A list of event dicts (may be empty).
    """
    if not topic:
        raise ValueError('topic is required')
    url = f'https://ntfy.sh/{topic}/json?poll={poll}'
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    # ntfy returns a JSON array of events
    try:
        data = resp.json()
    except Exception:
        # fallback: try to parse text
        text = resp.text
        return [{'raw': text}]
    if isinstance(data, list):
        return data
    # sometimes returns an object with 'events'
    if isinstance(data, dict) and 'events' in data:
        return data.get('events') or []
    return [data]


def print_notifications(events: t.List[dict]):
    """Pretty-print a list of ntfy event dicts."""
    if not events:
        print('No notifications found')
        return
    for ev in events:
        # common fields: id, time, event, topic, message, title, priority, tags
        eid = ev.get('id')
        title = ev.get('title')
        message = ev.get('message') or ev.get('msg') or ev.get('raw') or ev.get('body')
        topic = ev.get('topic')
        time = ev.get('time')
        priority = ev.get('priority')
        print('---')
        if eid:
            print('id:', eid)
        if title:
            print('title:', title)
        if topic:
            print('topic:', topic)
        if time:
            print('time:', time)
        if priority is not None:
            print('priority:', priority)
        print('message:')
        print(message)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Fetch and print ntfy notifications for a topic')
    parser.add_argument('topic', help='ntfy topic name')
    parser.add_argument('--poll', type=int, default=1)
    args = parser.parse_args()
    evs = fetch_notifications(args.topic, poll=args.poll)
    print_notifications(evs)
