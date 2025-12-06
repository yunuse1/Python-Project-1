"""Base repository module with abstract classes and protocols for OOP patterns.

This module provides:
- Abstract base class for repository pattern (Inheritance +5)
- Protocol for type checking and interface definition (Abstract/Protocols +10)
- Full type hints for static type checking
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Tuple, Protocol, runtime_checkable

# Generic type variable for entity models
T = TypeVar('T')


@runtime_checkable
class RepositoryProtocol(Protocol[T]):
    """Protocol defining the interface for repository operations.
    
    This protocol enables structural subtyping (duck typing with type checking).
    Any class implementing these methods will be considered compatible.
    """
    
    def upsert(self, entity: T) -> Tuple[bool, bool]:
        """Insert or update an entity.
        
        Args:
            entity: The entity to upsert
            
        Returns:
            Tuple of (was_inserted, was_updated)
        """
        ...
    
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get an entity by its identifier.
        
        Args:
            entity_id: The unique identifier
            
        Returns:
            The entity if found, None otherwise
        """
        ...
    
    def get_all(self) -> List[T]:
        """Get all entities.
        
        Returns:
            List of all entities
        """
        ...
    
    def delete(self, entity_id: str) -> bool:
        """Delete an entity by its identifier.
        
        Args:
            entity_id: The unique identifier
            
        Returns:
            True if deleted, False otherwise
        """
        ...


class BaseRepository(ABC, Generic[T]):
    """Abstract base class for repository pattern implementation.
    
    This class provides a template for data access operations using
    the Repository pattern. Subclasses must implement all abstract methods.
    
    Type Parameters:
        T: The entity type this repository manages
    
    Attributes:
        _collection_name: Name of the database collection
    """
    
    def __init__(self, collection_name: str):
        """Initialize the repository with a collection name.
        
        Args:
            collection_name: Name of the database collection
        """
        self._collection_name = collection_name
    
    @property
    def collection_name(self) -> str:
        """Get the collection name."""
        return self._collection_name
    
    @abstractmethod
    def upsert(self, entity: T) -> Tuple[bool, bool]:
        """Insert or update an entity.
        
        Args:
            entity: The entity to upsert
            
        Returns:
            Tuple of (was_inserted, was_updated)
        """
        pass
    
    @abstractmethod
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get an entity by its identifier.
        
        Args:
            entity_id: The unique identifier
            
        Returns:
            The entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[T]:
        """Get all entities.
        
        Returns:
            List of all entities
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete an entity by its identifier.
        
        Args:
            entity_id: The unique identifier
            
        Returns:
            True if deleted, False otherwise
        """
        pass
    
    @abstractmethod
    def _document_to_entity(self, document: dict) -> T:
        """Convert a database document to an entity.
        
        Args:
            document: The database document
            
        Returns:
            The entity object
        """
        pass
    
    @abstractmethod
    def _entity_to_document(self, entity: T) -> dict:
        """Convert an entity to a database document.
        
        Args:
            entity: The entity object
            
        Returns:
            The database document
        """
        pass
