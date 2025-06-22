"""
Command pattern implementations for undo/redo functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from copy import deepcopy

from ..interfaces.state import ICommand, IAppState
from ..models import NodeModel, EdgeModel, GroupModel


class Command(ICommand, ABC):
    """Base implementation of ICommand interface."""
    
    def __init__(self, app_state: IAppState, description: str = ""):
        """
        Initialize command with application state reference.
        
        Args:
            app_state: Application state to operate on
            description: Human-readable description
        """
        self._app_state = app_state
        self._description = description
        self._executed = False
    
    @property
    def description(self) -> str:
        """Get command description."""
        return self._description
    
    def can_execute(self) -> bool:
        """Check if the command can be executed."""
        return not self._executed
    
    def can_undo(self) -> bool:
        """Check if the command can be undone."""
        return self._executed


class AddNodeCommand(Command):
    """Command to add a node to the state."""
    
    def __init__(self, app_state: IAppState, node: NodeModel):
        """
        Initialize add node command.
        
        Args:
            app_state: Application state
            node: Node to add
        """
        super().__init__(app_state, f"Add node '{node.name}'")
        self._node = node
    
    def execute(self) -> None:
        """Execute the command."""
        if not self.can_execute():
            raise RuntimeError("Command has already been executed")
        
        self._app_state.add_node(self._node)
        self._executed = True
    
    def undo(self) -> None:
        """Undo the command."""
        if not self.can_undo():
            raise RuntimeError("Command has not been executed")
        
        self._app_state.remove_node(self._node.id)
        self._executed = False


class UpdateNodeCommand(Command):
    """Command to update a node's properties."""
    
    def __init__(self, app_state: IAppState, node_id: str, updates: Dict[str, Any]):
        """
        Initialize update node command.
        
        Args:
            app_state: Application state
            node_id: ID of node to update
            updates: Properties to update
        """
        super().__init__(app_state, f"Update node '{node_id}'")
        self._node_id = node_id
        self._updates = updates
        self._previous_state: Optional[Dict[str, Any]] = None
    
    def execute(self) -> None:
        """Execute the command."""
        if not self.can_execute():
            raise RuntimeError("Command has already been executed")
        
        # Save current state for undo
        node = self._app_state.nodes.get(self._node_id)
        if not node:
            raise ValueError(f"Node '{self._node_id}' not found")
        
        self._previous_state = node.to_dict()
        
        # Apply updates
        self._app_state.update_node(self._node_id, self._updates)
        self._executed = True
    
    def undo(self) -> None:
        """Undo the command."""
        if not self.can_undo():
            raise RuntimeError("Command has not been executed")
        
        if not self._previous_state:
            raise RuntimeError("No previous state saved")
        
        # Restore previous state
        restore_data = {k: v for k, v in self._previous_state.items() 
                       if k not in ['id', 'created_at', 'updated_at']}
        self._app_state.update_node(self._node_id, restore_data)
        self._executed = False


class DeleteNodeCommand(Command):
    """Command to delete a node from the state."""
    
    def __init__(self, app_state: IAppState, node_id: str):
        """
        Initialize delete node command.
        
        Args:
            app_state: Application state
            node_id: ID of node to delete
        """
        super().__init__(app_state, f"Delete node '{node_id}'")
        self._node_id = node_id
        self._deleted_node: Optional[NodeModel] = None
        self._deleted_edges: List[EdgeModel] = []
    
    def execute(self) -> None:
        """Execute the command."""
        if not self.can_execute():
            raise RuntimeError("Command has already been executed")
        
        # Save node for undo
        self._deleted_node = self._app_state.nodes.get(self._node_id)
        if not self._deleted_node:
            raise ValueError(f"Node '{self._node_id}' not found")
        
        # Save connected edges for undo
        self._deleted_edges = self._app_state.get_edges_for_node(self._node_id)
        
        # Delete node (and connected edges)
        self._app_state.remove_node(self._node_id)
        self._executed = True
    
    def undo(self) -> None:
        """Undo the command."""
        if not self.can_undo():
            raise RuntimeError("Command has not been executed")
        
        if not self._deleted_node:
            raise RuntimeError("No deleted node saved")
        
        # Restore node
        self._app_state.add_node(self._deleted_node)
        
        # Restore edges
        for edge in self._deleted_edges:
            self._app_state.add_edge(edge)
        
        self._executed = False


class AddEdgeCommand(Command):
    """Command to add an edge to the state."""
    
    def __init__(self, app_state: IAppState, edge: EdgeModel):
        """
        Initialize add edge command.
        
        Args:
            app_state: Application state
            edge: Edge to add
        """
        super().__init__(app_state, f"Add edge '{edge.source_id}' -> '{edge.target_id}'")
        self._edge = edge
    
    def execute(self) -> None:
        """Execute the command."""
        if not self.can_execute():
            raise RuntimeError("Command has already been executed")
        
        self._app_state.add_edge(self._edge)
        self._executed = True
    
    def undo(self) -> None:
        """Undo the command."""
        if not self.can_undo():
            raise RuntimeError("Command has not been executed")
        
        self._app_state.remove_edge(self._edge.id)
        self._executed = False


