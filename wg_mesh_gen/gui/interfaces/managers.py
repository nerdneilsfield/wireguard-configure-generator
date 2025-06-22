"""
Manager interfaces for handling business logic.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from .state import IAppState
from .models import INodeModel, IEdgeModel, IGroupModel


class IGraphManager(ABC):
    """Interface for managing the network graph and topology."""
    
    @abstractmethod
    def create_node(self, name: str, wireguard_ip: str, role: str = 'client', 
                   position: Optional[Dict[str, float]] = None) -> INodeModel:
        """
        Create a new node.
        
        Args:
            name: Node name
            wireguard_ip: WireGuard IP address with subnet
            role: Node role ('client' or 'relay')
            position: Optional position on canvas
            
        Returns:
            Created node model
        """
        pass
    
    @abstractmethod
    def create_edge(self, source_id: str, target_id: str, edge_type: str = 'peer',
                   allowed_ips: Optional[List[str]] = None) -> IEdgeModel:
        """
        Create a new edge between nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            edge_type: Edge type ('peer', 'mesh', 'star', 'relay')
            allowed_ips: Optional list of allowed IPs
            
        Returns:
            Created edge model
        """
        pass
    
    @abstractmethod
    def create_group(self, name: str, topology: str = 'single', 
                    color: Optional[str] = None) -> IGroupModel:
        """
        Create a new group.
        
        Args:
            name: Group name
            topology: Topology type ('mesh', 'star', 'chain', 'single')
            color: Optional color for visualization
            
        Returns:
            Created group model
        """
        pass
    
    @abstractmethod
    def auto_layout(self, layout_algorithm: str = 'force-directed',
                   options: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply automatic layout to nodes.
        
        Args:
            layout_algorithm: Layout algorithm name
            options: Algorithm-specific options
        """
        pass
    
    @abstractmethod
    def apply_group_topology(self, group_id: str) -> List[IEdgeModel]:
        """
        Apply the group's topology to create edges between its nodes.
        
        Args:
            group_id: Group ID
            
        Returns:
            List of created edges
        """
        pass
    
    @abstractmethod
    def validate_topology(self) -> List[str]:
        """
        Validate the current topology for issues.
        
        Returns:
            List of validation error messages
        """
        pass
    
    @abstractmethod
    def find_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """
        Find a path between two nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            
        Returns:
            List of node IDs forming the path, or None if no path exists
        """
        pass
    
    @abstractmethod
    def get_subnet_conflicts(self) -> List[Tuple[str, str, str]]:
        """
        Find IP subnet conflicts.
        
        Returns:
            List of (node1_id, node2_id, conflicting_subnet) tuples
        """
        pass
    
    @abstractmethod
    def suggest_ip_address(self, subnet: str = '10.0.0.0/24') -> Optional[str]:
        """
        Suggest an available IP address in the subnet.
        
        Args:
            subnet: Subnet to search in
            
        Returns:
            Suggested IP address or None if subnet is full
        """
        pass


