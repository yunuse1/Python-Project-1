from __future__ import annotations

import argparse
import pprint
import logging
from typing import Any, Dict, List

from util.connect import get_db
from pymongo.errors import CollectionInvalid

logger = logging.getLogger(__name__)


COLLECTION_NAME = "university_prices"


def get_validator() -> Dict[str, Any]:
    """Return MongoDB JSON Schema validator for university_prices collection.
    
    Returns:
        Dictionary containing the $jsonSchema validator
    """
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["university_name", "department_name"],
            "properties": {
                "university_name": {
                    "bsonType": "string",
                    "description": "Name of the university"
                },
                "faculty_name": {
                    "bsonType": ["string", "null"],
                    "description": "Name of the faculty (optional)"
                },
                "department_name": {
                    "bsonType": "string",
                    "description": "Name of the department/program"
                },
                "price_description": {
                    "bsonType": "string",
                    "description": "Original price text from source"
                },
                "price_amount": {
                    "bsonType": ["double", "null"],
                    "description": "Numeric price value"
                },
                "currency_code": {
                    "bsonType": ["string", "null"],
                    "description": "ISO currency code (e.g., TRY, USD)"
                },
                "last_scraped_at": {
                    "bsonType": "date",
                    "description": "Timestamp of last scrape"
                },
            },
        }
    }


def create_or_update_collection(db) -> None:
    """Create or update the university_prices collection with validator and indexes."""
    validator = get_validator()
    try:
        db.create_collection(COLLECTION_NAME, validator=validator)
        logger.info(f"Created collection '{COLLECTION_NAME}' with validator.")
    except CollectionInvalid:
        try:
            db.command(
                {
                    "collMod": COLLECTION_NAME,
                    "validator": validator,
                    "validationLevel": "moderate",
                }
            )
            logger.info(f"Updated validator for existing collection '{COLLECTION_NAME}'.")
        except Exception as exc:
            logger.error(f"Failed to update collection validator: {exc}")

    coll = db[COLLECTION_NAME]
    coll.create_index([("university_name", 1), ("department_name", 1)], unique=True)
    coll.create_index("last_scraped_at")
    logger.info("Ensured indexes on (university_name, department_name) and last_scraped_at.")


def seed_example(db) -> List[Dict[str, Any]]:
    """Insert example documents for testing."""
    import datetime
    
    docs = [
        {
            "university_name": "Istanbul Nisantasi University",
            "faculty_name": "Engineering Faculty",
            "department_name": "Computer Engineering",
            "price_description": "₺36.000",
            "price_amount": 36000.0,
            "currency_code": "TRY",
            "last_scraped_at": datetime.datetime.utcnow(),
        },
        {
            "university_name": "Istanbul Nisantasi University",
            "faculty_name": "Business Faculty",
            "department_name": "Business Administration",
            "price_description": "₺28.000",
            "price_amount": 28000.0,
            "currency_code": "TRY",
            "last_scraped_at": datetime.datetime.utcnow(),
        },
    ]
    coll = db[COLLECTION_NAME]
    result = coll.insert_many(docs)
    logger.info(f"Inserted sample documents, ids: {result.inserted_ids}")
    return docs


def main(argv: List[str] | None = None) -> None:
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    parser = argparse.ArgumentParser(description="Create migration for university_prices collection")
    parser.add_argument("--seed", action="store_true", help="Insert example documents after creating the collection")
    args = parser.parse_args(argv)

    try:
        db = get_db()
    except Exception as exc:
        logger.error(f"Could not get DB connection: {exc}")
        return

    create_or_update_collection(db)

    if args.seed:
        docs = seed_example(db)
        pprint.pprint(docs)


if __name__ == "__main__":
    main()
