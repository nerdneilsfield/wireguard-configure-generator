"""
Graph manager implementation for network topology operations.

This module properly integrates with existing CLI functionality through adapters
for graph operations, layout algorithms, and network analysis.
"""

from typing import Dict, List, Tuple, Optional, Any, Set
import math
import random
from dataclasses import dataclass
import networkx as nx
import logging

from ..interfaces.managers import IGraphManager
from ..interfaces.state import IAppState
from ..interfaces.models import INodeModel, IEdgeModel, IGroupModel
from ..models import NodeModel, EdgeModel, GroupModel
from ..adapters import CLIAdapter, GroupAdapter

# Use existing logger from CLI
from ...logger import get_logger

logger = get_logger()


@dataclass
class Position:
    """2D position for graph layout."""
    x: float
    y: float
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate distance to another position."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


class GraphManager(IGraphManager):
    """
    Implementation of IGraphManager that integrates with CLI functionality.
    
    Uses NetworkX for graph operations while maintaining compatibility with CLI.
    """
    
    def __init__(self):
        """Initialize the graph manager."""
        self.graph = nx.DiGraph()
        self._node_positions: Dict[str, Tuple[float, float]] = {}
        
        # Initialize adapters to reuse CLI functionality
        self.cli_adapter = CLIAdapter()
        self.group_adapter = GroupAdapter(self.cli_adapter)
        
        # Layout algorithms
        self._layout_algorithms = {
            'force': self._force_directed_layout,
            'hierarchical': self._hierarchical_layout,
            'circular': self._circular_layout,
            'grid': self._grid_layout,
            'group': self._group_based_layout
        }
    
    def add_node(self, state: IAppState, node: INodeModel, position: Optional[Dict[str, float]] = None) -> None:
        """Add a node to the graph."""
        # Add to state
        state.add_node(node)
        
        # Add to NetworkX graph
        self.graph.add_node(node.id, node=node)
        
        # Set position
        if position:
            node.position = position
            self._node_positions[node.id] = (position['x'], position['y'])
        else:
            # Auto-position
            self._auto_position_node(state, node)
    
    def remove_node(self, state: IAppState, node_id: str) -> None:
        """Remove a node from the graph."""
        # Remove from state (handles edges too)
        state.remove_node(node_id)
        
        # Remove from NetworkX graph
        if node_id in self.graph:
            self.graph.remove_node(node_id)
        
        # Remove position
        self._node_positions.pop(node_id, None)
    
    def add_edge(self, state: IAppState, edge: IEdgeModel) -> None:
        """Add an edge to the graph."""
        # Add to state
        state.add_edge(edge)
        
        # Add to NetworkX graph
        self.graph.add_edge(edge.source_id, edge.target_id, edge=edge)
    
    def remove_edge(self, state: IAppState, edge_id: str) -> None:
        """Remove an edge from the graph."""
        # Get edge to find source/target
        edge = state.edges.get(edge_id)
        if edge:
            # Remove from state
            state.remove_edge(edge_id)
            
            # Remove from NetworkX graph
            if self.graph.has_edge(edge.source_id, edge.target_id):
                self.graph.remove_edge(edge.source_id, edge.target_id)
    
    def get_connected_nodes(self, state: IAppState, node_id: str) -> List[str]:
        """Get all nodes connected to a specific node."""
        if node_id not in self.graph:
            return []
        
        # Get neighbors in both directions
        predecessors = list(self.graph.predecessors(node_id))
        successors = list(self.graph.successors(node_id))
        
        # Combine and deduplicate
        connected = list(set(predecessors + successors))
        return connected
    
    def get_node_edges(self, state: IAppState, node_id: str) -> List[IEdgeModel]:
        """Get all edges connected to a node."""
        return state.get_edges_for_node(node_id)
    
    def apply_layout(self, state: IAppState, layout: str, options: Optional[Dict[str, Any]] = None) -> None:
        """Apply a layout algorithm to the graph."""
        # Sync graph with state
        self._sync_with_state(state)
        
        if layout not in self._layout_algorithms:
            # Try NetworkX layouts
            try:
                self._apply_networkx_layout(state, layout, options)
            except:
                raise ValueError(f"Unknown layout algorithm: {layout}")
        else:
            # Use custom layout
            self._layout_algorithms[layout](state, options or {})
    
    def auto_layout(self, state: IAppState) -> None:
        """Automatically choose and apply the best layout."""
        node_count = len(state.nodes)
        edge_count = len(state.edges)
        has_groups = bool(state.groups)
        
        if has_groups:
            self.apply_layout(state, 'group')
        elif node_count <= 10:
            self.apply_layout(state, 'circular')
        elif edge_count < node_count * 1.5:
            self.apply_layout(state, 'hierarchical')
        else:
            self.apply_layout(state, 'force')
    
    def find_shortest_path(self, state: IAppState, source_id: str, target_id: str) -> Optional[List[str]]:
        """Find shortest path between two nodes."""
        self._sync_with_state(state)
        
        try:
            path = nx.shortest_path(self.graph, source_id, target_id)
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    
    def get_node_degree(self, state: IAppState, node_id: str) -> int:
        """Get the degree of a node."""
        self._sync_with_state(state)
        
        if node_id in self.graph:
            return self.graph.degree(node_id)
        return 0
    
    def analyze_topology(self, state: IAppState) -> Dict[str, Any]:
        """Analyze the network topology."""
        self._sync_with_state(state)
        
        # Basic metrics
        num_nodes = self.graph.number_of_nodes()
        num_edges = self.graph.number_of_edges()
        
        # Connectivity
        is_connected = nx.is_weakly_connected(self.graph) if num_nodes > 0 else True
        
        # Find isolated nodes
        isolated_nodes = list(nx.isolates(self.graph))
        
        # Node degree statistics
        in_degrees = dict(self.graph.in_degree())
        out_degrees = dict(self.graph.out_degree())
        
        # Average degree
        avg_degree = (sum(in_degrees.values()) + sum(out_degrees.values())) / (2 * num_nodes) if num_nodes > 0 else 0
        
        # Find relay nodes
        relay_nodes = [node for node in state.nodes.values() if node.role == 'relay']
        relay_names = [node.name for node in relay_nodes]
        
        # Clustering coefficient (for undirected version)
        undirected = self.graph.to_undirected()
        clustering_coeff = nx.average_clustering(undirected) if num_nodes > 0 else 0
        
        return {
            'num_nodes': num_nodes,
            'num_edges': num_edges,
            'is_connected': is_connected,
            'isolated_nodes': isolated_nodes,
            'average_degree': avg_degree,
            'relay_nodes': relay_names,
            'clustering_coefficient': clustering_coeff,
            'in_degrees': in_degrees,
            'out_degrees': out_degrees
        }
    
    def create_node(self, name: str, wireguard_ip: str, role: str = 'client', 
                   endpoints: Optional[Dict[str, str]] = None) -> INodeModel:
        """Factory method to create a new node."""
        node = NodeModel(
            name=name,
            wireguard_ip=wireguard_ip,
            role=role,
            endpoints=endpoints or {}
        )
        return node
    
    def create_edge(self, source_id: str, target_id: str, edge_type: str = 'peer',
                   allowed_ips: Optional[List[str]] = None) -> IEdgeModel:
        """Factory method to create a new edge."""
        edge = EdgeModel(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            allowed_ips=allowed_ips or []
        )
        return edge
    
    def create_group(self, name: str, topology: str = 'single', 
                    color: Optional[str] = None) -> IGroupModel:
        """Factory method to create a new group."""
        group = GroupModel(
            name=name,
            topology=topology,
            color=color or '#0080FF'
        )
        return group
    
    def apply_group_topology(self, group: IGroupModel, nodes: List[INodeModel]) -> List[IEdgeModel]:
        """Apply a topology pattern to a group of nodes using CLI functionality."""
        # Create a mapping of node IDs to nodes
        node_dict = {node.id: node for node in nodes}
        
        # Use group adapter to expand topology
        edges = self.group_adapter.expand_group_topology(group, node_dict)
        
        return edges
    
    def validate_topology(self, state: IAppState) -> List[str]:
        """Validate the current topology using CLI validators."""
        # Convert to lists for CLI adapter
        nodes = list(state.nodes.values())
        edges = list(state.edges.values())
        
        # Use CLI adapter for validation
        errors = self.cli_adapter.validate_configuration(nodes, edges)
        
        # Additional graph-specific validation
        self._sync_with_state(state)
        
        # Check for nodes with no path to relay nodes
        relay_nodes = [node_id for node_id, node in state.nodes.items() if node.role == 'relay']
        if relay_nodes:
            for node_id in self.graph.nodes():
                if node_id not in relay_nodes:
                    has_path = any(nx.has_path(self.graph, node_id, relay) for relay in relay_nodes)
                    if not has_path:
                        node_name = state.nodes[node_id].name if node_id in state.nodes else node_id
                        errors.append(f"Node '{node_name}' has no path to any relay node")
        
        return errors
    
    def find_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """Find shortest path between two nodes."""
        try:
            path = nx.shortest_path(self.graph, source_id, target_id)
            return path
        except nx.NetworkXNoPath:
            return None
        except nx.NodeNotFound:
            return None
    
    def get_subnet_conflicts(self, state: IAppState) -> List[Dict[str, Any]]:
        """Find subnet conflicts in the network."""
        conflicts = []
        nodes = list(state.nodes.values())
        
        # Check each pair of nodes for subnet conflicts
        for i, node1 in enumerate(nodes):
            for node2 in nodes[i+1:]:
                if node1.wireguard_ip and node2.wireguard_ip:
                    # Use validation manager's subnet overlap check
                    from .validation import ValidationManager
                    validator = ValidationManager()
                    if validator.check_subnet_overlaps(node1.wireguard_ip, node2.wireguard_ip):
                        conflicts.append({
                            'node1': node1.name,
                            'node1_ip': node1.wireguard_ip,
                            'node2': node2.name,
                            'node2_ip': node2.wireguard_ip
                        })
        
        return conflicts
    
    def suggest_ip_address(self, subnet: str, existing_ips: List[str]) -> Optional[str]:
        """Suggest an available IP address in a subnet."""
        import ipaddress
        
        try:
            network = ipaddress.ip_network(subnet, strict=False)
            
            # Convert existing IPs to set of addresses
            used_addresses = set()
            for ip in existing_ips:
                try:
                    if '/' in ip:
                        # It's a network, add the network address
                        addr = ipaddress.ip_interface(ip).ip
                    else:
                        addr = ipaddress.ip_address(ip)
                    used_addresses.add(addr)
                except ValueError:
                    continue
            
            # Find first available IP (skip network and broadcast)
            for addr in network.hosts():
                if addr not in used_addresses:
                    # Return with the same prefix length as the subnet
                    return f"{addr}/{network.prefixlen}"
            
            return None
            
        except ValueError:
            return None
    
    def _sync_with_state(self, state: IAppState) -> None:
        """Synchronize NetworkX graph with application state."""
        # Clear and rebuild graph
        self.graph.clear()
        
        # Add nodes
        for node_id, node in state.nodes.items():
            self.graph.add_node(node_id, node=node)
        
        # Add edges
        for edge_id, edge in state.edges.items():
            if edge.source_id in self.graph and edge.target_id in self.graph:
                self.graph.add_edge(edge.source_id, edge.target_id, edge=edge)
    
    def _auto_position_node(self, state: IAppState, node: INodeModel) -> None:
        """Automatically position a new node."""
        # Get existing positions
        positions = []
        for other_node in state.nodes.values():
            if other_node.id != node.id and hasattr(other_node, 'position') and other_node.position:
                pos = other_node.position
                positions.append(Position(pos['x'], pos['y']))
        
        if not positions:
            # First node, place at center
            node.position = {'x': 400, 'y': 300}
        else:
            # Find a good position away from existing nodes
            center_x = sum(p.x for p in positions) / len(positions)
            center_y = sum(p.y for p in positions) / len(positions)
            
            # Try positions in a circle around the center
            best_pos = None
            best_min_dist = 0
            
            for angle in range(0, 360, 30):
                rad = math.radians(angle)
                x = center_x + 150 * math.cos(rad)
                y = center_y + 150 * math.sin(rad)
                test_pos = Position(x, y)
                
                # Find minimum distance to existing nodes
                min_dist = min(test_pos.distance_to(p) for p in positions)
                
                if min_dist > best_min_dist:
                    best_min_dist = min_dist
                    best_pos = test_pos
            
            if best_pos:
                node.position = {'x': best_pos.x, 'y': best_pos.y}
            else:
                # Fallback: random position
                node.position = {
                    'x': random.randint(100, 700),
                    'y': random.randint(100, 500)
                }
    
    def _apply_networkx_layout(self, state: IAppState, layout: str, options: Optional[Dict[str, Any]] = None) -> None:
        """Apply NetworkX layout algorithm."""
        self._sync_with_state(state)
        
        # Map layout names to NetworkX functions
        layout_funcs = {
            'spring': nx.spring_layout,
            'kamada_kawai': nx.kamada_kawai_layout,
            'spectral': nx.spectral_layout,
            'shell': nx.shell_layout,
            'random': nx.random_layout
        }
        
        if layout not in layout_funcs:
            raise ValueError(f"Unknown NetworkX layout: {layout}")
        
        # Apply layout
        pos = layout_funcs[layout](self.graph)
        
        # Scale positions to canvas size
        if pos:
            # Find bounds
            x_values = [p[0] for p in pos.values()]
            y_values = [p[1] for p in pos.values()]
            
            min_x, max_x = min(x_values), max(x_values)
            min_y, max_y = min(y_values), max(y_values)
            
            # Scale to canvas (with margins)
            canvas_width = 700
            canvas_height = 500
            margin = 50
            
            for node_id, (x, y) in pos.items():
                # Normalize to [0, 1]
                norm_x = (x - min_x) / (max_x - min_x) if max_x > min_x else 0.5
                norm_y = (y - min_y) / (max_y - min_y) if max_y > min_y else 0.5
                
                # Scale to canvas
                scaled_x = margin + norm_x * (canvas_width - 2 * margin)
                scaled_y = margin + norm_y * (canvas_height - 2 * margin)
                
                # Update node position
                if node_id in state.nodes:
                    state.nodes[node_id].position = {'x': scaled_x, 'y': scaled_y}
    
    # Layout algorithms (simplified versions of the original implementations)
    
    def _force_directed_layout(self, state: IAppState, options: Dict[str, Any]) -> None:
        """Apply force-directed layout using NetworkX."""
        self._apply_networkx_layout(state, 'spring', options)
    
    def _hierarchical_layout(self, state: IAppState, options: Dict[str, Any]) -> None:
        """Apply hierarchical layout."""
        self._sync_with_state(state)
        
        # Find roots (relay nodes or nodes with no incoming edges)
        roots = []
        for node_id, node in state.nodes.items():
            if node.role == 'relay':
                roots.append(node_id)
            elif self.graph.in_degree(node_id) == 0:
                roots.append(node_id)
        
        if not roots and state.nodes:
            # Pick node with highest out-degree
            roots = [max(state.nodes.keys(), 
                        key=lambda n: self.graph.out_degree(n))]
        
        # Use NetworkX hierarchical layout
        try:
            # Create a tree from the graph for better layout
            if roots:
                tree = nx.bfs_tree(self.graph, roots[0])
                pos = nx.nx_agraph.graphviz_layout(tree, prog='dot')
                
                # Apply positions
                for node_id, (x, y) in pos.items():
                    if node_id in state.nodes:
                        state.nodes[node_id].position = {'x': x, 'y': y}
        except:
            # Fallback to spring layout
            self._force_directed_layout(state, options)
    
    def _circular_layout(self, state: IAppState, options: Dict[str, Any]) -> None:
        """Apply circular layout."""
        center_x = options.get('centerX', 400)
        center_y = options.get('centerY', 300)
        radius = options.get('radius', 200)
        
        nodes = list(state.nodes.values())
        if not nodes:
            return
        
        angle_step = 2 * math.pi / len(nodes)
        
        for i, node in enumerate(nodes):
            angle = i * angle_step
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            node.position = {'x': x, 'y': y}
    
    def _grid_layout(self, state: IAppState, options: Dict[str, Any]) -> None:
        """Apply grid layout."""
        cell_width = options.get('cellWidth', 120)
        cell_height = options.get('cellHeight', 100)
        start_x = options.get('startX', 100)
        start_y = options.get('startY', 100)
        
        nodes = list(state.nodes.values())
        if not nodes:
            return
        
        cols = math.ceil(math.sqrt(len(nodes)))
        
        for i, node in enumerate(nodes):
            row = i // cols
            col = i % cols
            x = start_x + col * cell_width
            y = start_y + row * cell_height
            node.position = {'x': x, 'y': y}
    
    def _group_based_layout(self, state: IAppState, options: Dict[str, Any]) -> None:
        """Apply group-based layout."""
        # Layout groups in a circle
        groups = list(state.groups.values())
        if not groups:
            # No groups, fall back to force-directed
            self._force_directed_layout(state, options)
            return
        
        group_positions = {}
        center_x = 400
        center_y = 300
        group_radius = 250
        
        angle_step = 2 * math.pi / len(groups)
        for i, group in enumerate(groups):
            angle = i * angle_step
            x = center_x + group_radius * math.cos(angle)
            y = center_y + group_radius * math.sin(angle)
            group_positions[group.id] = Position(x, y)
        
        # Layout nodes within groups
        for group in groups:
            group_center = group_positions[group.id]
            group_nodes = [state.nodes[nid] for nid in group.nodes if nid in state.nodes]
            
            if not group_nodes:
                continue
            
            # Apply sub-layout based on topology
            if group.topology == 'mesh' or len(group_nodes) == 1:
                # Circular sub-layout
                if len(group_nodes) == 1:
                    group_nodes[0].position = {'x': group_center.x, 'y': group_center.y}
                else:
                    radius = min(80, 150 / len(group_nodes))
                    angle_step = 2 * math.pi / len(group_nodes)
                    for i, node in enumerate(group_nodes):
                        angle = i * angle_step
                        x = group_center.x + radius * math.cos(angle)
                        y = group_center.y + radius * math.sin(angle)
                        node.position = {'x': x, 'y': y}
            
            elif group.topology == 'star':
                # Star sub-layout
                if group_nodes:
                    # Find relay node or use first
                    center_node = next((n for n in group_nodes if n.role == 'relay'), group_nodes[0])
                    center_node.position = {'x': group_center.x, 'y': group_center.y}
                    
                    other_nodes = [n for n in group_nodes if n.id != center_node.id]
                    if other_nodes:
                        radius = 60
                        angle_step = 2 * math.pi / len(other_nodes)
                        for i, node in enumerate(other_nodes):
                            angle = i * angle_step
                            x = group_center.x + radius * math.cos(angle)
                            y = group_center.y + radius * math.sin(angle)
                            node.position = {'x': x, 'y': y}
            
            elif group.topology == 'chain':
                # Linear sub-layout
                spacing = 50
                start_x = group_center.x - (len(group_nodes) - 1) * spacing / 2
                for i, node in enumerate(group_nodes):
                    x = start_x + i * spacing
                    y = group_center.y
                    node.position = {'x': x, 'y': y}
        
        # Layout ungrouped nodes
        grouped_ids = set()
        for group in groups:
            grouped_ids.update(group.nodes)
        
        ungrouped = [n for n in state.nodes.values() if n.id not in grouped_ids]
        if ungrouped:
            # Place at bottom
            y = 500
            spacing = 100
            start_x = 400 - (len(ungrouped) - 1) * spacing / 2
            
            for i, node in enumerate(ungrouped):
                x = start_x + i * spacing
                node.position = {'x': x, 'y': y}