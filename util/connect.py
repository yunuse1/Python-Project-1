"""MongoDB connection utilities.

This module provides functions for connecting to MongoDB and
accessing databases and collections.
"""
import logging
import os
import time

import pymongo
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

DEFAULT_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DEFAULT_DB = os.getenv("MONGO_DB", "mydatabase")
DEFAULT_COLLECTION = os.getenv("MONGO_COLLECTION", "customers")
DEFAULT_TIMEOUT_MS = 5000


def get_client(
    uri: str | None = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS
) -> pymongo.MongoClient:
    """Return a connected MongoClient.

    Args:
        uri: MongoDB connection URI.
        timeout_ms: Server selection timeout in milliseconds.

    Returns:
        Connected MongoClient instance.

    Raises:
        ConnectionError: If connection fails.
    """
    uri = uri or DEFAULT_URI
    mongo_client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=timeout_ms)
    try:
        mongo_client.admin.command("ping")
    except (ServerSelectionTimeoutError, ConnectionFailure) as err:
        raise ConnectionError(
            f"Could not connect to MongoDB at {uri}: {err}"
        ) from err
    return mongo_client


def get_db(
    db_name: str = DEFAULT_DB,
    client: pymongo.MongoClient | None = None
) -> pymongo.database.Database:
    """Return a Database object.

    Args:
        db_name: Name of the database.
        client: Optional MongoClient instance.

    Returns:
        MongoDB Database object.
    """
    mongo_client = client or get_client()
    return mongo_client[db_name]


def get_collection(
    db_name: str = DEFAULT_DB,
    collection_name: str = DEFAULT_COLLECTION,
    client: pymongo.MongoClient | None = None
) -> pymongo.collection.Collection:
    """Return a Collection object.

    Args:
        db_name: Name of the database.
        collection_name: Name of the collection.
        client: Optional MongoClient instance.

    Returns:
        MongoDB Collection object.
    """
    database = get_db(db_name, client)
    return database[collection_name]


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    max_retries = int(os.environ.get("MONGO_CONNECT_RETRIES", "12"))
    retry_interval = int(os.environ.get("MONGO_CONNECT_INTERVAL", "5"))
    attempt = 0

    while attempt < max_retries:
        try:
            mongo_client = get_client()
            database = get_db(client=mongo_client)
            collection = get_collection(client=mongo_client)
            logger.info("MongoDB connection successful.")
            break
        except ConnectionError as err:
            attempt += 1
            logger.error(
                "Could not connect to MongoDB (attempt %d/%d): %s",
                attempt, max_retries, err
            )
            if attempt >= max_retries:
                logger.error("Maximum retry attempts reached. Exiting.")
                break
            logger.info("Waiting %d seconds before retrying...", retry_interval)
            time.sleep(retry_interval)
