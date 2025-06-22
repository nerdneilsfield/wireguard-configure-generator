"""
Base interfaces for the GUI module.

These interfaces define the fundamental contracts that all models and components must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime


class ISerializable(ABC):
    """Interface for objects that can be serialized/deserialized."""
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the object to a dictionary representation.
        
        Returns:
            Dict containing the object's data
        """
        pass
    
    @abstractmethod
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update the object from a dictionary representation.
        
        Args:
            data: Dictionary containing the object's data
        """
        pass
    
    @abstractmethod
    def to_json(self) -> str:
        """
        Convert the object to a JSON string.
        
        Returns:
            JSON string representation
        """
        pass
    
    @abstractmethod
    def from_json(self, json_str: str) -> None:
        """
        Update the object from a JSON string.
        
        Args:
            json_str: JSON string representation
        """
        pass


class IValidatable(ABC):
    """Interface for objects that can be validated."""
    
    @abstractmethod
    def validate(self) -> List[str]:
        """
        Validate the object and return any validation errors.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        pass
    
    @abstractmethod
    def is_valid(self) -> bool:
        """
        Check if the object is valid.
        
        Returns:
            True if valid, False otherwise
        """
        pass


class IModel(ISerializable, IValidatable):
    """Base interface for all data models."""
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for the model."""
        pass
    
    @property
    @abstractmethod
    def created_at(self) -> datetime:
        """Timestamp when the model was created."""
        pass
    
    @property
    @abstractmethod
    def updated_at(self) -> datetime:
        """Timestamp when the model was last updated."""
        pass
    
    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Additional metadata for the model."""
        pass
    
    @abstractmethod
    def update(self, data: Dict[str, Any]) -> None:
        """
        Update the model with new data.
        
        Args:
            data: Dictionary containing fields to update
        """
        pass
    
    @abstractmethod
    def clone(self) -> 'IModel':
        """
        Create a deep copy of the model.
        
        Returns:
            A new instance with the same data
        """
        pass