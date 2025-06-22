"""
Graph manager implementation for network topology operations.

This module provides graph operations, layout algorithms, and
network analysis capabilities.
"""

from typing import Dict, List, Tuple, Optional, Any, Set
import math
import random
from dataclasses import dataclass

from ..interfaces.managers import IGraphManager
from ..interfaces.state import IAppState
from ..interfaces.models import INodeModel, IEdgeModel, IGroupModel


@dataclass
class Position:
    """2D position for graph layout."""
    x: float
    y: float
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate distance to another position."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


class GraphManager(IGraphManager):
    """Implementation of IGraphManager for graph operations."""
    
    def __init__(self):
        """Initialize the graph manager."""
        self._layout_algorithms = {
            'force': self._force_directed_layout,
            'hierarchical': self._hierarchical_layout,
            'circular': self._circular_layout,
            'grid': self._grid_layout,
            'group': self._group_based_layout
        }
    
    def add_node(self, app_state: IAppState, node: INodeModel, position: Optional[Dict[str, float]] = None) -> None:
        """
        Add a node to the graph.
        
        Args:
            app_state: Application state
            node: Node to add
            position: Optional position {x, y}
        """
        # Add node to state
        app_state.add_node(node)
        
        # Set position if provided
        if position:
            node.metadata['position'] = position
        else:
            # Auto-position the node
            self._auto_position_node(app_state, node)
    
    def remove_node(self, app_state: IAppState, node_id: str) -> None:
        """
        Remove a node and its connections.
        
        Args:
            app_state: Application state
            node_id: ID of node to remove
        """
        # This will also remove connected edges
        app_state.remove_node(node_id)
    
    def add_edge(self, app_state: IAppState, edge: IEdgeModel) -> None:
        """
        Add an edge to the graph.
        
        Args:
            app_state: Application state
            edge: Edge to add
        """
        app_state.add_edge(edge)
    
    def remove_edge(self, app_state: IAppState, edge_id: str) -> None:
        """
        Remove an edge.
        
        Args:
            app_state: Application state
            edge_id: ID of edge to remove
        """
        app_state.remove_edge(edge_id)
    
    def get_connected_nodes(self, app_state: IAppState, node_id: str) -> List[str]:
        """
        Get all nodes connected to a specific node.
        
        Args:
            app_state: Application state
            node_id: ID of the node
            
        Returns:
            List of connected node IDs
        """
        connected = set()
        
        for edge in app_state.edges.values():
            if edge.source_id == node_id:
                connected.add(edge.target_id)
            elif edge.target_id == node_id:
                connected.add(edge.source_id)
        
        return list(connected)
    
    def get_node_edges(self, app_state: IAppState, node_id: str) -> List[IEdgeModel]:
        """
        Get all edges connected to a node.
        
        Args:
            app_state: Application state
            node_id: ID of the node
            
        Returns:
            List of connected edges
        """
        return app_state.get_edges_for_node(node_id)
    
    def apply_layout(self, app_state: IAppState, layout: str, options: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply a layout algorithm to the graph.
        
        Args:
            app_state: Application state
            layout: Layout algorithm name
            options: Layout-specific options
        """
        if layout not in self._layout_algorithms:
            raise ValueError(f"Unknown layout algorithm: {layout}")
        
        options = options or {}
        self._layout_algorithms[layout](app_state, options)
    
    def auto_layout(self, app_state: IAppState) -> None:
        """
        Automatically choose and apply the best layout.
        
        Args:
            app_state: Application state
        """
        # Choose layout based on graph characteristics
        node_count = len(app_state.nodes)
        edge_count = len(app_state.edges)
        has_groups = bool(app_state.groups)
        
        if has_groups:
            # Use group-based layout if groups exist
            self.apply_layout(app_state, 'group')
        elif node_count <= 10:
            # Small graphs look good with circular layout
            self.apply_layout(app_state, 'circular')
        elif edge_count < node_count * 1.5:
            # Sparse graphs work well with hierarchical
            self.apply_layout(app_state, 'hierarchical')
        else:
            # Default to force-directed for most cases
            self.apply_layout(app_state, 'force')
    
    def find_shortest_path(self, app_state: IAppState, source_id: str, target_id: str) -> Optional[List[str]]:
        """
        Find shortest path between two nodes.
        
        Args:
            app_state: Application state
            source_id: Source node ID
            target_id: Target node ID
            
        Returns:
            List of node IDs forming the path, or None if no path exists
        """
        if source_id not in app_state.nodes or target_id not in app_state.nodes:
            return None
        
        if source_id == target_id:
            return [source_id]
        
        # Build adjacency list
        adjacency = self._build_adjacency_list(app_state)
        
        # BFS to find shortest path
        queue = [(source_id, [source_id])]
        visited = {source_id}
        
        while queue:
            current, path = queue.pop(0)
            
            for neighbor in adjacency.get(current, []):
                if neighbor == target_id:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def get_node_degree(self, app_state: IAppState, node_id: str) -> int:
        """
        Get the degree of a node.
        
        Args:
            app_state: Application state
            node_id: Node ID
            
        Returns:
            Node degree (number of connections)
        """
        return len(self.get_connected_nodes(app_state, node_id))
    
    def _auto_position_node(self, app_state: IAppState, node: INodeModel) -> None:
        """
        Automatically position a new node.
        
        Args:
            app_state: Application state
            node: Node to position
        """
        # Get existing positions
        positions = []
        for other_node in app_state.nodes.values():
            if other_node.id != node.id and 'position' in other_node.metadata:
                pos = other_node.metadata['position']
                positions.append(Position(pos['x'], pos['y']))
        
        if not positions:
            # First node, place at center
            node.metadata['position'] = {'x': 400, 'y': 300}
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
                node.metadata['position'] = {'x': best_pos.x, 'y': best_pos.y}
            else:
                # Fallback: random position
                node.metadata['position'] = {
                    'x': random.randint(100, 700),
                    'y': random.randint(100, 500)
                }
    
    def _build_adjacency_list(self, app_state: IAppState) -> Dict[str, Set[str]]:
        """Build adjacency list from edges."""
        adjacency = {node_id: set() for node_id in app_state.nodes}
        
        for edge in app_state.edges.values():
            if edge.source_id in adjacency:
                adjacency[edge.source_id].add(edge.target_id)
            if edge.target_id in adjacency:
                adjacency[edge.target_id].add(edge.source_id)
        
        return adjacency
    
    def _force_directed_layout(self, app_state: IAppState, options: Dict[str, Any]) -> None:
        """
        Apply force-directed layout algorithm.
        
        Args:
            app_state: Application state
            options: Layout options
        """
        # Parameters
        iterations = options.get('iterations', 100)
        k = options.get('springConstant', 100)  # Ideal edge length
        c = options.get('repulsion', 10000)  # Repulsion constant
        damping = options.get('damping', 0.95)
        
        # Initialize positions randomly if not set
        nodes = list(app_state.nodes.values())
        positions = {}
        velocities = {}
        
        for node in nodes:
            if 'position' in node.metadata:
                pos = node.metadata['position']
                positions[node.id] = Position(pos['x'], pos['y'])
            else:
                positions[node.id] = Position(
                    random.uniform(100, 700),
                    random.uniform(100, 500)
                )
            velocities[node.id] = Position(0, 0)
        
        # Build adjacency for efficiency
        adjacency = self._build_adjacency_list(app_state)
        
        # Run iterations
        for _ in range(iterations):
            forces = {node_id: Position(0, 0) for node_id in positions}
            
            # Calculate repulsive forces between all nodes
            for i, node1 in enumerate(nodes):
                for j in range(i + 1, len(nodes)):
                    node2 = nodes[j]
                    
                    delta_x = positions[node2.id].x - positions[node1.id].x
                    delta_y = positions[node2.id].y - positions[node1.id].y
                    distance = math.sqrt(delta_x ** 2 + delta_y ** 2)
                    
                    if distance < 0.01:
                        distance = 0.01
                    
                    # Repulsive force
                    force = c / (distance ** 2)
                    fx = force * delta_x / distance
                    fy = force * delta_y / distance
                    
                    forces[node1.id].x -= fx
                    forces[node1.id].y -= fy
                    forces[node2.id].x += fx
                    forces[node2.id].y += fy
            
            # Calculate attractive forces along edges
            for edge in app_state.edges.values():
                if edge.source_id not in positions or edge.target_id not in positions:
                    continue
                
                delta_x = positions[edge.target_id].x - positions[edge.source_id].x
                delta_y = positions[edge.target_id].y - positions[edge.source_id].y
                distance = math.sqrt(delta_x ** 2 + delta_y ** 2)
                
                if distance < 0.01:
                    distance = 0.01
                
                # Attractive force (Hooke's law)
                force = (distance - k) / k
                fx = force * delta_x / distance
                fy = force * delta_y / distance
                
                forces[edge.source_id].x += fx
                forces[edge.source_id].y += fy
                forces[edge.target_id].x -= fx
                forces[edge.target_id].y -= fy
            
            # Update positions
            for node_id in positions:
                # Update velocity with damping
                velocities[node_id].x = (velocities[node_id].x + forces[node_id].x) * damping
                velocities[node_id].y = (velocities[node_id].y + forces[node_id].y) * damping
                
                # Update position
                positions[node_id].x += velocities[node_id].x
                positions[node_id].y += velocities[node_id].y
                
                # Keep within bounds
                positions[node_id].x = max(50, min(750, positions[node_id].x))
                positions[node_id].y = max(50, min(550, positions[node_id].y))
        
        # Apply final positions
        for node_id, pos in positions.items():
            if node_id in app_state.nodes:
                app_state.nodes[node_id].metadata['position'] = {'x': pos.x, 'y': pos.y}
    
    def _hierarchical_layout(self, app_state: IAppState, options: Dict[str, Any]) -> None:
        """
        Apply hierarchical layout algorithm.
        
        Args:
            app_state: Application state
            options: Layout options
        """
        # Parameters
        level_height = options.get('levelHeight', 100)
        node_spacing = options.get('nodeSpacing', 80)
        
        # Find root nodes (nodes with no incoming edges or relay nodes)
        adjacency = self._build_adjacency_list(app_state)
        incoming_edges = {node_id: 0 for node_id in app_state.nodes}
        
        for edge in app_state.edges.values():
            incoming_edges[edge.target_id] = incoming_edges.get(edge.target_id, 0) + 1
        
        # Start with relay nodes or nodes with no incoming edges
        roots = []
        for node_id, node in app_state.nodes.items():
            if node.role == 'relay' or incoming_edges[node_id] == 0:
                roots.append(node_id)
        
        if not roots:
            # No clear roots, pick node with most outgoing edges
            roots = [max(app_state.nodes.keys(), 
                        key=lambda n: len(adjacency.get(n, [])))]
        
        # Assign levels using BFS
        levels = {}
        visited = set()
        queue = [(root, 0) for root in roots]
        
        for root, level in queue:
            visited.add(root)
            levels[root] = level
        
        while queue:
            current, level = queue.pop(0)
            
            for neighbor in adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    levels[neighbor] = level + 1
                    queue.append((neighbor, level + 1))
        
        # Group nodes by level
        level_nodes = {}
        for node_id, level in levels.items():
            if level not in level_nodes:
                level_nodes[level] = []
            level_nodes[level].append(node_id)
        
        # Position nodes
        for level, nodes in level_nodes.items():
            y = 100 + level * level_height
            total_width = len(nodes) * node_spacing
            start_x = 400 - total_width / 2
            
            for i, node_id in enumerate(nodes):
                x = start_x + i * node_spacing
                app_state.nodes[node_id].metadata['position'] = {'x': x, 'y': y}
    
    def _circular_layout(self, app_state: IAppState, options: Dict[str, Any]) -> None:
        """
        Apply circular layout algorithm.
        
        Args:
            app_state: Application state
            options: Layout options
        """
        # Parameters
        center_x = options.get('centerX', 400)
        center_y = options.get('centerY', 300)
        radius = options.get('radius', 200)
        
        nodes = list(app_state.nodes.values())
        if not nodes:
            return
        
        # Calculate angle step
        angle_step = 2 * math.pi / len(nodes)
        
        # Position nodes in a circle
        for i, node in enumerate(nodes):
            angle = i * angle_step
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            node.metadata['position'] = {'x': x, 'y': y}
    
    def _grid_layout(self, app_state: IAppState, options: Dict[str, Any]) -> None:
        """
        Apply grid layout algorithm.
        
        Args:
            app_state: Application state
            options: Layout options
        """
        # Parameters
        cell_width = options.get('cellWidth', 120)
        cell_height = options.get('cellHeight', 100)
        start_x = options.get('startX', 100)
        start_y = options.get('startY', 100)
        
        nodes = list(app_state.nodes.values())
        if not nodes:
            return
        
        # Calculate grid dimensions
        cols = math.ceil(math.sqrt(len(nodes)))
        
        # Position nodes in grid
        for i, node in enumerate(nodes):
            row = i // cols
            col = i % cols
            x = start_x + col * cell_width
            y = start_y + row * cell_height
            node.metadata['position'] = {'x': x, 'y': y}
    
    def _group_based_layout(self, app_state: IAppState, options: Dict[str, Any]) -> None:
        """
        Apply group-based layout algorithm.
        
        Args:
            app_state: Application state
            options: Layout options
        """
        # First, layout groups
        group_positions = {}
        groups = list(app_state.groups.values())
        ungrouped_nodes = []
        
        # Identify ungrouped nodes
        grouped_node_ids = set()
        for group in groups:
            grouped_node_ids.update(group.nodes)
        
        for node_id, node in app_state.nodes.items():
            if node_id not in grouped_node_ids:
                ungrouped_nodes.append(node)
        
        # Layout groups in a circle
        if groups:
            group_radius = 250
            center_x = 400
            center_y = 300
            
            angle_step = 2 * math.pi / len(groups)
            for i, group in enumerate(groups):
                angle = i * angle_step
                x = center_x + group_radius * math.cos(angle)
                y = center_y + group_radius * math.sin(angle)
                group_positions[group.id] = Position(x, y)
        
        # Layout nodes within each group
        for group in groups:
            group_center = group_positions[group.id]
            group_nodes = [app_state.nodes[node_id] for node_id in group.nodes 
                          if node_id in app_state.nodes]
            
            if not group_nodes:
                continue
            
            # Layout based on group topology
            if group.topology == 'mesh' or group.topology == 'single':
                # Circular layout for mesh
                if len(group_nodes) == 1:
                    group_nodes[0].metadata['position'] = {
                        'x': group_center.x,
                        'y': group_center.y
                    }
                else:
                    radius = min(80, 200 / len(group_nodes))
                    angle_step = 2 * math.pi / len(group_nodes)
                    for i, node in enumerate(group_nodes):
                        angle = i * angle_step
                        x = group_center.x + radius * math.cos(angle)
                        y = group_center.y + radius * math.sin(angle)
                        node.metadata['position'] = {'x': x, 'y': y}
            
            elif group.topology == 'star':
                # Star layout - center node and periphery
                if group_nodes:
                    # Assume first node is center (could be improved)
                    center_node = group_nodes[0]
                    center_node.metadata['position'] = {
                        'x': group_center.x,
                        'y': group_center.y
                    }
                    
                    if len(group_nodes) > 1:
                        radius = 60
                        angle_step = 2 * math.pi / (len(group_nodes) - 1)
                        for i, node in enumerate(group_nodes[1:]):
                            angle = i * angle_step
                            x = group_center.x + radius * math.cos(angle)
                            y = group_center.y + radius * math.sin(angle)
                            node.metadata['position'] = {'x': x, 'y': y}
            
            elif group.topology == 'chain':
                # Linear layout for chain
                spacing = 50
                start_x = group_center.x - (len(group_nodes) - 1) * spacing / 2
                for i, node in enumerate(group_nodes):
                    x = start_x + i * spacing
                    y = group_center.y
                    node.metadata['position'] = {'x': x, 'y': y}
        
        # Layout ungrouped nodes
        if ungrouped_nodes:
            # Place ungrouped nodes at the bottom
            y = 500
            spacing = 100
            start_x = 400 - (len(ungrouped_nodes) - 1) * spacing / 2
            
            for i, node in enumerate(ungrouped_nodes):
                x = start_x + i * spacing
                node.metadata['position'] = {'x': x, 'y': y}