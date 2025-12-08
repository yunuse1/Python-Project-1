"""Repository for university department price data.

This module provides the UniversityPriceRepository class for managing
university tuition price data in MongoDB.
"""
from __future__ import annotations

import os
import sys
from typing import List, Optional, Tuple

sys.path.insert(0, os.getcwd())

from models.university_models import UniversityDepartmentPrice
from repository.base_repository import BaseRepository
from util.connect import get_db


class UniversityPriceRepository(BaseRepository[UniversityDepartmentPrice]):
    """Repository for managing university department price data in MongoDB.

    This class inherits from BaseRepository and implements all abstract methods
    for the UniversityDepartmentPrice entity.
    """

    COLLECTION_NAME = 'university_prices'

    def __init__(self, database_name: Optional[str] = None):
        """Initialize the repository.

        Args:
            database_name: Optional database name, uses default if not provided.
        """
        super().__init__(self.COLLECTION_NAME)
        self._db = get_db(database_name) if database_name else get_db()

    def upsert(self, entity: UniversityDepartmentPrice) -> Tuple[bool, bool]:
        """Insert or update a department price entity.

        Args:
            entity: The UniversityDepartmentPrice to upsert.

        Returns:
            Tuple of (was_inserted, was_updated).
        """
        collection = self._db[self.COLLECTION_NAME]
        query_filter = {
            'university_name': entity.university_name,
            'department_name': entity.department_name
        }
        document = self._entity_to_document(entity)
        result = collection.update_one(query_filter, {'$set': document}, upsert=True)
        was_inserted = getattr(result, 'upserted_id', None) is not None
        was_updated = not was_inserted
        return was_inserted, was_updated

    def get_prices_by_university(
        self,
        university_name: str
    ) -> List[UniversityDepartmentPrice]:
        """Get all department prices for a specific university.

        Args:
            university_name: Name of the university.

        Returns:
            List of department prices.
        """
        collection = self._db[self.COLLECTION_NAME]
        cursor = collection.find({'university_name': university_name})
        results: List[UniversityDepartmentPrice] = []
        for document in cursor:
            results.append(self._document_to_entity(document))
        return results

    def get_all_prices(self) -> List[UniversityDepartmentPrice]:
        """Get all department prices from the database.

        Returns:
            List of all department prices.
        """
        collection = self._db[self.COLLECTION_NAME]
        cursor = collection.find({})
        results: List[UniversityDepartmentPrice] = []
        for document in cursor:
            results.append(self._document_to_entity(document))
        return results

    def find_price_by_department(
        self,
        university_name: str,
        department_name: str
    ) -> Optional[UniversityDepartmentPrice]:
        """Find a specific department price by university and department name.

        Args:
            university_name: Name of the university.
            department_name: Name of the department.

        Returns:
            The department price if found, None otherwise.
        """
        collection = self._db[self.COLLECTION_NAME]
        document = collection.find_one({
            'university_name': university_name,
            'department_name': department_name
        })
        if document:
            return self._document_to_entity(document)
        return None

    def get_by_id(self, entity_id: str) -> Optional[UniversityDepartmentPrice]:
        """Get an entity by its identifier.

        Args:
            entity_id: Composite key in format "university_name::department_name".

        Returns:
            The entity if found, None otherwise.
        """
        if '::' not in entity_id:
            return None
        parts = entity_id.split('::', 1)
        if len(parts) != 2:
            return None
        university_name, department_name = parts
        return self.find_price_by_department(university_name, department_name)

    def get_all(self) -> List[UniversityDepartmentPrice]:
        """Get all entities from the database.

        Returns:
            List of all UniversityDepartmentPrice entities.
        """
        return self.get_all_prices()

    def delete(self, entity_id: str) -> bool:
        """Delete an entity by its identifier.

        Args:
            entity_id: Composite key in format "university_name::department_name".

        Returns:
            True if deleted, False otherwise.
        """
        if '::' not in entity_id:
            return False
        parts = entity_id.split('::', 1)
        if len(parts) != 2:
            return False
        university_name, department_name = parts

        collection = self._db[self.COLLECTION_NAME]
        result = collection.delete_one({
            'university_name': university_name,
            'department_name': department_name
        })
        return result.deleted_count > 0

    def _entity_to_document(self, entity: UniversityDepartmentPrice) -> dict:
        """Convert an entity to a database document.

        Args:
            entity: The UniversityDepartmentPrice entity.

        Returns:
            Dictionary suitable for MongoDB.
        """
        return {
            'university_name': entity.university_name,
            'faculty_name': entity.faculty_name,
            'department_name': entity.department_name,
            'score_type': entity.score_type,
            'quota': entity.quota,
            'score': entity.score,
            'ranking': entity.ranking,
            'price_description': entity.price_description,
            'price_amount': entity.price_amount,
            'currency_code': entity.currency_code,
            'last_scraped_at': entity.last_scraped_at,
        }

    def _document_to_entity(self, document: dict) -> UniversityDepartmentPrice:
        """Convert a MongoDB document to a UniversityDepartmentPrice entity.

        Args:
            document: The MongoDB document.

        Returns:
            UniversityDepartmentPrice entity.
        """
        return UniversityDepartmentPrice(
            university_name=document.get('university_name', ''),
            faculty_name=document.get('faculty_name'),
            department_name=document.get('department_name', ''),
            score_type=document.get('score_type'),
            quota=document.get('quota'),
            score=document.get('score'),
            ranking=document.get('ranking'),
            price_description=document.get('price_description', ''),
            price_amount=document.get('price_amount'),
            currency_code=document.get('currency_code'),
            last_scraped_at=document.get('last_scraped_at')
        )
