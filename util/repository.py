from __future__ import annotations
from typing import Tuple
from util.connect import get_db
from util.models import DepartmentPrice


class UniversityPriceRepository:
    """Simple repository wrapping MongoDB access for university prices."""

    def __init__(self, db_name: str | None = None):
        # get_db will use default DB if db_name is None
        self._db = get_db(db_name) if db_name else get_db()

    def upsert_price(self, price: DepartmentPrice) -> Tuple[bool, bool]:
        """Upsert a DepartmentPrice into the `university_prices` collection.

        Returns (inserted, updated) where inserted=True when an insert occurred.
        """
        coll = self._db['university_prices']
        q = {'university_name': price.university, 'department': price.department}
        doc = {
            'university_name': price.university,
            'faculty': price.faculty,
            'department': price.department,
            'price_text': price.price_text,
            'price_value': price.price_value,
            'currency': price.currency,
            'scraped_at': price.scraped_at,
        }
        res = coll.update_one(q, {'$set': doc}, upsert=True)
        inserted = getattr(res, 'upserted_id', None) is not None
        updated = not inserted
        return inserted, updated
