"""
Status bar component implementation for showing application state.

This component displays current status and statistics.
"""

from typing import Optional, Dict, Any
from datetime import datetime

from nicegui import ui

from .base import BaseComponent
from ..interfaces.components import IStatusBar
from ..interfaces.state import IAppState


class StatusBar(BaseComponent, IStatusBar):
    """Implementation of IStatusBar for application status display."""
    
    def __init__(self, app_state: IAppState, component_id: Optional[str] = None):
        """
        Initialize status bar.
        
        Args:
            app_state: Application state
            component_id: Optional component ID
        """
        super().__init__(component_id)
        self._app_state = app_state
        
        # Status elements
        self._status_label: Optional[ui.label] = None
        self._node_count: Optional[ui.label] = None
        self._edge_count: Optional[ui.label] = None
        self._group_count: Optional[ui.label] = None
        self._validation_status: Optional[ui.label] = None
        self._last_action: Optional[ui.label] = None
        
        # Current status
        self._current_status = 'Ready'
        self._validation_state = 'unknown'
        self._last_action_text = ''
        self._last_action_time: Optional[datetime] = None
    
    def render(self) -> ui.element:
        """Render the status bar."""
        with ui.row().classes(
            'w-full items-center px-4 py-2 bg-gray-100 dark:bg-gray-800 '
            'border-t text-sm'
        ) as container:
            self._element = container
            
            # Status message
            self._status_label = ui.label(self._current_status)\
                .classes('font-medium')
            
            # Separator
            ui.label('|').classes('mx-2 text-gray-400')
            
            # Statistics
            with ui.row().classes('gap-4'):
                with ui.row().classes('items-center gap-1'):
                    ui.icon('device_hub').classes('text-xs')
                    self._node_count = ui.label(f'{len(self._app_state.nodes)}')
                
                with ui.row().classes('items-center gap-1'):
                    ui.icon('timeline').classes('text-xs')
                    self._edge_count = ui.label(f'{len(self._app_state.edges)}')
                
                with ui.row().classes('items-center gap-1'):
                    ui.icon('group_work').classes('text-xs')
                    self._group_count = ui.label(f'{len(self._app_state.groups)}')
            
            # Validation status
            ui.label('|').classes('mx-2 text-gray-400')
            with ui.row().classes('items-center gap-1'):
                self._validation_icon = ui.icon('help').classes('text-xs')
                self._validation_status = ui.label('Not validated')
            
            # Spacer
            ui.space()
            
            # Last action
            self._last_action = ui.label('').classes('text-gray-600 dark:text-gray-400')
            
            # Subscribe to state changes
            self._subscribe_to_state_changes()
        
        return container
    
    def _subscribe_to_state_changes(self) -> None:
        """Subscribe to application state changes."""
        # Node changes
        self._app_state.subscribe('node_added', lambda e: self._update_counts())
        self._app_state.subscribe('node_removed', lambda e: self._update_counts())
        self._app_state.subscribe('node_updated', lambda e: self._set_last_action('Node updated'))
        
        # Edge changes
        self._app_state.subscribe('edge_added', lambda e: self._update_counts())
        self._app_state.subscribe('edge_removed', lambda e: self._update_counts())
        self._app_state.subscribe('edge_updated', lambda e: self._set_last_action('Edge updated'))
        
        # Group changes
        self._app_state.subscribe('group_added', lambda e: self._update_counts())
        self._app_state.subscribe('group_removed', lambda e: self._update_counts())
        self._app_state.subscribe('group_updated', lambda e: self._set_last_action('Group updated'))
        
        # State changes
        self._app_state.subscribe('state_dirty', lambda e: self._set_status('Modified'))
        self._app_state.subscribe('state_clean', lambda e: self._set_status('Ready'))
    
    def _update_counts(self) -> None:
        """Update element counts."""
        if self._node_count:
            self._node_count.text = str(len(self._app_state.nodes))
        if self._edge_count:
            self._edge_count.text = str(len(self._app_state.edges))
        if self._group_count:
            self._group_count.text = str(len(self._app_state.groups))
    
    def set_status(self, message: str, status_type: str = 'info') -> None:
        """
        Set status message.
        
        Args:
            message: Status message
            status_type: Type of status (info, success, warning, error)
        """
        self._set_status(message)
        
        # Update status label style based on type
        if self._status_label:
            # Remove previous status classes
            self._status_label.classes(
                remove='text-positive text-negative text-warning'
            )
            
            # Add new status class
            if status_type == 'success':
                self._status_label.classes(add='text-positive')
            elif status_type == 'error':
                self._status_label.classes(add='text-negative')
            elif status_type == 'warning':
                self._status_label.classes(add='text-warning')
    
    def _set_status(self, message: str) -> None:
        """Internal method to set status."""
        self._current_status = message
        if self._status_label:
            self._status_label.text = message
    
    def set_validation_status(self, is_valid: bool, error_count: int = 0) -> None:
        """
        Set validation status.
        
        Args:
            is_valid: Whether configuration is valid
            error_count: Number of validation errors
        """
        if is_valid:
            self._validation_state = 'valid'
            if self._validation_icon:
                self._validation_icon.name = 'check_circle'
                self._validation_icon.classes(
                    remove='text-negative text-warning',
                    add='text-positive'
                )
            if self._validation_status:
                self._validation_status.text = 'Valid'
        else:
            self._validation_state = 'invalid'
            if self._validation_icon:
                self._validation_icon.name = 'error'
                self._validation_icon.classes(
                    remove='text-positive text-warning',
                    add='text-negative'
                )
            if self._validation_status:
                self._validation_status.text = f'{error_count} errors'
    
    def set_last_action(self, action: str) -> None:
        """
        Set last action text.
        
        Args:
            action: Description of last action
        """
        self._set_last_action(action)
    
    def _set_last_action(self, action: str) -> None:
        """Internal method to set last action."""
        self._last_action_text = action
        self._last_action_time = datetime.now()
        
        if self._last_action:
            time_str = self._last_action_time.strftime('%H:%M:%S')
            self._last_action.text = f'{action} ({time_str})'
    
    def show_progress(self, message: str, progress: Optional[float] = None) -> None:
        """
        Show progress indicator.
        
        Args:
            message: Progress message
            progress: Progress value (0-1) or None for indeterminate
        """
        # For now, just show as status
        # In a more complete implementation, would show actual progress bar
        if progress is not None:
            percentage = int(progress * 100)
            self.set_status(f'{message} ({percentage}%)', 'info')
        else:
            self.set_status(f'{message}...', 'info')
    
    def hide_progress(self) -> None:
        """Hide progress indicator."""
        self.set_status('Ready', 'info')
    
    def update_statistics(self, stats: Dict[str, Any]) -> None:
        """
        Update additional statistics.
        
        Args:
            stats: Dictionary of statistics to display
        """
        # This could be extended to show more statistics
        # For now, the basic counts are updated automatically
        pass