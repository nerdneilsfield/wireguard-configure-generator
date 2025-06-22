"""
Edge model implementation for WireGuard peer connections.
"""

import ipaddress
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .base import BaseModel
from ..interfaces.models import IEdgeModel


class EdgeModel(BaseModel, IEdgeModel):
    """Implementation of IEdgeModel for WireGuard peer connections."""
    
    def __init__(self,
                 source_id: str = "",
                 target_id: str = "",
                 edge_type: str = "peer",
                 allowed_ips: Optional[List[str]] = None,
                 endpoint_name: Optional[str] = None,
                 persistent_keepalive: Optional[int] = None,
                 **kwargs):
        """
        Initialize an EdgeModel.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            edge_type: Connection type (peer, mesh, star, relay)
            allowed_ips: List of allowed IP ranges
            endpoint_name: Optional endpoint name to use
            persistent_keepalive: Optional keepalive interval
            **kwargs: Additional arguments for BaseModel
        """
        # Initialize base model
        super().__init__(**kwargs)
        
        # Set properties
        self.source_id = source_id
        self.target_id = target_id
        self.edge_type = edge_type
        self.allowed_ips = allowed_ips or []
        self.endpoint_name = endpoint_name
        self.persistent_keepalive = persistent_keepalive
    
    @property
    def source_id(self) -> str:
        """Get source node ID."""
        return getattr(self, '_source_id', '')
    
    @source_id.setter
    def source_id(self, value: str) -> None:
        """Set source node ID."""
        self._source_id = value
    
    @property
    def target_id(self) -> str:
        """Get target node ID."""
        return getattr(self, '_target_id', '')
    
    @target_id.setter
    def target_id(self, value: str) -> None:
        """Set target node ID."""
        self._target_id = value
    
    @property
    def edge_type(self) -> str:
        """Get edge type."""
        return getattr(self, '_edge_type', 'peer')
    
    @edge_type.setter
    def edge_type(self, value: str) -> None:
        """Set edge type."""
        self._edge_type = value
    
    @property
    def allowed_ips(self) -> List[str]:
        """Get allowed IPs."""
        return getattr(self, '_allowed_ips', [])
    
    @allowed_ips.setter
    def allowed_ips(self, value: List[str]) -> None:
        """Set allowed IPs."""
        self._allowed_ips = value or []
    
    @property
    def endpoint_name(self) -> Optional[str]:
        """Get endpoint name."""
        return getattr(self, '_endpoint_name', None)
    
    @endpoint_name.setter
    def endpoint_name(self, value: Optional[str]) -> None:
        """Set endpoint name."""
        self._endpoint_name = value
    
    @property
    def persistent_keepalive(self) -> Optional[int]:
        """Get persistent keepalive interval."""
        return getattr(self, '_persistent_keepalive', None)
    
    @persistent_keepalive.setter
    def persistent_keepalive(self, value: Optional[int]) -> None:
        """Set persistent keepalive interval."""
        self._persistent_keepalive = value
    
    def validate(self) -> List[str]:
        """
        Validate the edge model.
        
        Returns:
            List of validation error messages
        """
        errors = super().validate()
        
        # Validate source and target IDs
        if not self.source_id:
            errors.append("Source node ID cannot be empty")
        if not self.target_id:
            errors.append("Target node ID cannot be empty")
        if self.source_id == self.target_id:
            errors.append("Source and target nodes cannot be the same")
        
        # Validate edge type
        valid_types = ['peer', 'mesh', 'star', 'relay']
        if self.edge_type not in valid_types:
            errors.append(f"Invalid edge type: {self.edge_type}. Must be one of: {', '.join(valid_types)}")
        
        # Validate allowed IPs
        for ip_range in self.allowed_ips:
            try:
                # Validate IP network format
                ipaddress.ip_network(ip_range, strict=False)
            except ValueError as e:
                errors.append(f"Invalid allowed IP range '{ip_range}': {str(e)}")
        
        # Check for duplicate allowed IPs
        unique_ips = set()
        for ip_range in self.allowed_ips:
            if ip_range in unique_ips:
                errors.append(f"Duplicate allowed IP range: {ip_range}")
            unique_ips.add(ip_range)
        
        # Validate persistent keepalive
        if self.persistent_keepalive is not None:
            if not isinstance(self.persistent_keepalive, int):
                errors.append("Persistent keepalive must be an integer")
            elif self.persistent_keepalive <= 0:
                errors.append("Persistent keepalive must be a positive integer")
            elif self.persistent_keepalive > 3600:
                errors.append("Persistent keepalive should not exceed 3600 seconds")
        
        return errors
    
    def is_bidirectional(self) -> bool:
        """
        Check if this edge represents a bidirectional connection.
        
        Returns:
            True if bidirectional (always False for unidirectional edges)
        """
        # In this implementation, edges are unidirectional
        # Bidirectional connections are represented by two separate edges
        return False
    
    def add_allowed_ip(self, ip_range: str) -> None:
        """
        Add an allowed IP range.
        
        Args:
            ip_range: IP range in CIDR notation
        """
        # Validate IP range
        try:
            ipaddress.ip_network(ip_range, strict=False)
        except ValueError as e:
            raise ValueError(f"Invalid IP range: {str(e)}")
        
        # Add if not already present
        if ip_range not in self.allowed_ips:
            self.allowed_ips.append(ip_range)
            self.updated_at = datetime.now()
    
    def remove_allowed_ip(self, ip_range: str) -> None:
        """
        Remove an allowed IP range.
        
        Args:
            ip_range: IP range to remove
        """
        if ip_range in self.allowed_ips:
            self.allowed_ips.remove(ip_range)
            self.updated_at = datetime.now()
    
    def get_direction(self) -> Tuple[str, str]:
        """
        Get the direction of the edge.
        
        Returns:
            Tuple of (from_id, to_id)
        """
        return (self.source_id, self.target_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation
        """
        data = {
            'id': self.id,
            'source_id': self.source_id,
            'target_id': self.target_id,
            'edge_type': self.edge_type,
            'allowed_ips': self.allowed_ips,
            'endpoint_name': self.endpoint_name,
            'persistent_keepalive': self.persistent_keepalive,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        # Remove None values
        cleaned_data = {}
        for key, value in data.items():
            if value is not None:
                if isinstance(value, list) and not value:
                    continue  # Skip empty lists
                cleaned_data[key] = value
        
        # For CLI compatibility mode
        if self.metadata.get('cli_compatible', False):
            # Convert to CLI format
            cli_data = {
                'from': self.source_id,
                'to': self.target_id,
            }
            
            if self.allowed_ips:
                cli_data['allowed_ips'] = self.allowed_ips
            if self.endpoint_name:
                cli_data['endpoint_name'] = self.endpoint_name
            if self.persistent_keepalive:
                cli_data['persistent_keepalive'] = self.persistent_keepalive
            
            return cli_data
        
        return cleaned_data
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update the model from a dictionary.
        
        Args:
            data: Dictionary containing the model's data
        """
        # Handle CLI format compatibility
        if 'from' in data and 'source_id' not in data:
            data['source_id'] = data.pop('from')
        if 'to' in data and 'target_id' not in data:
            data['target_id'] = data.pop('to')
        
        # Update properties
        for key, value in data.items():
            if hasattr(self, key) and not key.startswith('_'):
                if key in ('created_at', 'updated_at') and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                setattr(self, key, value)
        
        # Update timestamp
        self.updated_at = datetime.now()
        
        # Validate
        errors = self.validate()
        if errors:
            raise ValueError(f"Validation errors: {'; '.join(errors)}")
    
    def clone(self) -> 'EdgeModel':
        """
        Create a deep copy of the edge.
        
        Returns:
            A new EdgeModel instance with the same data
        """
        import uuid
        from copy import deepcopy
        
        cloned = EdgeModel(
            source_id=self.source_id,
            target_id=self.target_id,
            edge_type=self.edge_type,
            allowed_ips=deepcopy(self.allowed_ips),
            endpoint_name=self.endpoint_name,
            persistent_keepalive=self.persistent_keepalive
        )
        
        # Set new ID and timestamps
        cloned.id = str(uuid.uuid4())
        cloned.created_at = datetime.now()
        cloned.updated_at = datetime.now()
        cloned.metadata = deepcopy(self.metadata)
        
        return cloned
    
    def __repr__(self) -> str:
        """String representation of the edge."""
        return f"EdgeModel({self.source_id} -> {self.target_id}, type={self.edge_type})"