"""
Event handling interfaces for the GUI module.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass


@dataclass
class Event:
    """Base event class."""
    name: str
    source: Any
    data: Dict[str, Any]
    timestamp: float


class IEventHandler(ABC):
    """Interface for objects that can handle events."""
    
    @abstractmethod
    def handle_event(self, event: Event) -> None:
        """
        Handle an event.
        
        Args:
            event: Event to handle
        """
        pass
    
    @abstractmethod
    def can_handle(self, event: Event) -> bool:
        """
        Check if this handler can handle the given event.
        
        Args:
            event: Event to check
            
        Returns:
            True if the handler can handle this event
        """
        pass


class IEventEmitter(ABC):
    """Interface for objects that can emit events."""
    
    @abstractmethod
    def emit(self, event_name: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit an event.
        
        Args:
            event_name: Name of the event
            data: Optional event data
        """
        pass
    
    @abstractmethod
    def on(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """
        Register an event handler.
        
        Args:
            event_name: Event to listen for
            handler: Callback function
        """
        pass
    
    @abstractmethod
    def off(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """
        Unregister an event handler.
        
        Args:
            event_name: Event name
            handler: Handler to remove
        """
        pass
    
    @abstractmethod
    def once(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """
        Register a one-time event handler.
        
        Args:
            event_name: Event to listen for
            handler: Callback function (called only once)
        """
        pass
    
    @abstractmethod
    def emit_async(self, event_name: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit an event asynchronously.
        
        Args:
            event_name: Name of the event
            data: Optional event data
        """
        pass
    
    @abstractmethod
    def has_listeners(self, event_name: str) -> bool:
        """
        Check if there are listeners for an event.
        
        Args:
            event_name: Event name to check
            
        Returns:
            True if there are registered listeners
        """
        pass
    
    @abstractmethod
    def remove_all_listeners(self, event_name: Optional[str] = None) -> None:
        """
        Remove all listeners for an event or all events.
        
        Args:
            event_name: Specific event name, or None for all events
        """
        pass