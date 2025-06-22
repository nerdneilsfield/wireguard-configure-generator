"""
Group model implementation for organizing nodes.
"""

import re
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base import BaseModel
from ..interfaces.models import IGroupModel


class GroupModel(BaseModel, IGroupModel):
    """Implementation of IGroupModel for node groups."""
    
    def __init__(self,
                 name: str = "",
                 color: str = "#0080FF",
                 topology: str = "single",
                 mesh_endpoint: Optional[str] = None,
                 nodes: Optional[List[str]] = None,
                 **kwargs):
        """
        Initialize a GroupModel.
        
        Args:
            name: Group name
            color: Color for visualization (hex format)
            topology: Group topology (mesh, star, chain, single)
            mesh_endpoint: Optional endpoint name for mesh connections
            nodes: List of node IDs in this group
            **kwargs: Additional arguments for BaseModel
        """
        # Initialize base model
        base_kwargs = {k: v for k, v in kwargs.items() if k in ['id', 'created_at', 'updated_at', 'metadata']}
        super().__init__(**base_kwargs)
        
        # Set properties
        self.name = name
        self.color = color
        self.topology = topology
        self.mesh_endpoint = mesh_endpoint
        self._nodes = nodes or []
    
    @property
    def name(self) -> str:
        """Get group name."""
        return getattr(self, '_name', '')
    
    @name.setter
    def name(self, value: str) -> None:
        """Set group name."""
        self._name = value
    
    @property
    def color(self) -> str:
        """Get group color."""
        return getattr(self, '_color', '#0080FF')
    
    @color.setter
    def color(self, value: str) -> None:
        """Set group color."""
        self._color = value
    
    @property
    def topology(self) -> str:
        """Get group topology."""
        return getattr(self, '_topology', 'single')
    
    @topology.setter
    def topology(self, value: str) -> None:
        """Set group topology."""
        self._topology = value
    
    @property
    def mesh_endpoint(self) -> Optional[str]:
        """Get mesh endpoint name."""
        return getattr(self, '_mesh_endpoint', None)
    
    @mesh_endpoint.setter
    def mesh_endpoint(self, value: Optional[str]) -> None:
        """Set mesh endpoint name."""
        self._mesh_endpoint = value
    
    @property
    def nodes(self) -> List[str]:
        """Get list of node IDs."""
        return getattr(self, '_nodes', [])
    
    def validate(self) -> List[str]:
        """
        Validate the group model.
        
        Returns:
            List of validation error messages
        """
        errors = super().validate()
        
        # Validate name
        if not self.name:
            errors.append("Group name cannot be empty")
        elif not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', self.name):
            errors.append("Group name must start with a letter and contain only letters, numbers, hyphens, and underscores")
        
        # Validate color (hex format)
        if not re.match(r'^#[0-9A-Fa-f]{6}$', self.color):
            errors.append(f"Invalid color format: {self.color}. Must be hex format like #FF0000")
        
        # Validate topology
        valid_topologies = ['mesh', 'star', 'chain', 'single']
        if self.topology not in valid_topologies:
            errors.append(f"Invalid topology: {self.topology}. Must be one of: {', '.join(valid_topologies)}")
        
        # Validate topology constraints based on node count
        node_count = len(self.nodes)
        
        if self.topology == 'single' and node_count > 1:
            errors.append(f"Single topology can only have 1 node, but has {node_count}")
        elif self.topology == 'mesh' and node_count < 2:
            errors.append(f"Mesh topology requires at least 2 nodes, but has {node_count}")
        elif self.topology == 'star' and node_count < 3:
            errors.append(f"Star topology requires at least 3 nodes, but has {node_count}")
        elif self.topology == 'chain' and node_count < 2:
            errors.append(f"Chain topology requires at least 2 nodes, but has {node_count}")
        
        # Validate mesh endpoint (only valid for mesh topology)
        if self.mesh_endpoint and self.topology != 'mesh':
            errors.append(f"Mesh endpoint is only valid for mesh topology, not {self.topology}")
        
        # Check for duplicate nodes
        unique_nodes = set()
        for node_id in self.nodes:
            if node_id in unique_nodes:
                errors.append(f"Duplicate node ID in group: {node_id}")
            unique_nodes.add(node_id)
        
        return errors
    
    def add_node(self, node_id: str) -> None:
        """
        Add a node to the group.
        
        Args:
            node_id: ID of the node to add
        """
        if not node_id:
            raise ValueError("Node ID cannot be empty")
        
        if node_id not in self._nodes:
            self._nodes.append(node_id)
            self.updated_at = datetime.now()
            
            # Validate after adding
            errors = self.validate()
            if errors:
                # Rollback
                self._nodes.remove(node_id)
                raise ValueError(f"Cannot add node: {'; '.join(errors)}")
    
    def remove_node(self, node_id: str) -> None:
        """
        Remove a node from the group.
        
        Args:
            node_id: ID of the node to remove
        """
        if node_id in self._nodes:
            self._nodes.remove(node_id)
            self.updated_at = datetime.now()
            
            # Validate after removing
            errors = self.validate()
            if errors:
                # Rollback
                self._nodes.append(node_id)
                raise ValueError(f"Cannot remove node: {'; '.join(errors)}")
    
    def has_node(self, node_id: str) -> bool:
        """
        Check if a node is in this group.
        
        Args:
            node_id: ID of the node to check
            
        Returns:
            True if the node is in the group
        """
        return node_id in self._nodes
    
    def get_node_count(self) -> int:
        """
        Get the number of nodes in the group.
        
        Returns:
            Number of nodes
        """
        return len(self._nodes)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation
        """
        data = {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'topology': self.topology,
            'mesh_endpoint': self.mesh_endpoint,
            'nodes': self.nodes,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        # Remove None values
        cleaned_data = {}
        for key, value in data.items():
            if value is not None:
                if isinstance(value, list) and not value and key != 'nodes':
                    continue  # Skip empty lists except nodes
                cleaned_data[key] = value
        
        # For CLI compatibility mode (group config format)
        if self.metadata.get('cli_compatible', False):
            # Groups in CLI format don't have these fields
            for field in ['id', 'created_at', 'updated_at', 'color', 'metadata']:
                cleaned_data.pop(field, None)
            
            # Rename mesh_endpoint to endpoint for CLI
            if 'mesh_endpoint' in cleaned_data and cleaned_data['mesh_endpoint']:
                cleaned_data['endpoint'] = cleaned_data.pop('mesh_endpoint')
            elif 'mesh_endpoint' in cleaned_data:
                cleaned_data.pop('mesh_endpoint')
        
        return cleaned_data
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update the model from a dictionary.
        
        Args:
            data: Dictionary containing the model's data
        """
        # Handle CLI format compatibility
        if 'endpoint' in data and 'mesh_endpoint' not in data:
            data['mesh_endpoint'] = data.pop('endpoint')
        
        # Update properties
        for key, value in data.items():
            if hasattr(self, key) and not key.startswith('_'):
                if key in ('created_at', 'updated_at') and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                elif key == 'nodes':
                    # Directly set the nodes list
                    self._nodes = value or []
                    continue
                setattr(self, key, value)
        
        # Update timestamp
        self.updated_at = datetime.now()
        
        # Validate
        errors = self.validate()
        if errors:
            raise ValueError(f"Validation errors: {'; '.join(errors)}")
    
    def clone(self) -> 'GroupModel':
        """
        Create a deep copy of the group.
        
        Returns:
            A new GroupModel instance with the same data
        """
        import uuid
        from copy import deepcopy
        
        cloned = GroupModel(
            name=self.name,
            color=self.color,
            topology=self.topology,
            mesh_endpoint=self.mesh_endpoint,
            nodes=deepcopy(self.nodes)
        )
        
        # Set new ID and timestamps
        cloned.id = str(uuid.uuid4())
        cloned.created_at = datetime.now()
        cloned.updated_at = datetime.now()
        cloned.metadata = deepcopy(self.metadata)
        
        return cloned
    
    def __repr__(self) -> str:
        """String representation of the group."""
        return f"GroupModel(name={self.name}, topology={self.topology}, nodes={len(self.nodes)})"