"""
State management interfaces for the GUI application.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Set, Optional, Callable, Any
from .models import INodeModel, IEdgeModel, IGroupModel


class ICommand(ABC):
    """Interface for undoable commands (Command pattern)."""
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the command."""
        pass
    
    @abstractmethod
    def execute(self) -> None:
        """Execute the command."""
        pass
    
    @abstractmethod
    def undo(self) -> None:
        """Undo the command."""
        pass
    
    @abstractmethod
    def can_execute(self) -> bool:
        """
        Check if the command can be executed.
        
        Returns:
            True if the command can be executed
        """
        pass
    
    @abstractmethod
    def can_undo(self) -> bool:
        """
        Check if the command can be undone.
        
        Returns:
            True if the command can be undone
        """
        pass


class IHistoryManager(ABC):
    """Interface for managing command history (undo/redo)."""
    
    @abstractmethod
    def execute(self, command: ICommand) -> None:
        """
        Execute a command and add it to history.
        
        Args:
            command: Command to execute
        """
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """
        Undo the last command.
        
        Returns:
            True if a command was undone, False if history is empty
        """
        pass
    
    @abstractmethod
    def redo(self) -> bool:
        """
        Redo the last undone command.
        
        Returns:
            True if a command was redone, False if redo stack is empty
        """
        pass
    
    @abstractmethod
    def can_undo(self) -> bool:
        """Check if undo is available."""
        pass
    
    @abstractmethod
    def can_redo(self) -> bool:
        """Check if redo is available."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all history."""
        pass
    
    @abstractmethod
    def get_undo_description(self) -> Optional[str]:
        """Get description of the command that would be undone."""
        pass
    
    @abstractmethod
    def get_redo_description(self) -> Optional[str]:
        """Get description of the command that would be redone."""
        pass
    
    @abstractmethod
    def begin_batch(self, description: str) -> None:
        """
        Begin a batch of commands that will be treated as one.
        
        Args:
            description: Description of the batch operation
        """
        pass
    
    @abstractmethod
    def end_batch(self) -> None:
        """End the current batch of commands."""
        pass
    
    @property
    @abstractmethod
    def history_limit(self) -> int:
        """Maximum number of commands to keep in history."""
        pass
    
    @history_limit.setter
    @abstractmethod
    def history_limit(self, value: int) -> None:
        pass


class IAppState(ABC):
    """Interface for the main application state."""
    
    @property
    @abstractmethod
    def nodes(self) -> Dict[str, INodeModel]:
        """All nodes in the configuration."""
        pass
    
    @property
    @abstractmethod
    def edges(self) -> Dict[str, IEdgeModel]:
        """All edges in the configuration."""
        pass
    
    @property
    @abstractmethod
    def groups(self) -> Dict[str, IGroupModel]:
        """All groups in the configuration."""
        pass
    
    @property
    @abstractmethod
    def selected_elements(self) -> Set[str]:
        """Currently selected element IDs."""
        pass
    
    @property
    @abstractmethod
    def history(self) -> IHistoryManager:
        """Command history manager."""
        pass
    
    @property
    @abstractmethod
    def is_dirty(self) -> bool:
        """Whether the state has unsaved changes."""
        pass
    
    @property
    @abstractmethod
    def current_file(self) -> Optional[str]:
        """Path to the currently loaded file."""
        pass
    
    @current_file.setter
    @abstractmethod
    def current_file(self, value: Optional[str]) -> None:
        pass
    
    @abstractmethod
    def add_node(self, node: INodeModel) -> None:
        """
        Add a node to the state.
        
        Args:
            node: Node to add
        """
        pass
    
    @abstractmethod
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> None:
        """
        Update a node's properties.
        
        Args:
            node_id: ID of the node to update
            updates: Dictionary of properties to update
        """
        pass
    
    @abstractmethod
    def remove_node(self, node_id: str) -> None:
        """
        Remove a node and all connected edges.
        
        Args:
            node_id: ID of the node to remove
        """
        pass
    
    @abstractmethod
    def add_edge(self, edge: IEdgeModel) -> None:
        """
        Add an edge to the state.
        
        Args:
            edge: Edge to add
        """
        pass
    
    @abstractmethod
    def update_edge(self, edge_id: str, updates: Dict[str, Any]) -> None:
        """
        Update an edge's properties.
        
        Args:
            edge_id: ID of the edge to update
            updates: Dictionary of properties to update
        """
        pass
    
    @abstractmethod
    def remove_edge(self, edge_id: str) -> None:
        """
        Remove an edge.
        
        Args:
            edge_id: ID of the edge to remove
        """
        pass
    
    @abstractmethod
    def add_group(self, group: IGroupModel) -> None:
        """
        Add a group to the state.
        
        Args:
            group: Group to add
        """
        pass
    
    @abstractmethod
    def update_group(self, group_id: str, updates: Dict[str, Any]) -> None:
        """
        Update a group's properties.
        
        Args:
            group_id: ID of the group to update
            updates: Dictionary of properties to update
        """
        pass
    
    @abstractmethod
    def remove_group(self, group_id: str) -> None:
        """
        Remove a group and unassign all nodes.
        
        Args:
            group_id: ID of the group to remove
        """
        pass
    
    @abstractmethod
    def select_element(self, element_id: str) -> None:
        """Add an element to selection."""
        pass
    
    @abstractmethod
    def deselect_element(self, element_id: str) -> None:
        """Remove an element from selection."""
        pass
    
    @abstractmethod
    def clear_selection(self) -> None:
        """Clear all selected elements."""
        pass
    
    @abstractmethod
    def set_selection(self, element_ids: Set[str]) -> None:
        """Set the selection to specific elements."""
        pass
    
    @abstractmethod
    def mark_clean(self) -> None:
        """Mark the state as having no unsaved changes."""
        pass
    
    @abstractmethod
    def subscribe(self, event: str, handler: Callable) -> None:
        """
        Subscribe to state change events.
        
        Args:
            event: Event name (e.g., 'node_added', 'edge_updated')
            handler: Callback function
        """
        pass
    
    @abstractmethod
    def unsubscribe(self, event: str, handler: Callable) -> None:
        """
        Unsubscribe from state change events.
        
        Args:
            event: Event name
            handler: Callback function to remove
        """
        pass
    
    @abstractmethod
    def get_edges_for_node(self, node_id: str) -> List[IEdgeModel]:
        """
        Get all edges connected to a node.
        
        Args:
            node_id: ID of the node
            
        Returns:
            List of connected edges
        """
        pass
    
    @abstractmethod
    def get_nodes_in_group(self, group_id: str) -> List[INodeModel]:
        """
        Get all nodes in a group.
        
        Args:
            group_id: ID of the group
            
        Returns:
            List of nodes in the group
        """
        pass