class UpdateEdgeCommand(Command):
    """Command to update an edge's properties."""
    
    def __init__(self, app_state: IAppState, edge_id: str, updates: Dict[str, Any]):
        """
        Initialize update edge command.
        
        Args:
            app_state: Application state
            edge_id: ID of edge to update
            updates: Properties to update
        """
        super().__init__(app_state, f"Update edge '{edge_id}'")
        self._edge_id = edge_id
        self._updates = updates
        self._previous_state: Optional[Dict[str, Any]] = None
    
    def execute(self) -> None:
        """Execute the command."""
        if not self.can_execute():
            raise RuntimeError("Command has already been executed")
        
        # Save current state for undo
        edge = self._app_state.edges.get(self._edge_id)
        if not edge:
            raise ValueError(f"Edge '{self._edge_id}' not found")
        
        self._previous_state = edge.to_dict()
        
        # Apply updates
        self._app_state.update_edge(self._edge_id, self._updates)
        self._executed = True
    
    def undo(self) -> None:
        """Undo the command."""
        if not self.can_undo():
            raise RuntimeError("Command has not been executed")
        
        if not self._previous_state:
            raise RuntimeError("No previous state saved")
        
        # Restore previous state
        restore_data = {k: v for k, v in self._previous_state.items() 
                       if k not in ['id', 'created_at', 'updated_at']}
        self._app_state.update_edge(self._edge_id, restore_data)
        self._executed = False


class DeleteEdgeCommand(Command):
    """Command to delete an edge from the state."""
    
    def __init__(self, app_state: IAppState, edge_id: str):
        """
        Initialize delete edge command.
        
        Args:
            app_state: Application state
            edge_id: ID of edge to delete
        """
        super().__init__(app_state, f"Delete edge '{edge_id}'")
        self._edge_id = edge_id
        self._deleted_edge: Optional[EdgeModel] = None
    
    def execute(self) -> None:
        """Execute the command."""
        if not self.can_execute():
            raise RuntimeError("Command has already been executed")
        
        # Save edge for undo
        self._deleted_edge = self._app_state.edges.get(self._edge_id)
        if not self._deleted_edge:
            raise ValueError(f"Edge '{self._edge_id}' not found")
        
        # Delete edge
        self._app_state.remove_edge(self._edge_id)
        self._executed = True
    
    def undo(self) -> None:
        """Undo the command."""
        if not self.can_undo():
            raise RuntimeError("Command has not been executed")
        
        if not self._deleted_edge:
            raise RuntimeError("No deleted edge saved")
        
        # Restore edge
        self._app_state.add_edge(self._deleted_edge)
        self._executed = False


class AddGroupCommand(Command):
    """Command to add a group to the state."""
    
    def __init__(self, app_state: IAppState, group: GroupModel):
        """
        Initialize add group command.
        
        Args:
            app_state: Application state
            group: Group to add
        """
        super().__init__(app_state, f"Add group '{group.name}'")
        self._group = group
    
    def execute(self) -> None:
        """Execute the command."""
        if not self.can_execute():
            raise RuntimeError("Command has already been executed")
        
        self._app_state.add_group(self._group)
        self._executed = True
    
    def undo(self) -> None:
        """Undo the command."""
        if not self.can_undo():
            raise RuntimeError("Command has not been executed")
        
        self._app_state.remove_group(self._group.id)
        self._executed = False


class UpdateGroupCommand(Command):
    """Command to update a group's properties."""
    
    def __init__(self, app_state: IAppState, group_id: str, updates: Dict[str, Any]):
        """
        Initialize update group command.
        
        Args:
            app_state: Application state
            group_id: ID of group to update
            updates: Properties to update
        """
        super().__init__(app_state, f"Update group '{group_id}'")
        self._group_id = group_id
        self._updates = updates
        self._previous_state: Optional[Dict[str, Any]] = None
    
    def execute(self) -> None:
        """Execute the command."""
        if not self.can_execute():
            raise RuntimeError("Command has already been executed")
        
        # Save current state for undo
        group = self._app_state.groups.get(self._group_id)
        if not group:
            raise ValueError(f"Group '{self._group_id}' not found")
        
        self._previous_state = group.to_dict()
        
        # Apply updates
        self._app_state.update_group(self._group_id, self._updates)
        self._executed = True
    
    def undo(self) -> None:
        """Undo the command."""
        if not self.can_undo():
            raise RuntimeError("Command has not been executed")
        
        if not self._previous_state:
            raise RuntimeError("No previous state saved")
        
        # Restore previous state
        restore_data = {k: v for k, v in self._previous_state.items() 
                       if k not in ['id', 'created_at', 'updated_at']}
        self._app_state.update_group(self._group_id, restore_data)
        self._executed = False


