"""
Group configuration adapter for complex network topologies.

This adapter integrates with the existing GroupNetworkBuilder from CLI.
"""

from typing import Dict, List, Tuple, Any, Optional
import logging

from ..models import NodeModel, EdgeModel, GroupModel
from ..interfaces.models import INodeModel, IEdgeModel, IGroupModel

# Import existing CLI functionality
from ...group_network_builder import GroupNetworkBuilder

logger = logging.getLogger(__name__)


class GroupAdapter:
    """
    Adapter for group-based network configurations.
    
    Uses existing CLI GroupNetworkBuilder instead of reimplementing.
    """
    
    def __init__(self, cli_adapter):
        """
        Initialize group adapter.
        
        Args:
            cli_adapter: Instance of CLIAdapter for conversions
        """
        self.cli_adapter = cli_adapter
    
    def build_group_configuration(self, groups: List[IGroupModel], 
                                connections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a CLI-compatible group configuration from GUI models.
        
        Args:
            groups: List of group models
            connections: List of connection definitions
            
        Returns:
            CLI group configuration dictionary
        """
        group_config = {
            'groups': {},
            'connections': connections
        }
        
        # Convert each group
        for group in groups:
            group_data = {
                'nodes': {},
                'topology': group.topology
            }
            
            # Add optional fields
            if group.mesh_endpoint:
                group_data['mesh_endpoint'] = group.mesh_endpoint
            
            # Note: Node details will be filled by the builder
            # based on the actual node configurations
            
            group_config['groups'][group.name] = group_data
        
        return group_config
    
    def expand_group_topology(self, group: IGroupModel, 
                            nodes: Dict[str, INodeModel]) -> List[IEdgeModel]:
        """
        Expand a group's topology into edges using CLI logic.
        
        Args:
            group: Group model
            nodes: Dictionary of node ID to node model
            
        Returns:
            List of edges representing the group's topology
        """
        # Build a minimal group config for this single group
        group_nodes = {}
        for node_id in group.nodes:
            if node_id in nodes:
                node = nodes[node_id]
                cli_node = self.cli_adapter.node_model_to_cli(node)
                group_nodes[node.name] = {
                    'ip': cli_node.get('wireguard_ip', cli_node.get('ip')),
                    'endpoints': cli_node.get('endpoints', {}),
                    'is_relay': cli_node.get('role') == 'relay'
                }
        
        group_config = {
            'groups': {
                group.name: {
                    'nodes': group_nodes,
                    'topology': group.topology
                }
            },
            'connections': []
        }
        
        if group.mesh_endpoint:
            group_config['groups'][group.name]['mesh_endpoint'] = group.mesh_endpoint
        
        # Use GroupNetworkBuilder to expand
        try:
            builder = GroupNetworkBuilder(group_config)
            _, cli_peers = builder.build()
            
            # Convert CLI peers to edge models
            edges = []
            for cli_peer in cli_peers:
                edge = self.cli_adapter.cli_peer_to_model(cli_peer)
                edge.metadata['group_id'] = group.id
                edges.append(edge)
            
            return edges
            
        except Exception as e:
            logger.error(f"Error expanding group topology: {e}")
            return []
    
    def analyze_group_connections(self, groups: Dict[str, IGroupModel],
                                nodes: Dict[str, INodeModel],
                                connections: List[Dict[str, Any]]) -> List[IEdgeModel]:
        """
        Analyze inter-group connections using CLI logic.
        
        Args:
            groups: Dictionary of group ID to group model
            nodes: Dictionary of node ID to node model
            connections: List of connection definitions
            
        Returns:
            List of edges for inter-group connections
        """
        # Build complete group configuration
        group_config = {'groups': {}, 'connections': connections}
        
        # Build groups section
        for group in groups.values():
            group_nodes = {}
            for node_id in group.nodes:
                if node_id in nodes:
                    node = nodes[node_id]
                    cli_node = self.cli_adapter.node_model_to_cli(node)
                    group_nodes[node.name] = {
                        'ip': cli_node.get('wireguard_ip', cli_node.get('ip')),
                        'endpoints': cli_node.get('endpoints', {}),
                        'is_relay': cli_node.get('role') == 'relay'
                    }
            
            group_data = {
                'nodes': group_nodes,
                'topology': group.topology
            }
            
            if group.mesh_endpoint:
                group_data['mesh_endpoint'] = group.mesh_endpoint
            
            group_config['groups'][group.name] = group_data
        
        # Use GroupNetworkBuilder
        try:
            builder = GroupNetworkBuilder(group_config)
            _, cli_peers = builder.build()
            
            # Convert to edge models and mark inter-group connections
            edges = []
            for cli_peer in cli_peers:
                edge = self.cli_adapter.cli_peer_to_model(cli_peer)
                
                # Determine if this is an inter-group connection
                source_group = None
                target_group = None
                
                for group in groups.values():
                    for node_id in group.nodes:
                        node = nodes.get(node_id)
                        if node and node.name == cli_peer['from']:
                            source_group = group.id
                        if node and node.name == cli_peer['to']:
                            target_group = group.id
                
                if source_group and target_group and source_group != target_group:
                    edge.metadata['connection_type'] = 'inter-group'
                    edge.metadata['source_group'] = source_group
                    edge.metadata['target_group'] = target_group
                else:
                    edge.metadata['connection_type'] = 'intra-group'
                    edge.metadata['group_id'] = source_group or target_group
                
                edges.append(edge)
            
            return edges
            
        except Exception as e:
            logger.error(f"Error analyzing group connections: {e}")
            return []
    
    def suggest_hub_node(self, group: IGroupModel, nodes: Dict[str, INodeModel]) -> Optional[str]:
        """
        Suggest a hub node for star topology.
        
        Args:
            group: Group model
            nodes: Dictionary of node models
            
        Returns:
            Node ID of suggested hub, or None
        """
        # Prefer relay nodes as hubs
        relay_nodes = []
        client_nodes = []
        
        for node_id in group.nodes:
            node = nodes.get(node_id)
            if node:
                if node.role == 'relay':
                    relay_nodes.append(node_id)
                else:
                    client_nodes.append(node_id)
        
        # Return first relay node if available, otherwise first client
        if relay_nodes:
            return relay_nodes[0]
        elif client_nodes:
            return client_nodes[0]
        else:
            return None
    
    def validate_group_topology(self, group: IGroupModel, node_count: int) -> Optional[str]:
        """
        Validate if a topology is valid for the given node count.
        
        Args:
            group: Group model
            node_count: Number of nodes in the group
            
        Returns:
            Error message if invalid, None if valid
        """
        topology = group.topology
        
        if topology == 'single' and node_count != 1:
            return f"Single topology requires exactly 1 node, but has {node_count}"
        elif topology == 'mesh' and node_count < 2:
            return f"Mesh topology requires at least 2 nodes, but has {node_count}"
        elif topology == 'star' and node_count < 3:
            return f"Star topology requires at least 3 nodes, but has {node_count}"
        elif topology == 'chain' and node_count < 2:
            return f"Chain topology requires at least 2 nodes, but has {node_count}"
        
        return None
    
    def convert_to_node_edge_format(self, groups: List[IGroupModel],
                                  connections: List[Dict[str, Any]],
                                  existing_nodes: Dict[str, INodeModel]) -> Tuple[List[NodeModel], List[EdgeModel]]:
        """
        Convert group configuration to node/edge format using CLI builder.
        
        Args:
            groups: List of group models
            connections: List of connection definitions
            existing_nodes: Existing nodes to include in groups
            
        Returns:
            Tuple of (nodes, edges)
        """
        # Build group configuration
        group_config = self.build_group_configuration(groups, connections)
        
        # Add node details to groups
        for group in groups:
            group_nodes = {}
            for node_id in group.nodes:
                if node_id in existing_nodes:
                    node = existing_nodes[node_id]
                    cli_node = self.cli_adapter.node_model_to_cli(node)
                    group_nodes[node.name] = {
                        'ip': cli_node.get('wireguard_ip', cli_node.get('ip')),
                        'endpoints': cli_node.get('endpoints', {}),
                        'is_relay': cli_node.get('role') == 'relay'
                    }
            
            if group.name in group_config['groups']:
                group_config['groups'][group.name]['nodes'] = group_nodes
        
        # Use GroupNetworkBuilder
        builder = GroupNetworkBuilder(group_config)
        cli_nodes, cli_peers = builder.build()
        
        # Convert to GUI models
        node_models = [self.cli_adapter.cli_node_to_model(node) for node in cli_nodes]
        edge_models = [self.cli_adapter.cli_peer_to_model(peer) for peer in cli_peers]
        
        return node_models, edge_models