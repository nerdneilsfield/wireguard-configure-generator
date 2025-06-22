"""
Base model implementation for the GUI module.

Provides common functionality for all models including serialization and validation.
"""

import json
import uuid
from abc import ABC
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from copy import deepcopy

from ..interfaces.base import IModel


@dataclass
class BaseModel(IModel, ABC):
    """Base implementation of IModel interface using dataclasses."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Perform post-initialization validation."""
        # Ensure id is a string
        if not isinstance(self.id, str):
            self.id = str(self.id)
        
        # Ensure timestamps are datetime objects
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        
        # Validate the model
        errors = self.validate()
        if errors:
            raise ValueError(f"Validation errors: {'; '.join(errors)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the model to a dictionary representation.
        
        Returns:
            Dict containing the model's data
        """
        data = asdict(self)
        
        # Convert datetime objects to ISO format strings
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        
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