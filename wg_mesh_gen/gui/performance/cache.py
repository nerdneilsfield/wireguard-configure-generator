"""
Performance optimization and caching for GUI operations.

This module provides caching mechanisms to improve performance with large networks.
"""

import time
from typing import Dict, Any, Optional, List, Tuple, Callable
from functools import lru_cache
import hashlib
import json

from ...logger import get_logger


class GraphCache:
    """
    Cache for graph-related computations and rendering data.
    
    Improves performance for:
    - Layout calculations
    - Path finding
    - Subnet calculations
    - Rendering data
    """
    
    def __init__(self, ttl: int = 300):
        """
        Initialize graph cache.
        
        Args:
            ttl: Time-to-live for cache entries in seconds
        """
        self._logger = get_logger()
        self._ttl = ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._layout_cache: Dict[str, Any] = {}
        self._path_cache: Dict[str, Any] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                self._logger.debug(f"Cache hit for key: {key}")
                return value
            else:
                # Expired
                del self._cache[key]
                self._logger.debug(f"Cache expired for key: {key}")
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set cache value with current timestamp."""
        self._cache[key] = (value, time.time())
        self._logger.debug(f"Cache set for key: {key}")
    
    def invalidate(self, pattern: Optional[str] = None) -> None:
        """Invalidate cache entries matching pattern or all entries."""
        if pattern:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
            self._logger.info(f"Invalidated {len(keys_to_remove)} cache entries matching '{pattern}'")
        else:
            self._cache.clear()
            self._layout_cache.clear()
            self._path_cache.clear()
            self._logger.info("Invalidated all cache entries")
    
    @lru_cache(maxsize=128)
    def compute_layout_key(self, nodes: int, edges: int, layout_type: str) -> str:
        """Compute cache key for layout calculations."""
        return f"layout_{nodes}_{edges}_{layout_type}"
    
    def get_layout(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached layout positions."""
        return self._layout_cache.get(key)
    
    def set_layout(self, key: str, positions: Dict[str, Any]) -> None:
        """Cache layout positions."""
        self._layout_cache[key] = positions
    
    @lru_cache(maxsize=256)
    def compute_path_key(self, source: str, target: str) -> str:
        """Compute cache key for path calculations."""
        # Order doesn't matter for undirected paths
        nodes = sorted([source, target])
        return f"path_{nodes[0]}_{nodes[1]}"
    
    def get_path(self, source: str, target: str) -> Optional[List[str]]:
        """Get cached path between nodes."""
        key = self.compute_path_key(source, target)
        return self._path_cache.get(key)
    
    def set_path(self, source: str, target: str, path: List[str]) -> None:
        """Cache path between nodes."""
        key = self.compute_path_key(source, target)
        self._path_cache[key] = path


class RenderOptimizer:
    """
    Optimize rendering performance for large networks.
    
    Techniques:
    - Level-of-detail (LOD) rendering
    - Viewport culling
    - Batch updates
    - Progressive rendering
    """
    
    def __init__(self):
        """Initialize render optimizer."""
        self._logger = get_logger()
        self._batch_updates: List[Dict[str, Any]] = []
        self._batch_timeout: Optional[Any] = None
        self._lod_thresholds = {
            'high': 100,    # Full detail
            'medium': 500,  # Reduced detail
            'low': 1000     # Minimal detail
        }
    
    def get_render_options(self, element_count: int) -> Dict[str, Any]:
        """
        Get optimized render options based on element count.
        
        Args:
            element_count: Total number of nodes and edges
            
        Returns:
            Render options for Cytoscape
        """
        if element_count < self._lod_thresholds['high']:
            return {
                'textureOnViewport': False,
                'motionBlur': True,
                'motionBlurOpacity': 0.2,
                'pixelRatio': 'auto',
                'hideEdgesOnViewport': False,
                'hideLabelsOnViewport': False
            }
        elif element_count < self._lod_thresholds['medium']:
            return {
                'textureOnViewport': True,
                'motionBlur': False,
                'pixelRatio': 1,
                'hideEdgesOnViewport': False,
                'hideLabelsOnViewport': True
            }
        else:
            return {
                'textureOnViewport': True,
                'motionBlur': False,
                'pixelRatio': 1,
                'hideEdgesOnViewport': True,
                'hideLabelsOnViewport': True,
                'minZoom': 0.1,
                'maxZoom': 2
            }
    
    def get_style_options(self, element_count: int) -> List[Dict[str, Any]]:
        """Get optimized style options based on element count."""
        if element_count < self._lod_thresholds['high']:
            # Full detail styles
            return []
        elif element_count < self._lod_thresholds['medium']:
            # Simplified styles
            return [
                {
                    'selector': 'node',
                    'style': {
                        'width': 40,
                        'height': 40,
                        'font-size': 10
                    }
                },
                {
                    'selector': 'edge',
                    'style': {
                        'width': 2,
                        'curve-style': 'straight'  # Straight lines render faster
                    }
                }
            ]
        else:
            # Minimal styles
            return [
                {
                    'selector': 'node',
                    'style': {
                        'width': 20,
                        'height': 20,
                        'label': ''  # No labels
                    }
                },
                {
                    'selector': 'edge',
                    'style': {
                        'width': 1,
                        'curve-style': 'straight',
                        'target-arrow-shape': 'none'  # No arrows
                    }
                }
            ]
    
    def batch_update(self, update: Dict[str, Any], callback: Callable) -> None:
        """
        Batch multiple updates for efficient rendering.
        
        Args:
            update: Update operation to batch
            callback: Function to call with batched updates
        """
        self._batch_updates.append(update)
        
        # Cancel previous timeout
        if self._batch_timeout:
            self._batch_timeout.cancel()
        
        # Set new timeout for batch execution
        import threading
        self._batch_timeout = threading.Timer(0.05, lambda: self._execute_batch(callback))
        self._batch_timeout.start()
    
    def _execute_batch(self, callback: Callable) -> None:
        """Execute batched updates."""
        if self._batch_updates:
            updates = self._batch_updates.copy()
            self._batch_updates.clear()
            callback(updates)
            self._logger.debug(f"Executed batch of {len(updates)} updates")


