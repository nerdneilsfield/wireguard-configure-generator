"""
Model interfaces for WireGuard configuration entities.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from .base import IModel


class INodeModel(IModel):
    """Interface for WireGuard node models."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Display name of the node."""
        pass
    
    @name.setter
    @abstractmethod
    def name(self, value: str) -> None:
        pass
    
    @property
    @abstractmethod
    def wireguard_ip(self) -> str:
        """WireGuard IP address with subnet (e.g., '10.0.0.1/24')."""
        pass
    
    @wireguard_ip.setter
    @abstractmethod
    def wireguard_ip(self, value: str) -> None:
        pass
    
    @property
    @abstractmethod
    def endpoints(self) -> Dict[str, str]:
        """Mapping of endpoint names to addresses (e.g., {'default': 'host:port'})."""
        pass
    
    @property
    @abstractmethod
    def role(self) -> str:
        """Node role: 'client' or 'relay'."""
        pass
    
    @role.setter
    @abstractmethod
    def role(self, value: str) -> None:
        pass
    
    @property
    @abstractmethod
    def enable_ip_forward(self) -> bool:
        """Whether IP forwarding is enabled (for relay nodes)."""
        pass
    
    @enable_ip_forward.setter
    @abstractmethod
    def enable_ip_forward(self, value: bool) -> None:
        pass
    
    @property
    @abstractmethod
    def group_id(self) -> Optional[str]:
        """ID of the group this node belongs to."""
        pass
    
    @group_id.setter
    @abstractmethod
    def group_id(self, value: Optional[str]) -> None:
        pass
    
    @property
    @abstractmethod
    def position(self) -> Dict[str, float]:
        """Visual position on the canvas {'x': float, 'y': float}."""
        pass
    
    @position.setter
    @abstractmethod
    def position(self, value: Dict[str, float]) -> None:
        pass
    
    @abstractmethod
    def add_endpoint(self, name: str, address: str) -> None:
        """
        Add or update an endpoint.
        
        Args:
            name: Endpoint name
            address: Endpoint address (host:port)
        """
        pass
    
    @abstractmethod
    def remove_endpoint(self, name: str) -> None:
        """
        Remove an endpoint.
        
        Args:
            name: Endpoint name to remove
        """
        pass
    
    @abstractmethod
    def get_endpoint(self, name: str) -> Optional[str]:
        """
        Get an endpoint address by name.
        
        Args:
            name: Endpoint name
            
        Returns:
            Endpoint address or None if not found
        """
        pass


class IEdgeModel(IModel):
    """Interface for WireGuard peer connection models."""
    
    @property
    @abstractmethod
    def source_id(self) -> str:
        """ID of the source node."""
        pass
    
    @source_id.setter
    @abstractmethod
    def source_id(self, value: str) -> None:
        pass
    
    @property
    @abstractmethod
    def target_id(self) -> str:
        """ID of the target node."""
        pass
    
    @target_id.setter
    @abstractmethod
    def target_id(self, value: str) -> None:
        pass
    
    @property
    @abstractmethod
    def edge_type(self) -> str:
        """Connection type: 'peer', 'mesh', 'star', or 'relay'."""
        pass
    
    @edge_type.setter
    @abstractmethod
    def edge_type(self, value: str) -> None:
        pass
    
    @property
    @abstractmethod
    def allowed_ips(self) -> List[str]:
        """List of allowed IP ranges for routing."""
        pass
    
    @allowed_ips.setter
    @abstractmethod
    def allowed_ips(self, value: List[str]) -> None:
        pass
    
    @property
    @abstractmethod
    def endpoint_name(self) -> Optional[str]:
        """Name of the endpoint to use for this connection."""
        pass
    
    @endpoint_name.setter
    @abstractmethod
    def endpoint_name(self, value: Optional[str]) -> None:
        pass
    
    @property
    @abstractmethod
    def persistent_keepalive(self) -> Optional[int]:
        """Keepalive interval in seconds."""
        pass
    
    @persistent_keepalive.setter
    @abstractmethod
    def persistent_keepalive(self, value: Optional[int]) -> None:
        pass
    
    @abstractmethod
    def is_bidirectional(self) -> bool:
        """Check if this edge represents a bidirectional connection."""
        pass
    
    @abstractmethod
    def add_allowed_ip(self, ip_range: str) -> None:
        """
        Add an allowed IP range.
        
        Args:
            ip_range: IP range in CIDR notation
        """
        pass
    
    @abstractmethod
    def remove_allowed_ip(self, ip_range: str) -> None:
        """
        Remove an allowed IP range.
        
        Args:
            ip_range: IP range to remove
        """
        pass
    
    @abstractmethod
    def get_direction(self) -> Tuple[str, str]:
        """
        Get the direction of the edge.
        
        Returns:
            Tuple of (from_id, to_id)
        """
        pass


class IGroupModel(IModel):
    """Interface for node group models."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Group display name."""
        pass
    
    @name.setter
    @abstractmethod
    def name(self, value: str) -> None:
        pass
    
    @property
    @abstractmethod
    def color(self) -> str:
        """Color for visualization (hex format)."""
        pass
    
    @color.setter
    @abstractmethod
    def color(self, value: str) -> None:
        pass
    
    @property
    @abstractmethod
    def topology(self) -> str:
        """Group topology: 'mesh', 'star', 'chain', or 'single'."""
        pass
    
    @topology.setter
    @abstractmethod
    def topology(self, value: str) -> None:
        pass
    
    @property
    @abstractmethod
    def mesh_endpoint(self) -> Optional[str]:
        """Endpoint name to use for mesh connections."""
        pass
    
    @mesh_endpoint.setter
    @abstractmethod
    def mesh_endpoint(self, value: Optional[str]) -> None:
        pass
    
    @property
    @abstractmethod
    def nodes(self) -> List[str]:
        """List of node IDs in this group."""
        pass
    
    @abstractmethod
    def add_node(self, node_id: str) -> None:
        """
        Add a node to the group.
        
        Args:
            node_id: ID of the node to add
        """
        pass
    
    @abstractmethod
    def remove_node(self, node_id: str) -> None:
        """
        Remove a node from the group.
        
        Args:
            node_id: ID of the node to remove
        """
        pass
    
    @abstractmethod
    def has_node(self, node_id: str) -> bool:
        """
        Check if a node is in this group.
        
        Args:
            node_id: ID of the node to check
            
        Returns:
            True if the node is in the group
        """
        pass
    
    @abstractmethod
    def get_node_count(self) -> int:
        """
        Get the number of nodes in the group.
        
        Returns:
            Number of nodes
        """
        pass