"""
Node model implementation for WireGuard configuration.
"""

import re
import ipaddress
from typing import Dict, List, Optional, Any
from datetime import datetime

from dataclasses import dataclass, field

from .base import BaseModel
from ..interfaces.models import INodeModel


@dataclass
class NodeModel(BaseModel, INodeModel):
    """Implementation of INodeModel for WireGuard nodes."""
    
    def __init__(self, 
                 name: str = "",
                 wireguard_ip: str = "",
                 endpoints: Optional[Dict[str, str]] = None,
                 role: str = "client",
                 enable_ip_forward: bool = False,
                 group_id: Optional[str] = None,
                 position: Optional[Dict[str, float]] = None,
                 **kwargs):
        """
        Initialize a NodeModel.
        
        Args:
            name: Node name
            wireguard_ip: WireGuard IP address with subnet
            endpoints: Endpoint mappings
            role: Node role (client or relay)
            enable_ip_forward: Whether to enable IP forwarding
            group_id: Group ID if assigned
            position: Visual position
            **kwargs: Additional arguments for BaseModel
        """
        # Initialize base model
        super().__init__(**kwargs)
        
        # Set properties using setters for validation
        self.name = name
        self.wireguard_ip = wireguard_ip
        self.endpoints = endpoints or {}
        self.role = role
        self.enable_ip_forward = enable_ip_forward
        self.group_id = group_id
        self.position = position or {"x": 0.0, "y": 0.0}
    
    @property
    def name(self) -> str:
        """Get node name."""
        return getattr(self, '_name', '')
    
    @name.setter
    def name(self, value: str) -> None:
        """Set node name."""
        self._name = value
    
    @property
    def wireguard_ip(self) -> str:
        """Get WireGuard IP address."""
        return getattr(self, '_wireguard_ip', '')
    
    @wireguard_ip.setter
    def wireguard_ip(self, value: str) -> None:
        """Set WireGuard IP address."""
        self._wireguard_ip = value
    
    @property
    def endpoints(self) -> Dict[str, str]:
        """Get endpoints."""
        return getattr(self, '_endpoints', {})
    
    @endpoints.setter
    def endpoints(self, value: Dict[str, str]) -> None:
        """Set endpoints."""
        self._endpoints = value or {}
    
    @property
    def role(self) -> str:
        """Get node role."""
        return getattr(self, '_role', 'client')
    
    @role.setter
    def role(self, value: str) -> None:
        """Set node role and update related properties."""
        self._role = value
        # Automatically enable IP forwarding for relay nodes
        if value == "relay" and hasattr(self, '_enable_ip_forward'):
            self._enable_ip_forward = True
    
    @property
    def enable_ip_forward(self) -> bool:
        """Get IP forwarding status."""
        return getattr(self, '_enable_ip_forward', False)
    
    @enable_ip_forward.setter
    def enable_ip_forward(self, value: bool) -> None:
        """Set IP forwarding status."""
        self._enable_ip_forward = value
    
    @property
    def group_id(self) -> Optional[str]:
        """Get group ID."""
        return getattr(self, '_group_id', None)
    
    @group_id.setter
    def group_id(self, value: Optional[str]) -> None:
        """Set group ID."""
        self._group_id = value
    
    @property
    def position(self) -> Dict[str, float]:
        """Get node position."""
        return getattr(self, '_position', {"x": 0.0, "y": 0.0})
    
    @position.setter
    def position(self, value: Dict[str, float]) -> None:
        """Set node position."""
        self._position = value
    
    def validate(self) -> List[str]:
        """
        Validate the node model.
        
        Returns:
            List of validation error messages
        """
        errors = super().validate()
        
        # Validate name
        if not self.name:
            errors.append("Node name cannot be empty")
        elif not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', self.name):
            errors.append("Node name must start with a letter and contain only letters, numbers, hyphens, and underscores")
        
        # Validate WireGuard IP
        if not self.wireguard_ip:
            errors.append("WireGuard IP address cannot be empty")
        else:
            try:
                # Parse IP with subnet
                ipaddress.ip_interface(self.wireguard_ip)
            except ValueError as e:
                errors.append(f"Invalid WireGuard IP address: {str(e)}")
        
        # Validate endpoints
        for endpoint_name, endpoint_addr in self.endpoints.items():
            if not endpoint_name:
                errors.append("Endpoint name cannot be empty")
            if not endpoint_addr:
                errors.append(f"Endpoint address for '{endpoint_name}' cannot be empty")
            else:
                # Validate endpoint format (host:port)
                parts = endpoint_addr.rsplit(':', 1)
                if len(parts) != 2:
                    errors.append(f"Endpoint '{endpoint_name}' must be in format 'host:port'")
                else:
                    host, port = parts
                    if not host:
                        errors.append(f"Endpoint '{endpoint_name}' has empty host")
                    try:
                        port_num = int(port)
                        if not (1 <= port_num <= 65535):
                            errors.append(f"Endpoint '{endpoint_name}' port must be between 1 and 65535")
                    except ValueError:
                        errors.append(f"Endpoint '{endpoint_name}' has invalid port number")
        
        # Validate role
        if self.role not in ("client", "relay"):
            errors.append(f"Invalid role: {self.role}. Must be 'client' or 'relay'")
        
        # Validate position
        if not isinstance(self.position, dict):
            errors.append("Position must be a dictionary")
        elif 'x' not in self.position or 'y' not in self.position:
            errors.append("Position must have 'x' and 'y' coordinates")
        else:
            try:
                float(self.position['x'])
                float(self.position['y'])
            except (ValueError, TypeError):
                errors.append("Position coordinates must be numeric")
        
        return errors
    
    def add_endpoint(self, name: str, address: str) -> None:
        """
        Add or update an endpoint.
        
        Args:
            name: Endpoint name
            address: Endpoint address (host:port)
        """
        if not name:
            raise ValueError("Endpoint name cannot be empty")
        if not address:
            raise ValueError("Endpoint address cannot be empty")
        
        # Validate endpoint format
        parts = address.rsplit(':', 1)
        if len(parts) != 2:
            raise ValueError(f"Endpoint address must be in format 'host:port', got: {address}")
        
        host, port = parts
        try:
            port_num = int(port)
            if not (1 <= port_num <= 65535):
                raise ValueError(f"Port must be between 1 and 65535, got: {port}")
        except ValueError:
            raise ValueError(f"Invalid port number: {port}")
        
        self.endpoints[name] = address
        self.updated_at = datetime.now()
    
    def remove_endpoint(self, name: str) -> None:
        """
        Remove an endpoint.
        
        Args:
            name: Endpoint name to remove
        """
        if name in self.endpoints:
            del self.endpoints[name]
            self.updated_at = datetime.now()
    
    def get_endpoint(self, name: str) -> Optional[str]:
        """
        Get an endpoint address by name.
        
        Args:
            name: Endpoint name
            
        Returns:
            Endpoint address or None if not found
        """
        return self.endpoints.get(name)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary, compatible with existing YAML/JSON format.
        
        Returns:
            Dictionary representation
        """
        data = {
            'id': self.id,
            'name': self.name,
            'wireguard_ip': self.wireguard_ip,
            'endpoints': self.endpoints,
            'role': self.role,
            'enable_ip_forward': self.enable_ip_forward,
            'group_id': self.group_id,
            'position': self.position,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        # Remove None values and empty collections
        cleaned_data = {}
        for key, value in data.items():
            if value is not None:
                if isinstance(value, (list, dict)) and not value and key != 'position':
                    continue  # Skip empty collections except position
                cleaned_data[key] = value
        
        # For CLI compatibility mode
        if self.metadata.get('cli_compatible', False):
            # Remove GUI-specific fields
            for field in ['id', 'created_at', 'updated_at', 'position', 'group_id', 'metadata']:
                cleaned_data.pop(field, None)
            
            # Rename fields to match CLI format
            if 'wireguard_ip' in cleaned_data:
                cleaned_data['ip'] = cleaned_data.pop('wireguard_ip')
            
            # Only include enable_ip_forward if True
            if not cleaned_data.get('enable_ip_forward', False):
                cleaned_data.pop('enable_ip_forward', None)
        
        return cleaned_data
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update the model from a dictionary.
        
        Args:
            data: Dictionary containing the model's data
        """
        # Handle CLI format compatibility
        if 'ip' in data and 'wireguard_ip' not in data:
            data['wireguard_ip'] = data.pop('ip')
        
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
    
    def clone(self) -> 'NodeModel':
        """
        Create a deep copy of the node.
        
        Returns:
            A new NodeModel instance with the same data
        """
        import uuid
        from copy import deepcopy
        
        cloned = NodeModel(
            name=self.name,
            wireguard_ip=self.wireguard_ip,
            endpoints=deepcopy(self.endpoints),
            role=self.role,
            enable_ip_forward=self.enable_ip_forward,
            group_id=self.group_id,
            position=deepcopy(self.position)
        )
        
        # Set new ID and timestamps
        cloned.id = str(uuid.uuid4())
        cloned.created_at = datetime.now()
        cloned.updated_at = datetime.now()
        cloned.metadata = deepcopy(self.metadata)
        
        return cloned