class DataOptimizer:
    """
    Optimize data structures and queries for performance.
    
    Features:
    - Indexed lookups
    - Precomputed relationships
    - Efficient data structures
    """
    
    def __init__(self):
        """Initialize data optimizer."""
        self._logger = get_logger()
        self._node_index: Dict[str, Any] = {}
        self._edge_index: Dict[str, Any] = {}
        self._adjacency_list: Dict[str, set] = {}
        self._reverse_adjacency: Dict[str, set] = {}
    
    def build_indices(self, nodes: List[Any], edges: List[Any]) -> None:
        """
        Build optimized indices for fast lookups.
        
        Args:
            nodes: List of node objects
            edges: List of edge objects
        """
        start_time = time.time()
        
        # Clear existing indices
        self._node_index.clear()
        self._edge_index.clear()
        self._adjacency_list.clear()
        self._reverse_adjacency.clear()
        
        # Build node index
        for node in nodes:
            self._node_index[node.id] = node
            self._adjacency_list[node.id] = set()
            self._reverse_adjacency[node.id] = set()
        
        # Build edge index and adjacency lists
        for edge in edges:
            self._edge_index[edge.id] = edge
            
            # Forward adjacency
            if edge.source_id in self._adjacency_list:
                self._adjacency_list[edge.source_id].add(edge.target_id)
            
            # Reverse adjacency
            if edge.target_id in self._reverse_adjacency:
                self._reverse_adjacency[edge.target_id].add(edge.source_id)
        
        elapsed = time.time() - start_time
        self._logger.info(f"Built indices for {len(nodes)} nodes and {len(edges)} edges in {elapsed:.3f}s")
    
    def get_neighbors(self, node_id: str, direction: str = 'both') -> set:
        """
        Get neighbor nodes efficiently.
        
        Args:
            node_id: Node ID to get neighbors for
            direction: 'out', 'in', or 'both'
            
        Returns:
            Set of neighbor node IDs
        """
        if direction == 'out':
            return self._adjacency_list.get(node_id, set())
        elif direction == 'in':
            return self._reverse_adjacency.get(node_id, set())
        else:  # both
            out_neighbors = self._adjacency_list.get(node_id, set())
            in_neighbors = self._reverse_adjacency.get(node_id, set())
            return out_neighbors.union(in_neighbors)
    
    def get_degree(self, node_id: str, direction: str = 'both') -> int:
        """Get node degree efficiently."""
        return len(self.get_neighbors(node_id, direction))
    
    def find_connected_components(self) -> List[set]:
        """Find connected components efficiently using DFS."""
        visited = set()
        components = []
        
        for node_id in self._node_index:
            if node_id not in visited:
                component = set()
                self._dfs(node_id, visited, component)
                components.append(component)
        
        return components
    
    def _dfs(self, node_id: str, visited: set, component: set) -> None:
        """Depth-first search helper."""
        visited.add(node_id)
        component.add(node_id)
        
        for neighbor in self.get_neighbors(node_id):
            if neighbor not in visited:
                self._dfs(neighbor, visited, component)


# Global instances
graph_cache = GraphCache()
render_optimizer = RenderOptimizer()
data_optimizer = DataOptimizer()