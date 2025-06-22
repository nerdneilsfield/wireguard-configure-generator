"""
State management package for the WireGuard Visual Configuration Editor.

This package contains implementations for state management, commands, and history.
"""

from .commands import (
    Command,
    AddNodeCommand,
    UpdateNodeCommand, 
    DeleteNodeCommand,
    AddEdgeCommand,
    UpdateEdgeCommand,
    DeleteEdgeCommand,
    AddGroupCommand,
    UpdateGroupCommand,
    DeleteGroupCommand,
    MoveNodeToGroupCommand,
    BatchCommand
)
from .history import HistoryManager
from .app_state import AppState

__all__ = [
    # Base command
    'Command',
    
    # Node commands
    'AddNodeCommand',
    'UpdateNodeCommand',
    'DeleteNodeCommand',
    
    # Edge commands
    'AddEdgeCommand',
    'UpdateEdgeCommand',
    'DeleteEdgeCommand',
    
    # Group commands
    'AddGroupCommand',
    'UpdateGroupCommand',
    'DeleteGroupCommand',
    'MoveNodeToGroupCommand',
    
    # Batch command
    'BatchCommand',
    
    # History manager
    'HistoryManager',
    
    # Application state
    'AppState',
]