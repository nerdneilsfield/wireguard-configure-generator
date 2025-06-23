"""
Main adapter for integrating GUI with CLI functionality.

This adapter converts between GUI models and CLI formats, ensuring we reuse
existing CLI code instead of duplicating functionality.
"""

from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
import logging

from ..models import NodeModel, EdgeModel, GroupModel
from ..interfaces.models import INodeModel, IEdgeModel, IGroupModel

# Import existing CLI functionality
from ...loader import load_nodes, load_topology
from ...builder import build_from_data, build_peer_configs
from ...smart_builder import SmartConfigBuilder
from ...render import ConfigRenderer
from ...validator import validate_business_logic, validate_node_connectivity
from ...simple_storage import SimpleKeyStorage

logger = logging.getLogger(__name__)


class CLIAdapter:
    """
    Adapter that bridges GUI models with existing CLI functionality.
    
    This ensures we don't duplicate any CLI code and maintain consistency.
    """
    
    def __init__(self):
        """Initialize the CLI adapter."""
        self.key_storage = SimpleKeyStorage()
    
    # Model Conversion Methods
    
    def node_model_to_cli(self, node: INodeModel) -> Dict[str, Any]:
        """
        Convert a GUI NodeModel to CLI node format.
        
        Args:
            node: GUI node model
            
        Returns:
            CLI-compatible node dictionary
        """
        # Get base dictionary with cli_compatible flag
        node.metadata['cli_compatible'] = True
        cli_node = node.to_dict()
        
        # Ensure required CLI fields
        if 'wireguard_ip' in cli_node and 'ip' not in cli_node:
            cli_node['ip'] = cli_node['wireguard_ip']
        
        # Convert endpoints dict to list format if needed
        if isinstance(cli_node.get('endpoints'), dict):
            # CLI expects a list of endpoint strings
            endpoint_list = []
            for name, addr in cli_node['endpoints'].items():
                endpoint_list.append(addr)
            cli_node['endpoints'] = endpoint_list
        
        # Remove GUI-only fields
        gui_only_fields = ['id', 'created_at', 'updated_at', 'position', 'group_id', 'metadata']
        for field in gui_only_fields:
            cli_node.pop(field, None)
        
        return cli_node
    
    def edge_model_to_cli(self, edge: IEdgeModel) -> Dict[str, Any]:
        """
        Convert a GUI EdgeModel to CLI peer format.
        
        Args:
            edge: GUI edge model
            
        Returns:
            CLI-compatible peer dictionary
        """
        # Get base dictionary with cli_compatible flag
        edge.metadata['cli_compatible'] = True
        cli_peer = edge.to_dict()
        
        # Map to CLI field names
        field_mapping = {
            'source_id': 'from',
            'target_id': 'to',
            'endpoint_name': 'endpoint'
        }
        
        for gui_field, cli_field in field_mapping.items():
            if gui_field in cli_peer and cli_field not in cli_peer:
                cli_peer[cli_field] = cli_peer.pop(gui_field)
        
        # Remove GUI-only fields
        gui_only_fields = ['id', 'created_at', 'updated_at', 'edge_type', 'metadata']
        for field in gui_only_fields:
            cli_peer.pop(field, None)
        
        # Remove empty optional fields
        if not cli_peer.get('allowed_ips'):
            cli_peer.pop('allowed_ips', None)
        if not cli_peer.get('endpoint'):
            cli_peer.pop('endpoint', None)
        if not cli_peer.get('persistent_keepalive'):
            cli_peer.pop('persistent_keepalive', None)
        
        return cli_peer
    
    def cli_node_to_model(self, cli_node: Dict[str, Any]) -> NodeModel:
        """
        Convert a CLI node to GUI NodeModel.
        
        Args:
            cli_node: CLI node dictionary
            
        Returns:
            GUI NodeModel instance
        """
        # Map CLI fields to GUI fields
        if 'ip' in cli_node and 'wireguard_ip' not in cli_node:
            cli_node['wireguard_ip'] = cli_node.pop('ip')
        
        # Convert endpoints list to dict if needed
        if isinstance(cli_node.get('endpoints'), list):
            endpoint_dict = {}
            for i, endpoint in enumerate(cli_node['endpoints']):
                # Use default names for unnamed endpoints
                endpoint_dict[f'endpoint_{i}'] = endpoint
            cli_node['endpoints'] = endpoint_dict
        
        # Create and populate model
        model = NodeModel()
        model.from_dict(cli_node)
        return model
    
    def cli_peer_to_model(self, cli_peer: Dict[str, Any]) -> EdgeModel:
        """
        Convert a CLI peer to GUI EdgeModel.
        
        Args:
            cli_peer: CLI peer dictionary
            
        Returns:
            GUI EdgeModel instance
        """
        # Map CLI fields to GUI fields
        field_mapping = {
            'from': 'source_id',
            'to': 'target_id',
            'endpoint': 'endpoint_name'
        }
        
        for cli_field, gui_field in field_mapping.items():
            if cli_field in cli_peer and gui_field not in cli_peer:
                cli_peer[gui_field] = cli_peer.pop(cli_field)
        
        # Create and populate model
        model = EdgeModel()
        model.from_dict(cli_peer)
        return model
    
    # File Loading Methods
    
    def load_configuration_files(self, nodes_file: Path, 
                               topology_file: Path) -> Tuple[List[NodeModel], List[EdgeModel]]:
        """
        Load configuration files using CLI loaders.
        
        Args:
            nodes_file: Path to nodes configuration
            topology_file: Path to topology configuration
            
        Returns:
            Tuple of (node models, edge models)
        """
        # Use existing CLI loaders
        cli_nodes = load_nodes(str(nodes_file))
        cli_topology = load_topology(str(topology_file))
        
        # Extract peer list from topology
        cli_peers = cli_topology.get('peers', [])
        
        # Convert to GUI models
        node_models = [self.cli_node_to_model(node) for node in cli_nodes]
        edge_models = [self.cli_peer_to_model(peer) for peer in cli_peers]
        
        return node_models, edge_models
    
    # Configuration Building Methods
    
    def build_configurations(self, nodes: List[INodeModel], 
                           edges: List[IEdgeModel],
                           use_smart_builder: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Build WireGuard configurations using CLI builders.
        
        Args:
            nodes: List of node models
            edges: List of edge models
            use_smart_builder: Whether to use smart builder for optimization
            
        Returns:
            Dictionary mapping node names to their configurations
        """
        # Convert to CLI format
        cli_nodes = [self.node_model_to_cli(node) for node in nodes]
        cli_peers = [self.edge_model_to_cli(edge) for edge in edges]
        
        # Create CLI data structures
        nodes_data = {'nodes': cli_nodes}
        topology_data = {'peers': cli_peers}
        
        if use_smart_builder:
            # Use smart builder for optimization
            builder = SmartConfigBuilder(nodes_data, topology_data)
            return builder.build()
        else:
            # Use regular builder
            return build_from_data(nodes_data, topology_data)
    
    # Configuration Rendering Methods
    
    def render_configurations(self, configs: Dict[str, Dict[str, Any]], 
                            output_dir: Path) -> Dict[str, Path]:
        """
        Render WireGuard configuration files using CLI renderer.
        
        Args:
            configs: Configuration dictionary from builder
            output_dir: Directory to write configuration files
            
        Returns:
            Dictionary mapping node names to output file paths
        """
        renderer = ConfigRenderer()
        output_files = {}
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for node_name, config in configs.items():
            output_file = output_dir / f"{node_name}.conf"
            renderer.render_to_file(config, str(output_file))
            output_files[node_name] = output_file
        
        return output_files
    
    # Validation Methods
    
    def validate_configuration(self, nodes: List[INodeModel], 
                             edges: List[IEdgeModel]) -> List[str]:
        """
        Validate configuration using CLI validators.
        
        Args:
            nodes: List of node models
            edges: List of edge models
            
        Returns:
            List of validation error messages
        """
        # Convert to CLI format
        cli_nodes = [self.node_model_to_cli(node) for node in nodes]
        cli_peers = [self.edge_model_to_cli(edge) for edge in edges]
        
        errors = []
        
        # Use CLI business logic validation
        business_valid = validate_business_logic(cli_nodes, cli_peers)
        if not business_valid:
            errors.append("Business logic validation failed")
        
        # Use CLI connectivity validation  
        connectivity_result = validate_node_connectivity(cli_nodes, cli_peers)
        if isinstance(connectivity_result, dict):
            # Extract any error messages from connectivity analysis
            if 'errors' in connectivity_result:
                if isinstance(connectivity_result['errors'], list):
                    errors.extend(connectivity_result['errors'])
                elif connectivity_result['errors']:
                    errors.append(str(connectivity_result['errors']))
        
        return errors
    
    # Key Management Methods
    
    def get_or_generate_keys(self, node_name: str) -> Tuple[str, str]:
        """
        Get or generate keys for a node using CLI key storage.
        
        Args:
            node_name: Name of the node
            
        Returns:
            Tuple of (private_key, public_key)
        """
        return self.key_storage.get_or_generate_key(node_name)
    
    def list_keys(self) -> Dict[str, str]:
        """
        List all stored keys using CLI key storage.
        
        Returns:
            Dictionary mapping node names to public keys
        """
        return self.key_storage.list_keys()
    
    def delete_key(self, node_name: str) -> bool:
        """
        Delete keys for a node using CLI key storage.
        
        Args:
            node_name: Name of the node
            
        Returns:
            True if deleted, False if not found
        """
        return self.key_storage.delete_key(node_name)
    
    # Import/Export Methods
    
    def export_to_cli_format(self, nodes: List[INodeModel], 
                           edges: List[IEdgeModel]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Export GUI models to CLI configuration format.
        
        Args:
            nodes: List of node models
            edges: List of edge models
            
        Returns:
            Tuple of (nodes_config, topology_config) in CLI format
        """
        cli_nodes = [self.node_model_to_cli(node) for node in nodes]
        cli_peers = [self.edge_model_to_cli(edge) for edge in edges]
        
        nodes_config = {'nodes': cli_nodes}
        topology_config = {'peers': cli_peers}
        
        return nodes_config, topology_config
    
    def import_from_cli_format(self, nodes_config: Dict[str, Any], 
                             topology_config: Dict[str, Any]) -> Tuple[List[NodeModel], List[EdgeModel]]:
        """
        Import CLI configuration format to GUI models.
        
        Args:
            nodes_config: CLI nodes configuration
            topology_config: CLI topology configuration
            
        Returns:
            Tuple of (node models, edge models)
        """
        cli_nodes = nodes_config.get('nodes', [])
        cli_peers = topology_config.get('peers', [])
        
        node_models = [self.cli_node_to_model(node) for node in cli_nodes]
        edge_models = [self.cli_peer_to_model(peer) for peer in cli_peers]
        
        return node_models, edge_models