class IConfigManager(ABC):
    """Interface for managing configuration import/export."""
    
    @abstractmethod
    def load_configuration(self, file_path: Path) -> IAppState:
        """
        Load configuration from file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            Loaded application state
        """
        pass
    
    @abstractmethod
    def save_configuration(self, state: IAppState, file_path: Path) -> None:
        """
        Save configuration to file.
        
        Args:
            state: Application state to save
            file_path: Path to save to
        """
        pass
    
    @abstractmethod
    def import_nodes(self, nodes_file: Path) -> List[INodeModel]:
        """
        Import nodes from a nodes.yaml file.
        
        Args:
            nodes_file: Path to nodes file
            
        Returns:
            List of imported nodes
        """
        pass
    
    @abstractmethod
    def import_topology(self, topology_file: Path, nodes: Dict[str, INodeModel]) -> List[IEdgeModel]:
        """
        Import topology from a topology.yaml file.
        
        Args:
            topology_file: Path to topology file
            nodes: Existing nodes to connect
            
        Returns:
            List of created edges
        """
        pass
    
    @abstractmethod
    def import_group_config(self, group_file: Path) -> Tuple[List[INodeModel], List[IGroupModel], Dict[str, Any]]:
        """
        Import group configuration.
        
        Args:
            group_file: Path to group configuration file
            
        Returns:
            Tuple of (nodes, groups, routing_config)
        """
        pass
    
    @abstractmethod
    def export_nodes(self, state: IAppState, file_path: Path) -> None:
        """
        Export nodes to a nodes.yaml file.
        
        Args:
            state: Application state
            file_path: Path to save to
        """
        pass
    
    @abstractmethod
    def export_topology(self, state: IAppState, file_path: Path) -> None:
        """
        Export topology to a topology.yaml file.
        
        Args:
            state: Application state
            file_path: Path to save to
        """
        pass
    
    @abstractmethod
    def export_group_config(self, state: IAppState, file_path: Path) -> None:
        """
        Export group configuration.
        
        Args:
            state: Application state
            file_path: Path to save to
        """
        pass
    
    @abstractmethod
    def generate_wireguard_configs(self, state: IAppState, output_dir: Path) -> Dict[str, Path]:
        """
        Generate WireGuard configuration files.
        
        Args:
            state: Application state
            output_dir: Directory to save configs to
            
        Returns:
            Dictionary mapping node names to generated file paths
        """
        pass
    
    @abstractmethod
    def validate_configuration(self, state: IAppState) -> List[str]:
        """
        Validate the entire configuration.
        
        Args:
            state: Application state
            
        Returns:
            List of validation errors
        """
        pass


class IValidationManager(ABC):
    """Interface for validation operations."""
    
    @abstractmethod
    def validate_ip_address(self, ip: str) -> Optional[str]:
        """
        Validate an IP address with subnet.
        
        Args:
            ip: IP address to validate (e.g., '10.0.0.1/24')
            
        Returns:
            Error message if invalid, None if valid
        """
        pass
    
    @abstractmethod
    def validate_endpoint(self, endpoint: str) -> Optional[str]:
        """
        Validate an endpoint address.
        
        Args:
            endpoint: Endpoint to validate (e.g., 'example.com:51820')
            
        Returns:
            Error message if invalid, None if valid
        """
        pass
    
    @abstractmethod
    def validate_allowed_ips(self, allowed_ips: List[str]) -> List[str]:
        """
        Validate a list of allowed IPs.
        
        Args:
            allowed_ips: List of IP ranges to validate
            
        Returns:
            List of error messages (empty if all valid)
        """
        pass
    
    @abstractmethod
    def validate_node_name(self, name: str, existing_names: List[str]) -> Optional[str]:
        """
        Validate a node name.
        
        Args:
            name: Name to validate
            existing_names: List of existing node names
            
        Returns:
            Error message if invalid, None if valid
        """
        pass
    
    @abstractmethod
    def validate_group_topology(self, topology: str, node_count: int) -> Optional[str]:
        """
        Validate if a topology is valid for the number of nodes.
        
        Args:
            topology: Topology type
            node_count: Number of nodes in the group
            
        Returns:
            Error message if invalid, None if valid
        """
        pass
    
    @abstractmethod
    def check_ip_conflicts(self, ip: str, existing_ips: List[str]) -> Optional[str]:
        """
        Check for IP address conflicts.
        
        Args:
            ip: IP to check
            existing_ips: List of existing IPs
            
        Returns:
            Error message if conflict found, None otherwise
        """
        pass
    
    @abstractmethod
    def check_subnet_overlaps(self, subnet1: str, subnet2: str) -> bool:
        """
        Check if two subnets overlap.
        
        Args:
            subnet1: First subnet
            subnet2: Second subnet
            
        Returns:
            True if subnets overlap
        """
        pass