"""
Validation manager implementation for the GUI.

This module properly integrates with existing CLI validation through adapters,
avoiding any duplication of validation logic.
"""

from typing import List, Optional, Dict, Any
import ipaddress
import re
import logging

from ..interfaces.managers import IValidationManager
from ..interfaces.state import IAppState  
from ..interfaces.models import INodeModel, IEdgeModel, IGroupModel
from ..adapters import CLIAdapter

# Import validation functions from main library
from ...validator import validate_business_logic, validate_node_connectivity, ValidationContext
from ...logger import get_logger

logger = get_logger()


class ValidationManager(IValidationManager):
    """
    Implementation of IValidationManager that uses CLI validation through adapters.
    
    This ensures consistent validation behavior between GUI and CLI.
    """
    
    def __init__(self):
        """Initialize the validation manager."""
        self.validation_rules = self._initialize_validation_rules()
        # Initialize CLI adapter to use existing validation
        self.cli_adapter = CLIAdapter()
    
    def validate_configuration(self, state: IAppState) -> List[str]:
        """Validate the entire configuration using CLI validators."""
        # Convert GUI models to lists
        nodes = list(state.nodes.values())
        edges = list(state.edges.values())
        
        # Use CLI adapter for validation
        errors = self.cli_adapter.validate_configuration(nodes, edges)
        
        # Add GUI-specific validation
        errors.extend(self._validate_gui_specific(state))
        
        return errors
    
    def validate_node(self, node: INodeModel, existing_nodes: List[INodeModel]) -> List[str]:
        """Validate a single node."""
        errors = []
        
        # Use the node's own validation
        errors.extend(node.validate())
        
        # Check for duplicate names
        existing_names = [n.name for n in existing_nodes if n.id != node.id]
        name_error = self.validate_node_name(node.name, existing_names)
        if name_error:
            errors.append(name_error)
        
        # Check for IP conflicts
        existing_ips = [n.wireguard_ip for n in existing_nodes if n.id != node.id and n.wireguard_ip]
        ip_error = self.check_ip_conflicts(node.wireguard_ip, existing_ips)
        if ip_error:
            errors.append(ip_error)
        
        return errors
    
    def validate_edge(self, edge: IEdgeModel, state: IAppState) -> List[str]:
        """Validate a single edge."""
        errors = []
        
        # Use the edge's own validation
        errors.extend(edge.validate())
        
        # Validate nodes exist
        if edge.source_id not in state.nodes:
            errors.append("Source node does not exist")
        if edge.target_id not in state.nodes:
            errors.append("Target node does not exist")
        
        # Check for duplicate edges
        for existing_edge in state.edges.values():
            if existing_edge.id != edge.id:
                if (existing_edge.source_id == edge.source_id and 
                    existing_edge.target_id == edge.target_id):
                    errors.append("An edge already exists between these nodes")
        
        # Validate allowed IPs don't conflict
        if edge.allowed_ips and edge.source_id in state.nodes and edge.target_id in state.nodes:
            source_node = state.nodes[edge.source_id]
            target_node = state.nodes[edge.target_id]
            
            # Check if allowed IPs overlap with node subnets
            for ip_range in edge.allowed_ips:
                if source_node.wireguard_ip and self.check_subnet_overlaps(ip_range, source_node.wireguard_ip):
                    errors.append(f"Allowed IP {ip_range} overlaps with source node's subnet")
                if target_node.wireguard_ip and self.check_subnet_overlaps(ip_range, target_node.wireguard_ip):
                    errors.append(f"Allowed IP {ip_range} overlaps with target node's subnet")
        
        return errors
    
    def validate_group(self, group: IGroupModel, state: IAppState) -> List[str]:
        """Validate a single group."""
        errors = []
        
        # Use the group's own validation
        errors.extend(group.validate())
        
        # Check for duplicate group names
        existing_names = [g.name for g in state.groups.values() if g.id != group.id]
        if group.name in existing_names:
            errors.append(f"Group name '{group.name}' already exists")
        
        # Validate all nodes exist
        for node_id in group.nodes:
            if node_id not in state.nodes:
                errors.append(f"Node {node_id} in group does not exist")
        
        # Validate topology for node count
        topology_error = self.validate_group_topology(group.topology, len(group.nodes))
        if topology_error:
            errors.append(topology_error)
        
        return errors
    
    def check_connectivity(self, state: IAppState) -> Dict[str, Any]:
        """Check network connectivity using CLI validator."""
        nodes = list(state.nodes.values())
        edges = list(state.edges.values())
        
        # Convert to CLI format
        cli_nodes = [self.cli_adapter.node_model_to_cli(node) for node in nodes]
        cli_peers = [self.cli_adapter.edge_model_to_cli(edge) for edge in edges]
        
        # Use CLI connectivity validation
        connectivity_errors = validate_node_connectivity(cli_nodes, cli_peers)
        
        # Parse results
        isolated_nodes = []
        is_connected = True
        
        for error in connectivity_errors:
            if "isolated" in error.lower():
                # Extract node names from error message
                is_connected = False
                # Simple parsing - in production would need better parsing
                if ":" in error:
                    nodes_part = error.split(":")[1].strip()
                    isolated_nodes = [n.strip() for n in nodes_part.split(",")]
        
        return {
            'is_connected': is_connected,
            'isolated_nodes': isolated_nodes,
            'node_count': len(nodes),
            'edge_count': len(edges)
        }
    
    def validate_ip_address(self, ip: str) -> bool:
        """Validate IP address format."""
        if not ip:
            return False
        
        try:
            # Check if it's a network (CIDR notation)
            if '/' in ip:
                ipaddress.ip_network(ip, strict=False)
            else:
                ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def validate_endpoint(self, endpoint: str) -> bool:
        """Validate endpoint format (host:port)."""
        if not endpoint:
            return True  # Empty endpoint is valid for client nodes
        
        # Check format
        parts = endpoint.rsplit(':', 1)
        if len(parts) != 2:
            return False
        
        host, port_str = parts
        
        # Validate port
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                return False
        except ValueError:
            return False
        
        # Validate host (can be IP or hostname)
        if not host:
            return False
        
        # Try as IP first
        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            # Not an IP, check as hostname
            # Simple hostname regex validation
            hostname_pattern = re.compile(
                r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*'
                r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
            )
            return bool(hostname_pattern.match(host))
    
    def validate_allowed_ips(self, allowed_ips: List[str]) -> List[str]:
        """Validate allowed IP ranges."""
        errors = []
        seen_networks = set()
        
        for ip_range in allowed_ips:
            if not ip_range:
                continue
            
            # Validate format
            if not self.validate_ip_address(ip_range):
                errors.append(f"Invalid IP range format: {ip_range}")
                continue
            
            # Check for overlaps
            try:
                network = ipaddress.ip_network(ip_range, strict=False)
                for seen_net in seen_networks:
                    if network.overlaps(seen_net):
                        errors.append(f"Overlapping IP ranges: {ip_range} overlaps with {seen_net}")
                seen_networks.add(network)
            except ValueError as e:
                errors.append(f"Invalid network: {ip_range} - {str(e)}")
        
        return errors
    
    def validate_node_name(self, name: str, existing_names: List[str]) -> Optional[str]:
        """Validate node name."""
        if not name:
            return "Node name cannot be empty"
        
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', name):
            return "Node name must start with a letter and contain only letters, numbers, hyphens, and underscores"
        
        if name in existing_names:
            return f"Node name '{name}' already exists"
        
        return None
    
    def validate_group_topology(self, topology: str, node_count: int) -> Optional[str]:
        """Validate if topology is appropriate for node count."""
        if topology == 'single' and node_count != 1:
            return f"Single topology requires exactly 1 node, but has {node_count}"
        elif topology == 'mesh' and node_count < 2:
            return f"Mesh topology requires at least 2 nodes, but has {node_count}"
        elif topology == 'star' and node_count < 3:
            return f"Star topology requires at least 3 nodes, but has {node_count}"
        elif topology == 'chain' and node_count < 2:
            return f"Chain topology requires at least 2 nodes, but has {node_count}"
        
        return None
    
    def check_ip_conflicts(self, ip: str, existing_ips: List[str]) -> Optional[str]:
        """Check for IP address conflicts."""
        if not ip:
            return None
        
        if ip in existing_ips:
            return f"IP address '{ip}' is already in use"
        
        # Check for subnet conflicts
        try:
            new_network = ipaddress.ip_interface(ip).network
            for existing_ip in existing_ips:
                existing_network = ipaddress.ip_interface(existing_ip).network
                if new_network.overlaps(existing_network):
                    return f"IP subnet {new_network} overlaps with existing subnet {existing_network}"
        except ValueError:
            return f"Invalid IP address format: {ip}"
        
        return None
    
    def check_subnet_overlaps(self, subnet1: str, subnet2: str) -> bool:
        """Check if two subnets overlap."""
        try:
            network1 = ipaddress.ip_network(subnet1, strict=False)
            network2 = ipaddress.ip_network(subnet2, strict=False)
            return network1.overlaps(network2)
        except ValueError:
            return False
    
    def add_custom_rule(self, name: str, validator: Any) -> None:
        """Add a custom validation rule."""
        self.validation_rules['custom'].append({
            'name': name,
            'validator': validator
        })
    
    def get_validation_context(self, state: IAppState) -> Dict[str, Any]:
        """Get validation context for the current state."""
        # Create a ValidationContext compatible with CLI
        nodes = list(state.nodes.values())
        edges = list(state.edges.values())
        
        # Convert to CLI format for context
        cli_nodes = [self.cli_adapter.node_model_to_cli(node) for node in nodes]
        cli_peers = [self.cli_adapter.edge_model_to_cli(edge) for edge in edges]
        
        # Create context using CLI's ValidationContext
        context = ValidationContext(cli_nodes, cli_peers)
        
        return {
            'node_count': len(state.nodes),
            'edge_count': len(state.edges),
            'group_count': len(state.groups),
            'has_relay_nodes': any(node.role == 'relay' for node in state.nodes.values()),
            'has_groups': len(state.groups) > 0,
            'cli_context': context  # Include CLI context for compatibility
        }
    
    def _initialize_validation_rules(self) -> Dict[str, List[Any]]:
        """Initialize validation rules."""
        return {
            'node': [],
            'edge': [],
            'group': [],
            'custom': []
        }
    
    def _validate_gui_specific(self, state: IAppState) -> List[str]:
        """Perform GUI-specific validation that doesn't exist in CLI."""
        errors = []
        
        # Check for nodes assigned to multiple groups
        node_to_groups = {}
        for group in state.groups.values():
            for node_id in group.nodes:
                if node_id not in node_to_groups:
                    node_to_groups[node_id] = []
                node_to_groups[node_id].append(group.name)
        
        # Report nodes in multiple groups
        for node_id, group_names in node_to_groups.items():
            if len(group_names) > 1:
                node = state.nodes.get(node_id)
                node_name = node.name if node else node_id
                errors.append(f"Node '{node_name}' is assigned to multiple groups: {', '.join(group_names)}")
        
        # Validate visual positions
        for node in state.nodes.values():
            if hasattr(node, 'position') and node.position:
                if 'x' not in node.position or 'y' not in node.position:
                    errors.append(f"Node '{node.name}' has invalid position data")
        
        # Run custom validation rules
        for rule in self.validation_rules.get('custom', []):
            try:
                rule_errors = rule['validator'](state)
                if rule_errors:
                    errors.extend(rule_errors)
            except Exception as e:
                errors.append(f"Custom validation rule '{rule['name']}' failed: {str(e)}")
        
        return errors