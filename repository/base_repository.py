"""Abstract base repository for database operations.

This module provides an abstract base class that defines the interface
for all repository implementations using the Generic type pattern.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, Tuple, TypeVar

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Abstract base class for repository pattern implementation.

    This class defines the common interface that all repository classes
    must implement. It uses Python's Generic type to provide type safety.

    Type Parameters:
        T: The entity type this repository manages.
    """

    def __init__(self, collection_name: str):
        """Initialize the base repository.

        Args:
            collection_name: Name of the database collection.
        """
        self._collection_name = collection_name

    @abstractmethod
    def upsert(self, entity: T) -> Tuple[bool, bool]:
        """Insert or update an entity in the database.

        Args:
            entity: The entity to upsert.

        Returns:
            Tuple of (was_inserted, was_updated).
        """

    @abstractmethod
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get an entity by its identifier.

        Args:
            entity_id: The unique identifier of the entity.

        Returns:
            The entity if found, None otherwise.
        """

    @abstractmethod
    def get_all(self) -> List[T]:
        """Get all entities from the database.

        Returns:
            List of all entities.
        """

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete an entity by its identifier.

        Args:
            entity_id: The unique identifier of the entity.

        Returns:
            True if deleted, False otherwise.
        """

    @abstractmethod
    def _entity_to_document(self, entity: T) -> dict:
        """Convert an entity to a database document.

        Args:
            entity: The entity to convert.

        Returns:
            Dictionary suitable for database storage.
        """

    @abstractmethod
    def _document_to_entity(self, document: dict) -> T:
        """Convert a database document to an entity.

        Args:
            document: The database document.

        Returns:
            The converted entity.
        """
