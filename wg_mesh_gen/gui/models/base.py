"""
Base model implementation for the GUI module.

Provides common functionality for all models including serialization and validation.
"""

import json
import uuid
from abc import ABC
from datetime import datetime
from typing import Any, Dict, List, Optional
from copy import deepcopy

from ..interfaces.base import IModel


class BaseModel(IModel, ABC):
    """Base implementation of IModel interface."""
    
    def __init__(self, id: Optional[str] = None, created_at: Optional[datetime] = None,
                 updated_at: Optional[datetime] = None, metadata: Optional[Dict[str, Any]] = None):
        """Initialize base model."""
        self._id = id or str(uuid.uuid4())
        self._created_at = created_at or datetime.now()
        self._updated_at = updated_at or datetime.now()
        self._metadata = metadata or {}
        
        # Ensure id is a string
        if not isinstance(self._id, str):
            self._id = str(self._id)
        
        # Ensure timestamps are datetime objects
        if isinstance(self._created_at, str):
            self._created_at = datetime.fromisoformat(self._created_at)
        if isinstance(self._updated_at, str):
            self._updated_at = datetime.fromisoformat(self._updated_at)
        
        # Skip validation during initialization - it will be done after setting properties
    
    @property
    def id(self) -> str:
        """Unique identifier for the model."""
        return self._id
    
    @property
    def created_at(self) -> datetime:
        """Timestamp when the model was created."""
        return self._created_at
    
    @property
    def updated_at(self) -> datetime:
        """Timestamp when the model was last updated."""
        return self._updated_at
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Additional metadata for the model."""
        return self._metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the model to a dictionary representation.
        
        Returns:
            Dict containing the model's data
        """
        # Get all public attributes
        data = {}
        for attr_name in dir(self):
            if not attr_name.startswith('_') and not callable(getattr(self, attr_name)):
                value = getattr(self, attr_name)
                data[attr_name] = value
        
        # Convert datetime objects to ISO format strings
        data['created_at'] = self._created_at.isoformat()
        data['updated_at'] = self._updated_at.isoformat()
        
        # Remove None values and empty collections
        cleaned_data = {}
        for key, value in data.items():
            if value is not None:
                if isinstance(value, (list, dict, str)) and not value:
                    continue  # Skip empty collections and strings
                cleaned_data[key] = value
        
        return cleaned_data
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update the model from a dictionary representation.
        
        Args:
            data: Dictionary containing the model's data
        """
        for key, value in data.items():
            if hasattr(self, key):
                # Convert ISO strings back to datetime objects
                if key in ('created_at', 'updated_at') and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                setattr(self, key, value)
        
        # Update the updated_at timestamp
        self.updated_at = datetime.now()
        
        # Re-validate after update
        errors = self.validate()
        if errors:
            raise ValueError(f"Validation errors after update: {'; '.join(errors)}")
    
    def to_json(self) -> str:
        """
        Convert the model to a JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    def from_json(self, json_str: str) -> None:
        """
        Update the model from a JSON string.
        
        Args:
            json_str: JSON string representation
        """
        data = json.loads(json_str)
        self.from_dict(data)
    
    def validate(self) -> List[str]:
        """
        Validate the model and return any validation errors.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Basic validation that applies to all models
        if not self.id:
            errors.append("ID cannot be empty")
        
        if not isinstance(self.created_at, datetime):
            errors.append("created_at must be a datetime object")
        
        if not isinstance(self.updated_at, datetime):
            errors.append("updated_at must be a datetime object")
        
        if self.created_at > self.updated_at:
            errors.append("created_at cannot be later than updated_at")
        
        if not isinstance(self.metadata, dict):
            errors.append("metadata must be a dictionary")
        
        return errors
    
    def is_valid(self) -> bool:
        """
        Check if the model is valid.
        
        Returns:
            True if valid, False otherwise
        """
        return len(self.validate()) == 0
    
    def update(self, data: Dict[str, Any]) -> None:
        """
        Update the model with new data.
        
        Args:
            data: Dictionary containing fields to update
        """
        # Filter out protected fields
        protected_fields = {'id', 'created_at'}
        update_data = {k: v for k, v in data.items() if k not in protected_fields}
        
        # Apply updates
        for key, value in update_data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Update timestamp
        self.updated_at = datetime.now()
        
        # Validate after update
        errors = self.validate()
        if errors:
            raise ValueError(f"Validation errors after update: {'; '.join(errors)}")
    
    def clone(self) -> 'BaseModel':
        """
        Create a deep copy of the model.
        
        Returns:
            A new instance with the same data
        """
        # Create a deep copy of the current instance
        cloned_data = deepcopy(self.to_dict())
        
        # Generate a new ID for the clone
        cloned_data['id'] = str(uuid.uuid4())
        cloned_data['created_at'] = datetime.now().isoformat()
        cloned_data['updated_at'] = datetime.now().isoformat()
        
        # Create a new instance of the same class
        cloned = self.__class__(**{})
        cloned.from_dict(cloned_data)
        
        return cloned
    
    def __eq__(self, other: Any) -> bool:
        """Check equality based on ID."""
        if not isinstance(other, BaseModel):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Make the model hashable based on ID."""
        return hash(self.id)