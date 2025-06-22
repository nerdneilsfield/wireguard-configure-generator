"""
Command manager implementation for undo/redo functionality.

This module implements the command pattern for application actions.
"""

from typing import List, Optional, Any, Dict
from abc import ABC, abstractmethod
from datetime import datetime

from ..interfaces.managers import ICommandManager
from ..interfaces.state import IAppState
from ...logger import get_logger


logger = get_logger()


class ICommand(ABC):
    """Interface for command objects."""
    
    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the command.
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """
        Undo the command.
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def redo(self) -> bool:
        """
        Redo the command.
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get command description."""
        pass


class BaseCommand(ICommand):
    """Base class for commands."""
    
    def __init__(self, app_state: IAppState):
        self.app_state = app_state
        self.timestamp = datetime.now()
        self._executed = False
    
    def execute(self) -> bool:
        """Execute the command."""
        if self._executed:
            return False
        
        result = self._do_execute()
        if result:
            self._executed = True
        return result
    
    def undo(self) -> bool:
        """Undo the command."""
        if not self._executed:
            return False
        
        result = self._do_undo()
        if result:
            self._executed = False
        return result
    
    def redo(self) -> bool:
        """Redo the command."""
        if self._executed:
            return False
        
        result = self._do_execute()
        if result:
            self._executed = True
        return result
    
    @abstractmethod
    def _do_execute(self) -> bool:
        """Internal execute implementation."""
        pass
    
    @abstractmethod
    def _do_undo(self) -> bool:
        """Internal undo implementation."""
        pass


class AddNodeCommand(BaseCommand):
    """Command to add a node."""
    
    def __init__(self, app_state: IAppState, node_data: Dict[str, Any]):
        super().__init__(app_state)
        self.node_data = node_data
        self.node_id: Optional[str] = None
    
    @property
    def description(self) -> str:
        return f"Add node '{self.node_data.get('name', 'unnamed')}'"
    
    def _do_execute(self) -> bool:
        """Add the node."""
        try:
            from ..models import NodeModel
            node = NodeModel.from_dict(self.node_data)
            self.node_id = node.id
            self.app_state.add_node(node)
            return True
        except Exception as e:
            logger.error(f"Failed to add node: {e}")
            return False
    
    def _do_undo(self) -> bool:
        """Remove the node."""
        try:
            if self.node_id:
                self.app_state.remove_node(self.node_id)
            return True
        except Exception as e:
            logger.error(f"Failed to remove node: {e}")
            return False


class RemoveNodeCommand(BaseCommand):
    """Command to remove a node."""
    
    def __init__(self, app_state: IAppState, node_id: str):
        super().__init__(app_state)
        self.node_id = node_id
        self.node_data: Optional[Dict[str, Any]] = None
        self.affected_edges: List[Dict[str, Any]] = []
    
    @property
    def description(self) -> str:
        node_name = self.node_data.get('name', 'unknown') if self.node_data else 'unknown'
        return f"Remove node '{node_name}'"
    
    def _do_execute(self) -> bool:
        """Remove the node and its edges."""
        try:
            # Save node data before removal
            if self.node_id in self.app_state.nodes:
                self.node_data = self.app_state.nodes[self.node_id].to_dict()
                
                # Save affected edges
                self.affected_edges = []
                for edge in self.app_state.edges.values():
                    if edge.source_id == self.node_id or edge.target_id == self.node_id:
                        self.affected_edges.append(edge.to_dict())
            
            self.app_state.remove_node(self.node_id)
            return True
        except Exception as e:
            logger.error(f"Failed to remove node: {e}")
            return False
    
    def _do_undo(self) -> bool:
        """Restore the node and its edges."""
        try:
            if self.node_data:
                from ..models import NodeModel, EdgeModel
                
                # Restore node
                node = NodeModel.from_dict(self.node_data)
                self.app_state.add_node(node)
                
                # Restore edges
                for edge_data in self.affected_edges:
                    edge = EdgeModel.from_dict(edge_data)
                    self.app_state.add_edge(edge)
            
            return True
        except Exception as e:
            logger.error(f"Failed to restore node: {e}")
            return False


class UpdateNodeCommand(BaseCommand):
    """Command to update node properties."""
    
    def __init__(self, app_state: IAppState, node_id: str, old_data: Dict[str, Any], new_data: Dict[str, Any]):
        super().__init__(app_state)
        self.node_id = node_id
        self.old_data = old_data
        self.new_data = new_data
    
    @property
    def description(self) -> str:
        return f"Update node '{self.new_data.get('name', 'unnamed')}'"
    
    def _do_execute(self) -> bool:
        """Update the node."""
        try:
            if self.node_id in self.app_state.nodes:
                node = self.app_state.nodes[self.node_id]
                for key, value in self.new_data.items():
                    setattr(node, key, value)
                node.updated_at = datetime.now()
                self.app_state._emit_event('node_updated', {'node_id': self.node_id})
            return True
        except Exception as e:
            logger.error(f"Failed to update node: {e}")
            return False
    
    def _do_undo(self) -> bool:
        """Restore old node data."""
        try:
            if self.node_id in self.app_state.nodes:
                node = self.app_state.nodes[self.node_id]
                for key, value in self.old_data.items():
                    setattr(node, key, value)
                node.updated_at = datetime.now()
                self.app_state._emit_event('node_updated', {'node_id': self.node_id})
            return True
        except Exception as e:
            logger.error(f"Failed to restore node: {e}")
            return False


class AddEdgeCommand(BaseCommand):
    """Command to add an edge."""
    
    def __init__(self, app_state: IAppState, edge_data: Dict[str, Any]):
        super().__init__(app_state)
        self.edge_data = edge_data
        self.edge_id: Optional[str] = None
    
    @property
    def description(self) -> str:
        return "Add connection"
    
    def _do_execute(self) -> bool:
        """Add the edge."""
        try:
            from ..models import EdgeModel
            edge = EdgeModel.from_dict(self.edge_data)
            self.edge_id = edge.id
            self.app_state.add_edge(edge)
            return True
        except Exception as e:
            logger.error(f"Failed to add edge: {e}")
            return False
    
    def _do_undo(self) -> bool:
        """Remove the edge."""
        try:
            if self.edge_id:
                self.app_state.remove_edge(self.edge_id)
            return True
        except Exception as e:
            logger.error(f"Failed to remove edge: {e}")
            return False


class RemoveEdgeCommand(BaseCommand):
    """Command to remove an edge."""
    
    def __init__(self, app_state: IAppState, edge_id: str):
        super().__init__(app_state)
        self.edge_id = edge_id
        self.edge_data: Optional[Dict[str, Any]] = None
    
    @property
    def description(self) -> str:
        return "Remove connection"
    
    def _do_execute(self) -> bool:
        """Remove the edge."""
        try:
            # Save edge data before removal
            if self.edge_id in self.app_state.edges:
                self.edge_data = self.app_state.edges[self.edge_id].to_dict()
            
            self.app_state.remove_edge(self.edge_id)
            return True
        except Exception as e:
            logger.error(f"Failed to remove edge: {e}")
            return False
    
    def _do_undo(self) -> bool:
        """Restore the edge."""
        try:
            if self.edge_data:
                from ..models import EdgeModel
                edge = EdgeModel.from_dict(self.edge_data)
                self.app_state.add_edge(edge)
            return True
        except Exception as e:
            logger.error(f"Failed to restore edge: {e}")
            return False


class BatchCommand(BaseCommand):
    """Command that executes multiple commands as a batch."""
    
    def __init__(self, app_state: IAppState, description: str = "Batch operation"):
        super().__init__(app_state)
        self.commands: List[ICommand] = []
        self._description = description
    
    @property
    def description(self) -> str:
        return self._description
    
    def _do_execute(self) -> bool:
        """Execute all commands."""
        for command in self.commands:
            if not command.execute():
                # Rollback on failure
                for cmd in reversed(self.commands[:self.commands.index(command)]):
                    cmd.undo()
                return False
        return True
    
    def _do_undo(self) -> bool:
        """Undo all commands in reverse order."""
        for command in reversed(self.commands):
            if not command.undo():
                return False
        return True


class CommandManager(ICommandManager):
    """Implementation of command manager for undo/redo."""
    
    def __init__(self, max_history: int = 100):
        """
        Initialize command manager.
        
        Args:
            max_history: Maximum number of commands to keep in history
        """
        self._history: List[ICommand] = []
        self._redo_stack: List[ICommand] = []
        self._max_history = max_history
        self._current_batch: Optional[BatchCommand] = None
    
    def execute(self, command: ICommand) -> bool:
        """
        Execute a command and add to history.
        
        Args:
            command: Command to execute
            
        Returns:
            True if successful
        """
        # If in batch mode, add to batch
        if self._current_batch:
            self._current_batch.commands.append(command)
            return command.execute()
        
        # Execute command
        if command.execute():
            # Add to history
            self._history.append(command)
            
            # Clear redo stack
            self._redo_stack.clear()
            
            # Trim history if needed
            if len(self._history) > self._max_history:
                self._history.pop(0)
            
            logger.debug(f"Executed command: {command.description}")
            return True
        
        return False
    
    def undo(self) -> bool:
        """
        Undo the last command.
        
        Returns:
            True if successful
        """
        if not self.can_undo():
            return False
        
        command = self._history.pop()
        if command.undo():
            self._redo_stack.append(command)
            logger.debug(f"Undid command: {command.description}")
            return True
        else:
            # Restore to history if undo failed
            self._history.append(command)
            return False
    
    def redo(self) -> bool:
        """
        Redo the last undone command.
        
        Returns:
            True if successful
        """
        if not self.can_redo():
            return False
        
        command = self._redo_stack.pop()
        if command.redo():
            self._history.append(command)
            logger.debug(f"Redid command: {command.description}")
            return True
        else:
            # Restore to redo stack if redo failed
            self._redo_stack.append(command)
            return False
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._history) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0
    
    def get_history(self) -> List[str]:
        """
        Get command history descriptions.
        
        Returns:
            List of command descriptions
        """
        return [cmd.description for cmd in self._history]
    
    def clear(self) -> None:
        """Clear command history."""
        self._history.clear()
        self._redo_stack.clear()
        self._current_batch = None
        logger.debug("Cleared command history")
    
    def begin_batch(self, description: str) -> None:
        """
        Begin a batch operation.
        
        Args:
            description: Batch operation description
        """
        if self._current_batch:
            logger.warning("Already in batch mode")
            return
        
        # Get app_state from last command or create dummy
        app_state = self._history[-1].app_state if self._history else None
        self._current_batch = BatchCommand(app_state=app_state, _description=description)
    
    def end_batch(self) -> bool:
        """
        End batch operation and execute as single command.
        
        Returns:
            True if successful
        """
        if not self._current_batch:
            logger.warning("Not in batch mode")
            return False
        
        batch = self._current_batch
        self._current_batch = None
        
        if batch.commands:
            # Execute the batch as a single command
            return self.execute(batch)
        
        return True
    
    def get_undo_description(self) -> Optional[str]:
        """Get description of command that would be undone."""
        if self.can_undo():
            return self._history[-1].description
        return None
    
    def get_redo_description(self) -> Optional[str]:
        """Get description of command that would be redone."""
        if self.can_redo():
            return self._redo_stack[-1].description
        return None