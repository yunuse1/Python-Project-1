"""Create `university_prices` collection with JSON schema and indexes.

Usage:
    # Run inside docker-compose app service:
    docker-compose exec app python -u util/migrations/create_prices_migration.py --seed

    # Or run locally (ensure MONGO_URI env var points to your Mongo):
    MONGO_URI='mongodb://localhost:27017' python util/migrations/create_prices_migration.py --seed

The script is idempotent: it will create the collection if missing or update
the validator if already present. When `--seed` is passed it inserts a few
example documents that follow the schema.
"""
from __future__ import annotations

import argparse
import pprint
from typing import Any, Dict, List

from connect import get_db
from pymongo.errors import CollectionInvalid


COLLECTION_NAME = "university_prices"


def get_validator() -> Dict[str, Any]:
    """Return a MongoDB JSON schema validator for the collection."""
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["university_name", "department", "prices"],
            "properties": {
                "university_name": {"bsonType": "string"},
                "department": {"bsonType": "string"},
                "prices": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "required": ["item", "price_text"],
                        "properties": {
                            "item": {"bsonType": "string"},
                            "price_text": {"bsonType": "string"},
                            "meta": {"bsonType": "object"},
                        },
                    },
                },
                "scraped_at": {"bsonType": "date"},
            },
        }
    }


def create_or_update_collection(db) -> None:
    validator = get_validator()
    try:
        # Try create with validator (idempotent if not existing)
        db.create_collection(COLLECTION_NAME, validator=validator)
        print(f"Created collection '{COLLECTION_NAME}' with validator.")
    except CollectionInvalid:
        # Already exists — update validator using collMod
        try:
            db.command(
                {
                    "collMod": COLLECTION_NAME,
                    "validator": validator,
                    "validationLevel": "moderate",
                }
            )
            print(f"Updated validator for existing collection '{COLLECTION_NAME}'.")
        except Exception as exc:
            print("Failed to update collection validator:", exc)

    coll = db[COLLECTION_NAME]
    # Create useful indexes
    coll.create_index([("university_name", 1), ("department", 1)])
    coll.create_index("scraped_at")
    print("Ensured indexes on (university_name, department) and scraped_at.")


def seed_example(db) -> List[Dict[str, Any]]:
    docs = [
        {
            "university_name": "Istanbul Nisantasi University",
            "department": "Computer Engineering",
            "prices": [
                {"item": "Tuition per credit", "price_text": "₺4.500"},
                {"item": "Semester fee", "price_text": "₺36.000"},
            ],
        },
        {
            "university_name": "Istanbul Nisantasi University",
            "department": "Business Administration",
            "prices": [{"item": "Tuition (annual)", "price_text": "₺28.000"}],
        },
    ]
    coll = db[COLLECTION_NAME]
    result = coll.insert_many(docs)
    print(f"Inserted sample documents, ids: {result.inserted_ids}")
    return docs


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create migration for university_prices collection")
    parser.add_argument("--seed", action="store_true", help="Insert example documents after creating the collection")
    args = parser.parse_args(argv)

    try:
        db = get_db()
    except Exception as exc:
        print("Could not get DB connection:", exc)
        return

    create_or_update_collection(db)

    if args.seed:
        docs = seed_example(db)
        pprint.pprint(docs)


if __name__ == "__main__":
    main()
