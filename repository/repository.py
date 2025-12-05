from __future__ import annotations
from typing import Tuple, List
import sys
import os

# Ensure project root is on sys.path so imports like `util.models` work
sys.path.insert(0, os.getcwd())

from util.connect import get_db
from models.university_models import DepartmentPrice


class UniversityPriceRepository:

    def __init__(self, db_name: str | None = None):
        self._db = get_db(db_name) if db_name else get_db()

    def upsert_price(self, price: DepartmentPrice) -> Tuple[bool, bool]:
        """Insert or update a DepartmentPrice document."""
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

    # backward-compatible alias
    def update_price(self, price: DepartmentPrice) -> Tuple[bool, bool]:
        return self.upsert_price(price)

    def get_prices_by_university(self, university_name: str) -> List[DepartmentPrice]:
        coll = self._db['university_prices']
        cursor = coll.find({'university_name': university_name})
        results: List[DepartmentPrice] = []
        for doc in cursor:
            results.append(DepartmentPrice(
                university=doc.get('university_name', ''),
                faculty=doc.get('faculty'),
                department=doc.get('department', ''),
                price_text=doc.get('price_text', ''),
                price_value=doc.get('price_value'),
                currency=doc.get('currency'),
                scraped_at=doc.get('scraped_at')
            ))
        return results

    def get_all_prices(self) -> List[DepartmentPrice]:
        coll = self._db['university_prices']
        cursor = coll.find({})
        results: List[DepartmentPrice] = []
        for doc in cursor:
            results.append(DepartmentPrice(
                university=doc.get('university_name', ''),
                faculty=doc.get('faculty'),
                department=doc.get('department', ''),
                price_text=doc.get('price_text', ''),
                price_value=doc.get('price_value'),
                currency=doc.get('currency'),
                scraped_at=doc.get('scraped_at')
            ))
        return results

    def find_price_by_department(self, university_name: str, department_name: str) -> DepartmentPrice | None:
        coll = self._db['university_prices']
        doc = coll.find_one({'university_name': university_name, 'department': department_name})
        if doc:
            return DepartmentPrice(
                university=doc.get('university_name', ''),
                faculty=doc.get('faculty'),
                department=doc.get('department', ''),
                price_text=doc.get('price_text', ''),
                price_value=doc.get('price_value'),
                currency=doc.get('currency'),
                scraped_at=doc.get('scraped_at')
            )
        return None