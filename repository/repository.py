from __future__ import annotations
from typing import Tuple, List, Optional
import sys
import os

# Ensure project root is on sys.path so imports like `util.models` work
sys.path.insert(0, os.getcwd())

from util.connect import get_db
from models.university_models import UniversityDepartmentPrice
from repository.base_repository import BaseRepository


class UniversityPriceRepository(BaseRepository[UniversityDepartmentPrice]):
    """Repository for managing university department price data in MongoDB.
    
    This class inherits from BaseRepository and implements all abstract methods
    for the UniversityDepartmentPrice entity.
    
    Inheritance hierarchy:
        BaseRepository[T] (Abstract)
            └── UniversityPriceRepository
    """

    COLLECTION_NAME = 'university_prices'

    def __init__(self, database_name: Optional[str] = None):
        """Initialize the repository.
        
        Args:
            database_name: Optional database name, uses default if not provided
        """
        super().__init__(self.COLLECTION_NAME)
        self._db = get_db(database_name) if database_name else get_db()

    def upsert(self, entity: UniversityDepartmentPrice) -> Tuple[bool, bool]:
        """Insert or update a department price entity.
        
        Implements the abstract method from BaseRepository.
        
        Args:
            entity: The UniversityDepartmentPrice to upsert
            
        Returns:
            Tuple of (was_inserted, was_updated)
        """
        return self.upsert_department_price(entity)

    def upsert_department_price(self, department_price: UniversityDepartmentPrice) -> Tuple[bool, bool]:
        """Insert or update a UniversityDepartmentPrice document.
        
        Returns:
            Tuple of (was_inserted, was_updated)
        """
        collection = self._db[self.COLLECTION_NAME]
        query_filter = {
            'university_name': department_price.university_name,
            'department_name': department_price.department_name
        }
        document = {
            'university_name': department_price.university_name,
            'faculty_name': department_price.faculty_name,
            'department_name': department_price.department_name,
            'price_description': department_price.price_description,
            'price_amount': department_price.price_amount,
            'currency_code': department_price.currency_code,
            'last_scraped_at': department_price.last_scraped_at,
        }
        result = collection.update_one(query_filter, {'$set': document}, upsert=True)
        was_inserted = getattr(result, 'upserted_id', None) is not None
        was_updated = not was_inserted
        return was_inserted, was_updated

    # Backward-compatible alias
    def update_price(self, department_price: UniversityDepartmentPrice) -> Tuple[bool, bool]:
        return self.upsert_department_price(department_price)

    def get_prices_by_university(self, university_name: str) -> List[UniversityDepartmentPrice]:
        """Get all department prices for a specific university."""
        collection = self._db[self.COLLECTION_NAME]
        cursor = collection.find({'university_name': university_name})
        results: List[UniversityDepartmentPrice] = []
        for document in cursor:
            results.append(self._document_to_model(document))
        return results

    def get_all_prices(self) -> List[UniversityDepartmentPrice]:
        """Get all department prices from the database."""
        collection = self._db[self.COLLECTION_NAME]
        cursor = collection.find({})
        results: List[UniversityDepartmentPrice] = []
        for document in cursor:
            results.append(self._document_to_model(document))
        return results

    def find_price_by_department(self, university_name: str, department_name: str) -> Optional[UniversityDepartmentPrice]:
        """Find a specific department price by university and department name."""
        collection = self._db[self.COLLECTION_NAME]
        document = collection.find_one({
            'university_name': university_name,
            'department_name': department_name
        })
        if document:
            return self._document_to_model(document)
        return None

    # ========== Abstract Method Implementations ==========

    def get_by_id(self, entity_id: str) -> Optional[UniversityDepartmentPrice]:
        """Get an entity by its identifier (composite key: university_name::department_name).
        
        Implements the abstract method from BaseRepository.
        
        Args:
            entity_id: Composite key in format "university_name::department_name"
            
        Returns:
            The entity if found, None otherwise
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
        
        Implements the abstract method from BaseRepository.
        
        Returns:
            List of all UniversityDepartmentPrice entities
        """
        return self.get_all_prices()

    def delete(self, entity_id: str) -> bool:
        """Delete an entity by its identifier.
        
        Implements the abstract method from BaseRepository.
        
        Args:
            entity_id: Composite key in format "university_name::department_name"
            
        Returns:
            True if deleted, False otherwise
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

    def _document_to_entity(self, document: dict) -> UniversityDepartmentPrice:
        """Convert a database document to an entity.
        
        Implements the abstract method from BaseRepository.
        
        Args:
            document: The MongoDB document
            
        Returns:
            UniversityDepartmentPrice entity
        """
        return self._document_to_model(document)

    def _entity_to_document(self, entity: UniversityDepartmentPrice) -> dict:
        """Convert an entity to a database document.
        
        Implements the abstract method from BaseRepository.
        
        Args:
            entity: The UniversityDepartmentPrice entity
            
        Returns:
            Dictionary suitable for MongoDB
        """
        return {
            'university_name': entity.university_name,
            'faculty_name': entity.faculty_name,
            'department_name': entity.department_name,
            'price_description': entity.price_description,
            'price_amount': entity.price_amount,
            'currency_code': entity.currency_code,
            'last_scraped_at': entity.last_scraped_at,
        }

    def _document_to_model(self, document: dict) -> UniversityDepartmentPrice:
        """Convert a MongoDB document to a UniversityDepartmentPrice model."""
        return UniversityDepartmentPrice(
            university_name=document.get('university_name', ''),
            faculty_name=document.get('faculty_name'),
            department_name=document.get('department_name', ''),
            price_description=document.get('price_description', ''),
            price_amount=document.get('price_amount'),
            currency_code=document.get('currency_code'),
            last_scraped_at=document.get('last_scraped_at')
        )