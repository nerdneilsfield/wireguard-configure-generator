"""
GUI Interfaces Package

This package defines all interfaces for the WireGuard Visual Configuration Editor.
Following TDD principles, these interfaces define the contracts that all implementations must follow.
"""

from .base import IModel, ISerializable, IValidatable
from .models import INodeModel, IEdgeModel, IGroupModel
from .state import IAppState, ICommand, IHistoryManager
from .managers import IGraphManager, IConfigManager, IValidationManager
from .components import IComponent, ICytoscapeWidget
from .events import IEventHandler, IEventEmitter

__all__ = [
    # Base interfaces
    'IModel', 'ISerializable', 'IValidatable',
    
    # Model interfaces
    'INodeModel', 'IEdgeModel', 'IGroupModel',
    
    # State interfaces
    'IAppState', 'ICommand', 'IHistoryManager',
    
    # Manager interfaces
    'IGraphManager', 'IConfigManager', 'IValidationManager',
    
    # Component interfaces
    'IComponent', 'ICytoscapeWidget',
    
    # Event interfaces
    'IEventHandler', 'IEventEmitter',
]