class DeleteGroupCommand(Command):
    """Command to delete a group from the state."""
    
    def __init__(self, app_state: IAppState, group_id: str):
        """
        Initialize delete group command.
        
        Args:
            app_state: Application state
            group_id: ID of group to delete
        """
        super().__init__(app_state, f"Delete group '{group_id}'")
        self._group_id = group_id
        self._deleted_group: Optional[GroupModel] = None
        self._node_assignments: Dict[str, str] = {}  # node_id -> group_id
    
    def execute(self) -> None:
        """Execute the command."""
        if not self.can_execute():
            raise RuntimeError("Command has already been executed")
        
        # Save group for undo
        self._deleted_group = self._app_state.groups.get(self._group_id)
        if not self._deleted_group:
            raise ValueError(f"Group '{self._group_id}' not found")
        
        # Save node assignments for undo
        for node_id in self._deleted_group.nodes:
            node = self._app_state.nodes.get(node_id)
            if node and node.group_id == self._group_id:
                self._node_assignments[node_id] = self._group_id
        
        # Delete group (and unassign nodes)
        self._app_state.remove_group(self._group_id)
        self._executed = True
    
    def undo(self) -> None:
        """Undo the command."""
        if not self.can_undo():
            raise RuntimeError("Command has not been executed")
        
        if not self._deleted_group:
            raise RuntimeError("No deleted group saved")
        
        # Restore group
        self._app_state.add_group(self._deleted_group)
        
        # Restore node assignments
        for node_id, group_id in self._node_assignments.items():
            self._app_state.update_node(node_id, {'group_id': group_id})
        
        self._executed = False


class MoveNodeToGroupCommand(Command):
    """Command to move a node to a different group."""
    
    def __init__(self, app_state: IAppState, node_id: str, new_group_id: Optional[str]):
        """
        Initialize move node to group command.
        
        Args:
            app_state: Application state
            node_id: ID of node to move
            new_group_id: ID of new group (None to remove from group)
        """
        group_name = new_group_id or "no group"
        super().__init__(app_state, f"Move node '{node_id}' to {group_name}")
        self._node_id = node_id
        self._new_group_id = new_group_id
        self._old_group_id: Optional[str] = None
    
    def execute(self) -> None:
        """Execute the command."""
        if not self.can_execute():
            raise RuntimeError("Command has already been executed")
        
        # Get current group
        node = self._app_state.nodes.get(self._node_id)
        if not node:
            raise ValueError(f"Node '{self._node_id}' not found")
        
        self._old_group_id = node.group_id
        
        # Remove from old group if any
        if self._old_group_id:
            old_group = self._app_state.groups.get(self._old_group_id)
            if old_group and old_group.has_node(self._node_id):
                old_group.remove_node(self._node_id)
        
        # Add to new group if specified
        if self._new_group_id:
            new_group = self._app_state.groups.get(self._new_group_id)
            if not new_group:
                raise ValueError(f"Group '{self._new_group_id}' not found")
            new_group.add_node(self._node_id)
        
        # Update node's group assignment
        self._app_state.update_node(self._node_id, {'group_id': self._new_group_id})
        self._executed = True
    
    def undo(self) -> None:
        """Undo the command."""
        if not self.can_undo():
            raise RuntimeError("Command has not been executed")
        
        # Remove from new group if any
        if self._new_group_id:
            new_group = self._app_state.groups.get(self._new_group_id)
            if new_group and new_group.has_node(self._node_id):
                new_group.remove_node(self._node_id)
        
        # Add back to old group if any
        if self._old_group_id:
            old_group = self._app_state.groups.get(self._old_group_id)
            if old_group:
                old_group.add_node(self._node_id)
        
        # Restore node's group assignment
        self._app_state.update_node(self._node_id, {'group_id': self._old_group_id})
        self._executed = False


class BatchCommand(Command):
    """Command that executes multiple commands as a single unit."""
    
    def __init__(self, app_state: IAppState, commands: List[ICommand], description: str):
        """
        Initialize batch command.
        
        Args:
            app_state: Application state
            commands: List of commands to execute
            description: Description of the batch operation
        """
        super().__init__(app_state, description)
        self._commands = commands
        self._executed_count = 0
    
    def execute(self) -> None:
        """Execute all commands in the batch."""
        if not self.can_execute():
            raise RuntimeError("Batch command has already been executed")
        
        # Execute commands in order
        for i, command in enumerate(self._commands):
            try:
                command.execute()
                self._executed_count = i + 1
            except Exception as e:
                # Rollback on error
                for j in range(i, -1, -1):
                    if j < self._executed_count:
                        self._commands[j].undo()
                self._executed_count = 0
                raise RuntimeError(f"Batch command failed at step {i+1}: {str(e)}")
        
        self._executed = True
    
    def undo(self) -> None:
        """Undo all commands in the batch."""
        if not self.can_undo():
            raise RuntimeError("Batch command has not been executed")
        
        # Undo commands in reverse order
        for i in range(len(self._commands) - 1, -1, -1):
            self._commands[i].undo()
        
        self._executed_count = 0
        self._executed = False
    
    def can_execute(self) -> bool:
        """Check if all commands can be executed."""
        if self._executed:
            return False
        return all(cmd.can_execute() for cmd in self._commands)
    
    def can_undo(self) -> bool:
        """Check if all commands can be undone."""
        if not self._executed:
            return False
        return all(cmd.can_undo() for cmd in self._commands)