"""
Application state implementation for the GUI.
"""

from typing import Dict, List, Set, Optional, Callable, Any
from collections import defaultdict
import time

from ..interfaces.state import IAppState, IHistoryManager
from ..interfaces.models import INodeModel, IEdgeModel, IGroupModel
from ..interfaces.events import Event
from ..models import NodeModel, EdgeModel, GroupModel
from .history import HistoryManager


class AppState(IAppState):
    """Implementation of IAppState for managing application state."""
    
    def __init__(self, history_manager: Optional[IHistoryManager] = None):
        """
        Initialize application state.
        
        Args:
            history_manager: Optional history manager instance
        """
        self._nodes: Dict[str, INodeModel] = {}
        self._edges: Dict[str, IEdgeModel] = {}
        self._groups: Dict[str, IGroupModel] = {}
        self._selected_elements: Set[str] = set()
        self._history = history_manager or HistoryManager()
        self._is_dirty = False
        self._current_file: Optional[str] = None
        
        # Event system
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
    
    @property
    def nodes(self) -> Dict[str, INodeModel]:
        """Get all nodes."""
        return self._nodes
    
    @property
    def edges(self) -> Dict[str, IEdgeModel]:
        """Get all edges."""
        return self._edges
    
    @property
    def groups(self) -> Dict[str, IGroupModel]:
        """Get all groups."""
        return self._groups
    
    @property
    def selected_elements(self) -> Set[str]:
        """Get selected element IDs."""
        return self._selected_elements.copy()
    
    @property
    def history(self) -> IHistoryManager:
        """Get history manager."""
        return self._history
    
    @property
    def is_dirty(self) -> bool:
        """Check if state has unsaved changes."""
        return self._is_dirty
    
    @property
    def current_file(self) -> Optional[str]:
        """Get current file path."""
        return self._current_file
    
    @current_file.setter
    def current_file(self, value: Optional[str]) -> None:
        """Set current file path."""
        self._current_file = value
    
    def add_node(self, node: INodeModel) -> None:
        """
        Add a node to the state.
        
        Args:
            node: Node to add
        """
        if node.id in self._nodes:
            raise ValueError(f"Node with ID '{node.id}' already exists")
        
        self._nodes[node.id] = node
        self._is_dirty = True
        
        # Emit event
        self._emit_event('node_added', {'node': node})
    
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> None:
        """
        Update a node's properties.
        
        Args:
            node_id: ID of the node to update
            updates: Dictionary of properties to update
        """
        node = self._nodes.get(node_id)
        if not node:
            raise ValueError(f"Node '{node_id}' not found")
        
        # Apply updates
        node.update(updates)
        self._is_dirty = True
        
        # Emit event
        self._emit_event('node_updated', {'node_id': node_id, 'updates': updates})
    
    def remove_node(self, node_id: str) -> None:
        """
        Remove a node and all connected edges.
        
        Args:
            node_id: ID of the node to remove
        """
        node = self._nodes.get(node_id)
        if not node:
            raise ValueError(f"Node '{node_id}' not found")
        
        # Remove from any group
        if node.group_id:
            group = self._groups.get(node.group_id)
            if group and group.has_node(node_id):
                group.remove_node(node_id)
        
        # Remove connected edges
        edges_to_remove = []
        for edge_id, edge in self._edges.items():
            if edge.source_id == node_id or edge.target_id == node_id:
                edges_to_remove.append(edge_id)
        
        for edge_id in edges_to_remove:
            del self._edges[edge_id]
            self._emit_event('edge_removed', {'edge_id': edge_id})
        
        # Remove from selection
        self._selected_elements.discard(node_id)
        
        # Remove node
        del self._nodes[node_id]
        self._is_dirty = True
        
        # Emit event
        self._emit_event('node_removed', {'node_id': node_id})
    
    def add_edge(self, edge: IEdgeModel) -> None:
        """
        Add an edge to the state.
        
        Args:
            edge: Edge to add
        """
        if edge.id in self._edges:
            raise ValueError(f"Edge with ID '{edge.id}' already exists")
        
        # Verify nodes exist
        if edge.source_id not in self._nodes:
            raise ValueError(f"Source node '{edge.source_id}' not found")
        if edge.target_id not in self._nodes:
            raise ValueError(f"Target node '{edge.target_id}' not found")
        
        self._edges[edge.id] = edge
        self._is_dirty = True
        
        # Emit event
        self._emit_event('edge_added', {'edge': edge})
    
    def update_edge(self, edge_id: str, updates: Dict[str, Any]) -> None:
        """
        Update an edge's properties.
        
        Args:
            edge_id: ID of the edge to update
            updates: Dictionary of properties to update
        """
        edge = self._edges.get(edge_id)
        if not edge:
            raise ValueError(f"Edge '{edge_id}' not found")
        
        # Apply updates
        edge.update(updates)
        self._is_dirty = True
        
        # Emit event
        self._emit_event('edge_updated', {'edge_id': edge_id, 'updates': updates})
    
    def remove_edge(self, edge_id: str) -> None:
        """
        Remove an edge.
        
        Args:
            edge_id: ID of the edge to remove
        """
        if edge_id not in self._edges:
            raise ValueError(f"Edge '{edge_id}' not found")
        
        # Remove from selection
        self._selected_elements.discard(edge_id)
        
        # Remove edge
        del self._edges[edge_id]
        self._is_dirty = True
        
        # Emit event
        self._emit_event('edge_removed', {'edge_id': edge_id})
    
    def add_group(self, group: IGroupModel) -> None:
        """
        Add a group to the state.
        
        Args:
            group: Group to add
        """
        if group.id in self._groups:
            raise ValueError(f"Group with ID '{group.id}' already exists")
        
        self._groups[group.id] = group
        self._is_dirty = True
        
        # Update nodes that are in this group
        for node_id in group.nodes:
            if node_id in self._nodes:
                self._nodes[node_id].group_id = group.id
        
        # Emit event
        self._emit_event('group_added', {'group': group})
    
    def update_group(self, group_id: str, updates: Dict[str, Any]) -> None:
        """
        Update a group's properties.
        
        Args:
            group_id: ID of the group to update
            updates: Dictionary of properties to update
        """
        group = self._groups.get(group_id)
        if not group:
            raise ValueError(f"Group '{group_id}' not found")
        
        # Apply updates
        group.update(updates)
        self._is_dirty = True
        
        # Emit event
        self._emit_event('group_updated', {'group_id': group_id, 'updates': updates})
    
    def remove_group(self, group_id: str) -> None:
        """
        Remove a group and unassign all nodes.
        
        Args:
            group_id: ID of the group to remove
        """
        group = self._groups.get(group_id)
        if not group:
            raise ValueError(f"Group '{group_id}' not found")
        
        # Unassign nodes
        for node_id in group.nodes:
            if node_id in self._nodes:
                self._nodes[node_id].group_id = None
        
        # Remove from selection
        self._selected_elements.discard(group_id)
        
        # Remove group
        del self._groups[group_id]
        self._is_dirty = True
        
        # Emit event
        self._emit_event('group_removed', {'group_id': group_id})
    
    def select_element(self, element_id: str) -> None:
        """Add an element to selection."""
        # Verify element exists
        if (element_id not in self._nodes and 
            element_id not in self._edges and 
            element_id not in self._groups):
            raise ValueError(f"Element '{element_id}' not found")
        
        self._selected_elements.add(element_id)
        self._emit_event('selection_changed', {'selected': list(self._selected_elements)})
    
    def deselect_element(self, element_id: str) -> None:
        """Remove an element from selection."""
        self._selected_elements.discard(element_id)
        self._emit_event('selection_changed', {'selected': list(self._selected_elements)})
    
    def clear_selection(self) -> None:
        """Clear all selected elements."""
        self._selected_elements.clear()
        self._emit_event('selection_changed', {'selected': []})
    
    def set_selection(self, element_ids: Set[str]) -> None:
        """Set the selection to specific elements."""
        # Verify all elements exist
        for element_id in element_ids:
            if (element_id not in self._nodes and 
                element_id not in self._edges and 
                element_id not in self._groups):
                raise ValueError(f"Element '{element_id}' not found")
        
        self._selected_elements = element_ids.copy()
        self._emit_event('selection_changed', {'selected': list(self._selected_elements)})
    
    def mark_clean(self) -> None:
        """Mark the state as having no unsaved changes."""
        self._is_dirty = False
        self._emit_event('state_cleaned', {})
    
    def subscribe(self, event: str, handler: Callable) -> None:
        """
        Subscribe to state change events.
        
        Args:
            event: Event name (e.g., 'node_added', 'edge_updated')
            handler: Callback function
        """
        self._event_handlers[event].append(handler)
    
    def unsubscribe(self, event: str, handler: Callable) -> None:
        """
        Unsubscribe from state change events.
        
        Args:
            event: Event name
            handler: Callback function to remove
        """
        if event in self._event_handlers and handler in self._event_handlers[event]:
            self._event_handlers[event].remove(handler)
    
    def get_edges_for_node(self, node_id: str) -> List[IEdgeModel]:
        """
        Get all edges connected to a node.
        
        Args:
            node_id: ID of the node
            
        Returns:
            List of connected edges
        """
        edges = []
        for edge in self._edges.values():
            if edge.source_id == node_id or edge.target_id == node_id:
                edges.append(edge)
        return edges
    
    def get_nodes_in_group(self, group_id: str) -> List[INodeModel]:
        """
        Get all nodes in a group.
        
        Args:
            group_id: ID of the group
            
        Returns:
            List of nodes in the group
        """
        group = self._groups.get(group_id)
        if not group:
            return []
        
        nodes = []
        for node_id in group.nodes:
            node = self._nodes.get(node_id)
            if node:
                nodes.append(node)
        return nodes
    
    def _emit_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """
        Emit an event to all registered handlers.
        
        Args:
            event_name: Name of the event
            data: Event data
        """
        event = Event(
            name=event_name,
            source=self,
            data=data,
            timestamp=time.time()
        )
        
        # Call handlers
        for handler in self._event_handlers.get(event_name, []):
            try:
                handler(event)
            except Exception as e:
                # Log error but don't stop other handlers
                print(f"Error in event handler for '{event_name}': {str(e)}")
    
    def validate_state(self) -> List[str]:
        """
        Validate the entire application state.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate all nodes
        for node_id, node in self._nodes.items():
            node_errors = node.validate()
            for error in node_errors:
                errors.append(f"Node '{node.name}': {error}")
        
        # Validate all edges
        for edge_id, edge in self._edges.items():
            edge_errors = edge.validate()
            for error in edge_errors:
                errors.append(f"Edge '{edge_id}': {error}")
            
            # Verify edge references valid nodes
            if edge.source_id not in self._nodes:
                errors.append(f"Edge '{edge_id}' references non-existent source node '{edge.source_id}'")
            if edge.target_id not in self._nodes:
                errors.append(f"Edge '{edge_id}' references non-existent target node '{edge.target_id}'")
        
        # Validate all groups
        for group_id, group in self._groups.items():
            group_errors = group.validate()
            for error in group_errors:
                errors.append(f"Group '{group.name}': {error}")
            
            # Verify group references valid nodes
            for node_id in group.nodes:
                if node_id not in self._nodes:
                    errors.append(f"Group '{group.name}' references non-existent node '{node_id}'")
        
        # Check for orphaned group assignments
        for node_id, node in self._nodes.items():
            if node.group_id and node.group_id not in self._groups:
                errors.append(f"Node '{node.name}' references non-existent group '{node.group_id}'")
        
        return errors