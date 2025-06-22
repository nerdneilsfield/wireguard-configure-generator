"""
Validation manager implementation for the GUI.

This module integrates with the existing CLI validation logic while providing
GUI-specific validation capabilities.
"""

from typing import List, Dict, Any, Optional, Set
import ipaddress
import re

from ..interfaces.managers import IValidationManager
from ..interfaces.state import IAppState
from ..interfaces.models import INodeModel, IEdgeModel, IGroupModel

# Import existing validators
from ...validator import validate_business_logic, validate_node_connectivity
from ...data_utils import validate_schema
from ...logger import get_logger


class ValidationManager(IValidationManager):
    """Implementation of IValidationManager for configuration validation."""
    
    def __init__(self):
        """Initialize the validation manager."""
        self._logger = get_logger()
        self._validation_rules: Dict[str, List[Any]] = {
            'ip_format': [],
            'endpoint_format': [],
            'allowed_ips': [],
            'custom': []
        }
    
    def validate_configuration(self, app_state: IAppState) -> List[str]:
        """
        Validate the entire configuration.
        
        Args:
            app_state: Application state to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # First validate the app state itself
        state_errors = app_state.validate_state()
        errors.extend(state_errors)
        
        # Convert to CLI format for validation
        nodes_data = self._convert_nodes_to_cli_format(app_state)
        peers_data = self._convert_edges_to_cli_format(app_state)
        
        # Validate using existing business logic
        try:
            validate_business_logic(nodes_data, peers_data)
        except ValueError as e:
            errors.append(str(e))
        
        # Additional GUI-specific validations
        errors.extend(self._validate_gui_specific(app_state))
        
        # Check connectivity
        connectivity = self.check_connectivity(app_state)
        if not connectivity['is_connected'] and connectivity['node_count'] > 1:
            errors.append("Network is not fully connected")
        if connectivity['isolated_nodes']:
            errors.append(f"Isolated nodes found: {', '.join(connectivity['isolated_nodes'])}")
        
        return errors
    
    def validate_node(self, node: INodeModel) -> List[str]:
        """
        Validate a single node.
        
        Args:
            node: Node to validate
            
        Returns:
            List of validation errors
        """
        # Use the node's built-in validation
        return node.validate()
    
    def validate_edge(self, edge: IEdgeModel) -> List[str]:
        """
        Validate a single edge.
        
        Args:
            edge: Edge to validate
            
        Returns:
            List of validation errors
        """
        # Use the edge's built-in validation
        return edge.validate()
    
    def validate_group(self, group: IGroupModel) -> List[str]:
        """
        Validate a single group.
        
        Args:
            group: Group to validate
            
        Returns:
            List of validation errors
        """
        # Use the group's built-in validation
        return group.validate()
    
    def validate_ip_address(self, ip: str) -> bool:
        """
        Validate an IP address or CIDR.
        
        Args:
            ip: IP address to validate
            
        Returns:
            True if valid
        """
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
        """
        Validate an endpoint format.
        
        Args:
            endpoint: Endpoint to validate (host:port)
            
        Returns:
            True if valid
        """
        if not endpoint:
            return True  # Empty endpoint is valid (for clients)
        
        # Check format
        if ':' not in endpoint:
            return False
        
        parts = endpoint.rsplit(':', 1)
        if len(parts) != 2:
            return False
        
        host, port_str = parts
        
        # Validate port
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
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
            # Simple hostname validation
            hostname_pattern = re.compile(
                r'^(?=.{1,253}$)'  # Total length
                r'(?:[a-zA-Z0-9]'   # First char of label
                r'(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'  # Rest of label
                r'\.)*'             # Other labels
                r'[a-zA-Z0-9]'      # First char of TLD
                r'(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'  # Rest of TLD
            )
            return bool(hostname_pattern.match(host))
    
    def validate_allowed_ips(self, allowed_ips: List[str]) -> List[str]:
        """
        Validate a list of allowed IPs.
        
        Args:
            allowed_ips: List of allowed IPs to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        seen_networks = set()
        
        for ip in allowed_ips:
            if not ip:
                continue
            
            # Validate format
            if not self.validate_ip_address(ip):
                errors.append(f"Invalid IP address format: {ip}")
                continue
            
            # Check for overlaps
            try:
                network = ipaddress.ip_network(ip, strict=False)
                for seen_net in seen_networks:
                    if network.overlaps(seen_net):
                        errors.append(f"Overlapping networks: {ip} overlaps with {seen_net}")
                seen_networks.add(network)
            except ValueError as e:
                errors.append(f"Invalid network: {ip} - {str(e)}")
        
        return errors
    
    def check_connectivity(self, app_state: IAppState) -> Dict[str, Any]:
        """
        Check network connectivity.
        
        Args:
            app_state: Application state to check
            
        Returns:
            Connectivity analysis results
        """
        # Convert to CLI format for analysis
        nodes_data = self._convert_nodes_to_cli_format(app_state)
        peers_data = self._convert_edges_to_cli_format(app_state)
        
        # Use existing connectivity analysis
        return validate_node_connectivity(nodes_data, peers_data)
    
    def add_custom_rule(self, name: str, validator: Any) -> None:
        """
        Add a custom validation rule.
        
        Args:
            name: Rule name
            validator: Validation function
        """
        self._validation_rules['custom'].append({
            'name': name,
            'validator': validator
        })
    
    def _convert_nodes_to_cli_format(self, app_state: IAppState) -> List[Dict[str, Any]]:
        """
        Convert GUI nodes to CLI format for validation.
        
        Args:
            app_state: Application state
            
        Returns:
            List of nodes in CLI format
        """
        nodes = []
        for node_id, node in app_state.nodes.items():
            # Convert to CLI format
            node_data = {
                'name': node.name,
                'role': node.role,
                'endpoints': {}
            }
            
            # Add WireGuard IP if present
            if node.wireguard_ip:
                node_data['wireguard_ip'] = node.wireguard_ip
            
            # Add endpoint
            if node.endpoint:
                # In GUI, we store single endpoint, but CLI expects endpoints dict
                node_data['endpoints']['default'] = node.endpoint
            
            # Add listen port if present
            if hasattr(node, 'listen_port') and node.listen_port:
                node_data['listen_port'] = node.listen_port
            
            nodes.append(node_data)
        
        return nodes
    
    def _convert_edges_to_cli_format(self, app_state: IAppState) -> List[Dict[str, Any]]:
        """
        Convert GUI edges to CLI peer format for validation.
        
        Args:
            app_state: Application state
            
        Returns:
            List of peers in CLI format
        """
        peers = []
        for edge_id, edge in app_state.edges.items():
            # Get source and target nodes
            source_node = app_state.nodes.get(edge.source_id)
            target_node = app_state.nodes.get(edge.target_id)
            
            if not source_node or not target_node:
                continue
            
            # Create peer connection
            peer_data = {
                'from': source_node.name,
                'to': target_node.name
            }
            
            # Add allowed IPs if present
            if edge.allowed_ips:
                peer_data['allowed_ips'] = edge.allowed_ips
            
            # Add endpoint selection if present
            endpoint_key = edge.metadata.get('endpoint_key', 'default')
            if endpoint_key != 'default':
                peer_data['endpoint'] = endpoint_key
            
            peers.append(peer_data)
        
        return peers
    
    def _validate_gui_specific(self, app_state: IAppState) -> List[str]:
        """
        Perform GUI-specific validations.
        
        Args:
            app_state: Application state
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check for duplicate edges
        edge_pairs = set()
        for edge_id, edge in app_state.edges.items():
            # Create a normalized pair (smaller ID first)
            pair = tuple(sorted([edge.source_id, edge.target_id]))
            if pair in edge_pairs:
                source_name = app_state.nodes.get(edge.source_id, {}).name or edge.source_id
                target_name = app_state.nodes.get(edge.target_id, {}).name or edge.target_id
                errors.append(f"Duplicate edge between {source_name} and {target_name}")
            edge_pairs.add(pair)
        
        # Validate group node assignments
        for group_id, group in app_state.groups.items():
            # Check that all nodes in group exist
            for node_id in group.nodes:
                if node_id not in app_state.nodes:
                    errors.append(f"Group '{group.name}' references non-existent node: {node_id}")
        
        # Check for nodes assigned to multiple groups
        node_group_map = {}
        for group_id, group in app_state.groups.items():
            for node_id in group.nodes:
                if node_id in node_group_map:
                    node_name = app_state.nodes.get(node_id, {}).name or node_id
                    errors.append(f"Node '{node_name}' is assigned to multiple groups")
                node_group_map[node_id] = group_id
        
        # Run custom validation rules
        for rule in self._validation_rules['custom']:
            try:
                rule_errors = rule['validator'](app_state)
                if rule_errors:
                    errors.extend(rule_errors)
            except Exception as e:
                errors.append(f"Custom validation rule '{rule['name']}' failed: {str(e)}")
        
        return errors
    
    def validate_import_data(self, data: Dict[str, Any], file_type: str) -> List[str]:
        """
        Validate data before import.
        
        Args:
            data: Data to validate
            file_type: Type of file being imported
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate based on file type
        if file_type == 'nodes':
            # Validate against nodes schema
            try:
                validate_schema(data, "nodes.schema.json")
            except Exception as e:
                errors.append(f"Schema validation failed: {str(e)}")
            
            # Additional checks
            if 'nodes' not in data:
                errors.append("Missing 'nodes' field in nodes configuration")
            
        elif file_type == 'topology':
            # Validate against topology schema
            try:
                validate_schema(data, "topology.schema.json")
            except Exception as e:
                errors.append(f"Schema validation failed: {str(e)}")
            
            # Additional checks
            if 'peers' not in data:
                errors.append("Missing 'peers' field in topology configuration")
            
        elif file_type == 'group_config':
            # Validate group configuration
            if 'groups' not in data:
                errors.append("Missing 'groups' field in group configuration")
            else:
                # Validate each group
                for i, group_data in enumerate(data['groups']):
                    if 'name' not in group_data:
                        errors.append(f"Group {i} missing required 'name' field")
                    if 'topology' not in group_data:
                        errors.append(f"Group {i} missing required 'topology' field")
                    if 'nodes' not in group_data:
                        errors.append(f"Group {i} missing required 'nodes' field")
        
        return errors