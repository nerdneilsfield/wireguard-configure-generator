"""
Configuration adapter for file management and format conversion.

This adapter handles all configuration file operations using existing CLI functionality.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import logging

from ..interfaces.state import IAppState
from ..models import NodeModel, EdgeModel, GroupModel
from ..state import AppState

# Import existing CLI functionality
from ...loader import load_nodes, load_topology, validate_configuration
from ...group_network_builder import GroupNetworkBuilder

logger = logging.getLogger(__name__)


class ConfigAdapter:
    """
    Adapter for configuration file management.
    
    Uses existing CLI loaders and builders instead of reimplementing.
    """
    
    def __init__(self, cli_adapter):
        """
        Initialize configuration adapter.
        
        Args:
            cli_adapter: Instance of CLIAdapter for conversions
        """
        self.cli_adapter = cli_adapter
    
    def load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Load a YAML file using the same method as CLI.
        
        Args:
            file_path: Path to YAML file
            
        Returns:
            Loaded data dictionary
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Load a JSON file using the same method as CLI.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Loaded data dictionary
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_yaml_file(self, data: Dict[str, Any], file_path: Path) -> None:
        """
        Save data to YAML file.
        
        Args:
            data: Data to save
            file_path: Path to save to
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, 
                          default_flow_style=False, 
                          allow_unicode=True,
                          sort_keys=False)
    
    def save_json_file(self, data: Dict[str, Any], file_path: Path) -> None:
        """
        Save data to JSON file.
        
        Args:
            data: Data to save
            file_path: Path to save to
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def detect_file_type(self, file_path: Path) -> str:
        """
        Detect configuration file type.
        
        Args:
            file_path: Path to file
            
        Returns:
            'nodes', 'topology', 'group', or 'unknown'
        """
        try:
            # Load file content
            if file_path.suffix in ['.yaml', '.yml']:
                data = self.load_yaml_file(file_path)
            elif file_path.suffix == '.json':
                data = self.load_json_file(file_path)
            else:
                return 'unknown'
            
            # Detect type based on content
            if 'nodes' in data:
                return 'nodes'
            elif 'peers' in data:
                return 'topology'
            elif 'groups' in data and 'connections' in data:
                return 'group'
            else:
                return 'unknown'
                
        except Exception as e:
            logger.error(f"Error detecting file type: {e}")
            return 'unknown'
    
    def load_nodes_file(self, file_path: Path) -> List[NodeModel]:
        """
        Load nodes configuration file using CLI loader.
        
        Args:
            file_path: Path to nodes file
            
        Returns:
            List of NodeModel instances
        """
        # Use existing CLI loader
        cli_nodes = load_nodes(str(file_path))
        
        # Convert to GUI models
        return [self.cli_adapter.cli_node_to_model(node) for node in cli_nodes]
    
    def load_topology_file(self, file_path: Path) -> List[EdgeModel]:
        """
        Load topology configuration file using CLI loader.
        
        Args:
            file_path: Path to topology file
            
        Returns:
            List of EdgeModel instances
        """
        # Use existing CLI loader
        cli_topology = load_topology(str(file_path))
        cli_peers = cli_topology.get('peers', [])
        
        # Convert to GUI models
        return [self.cli_adapter.cli_peer_to_model(peer) for peer in cli_peers]
    
    def load_group_configuration(self, file_path: Path) -> Tuple[List[NodeModel], List[EdgeModel], List[GroupModel]]:
        """
        Load group configuration and expand using CLI GroupNetworkBuilder.
        
        Args:
            file_path: Path to group configuration file
            
        Returns:
            Tuple of (nodes, edges, groups)
        """
        # Load group configuration
        if file_path.suffix in ['.yaml', '.yml']:
            group_config = self.load_yaml_file(file_path)
        else:
            group_config = self.load_json_file(file_path)
        
        # Use existing GroupNetworkBuilder to expand
        builder = GroupNetworkBuilder(group_config)
        cli_nodes, cli_peers = builder.build()
        
        # Convert to GUI models
        node_models = [self.cli_adapter.cli_node_to_model(node) for node in cli_nodes]
        edge_models = [self.cli_adapter.cli_peer_to_model(peer) for peer in cli_peers]
        
        # Extract group information
        group_models = []
        for group_name, group_data in group_config.get('groups', {}).items():
            group = GroupModel(
                name=group_name,
                topology=group_data.get('topology', 'single'),
                mesh_endpoint=group_data.get('mesh_endpoint'),
                nodes=[node['name'] for node in cli_nodes 
                      if any(node['name'] == n for n in group_data.get('nodes', {}))]
            )
            group_models.append(group)
        
        return node_models, edge_models, group_models
    
    def save_nodes_file(self, nodes: List[NodeModel], file_path: Path) -> None:
        """
        Save nodes to configuration file.
        
        Args:
            nodes: List of node models
            file_path: Path to save to
        """
        # Convert to CLI format
        cli_nodes = [self.cli_adapter.node_model_to_cli(node) for node in nodes]
        nodes_config = {'nodes': cli_nodes}
        
        # Save based on extension
        if file_path.suffix in ['.yaml', '.yml']:
            self.save_yaml_file(nodes_config, file_path)
        else:
            self.save_json_file(nodes_config, file_path)
    
    def save_topology_file(self, edges: List[EdgeModel], file_path: Path) -> None:
        """
        Save topology to configuration file.
        
        Args:
            edges: List of edge models
            file_path: Path to save to
        """
        # Convert to CLI format
        cli_peers = [self.cli_adapter.edge_model_to_cli(edge) for edge in edges]
        topology_config = {'peers': cli_peers}
        
        # Save based on extension
        if file_path.suffix in ['.yaml', '.yml']:
            self.save_yaml_file(topology_config, file_path)
        else:
            self.save_json_file(topology_config, file_path)
    
    def load_complete_configuration(self, config_file: Path) -> IAppState:
        """
        Load a complete configuration file and create app state.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Populated app state
        """
        file_type = self.detect_file_type(config_file)
        
        if file_type == 'group':
            # Load group configuration
            nodes, edges, groups = self.load_group_configuration(config_file)
            
            # Create state
            state = AppState()
            for node in nodes:
                state.nodes[node.id] = node
            for edge in edges:
                state.edges[edge.id] = edge
            for group in groups:
                state.groups[group.id] = group
            
            return state
            
        elif file_type == 'nodes':
            # This is just a nodes file, need topology separately
            nodes = self.load_nodes_file(config_file)
            
            state = AppState()
            for node in nodes:
                state.nodes[node.id] = node
            
            return state
            
        elif file_type == 'topology':
            # This is just a topology file, need nodes separately
            edges = self.load_topology_file(config_file)
            
            state = AppState()
            for edge in edges:
                state.edges[edge.id] = edge
            
            return state
            
        else:
            raise ValueError(f"Unknown configuration file type: {config_file}")
    
    def validate_configuration_files(self, nodes_file: Path, topology_file: Path) -> List[str]:
        """
        Validate configuration files using CLI validator.
        
        Args:
            nodes_file: Path to nodes file
            topology_file: Path to topology file
            
        Returns:
            List of validation errors
        """
        # Use existing CLI validation
        return validate_configuration(str(nodes_file), str(topology_file))
    
    def export_state_to_files(self, state: IAppState, nodes_file: Path, topology_file: Path) -> None:
        """
        Export app state to configuration files.
        
        Args:
            state: Application state
            nodes_file: Path for nodes configuration
            topology_file: Path for topology configuration
        """
        # Extract models from state
        nodes = list(state.nodes.values())
        edges = list(state.edges.values())
        
        # Save files
        self.save_nodes_file(nodes, nodes_file)
        self.save_topology_file(edges, topology_file)