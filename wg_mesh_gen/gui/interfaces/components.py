"""
Component interfaces for UI elements.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from nicegui import ui


class IComponent(ABC):
    """Base interface for all UI components."""
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for the component."""
        pass
    
    @property
    @abstractmethod
    def visible(self) -> bool:
        """Whether the component is visible."""
        pass
    
    @visible.setter
    @abstractmethod
    def visible(self, value: bool) -> None:
        pass
    
    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether the component is enabled."""
        pass
    
    @enabled.setter
    @abstractmethod
    def enabled(self, value: bool) -> None:
        pass
    
    @abstractmethod
    def render(self) -> 'ui.element':
        """
        Render the component.
        
        Returns:
            NiceGUI element
        """
        pass
    
    @abstractmethod
    def update(self) -> None:
        """Update the component display."""
        pass
    
    @abstractmethod
    def destroy(self) -> None:
        """Clean up the component."""
        pass


class ICytoscapeWidget(IComponent):
    """Interface for the Cytoscape graph widget."""
    
    @abstractmethod
    def add_node(self, node_id: str, label: str, 
                wireguard_ip: Optional[str] = None,
                role: str = 'client', 
                group: Optional[str] = None,
                position: Optional[Dict[str, float]] = None) -> None:
        """
        Add a node to the graph.
        
        Args:
            node_id: Unique node identifier
            label: Display label
            wireguard_ip: WireGuard IP address
            role: Node role ('client' or 'relay')
            group: Group ID
            position: Optional position dict with 'x' and 'y'
        """
        pass
    
    @abstractmethod
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> None:
        """
        Update node properties.
        
        Args:
            node_id: Node to update
            updates: Properties to update
        """
        pass
    
    @abstractmethod
    def delete_node(self, node_id: str) -> None:
        """
        Delete a node from the graph.
        
        Args:
            node_id: Node to delete
        """
        pass
    
    @abstractmethod
    def add_edge(self, edge_id: str, source: str, target: str,
                edge_type: str = 'peer',
                allowed_ips: Optional[List[str]] = None) -> None:
        """
        Add an edge to the graph.
        
        Args:
            edge_id: Unique edge identifier
            source: Source node ID
            target: Target node ID
            edge_type: Edge type
            allowed_ips: Optional allowed IPs
        """
        pass
    
    @abstractmethod
    def update_edge(self, edge_id: str, updates: Dict[str, Any]) -> None:
        """
        Update edge properties.
        
        Args:
            edge_id: Edge to update
            updates: Properties to update
        """
        pass
    
    @abstractmethod
    def delete_edge(self, edge_id: str) -> None:
        """
        Delete an edge from the graph.
        
        Args:
            edge_id: Edge to delete
        """
        pass
    
    @abstractmethod
    def apply_layout(self, layout_name: str, 
                    options: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply a layout algorithm to the graph.
        
        Args:
            layout_name: Layout algorithm name
            options: Layout-specific options
        """
        pass
    
    @abstractmethod
    def fit_view(self, padding: int = 50) -> None:
        """
        Fit the graph view to show all elements.
        
        Args:
            padding: Padding around elements
        """
        pass
    
    @abstractmethod
    def get_elements(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all graph elements.
        
        Returns:
            Dict with 'nodes' and 'edges' lists
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all elements from the graph."""
        pass
    
    @abstractmethod
    def set_style(self, element_id: str, style: Dict[str, Any]) -> None:
        """
        Set custom style for an element.
        
        Args:
            element_id: Element to style
            style: Style properties
        """
        pass
    
    @abstractmethod
    def highlight_elements(self, element_ids: List[str]) -> None:
        """
        Highlight specific elements.
        
        Args:
            element_ids: Elements to highlight
        """
        pass
    
    @abstractmethod
    def unhighlight_all(self) -> None:
        """Remove all highlights."""
        pass
    
    @abstractmethod
    def export_image(self, format: str = 'png') -> bytes:
        """
        Export the graph as an image.
        
        Args:
            format: Image format ('png', 'jpg', 'svg')
            
        Returns:
            Image data as bytes
        """
        pass
    
    @abstractmethod
    def on_node_click(self, handler: Callable[[str], None]) -> None:
        """Register node click handler."""
        pass
    
    @abstractmethod
    def on_edge_click(self, handler: Callable[[str], None]) -> None:
        """Register edge click handler."""
        pass
    
    @abstractmethod
    def on_canvas_click(self, handler: Callable[[Dict[str, float]], None]) -> None:
        """Register canvas click handler."""
        pass
    
    @abstractmethod
    def on_node_drag_end(self, handler: Callable[[str, Dict[str, float]], None]) -> None:
        """Register node drag end handler."""
        pass
    
    @abstractmethod
    def on_selection_change(self, handler: Callable[[List[str]], None]) -> None:
        """Register selection change handler."""
        pass


class IPropertyPanel(IComponent):
    """Interface for property editing panels."""
    
    @property
    @abstractmethod
    def target_id(self) -> Optional[str]:
        """ID of the element being edited."""
        pass
    
    @target_id.setter
    @abstractmethod
    def target_id(self, value: Optional[str]) -> None:
        pass
    
    @abstractmethod
    def load_properties(self, element_id: str) -> None:
        """
        Load properties for an element.
        
        Args:
            element_id: Element to load
        """
        pass
    
    @abstractmethod
    def save_properties(self) -> Dict[str, Any]:
        """
        Save current property values.
        
        Returns:
            Dictionary of property values
        """
        pass
    
    @abstractmethod
    def validate(self) -> List[str]:
        """
        Validate current property values.
        
        Returns:
            List of validation errors
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset to original values."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all fields."""
        pass
    
    @abstractmethod
    def on_property_change(self, handler: Callable[[str, Any], None]) -> None:
        """
        Register property change handler.
        
        Args:
            handler: Callback receiving (property_name, new_value)
        """
        pass


class INodeTree(IComponent):
    """Interface for the node tree component."""
    
    @abstractmethod
    def add_node(self, node_id: str, label: str, 
                parent_id: Optional[str] = None,
                icon: Optional[str] = None) -> None:
        """
        Add a node to the tree.
        
        Args:
            node_id: Node identifier
            label: Display label
            parent_id: Parent node ID (for groups)
            icon: Optional icon name
        """
        pass
    
    @abstractmethod
    def remove_node(self, node_id: str) -> None:
        """Remove a node from the tree."""
        pass
    
    @abstractmethod
    def update_node(self, node_id: str, label: Optional[str] = None,
                   icon: Optional[str] = None) -> None:
        """Update node display properties."""
        pass
    
    @abstractmethod
    def move_node(self, node_id: str, new_parent_id: Optional[str]) -> None:
        """Move a node to a different parent."""
        pass
    
    @abstractmethod
    def select_node(self, node_id: str) -> None:
        """Select a node in the tree."""
        pass
    
    @abstractmethod
    def get_selected(self) -> List[str]:
        """Get selected node IDs."""
        pass
    
    @abstractmethod
    def expand_node(self, node_id: str) -> None:
        """Expand a tree node."""
        pass
    
    @abstractmethod
    def collapse_node(self, node_id: str) -> None:
        """Collapse a tree node."""
        pass
    
    @abstractmethod
    def on_selection_change(self, handler: Callable[[List[str]], None]) -> None:
        """Register selection change handler."""
        pass
    
    @abstractmethod
    def on_node_drop(self, handler: Callable[[str, Optional[str]], None]) -> None:
        """
        Register drag-and-drop handler.
        
        Args:
            handler: Callback receiving (dragged_id, drop_target_id)
        """
        pass


class IFileUploadComponent(IComponent):
    """Interface for file upload component."""
    
    @property
    @abstractmethod
    def accepted_extensions(self) -> List[str]:
        """List of accepted file extensions."""
        pass
    
    @accepted_extensions.setter
    @abstractmethod
    def accepted_extensions(self, value: List[str]) -> None:
        pass
    
    @property
    @abstractmethod
    def max_file_size(self) -> int:
        """Maximum file size in bytes."""
        pass
    
    @max_file_size.setter
    @abstractmethod
    def max_file_size(self, value: int) -> None:
        pass
    
    @property
    @abstractmethod
    def multiple(self) -> bool:
        """Whether multiple files can be uploaded."""
        pass
    
    @multiple.setter
    @abstractmethod
    def multiple(self, value: bool) -> None:
        pass
    
    @abstractmethod
    def clear_files(self) -> None:
        """Clear uploaded files."""
        pass
    
    @abstractmethod
    def get_uploaded_files(self) -> List[Dict[str, Any]]:
        """
        Get information about uploaded files.
        
        Returns:
            List of file info dicts with 'name', 'size', 'path'
        """
        pass
    
    @abstractmethod
    def on_upload(self, handler: Callable[[List[Dict[str, Any]]], None]) -> None:
        """
        Register upload handler.
        
        Args:
            handler: Callback receiving list of uploaded file info
        """
        pass
    
    @abstractmethod
    def on_error(self, handler: Callable[[str], None]) -> None:
        """
        Register error handler.
        
        Args:
            handler: Callback receiving error message
        """
        pass


class IExportDialog(IComponent):
    """Interface for export dialog component."""
    
    @abstractmethod
    def show(self, options: Dict[str, Any]) -> None:
        """
        Show export dialog with options.
        
        Args:
            options: Export options to display
        """
        pass
    
    @abstractmethod
    def hide(self) -> None:
        """Hide the export dialog."""
        pass
    
    @abstractmethod
    def get_selected_options(self) -> Dict[str, bool]:
        """
        Get user-selected export options.
        
        Returns:
            Dict of option names to boolean values
        """
        pass
    
    @abstractmethod
    def set_preview(self, preview: Dict[str, Any]) -> None:
        """
        Set export preview information.
        
        Args:
            preview: Preview data with file counts and sizes
        """
        pass
    
    @abstractmethod
    def on_export(self, handler: Callable[[Dict[str, bool]], None]) -> None:
        """
        Register export handler.
        
        Args:
            handler: Callback receiving selected options
        """
        pass
    
    @abstractmethod
    def on_cancel(self, handler: Callable[[], None]) -> None:
        """Register cancel handler."""
        pass


class IStatusBar(IComponent):
    """Interface for status bar component."""
    
    @abstractmethod
    def set_status(self, message: str, status_type: str = 'info') -> None:
        """
        Set status message.
        
        Args:
            message: Status message
            status_type: Type of status (info, success, warning, error)
        """
        pass
    
    @abstractmethod
    def set_validation_status(self, is_valid: bool, error_count: int = 0) -> None:
        """
        Set validation status.
        
        Args:
            is_valid: Whether configuration is valid
            error_count: Number of validation errors
        """
        pass
    
    @abstractmethod
    def set_last_action(self, action: str) -> None:
        """
        Set last action text.
        
        Args:
            action: Description of last action
        """
        pass
    
    @abstractmethod
    def show_progress(self, message: str, progress: Optional[float] = None) -> None:
        """
        Show progress indicator.
        
        Args:
            message: Progress message
            progress: Progress value (0-1) or None for indeterminate
        """
        pass
    
    @abstractmethod
    def hide_progress(self) -> None:
        """Hide progress indicator."""
        pass
    
    @abstractmethod
    def update_statistics(self, stats: Dict[str, Any]) -> None:
        """
        Update additional statistics.
        
        Args:
            stats: Dictionary of statistics to display
        """
        pass


# Dialog components (for popup dialogs, wizards, etc.)
class IDialog(IComponent):
    """Base interface for dialog components."""
    
    @abstractmethod
    def show(self) -> None:
        """Show the dialog."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the dialog."""
        pass
    
    @abstractmethod
    def on_close(self, handler: Callable[[], None]) -> None:
        """
        Register close handler.
        
        Args:
            handler: Callback when dialog is closed
        """
        pass


class IToolBar(IComponent):
    """Interface for toolbar component."""
    
    @abstractmethod
    def add_button(self, action: str, label: str, icon: Optional[str] = None,
                   tooltip: Optional[str] = None) -> None:
        """
        Add a button to the toolbar.
        
        Args:
            action: Action identifier
            label: Button label
            icon: Optional icon name
            tooltip: Optional tooltip text
        """
        pass
    
    @abstractmethod
    def remove_button(self, action: str) -> None:
        """
        Remove a button from the toolbar.
        
        Args:
            action: Action identifier
        """
        pass
    
    @abstractmethod
    def set_button_enabled(self, action: str, enabled: bool) -> None:
        """
        Set button enabled state.
        
        Args:
            action: Action identifier
            enabled: Whether button is enabled
        """
        pass
    
    @abstractmethod
    def set_action_handler(self, action: str, handler: Callable[[], None]) -> None:
        """
        Set action handler for a button.
        
        Args:
            action: Action identifier
            handler: Click handler
        """
        pass


class IMenuBar(IComponent):
    """Interface for menu bar component."""
    
    @abstractmethod
    def add_menu(self, menu_id: str, label: str) -> None:
        """
        Add a top-level menu.
        
        Args:
            menu_id: Menu identifier
            label: Menu label
        """
        pass
    
    @abstractmethod
    def add_menu_item(self, menu_id: str, item_id: str, label: str,
                      handler: Optional[Callable[[], None]] = None,
                      icon: Optional[str] = None,
                      shortcut: Optional[str] = None) -> None:
        """
        Add a menu item.
        
        Args:
            menu_id: Parent menu identifier
            item_id: Item identifier
            label: Item label
            handler: Click handler
            icon: Optional icon name
            shortcut: Optional keyboard shortcut
        """
        pass
    
    @abstractmethod
    def add_separator(self, menu_id: str) -> None:
        """
        Add a separator to a menu.
        
        Args:
            menu_id: Menu identifier
        """
        pass
    
    @abstractmethod
    def set_item_enabled(self, menu_id: str, item_id: str, enabled: bool) -> None:
        """
        Set menu item enabled state.
        
        Args:
            menu_id: Menu identifier
            item_id: Item identifier
            enabled: Whether item is enabled
        """
        pass