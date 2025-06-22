"""
Configuration manager implementation for the GUI.

This module integrates with existing CLI loaders and provides
configuration import/export functionality.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import yaml

from ..interfaces.managers import IConfigManager
from ..interfaces.state import IAppState
from ..models import NodeModel, EdgeModel, GroupModel

# Import existing CLI utilities
from ...loader import load_nodes, load_topology
from ...group_network_builder import GroupNetworkBuilder
from ...file_utils import load_config, save_yaml
from ...logger import get_logger


class ConfigManager(IConfigManager):
    """Implementation of IConfigManager for configuration management."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        self._logger = get_logger()
        self._supported_formats = {
            'nodes': ['yaml', 'json'],
            'topology': ['yaml', 'json'],
            'group_config': ['yaml', 'json'],
            'wg_keys': ['json']
        }
    
    def load_nodes_config(self, file_path: str) -> Dict[str, Any]:
        """
        Load nodes configuration from file.
        
        Args:
            file_path: Path to nodes configuration file
            
        Returns:
            Nodes configuration data
        """
        self._logger.info(f"Loading nodes configuration from: {file_path}")
        
        # Use existing loader
        nodes_list = load_nodes(file_path)
        
        # Convert to dict format expected by GUI
        return {'nodes': nodes_list}
    
    def load_topology_config(self, file_path: str) -> Dict[str, Any]:
        """
        Load topology configuration from file.
        
        Args:
            file_path: Path to topology configuration file
            
        Returns:
            Topology configuration data
        """
        self._logger.info(f"Loading topology configuration from: {file_path}")
        
        # Use existing loader
        peers_list = load_topology(file_path)
        
        # Convert to dict format expected by GUI
        return {'peers': peers_list}
    
    def load_group_config(self, file_path: str) -> Dict[str, Any]:
        """
        Load group configuration from file.
        
        Args:
            file_path: Path to group configuration file
            
        Returns:
            Group configuration data
        """
        self._logger.info(f"Loading group configuration from: {file_path}")
        
        # Load using existing utility
        config_data = load_config(file_path)
        
        # Validate structure
        if 'groups' not in config_data:
            raise ValueError("Invalid group configuration: missing 'groups' field")
        
        return config_data
    
    def save_configuration(self, app_state: IAppState, file_path: str, format: str = 'yaml') -> None:
        """
        Save the current configuration to file.
        
        Args:
            app_state: Application state to save
            file_path: Path to save configuration
            format: Output format ('yaml' or 'json')
        """
        self._logger.info(f"Saving configuration to: {file_path} (format: {format})")
        
        # Determine what type of configuration to save based on filename
        path = Path(file_path)
        filename = path.stem.lower()
        
        if 'node' in filename:
            data = self._export_nodes_config(app_state)
        elif 'topology' in filename or 'topo' in filename:
            data = self._export_topology_config(app_state)
        elif 'group' in filename:
            data = self._export_group_config(app_state)
        else:
            # Default to complete configuration
            data = self.export_configuration(app_state)
        
        # Save using existing utility
        if format == 'json':
            import json
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            save_yaml(data, file_path)
    
    def import_from_cli(self, app_state: IAppState, nodes_file: Optional[str] = None,
                       topology_file: Optional[str] = None, group_file: Optional[str] = None) -> None:
        """
        Import configuration from CLI format files.
        
        Args:
            app_state: Application state to populate
            nodes_file: Optional nodes configuration file
            topology_file: Optional topology configuration file
            group_file: Optional group configuration file
        """
        # Clear existing state
        app_state.nodes.clear()
        app_state.edges.clear()
        app_state.groups.clear()
        app_state.clear_selection()
        
        # Load group configuration if provided
        if group_file:
            self._import_group_config(app_state, group_file)
        
        # Load nodes if provided
        if nodes_file:
            self._import_nodes(app_state, nodes_file)
        
        # Load topology if provided
        if topology_file:
            self._import_topology(app_state, topology_file)
        
        # Mark state as clean after import
        app_state.mark_clean()
    
    def export_configuration(self, app_state: IAppState) -> Dict[str, Any]:
        """
        Export complete configuration from app state.
        
        Args:
            app_state: Application state to export
            
        Returns:
            Complete configuration data
        """
        return {
            'nodes': self._export_nodes_config(app_state),
            'topology': self._export_topology_config(app_state),
            'groups': self._export_group_config(app_state)
        }
    
    def merge_configurations(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two configurations.
        
        Args:
            base: Base configuration
            overlay: Configuration to overlay
            
        Returns:
            Merged configuration
        """
        # Deep merge logic
        merged = base.copy()
        
        for key, value in overlay.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursive merge for dicts
                merged[key] = self.merge_configurations(merged[key], value)
            elif key in merged and isinstance(merged[key], list) and isinstance(value, list):
                # For lists, we'll append (could be made smarter)
                merged[key] = merged[key] + value
            else:
                # Direct overlay
                merged[key] = value
        
        return merged
    
    def validate_configuration(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate a configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check structure
        if not isinstance(config, dict):
            errors.append("Configuration must be a dictionary")
            return errors
        
        # Validate nodes if present
        if 'nodes' in config:
            if not isinstance(config['nodes'], dict):
                errors.append("'nodes' must be a dictionary")
            else:
                nodes_data = config['nodes']
                if 'nodes' in nodes_data and isinstance(nodes_data['nodes'], list):
                    for i, node_data in enumerate(nodes_data['nodes']):
                        if 'name' not in node_data:
                            errors.append(f"Node {i} missing required 'name' field")
        
        # Validate topology if present
        if 'topology' in config:
            if not isinstance(config['topology'], dict):
                errors.append("'topology' must be a dictionary")
            else:
                topo_data = config['topology']
                if 'peers' in topo_data and isinstance(topo_data['peers'], list):
                    for i, peer_data in enumerate(topo_data['peers']):
                        if 'from' not in peer_data:
                            errors.append(f"Peer {i} missing required 'from' field")
                        if 'to' not in peer_data:
                            errors.append(f"Peer {i} missing required 'to' field")
        
        # Validate groups if present
        if 'groups' in config:
            if not isinstance(config['groups'], dict):
                errors.append("'groups' must be a dictionary")
            else:
                groups_data = config['groups']
                if 'groups' in groups_data and isinstance(groups_data['groups'], list):
                    for i, group_data in enumerate(groups_data['groups']):
                        if 'name' not in group_data:
                            errors.append(f"Group {i} missing required 'name' field")
                        if 'topology' not in group_data:
                            errors.append(f"Group {i} missing required 'topology' field")
        
        return errors
    
    def _import_nodes(self, app_state: IAppState, nodes_file: str) -> None:
        """Import nodes from CLI format."""
        nodes_list = load_nodes(nodes_file)
        
        for node_data in nodes_list:
            # Create NodeModel
            node = NodeModel(
                name=node_data['name'],
                role=node_data.get('role', 'client'),
                wireguard_ip=node_data.get('wireguard_ip')
            )
            
            # Handle endpoints
            endpoints = node_data.get('endpoints', {})
            if endpoints:
                # Take the first endpoint as primary
                for endpoint_name, endpoint_value in endpoints.items():
                    node.endpoint = endpoint_value
                    node.metadata['endpoint_name'] = endpoint_name
                    break
            
            # Add listen port if present
            if 'listen_port' in node_data:
                node.metadata['listen_port'] = node_data['listen_port']
            
            # Add to state
            app_state.add_node(node)
    
    def _import_topology(self, app_state: IAppState, topology_file: str) -> None:
        """Import topology from CLI format."""
        peers_list = load_topology(topology_file)
        
        # Create name to ID mapping
        name_to_id = {node.name: node.id for node in app_state.nodes.values()}
        
        for peer_data in peers_list:
            from_name = peer_data['from']
            to_name = peer_data['to']
            
            # Skip if nodes don't exist
            if from_name not in name_to_id or to_name not in name_to_id:
                self._logger.warning(f"Skipping peer {from_name} -> {to_name}: node not found")
                continue
            
            # Create EdgeModel
            edge = EdgeModel(
                source_id=name_to_id[from_name],
                target_id=name_to_id[to_name],
                allowed_ips=peer_data.get('allowed_ips', [])
            )
            
            # Add endpoint selection if present
            if 'endpoint' in peer_data:
                edge.metadata['endpoint_key'] = peer_data['endpoint']
            
            # Add to state
            app_state.add_edge(edge)
    
    def _import_group_config(self, app_state: IAppState, group_file: str) -> None:
        """Import group configuration."""
        config_data = load_config(group_file)
        groups_list = config_data.get('groups', [])
        
        # First pass: create all nodes from groups
        all_nodes = {}  # name -> node_data
        for group_data in groups_list:
            for node_name in group_data.get('nodes', []):
                if node_name not in all_nodes:
                    all_nodes[node_name] = {
                        'name': node_name,
                        'role': 'client',  # Default role
                        'groups': []
                    }
                all_nodes[node_name]['groups'].append(group_data['name'])
        
        # Create nodes
        name_to_id = {}
        for node_name, node_info in all_nodes.items():
            node = NodeModel(name=node_name, role=node_info['role'])
            app_state.add_node(node)
            name_to_id[node_name] = node.id
        
        # Create groups
        for group_data in groups_list:
            # Create GroupModel
            group = GroupModel(
                name=group_data['name'],
                topology=group_data['topology'],
                mesh_endpoint=group_data.get('endpoint')
            )
            
            # Set CLI compatibility flag
            group.metadata['cli_compatible'] = True
            
            # Add nodes to group
            for node_name in group_data.get('nodes', []):
                if node_name in name_to_id:
                    group.add_node(name_to_id[node_name])
            
            # Add to state
            app_state.add_group(group)
        
        # Build network from groups
        builder = GroupNetworkBuilder()
        expanded_config = builder.build_from_groups(config_data)
        
        # Import the expanded topology
        if 'peers' in expanded_config:
            for peer_data in expanded_config['peers']:
                from_name = peer_data['from']
                to_name = peer_data['to']
                
                if from_name in name_to_id and to_name in name_to_id:
                    edge = EdgeModel(
                        source_id=name_to_id[from_name],
                        target_id=name_to_id[to_name],
                        allowed_ips=peer_data.get('allowed_ips', [])
                    )
                    
                    if 'endpoint' in peer_data:
                        edge.metadata['endpoint_key'] = peer_data['endpoint']
                    
                    app_state.add_edge(edge)
    
    def _export_nodes_config(self, app_state: IAppState) -> Dict[str, Any]:
        """Export nodes to CLI format."""
        nodes_list = []
        
        for node in app_state.nodes.values():
            node_data = {
                'name': node.name,
                'role': node.role
            }
            
            # Add WireGuard IP if present
            if node.wireguard_ip:
                node_data['wireguard_ip'] = node.wireguard_ip
            
            # Add endpoint
            if node.endpoint:
                endpoint_name = node.metadata.get('endpoint_name', 'default')
                node_data['endpoints'] = {endpoint_name: node.endpoint}
            
            # Add listen port if present
            if 'listen_port' in node.metadata:
                node_data['listen_port'] = node.metadata['listen_port']
            
            nodes_list.append(node_data)
        
        return {'nodes': nodes_list}
    
    def _export_topology_config(self, app_state: IAppState) -> Dict[str, Any]:
        """Export topology to CLI format."""
        peers_list = []
        seen_pairs = set()
        
        for edge in app_state.edges.values():
            # Get node names
            source_node = app_state.nodes.get(edge.source_id)
            target_node = app_state.nodes.get(edge.target_id)
            
            if not source_node or not target_node:
                continue
            
            # Avoid duplicate edges (since GUI edges are directional but CLI peers are bidirectional)
            pair = tuple(sorted([source_node.name, target_node.name]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            
            peer_data = {
                'from': source_node.name,
                'to': target_node.name
            }
            
            # Add allowed IPs if present
            if edge.allowed_ips:
                peer_data['allowed_ips'] = edge.allowed_ips
            
            # Add endpoint selection if not default
            endpoint_key = edge.metadata.get('endpoint_key')
            if endpoint_key and endpoint_key != 'default':
                peer_data['endpoint'] = endpoint_key
            
            peers_list.append(peer_data)
        
        return {'peers': peers_list}
    
    def _export_group_config(self, app_state: IAppState) -> Dict[str, Any]:
        """Export groups to CLI format."""
        groups_list = []
        
        for group in app_state.groups.values():
            # Get node names
            node_names = []
            for node_id in group.nodes:
                node = app_state.nodes.get(node_id)
                if node:
                    node_names.append(node.name)
            
            group_data = {
                'name': group.name,
                'topology': group.topology,
                'nodes': node_names
            }
            
            # Add mesh endpoint if present
            if group.mesh_endpoint:
                group_data['endpoint'] = group.mesh_endpoint
            
            groups_list.append(group_data)
        
        return {'groups': groups_list} if groups_list else {}