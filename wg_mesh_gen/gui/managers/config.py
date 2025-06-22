"""
Configuration manager implementation for the GUI.

This module properly integrates with existing CLI functionality through adapters,
avoiding any duplication of code.
"""

from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

from ..interfaces.managers import IConfigManager
from ..interfaces.state import IAppState
from ..models import NodeModel, EdgeModel, GroupModel
from ..state import AppState
from ..adapters import CLIAdapter, ConfigAdapter, GroupAdapter

# Use existing logger from CLI
from ...logger import get_logger


class ConfigManager(IConfigManager):
    """
    Implementation of IConfigManager that uses CLI functionality through adapters.
    
    This avoids any duplication and ensures consistency with CLI behavior.
    """
    
    def __init__(self):
        """Initialize the configuration manager."""
        self._logger = get_logger()
        self.current_file: Optional[Path] = None
        self.has_unsaved_changes = False
        
        # Initialize adapters to reuse CLI functionality
        self.cli_adapter = CLIAdapter()
        self.config_adapter = ConfigAdapter(self.cli_adapter)
        self.group_adapter = GroupAdapter(self.cli_adapter)
    
    # File Format Support
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """Get supported file formats for each configuration type."""
        return {
            'nodes': ['yaml', 'yml', 'json'],
            'topology': ['yaml', 'yml', 'json'],
            'group': ['yaml', 'yml', 'json'],
            'wireguard': ['conf'],
            'keys': ['json']
        }
    
    # Main Load/Save Methods
    
    def load_configuration(self, file_path: Path) -> IAppState:
        """
        Load configuration from file using CLI loaders.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            Loaded application state
        """
        self._logger.info(f"Loading configuration from {file_path}")
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        # Use config adapter which properly uses CLI loaders
        state = self.config_adapter.load_complete_configuration(file_path)
        
        self.current_file = file_path
        self.has_unsaved_changes = False
        
        return state
    
    def save_configuration(self, state: IAppState, file_path: Optional[Path] = None) -> None:
        """
        Save configuration to file using CLI formats.
        
        Args:
            state: Application state to save
            file_path: Path to save to (uses current file if None)
        """
        if file_path is None:
            file_path = self.current_file
        
        if file_path is None:
            raise ValueError("No file path specified")
        
        self._logger.info(f"Saving configuration to {file_path}")
        
        # Detect file type to determine format
        file_type = self.config_adapter.detect_file_type(file_path) if file_path.exists() else None
        
        # Determine format based on filename if new file
        if file_type is None:
            if 'group' in file_path.name.lower():
                file_type = 'group'
            elif 'topo' in file_path.name.lower():
                file_type = 'topology'
            else:
                file_type = 'nodes'
        
        # Save appropriately
        if file_type == 'group':
            self.export_group_config(state, file_path)
        elif file_type == 'topology':
            nodes_file = file_path.parent / 'nodes.yaml'
            self.config_adapter.export_state_to_files(state, nodes_file, file_path)
        else:
            # Default to nodes file
            topo_file = file_path.parent / 'topology.yaml'
            self.config_adapter.export_state_to_files(state, file_path, topo_file)
        
        self.current_file = file_path
        self.has_unsaved_changes = False
    
    # Import Methods
    
    
    def import_nodes(self, file_path: Path) -> List[NodeModel]:
        """Import nodes from file using CLI loader."""
        return self.config_adapter.load_nodes_file(file_path)
    
    def import_topology(self, file_path: Path, nodes: Dict[str, NodeModel]) -> List[EdgeModel]:
        """Import topology from file using CLI loader."""
        edges = self.config_adapter.load_topology_file(file_path)
        
        # Update edge source/target IDs based on current node IDs
        name_to_id = {node.name: node.id for node in nodes.values()}
        
        for edge in edges:
            # Find source and target by name
            for node in nodes.values():
                if hasattr(edge, '_source_name') and node.name == edge._source_name:
                    edge.source_id = node.id
                if hasattr(edge, '_target_name') and node.name == edge._target_name:
                    edge.target_id = node.id
        
        return edges
    
    def import_group_config(self, file_path: Path) -> Tuple[List[NodeModel], List[EdgeModel], List[GroupModel]]:
        """Import group configuration using CLI GroupNetworkBuilder."""
        return self.config_adapter.load_group_configuration(file_path)
    
    def import_wireguard(self, conf_dir: Path) -> IAppState:
        """
        Import from existing WireGuard configurations.
        
        Note: This feature doesn't exist in CLI yet.
        """
        self._logger.warning("WireGuard config import not yet implemented")
        return AppState()
    
    # Export Methods
    
    def export_yaml(self, state: IAppState, file_path: Path) -> None:
        """Export configuration to YAML file."""
        nodes = list(state.nodes.values())
        edges = list(state.edges.values())
        
        # Determine what to export based on filename
        if 'topo' in file_path.name.lower():
            self.config_adapter.save_topology_file(edges, file_path)
        else:
            self.config_adapter.save_nodes_file(nodes, file_path)
    
    def export_json(self, state: IAppState, file_path: Path) -> None:
        """Export configuration to JSON file."""
        nodes = list(state.nodes.values())
        edges = list(state.edges.values())
        
        # Determine what to export based on filename
        if 'topo' in file_path.name.lower():
            self.config_adapter.save_topology_file(edges, file_path)
        else:
            self.config_adapter.save_nodes_file(nodes, file_path)
    
    def export_nodes(self, state: IAppState, file_path: Path) -> None:
        """Export nodes to file."""
        nodes = list(state.nodes.values())
        self.config_adapter.save_nodes_file(nodes, file_path)
    
    def export_topology(self, state: IAppState, file_path: Path) -> None:
        """Export topology to file."""
        edges = list(state.edges.values())
        self.config_adapter.save_topology_file(edges, file_path)
    
    def export_group_config(self, state: IAppState, file_path: Path) -> None:
        """Export group configuration."""
        groups = list(state.groups.values())
        
        # Extract connections from edges
        # This is a simplified version - a full implementation would analyze
        # edge metadata to reconstruct connection definitions
        connections = []
        
        group_config = self.group_adapter.build_group_configuration(groups, connections)
        
        if file_path.suffix in ['.yaml', '.yml']:
            self.config_adapter.save_yaml_file(group_config, file_path)
        else:
            self.config_adapter.save_json_file(group_config, file_path)
    
    def export_wireguard(self, state: IAppState, output_dir: Path) -> None:
        """Export to WireGuard configuration files using CLI renderer."""
        nodes = list(state.nodes.values())
        edges = list(state.edges.values())
        
        # Build configurations using CLI builder
        configs = self.cli_adapter.build_configurations(nodes, edges, use_smart_builder=True)
        
        # Render to files using CLI renderer
        output_files = self.cli_adapter.render_configurations(configs, output_dir)
        
        self._logger.info(f"Generated {len(output_files)} WireGuard configurations")
    
    # Configuration Generation
    
    def generate_wireguard_configs(self, state: IAppState, output_dir: Path) -> Dict[str, Path]:
        """
        Generate WireGuard configuration files using CLI functionality.
        
        Args:
            state: Application state
            output_dir: Directory to save configs to
            
        Returns:
            Dictionary mapping node names to file paths
        """
        nodes = list(state.nodes.values())
        edges = list(state.edges.values())
        
        # Build and render using CLI tools
        configs = self.cli_adapter.build_configurations(nodes, edges, use_smart_builder=True)
        return self.cli_adapter.render_configurations(configs, output_dir)
    
    # Validation
    
    def validate_configuration(self, state: IAppState) -> List[str]:
        """Validate configuration using CLI validators."""
        nodes = list(state.nodes.values())
        edges = list(state.edges.values())
        
        return self.cli_adapter.validate_configuration(nodes, edges)
    
    
    # Key Management
    
    def import_key_database(self, file_path: Path) -> Dict[str, Dict[str, str]]:
        """Import key database from file."""
        try:
            # Use config adapter to load JSON
            data = self.config_adapter.load_json_file(file_path)
            
            # Convert to expected format
            keys = {}
            for node_name, node_data in data.items():
                if isinstance(node_data, dict) and 'private_key' in node_data:
                    keys[node_name] = {
                        'private_key': node_data['private_key'],
                        'public_key': node_data.get('public_key', '')
                    }
            
            return keys
            
        except Exception as e:
            self._logger.error(f"Failed to import key database: {e}")
            return {}
    
    def export_key_database(self, keys: Dict[str, Dict[str, str]], file_path: Path) -> None:
        """Export key database to file."""
        try:
            self.config_adapter.save_json_file(keys, file_path)
        except Exception as e:
            self._logger.error(f"Failed to export key database: {e}")
    
    # Utility Methods
    
    def merge_configurations(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two configurations.
        
        Args:
            base: Base configuration
            overlay: Configuration to overlay
            
        Returns:
            Merged configuration
        """
        merged = base.copy()
        
        for key, value in overlay.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursive merge for dicts
                merged[key] = self.merge_configurations(merged[key], value)
            elif key in merged and isinstance(merged[key], list) and isinstance(value, list):
                # For lists, append unique items
                existing = set(str(item) for item in merged[key])
                for item in value:
                    if str(item) not in existing:
                        merged[key].append(item)
            else:
                # Direct overlay
                merged[key] = value
        
        return merged
    
    def get_configuration_type(self, file_path: Path) -> str:
        """Detect configuration file type."""
        return self.config_adapter.detect_file_type(file_path)
    
    def has_changes(self) -> bool:
        """Check if there are unsaved changes."""
        return self.has_unsaved_changes
    
    def mark_changed(self) -> None:
        """Mark that changes have been made."""
        self.has_unsaved_changes = True
    
    def get_current_file(self) -> Optional[Path]:
        """Get the current file path."""
        return self.current_file