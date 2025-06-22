"""
Base component implementation with common functionality.
"""

import uuid
from abc import ABC
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from nicegui import ui

from ..interfaces.components import IComponent


class BaseComponent(IComponent, ABC):
    """Base implementation for UI components with common functionality."""
    
    def __init__(self, component_id: Optional[str] = None):
        """
        Initialize base component.
        
        Args:
            component_id: Optional component ID, generates UUID if not provided
        """
        self._id = component_id or str(uuid.uuid4())
        self._visible = True
        self._enabled = True
        self._element: Optional['ui.element'] = None
    
    @property
    def id(self) -> str:
        """Get component ID."""
        return self._id
    
    @property
    def visible(self) -> bool:
        """Get visibility state."""
        return self._visible
    
    @visible.setter
    def visible(self, value: bool) -> None:
        """Set visibility state."""
        self._visible = value
        if self._element:
            self._element.visible = value
    
    @property
    def enabled(self) -> bool:
        """Get enabled state."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set enabled state."""
        self._enabled = value
        if self._element and hasattr(self._element, 'enabled'):
            self._element.enabled = value
    
    def update(self) -> None:
        """Default update implementation."""
        if self._element:
            self._element.update()
    
    def destroy(self) -> None:
        """Clean up the component."""
        if self._element:
            self._element.delete()
            self._element = None