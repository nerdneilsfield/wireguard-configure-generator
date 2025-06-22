"""
Toolbar implementation with common actions.

This component provides quick access to frequently used actions.
"""

from typing import Dict, Optional, Callable

from nicegui import ui

from .base import BaseComponent
from ..interfaces.components import IToolBar
from ..interfaces.state import IAppState
from ..models import NodeModel, EdgeModel, GroupModel
from ..state import AddNodeCommand, AddEdgeCommand, AddGroupCommand, DeleteNodeCommand, DeleteEdgeCommand, DeleteGroupCommand


class ToolBar(BaseComponent, IToolBar):
    """Implementation of IToolBar for common actions."""
    
    def __init__(self, 
                 app_state: IAppState,
                 component_id: Optional[str] = None):
        """
        Initialize toolbar.
        
        Args:
            app_state: Application state
            component_id: Optional component ID
        """
        super().__init__(component_id)
        self._app_state = app_state
        self._actions: Dict[str, Callable] = {}
        
        # Track UI state
        self._can_undo = False
        self._can_redo = False
        self._has_selection = False
        
        # Subscribe to state changes
        self._subscribe_to_events()
    
    def render(self) -> ui.element:
        """Render the toolbar."""
        with ui.toolbar().classes('bg-primary') as self._element:
            # File actions
            with ui.button_group().props('flat'):
                self._add_action('new', 'New', 'add', self._handle_new)
                self._add_action('open', 'Open', 'folder_open', self._handle_open)
                self._add_action('save', 'Save', 'save', self._handle_save)
            
            ui.separator().props('vertical inset')
            
            # Edit actions
            with ui.button_group().props('flat'):
                self._undo_btn = self._add_action('undo', 'Undo', 'undo', self._handle_undo)
                self._redo_btn = self._add_action('redo', 'Redo', 'redo', self._handle_redo)
            
            ui.separator().props('vertical inset')
            
            # Graph actions
            with ui.button_group().props('flat'):
                self._add_action('add_node', 'Add Node', 'add_circle', self._handle_add_node)
                self._add_action('add_edge', 'Add Edge', 'timeline', self._handle_add_edge)
                self._add_action('add_group', 'Add Group', 'group_work', self._handle_add_group)
                self._delete_btn = self._add_action('delete', 'Delete', 'delete', self._handle_delete)
            
            ui.separator().props('vertical inset')
            
            # Layout actions
            with ui.button_group().props('flat'):
                self._add_action('layout', 'Auto Layout', 'auto_fix_high', self._handle_layout)
                self._add_action('fit', 'Fit View', 'fit_screen', self._handle_fit)
            
            ui.separator().props('vertical inset')
            
            # View actions
            with ui.button_group().props('flat'):
                self._add_action('validate', 'Validate', 'fact_check', self._handle_validate)
                self._add_action('export', 'Export', 'download', self._handle_export)
            
            # Update initial state
            self._update_button_states()
        
        return self._element
    
    def _add_action(self, action_id: str, tooltip: str, icon: str, handler: Callable) -> ui.button:
        """Add an action button to the toolbar."""
        btn = ui.button(icon=icon, on_click=handler)\
            .props('flat round')\
            .tooltip(tooltip)
        
        self._actions[action_id] = handler
        return btn
    
    def add_action(self, action_id: str, label: str, icon: Optional[str] = None,
                  handler: Optional[Callable] = None) -> None:
        """Add a custom action to the toolbar."""
        if handler:
            self._actions[action_id] = handler
    
    def remove_action(self, action_id: str) -> None:
        """Remove an action from the toolbar."""
        self._actions.pop(action_id, None)
    
    def enable_action(self, action_id: str) -> None:
        """Enable a toolbar action."""
        # Would need to track button references for this
        pass
    
    def disable_action(self, action_id: str) -> None:
        """Disable a toolbar action."""
        # Would need to track button references for this
        pass
    
    def set_action_handler(self, action_id: str, handler: Callable) -> None:
        """Set handler for an action."""
        self._actions[action_id] = handler
    
    def _handle_new(self) -> None:
        """Handle new project action."""
        # Confirm if there are unsaved changes
        if self._app_state.is_dirty:
            with ui.dialog() as dialog, ui.card():
                ui.label('Unsaved changes will be lost. Continue?')
                with ui.row():
                    ui.button('Cancel', on_click=dialog.close)
                    ui.button('Continue', on_click=lambda: self._create_new_project(dialog))\
                        .props('color=primary')
            dialog.open()
        else:
            self._create_new_project()
    
    def _create_new_project(self, dialog=None) -> None:
        """Create a new project."""
        if dialog:
            dialog.close()
        
        # Clear state
        self._app_state.nodes.clear()
        self._app_state.edges.clear()
        self._app_state.groups.clear()
        self._app_state.clear_selection()
        self._app_state.history.clear()
        self._app_state.mark_clean()
        
        ui.notify('New project created', type='positive')
    
    def _handle_open(self) -> None:
        """Handle open file action."""
        if self._actions.get('open'):
            self._actions['open']()
    
    def _handle_save(self) -> None:
        """Handle save action."""
        if self._actions.get('save'):
            self._actions['save']()
            self._app_state.mark_clean()
    
    def _handle_undo(self) -> None:
        """Handle undo action."""
        if self._app_state.history.can_undo():
            self._app_state.history.undo()
            ui.notify('Undone', type='info')
    
    def _handle_redo(self) -> None:
        """Handle redo action."""
        if self._app_state.history.can_redo():
            self._app_state.history.redo()
            ui.notify('Redone', type='info')
    
    def _handle_add_node(self) -> None:
        """Handle add node action."""
        # Create dialog for node properties
        with ui.dialog() as dialog, ui.card():
            ui.label('Add New Node').classes('text-h6')
            
            name_input = ui.input('Name', placeholder='node1').classes('w-full')
            role_select = ui.select('Role', options=['client', 'relay'], value='client').classes('w-full')
            ip_input = ui.input('WireGuard IP', placeholder='10.0.0.1/24').classes('w-full')
            
            endpoint_container = ui.column().classes('w-full')
            with endpoint_container:
                endpoint_input = ui.input('Endpoint', placeholder='example.com:51820').classes('w-full')
            
            # Show/hide endpoint based on role
            def update_endpoint():
                endpoint_container.visible = role_select.value == 'relay'
            
            role_select.on('update:model-value', update_endpoint)
            update_endpoint()
            
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancel', on_click=dialog.close)
                ui.button('Add', on_click=lambda: self._create_node(
                    dialog, name_input.value, role_select.value, 
                    ip_input.value, endpoint_input.value
                )).props('color=primary')
        
        dialog.open()
    
    def _create_node(self, dialog, name: str, role: str, ip: str, endpoint: str) -> None:
        """Create a new node."""
        if not name:
            ui.notify('Name is required', type='negative')
            return
        
        # Check for duplicate name
        for node in self._app_state.nodes.values():
            if node.name == name:
                ui.notify('Node name already exists', type='negative')
                return
        
        dialog.close()
        
        # Create node
        node = NodeModel()
        node.name = name
        node.role = role
        node.wireguard_ip = ip if ip else None
        
        if role == 'relay' and endpoint:
            node.endpoints = {'default': endpoint}
        
        # Add to state
        cmd = AddNodeCommand(self._app_state, node)
        self._app_state.history.execute(cmd)
        
        ui.notify(f'Node "{name}" added', type='positive')
    
    def _handle_add_edge(self) -> None:
        """Handle add edge action."""
        # Need at least 2 nodes
        if len(self._app_state.nodes) < 2:
            ui.notify('Need at least 2 nodes to create an edge', type='warning')
            return
        
        # Create dialog for edge properties
        with ui.dialog() as dialog, ui.card():
            ui.label('Add New Edge').classes('text-h6')
            
            node_options = {node.id: node.name for node in self._app_state.nodes.values()}
            
            source_select = ui.select('From Node', options=node_options).classes('w-full')
            target_select = ui.select('To Node', options=node_options).classes('w-full')
            
            ui.label('Allowed IPs').classes('text-subtitle2 mt-2')
            allowed_ips = []
            ips_container = ui.column().classes('w-full gap-2')
            
            def add_ip():
                with ips_container:
                    with ui.row().classes('w-full gap-2'):
                        ip_input = ui.input('IP Range', placeholder='10.0.0.0/24').classes('flex-grow')
                        ui.button(icon='delete', on_click=lambda: remove_ip(ip_input)).props('flat dense')
                        allowed_ips.append(ip_input)
            
            def remove_ip(ip_input):
                allowed_ips.remove(ip_input)
                ip_input.parent_slot.parent.delete()
            
            with ips_container:
                add_ip()  # Add first IP input
            
            ui.button('Add IP Range', icon='add', on_click=add_ip).props('flat')
            
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancel', on_click=dialog.close)
                ui.button('Add', on_click=lambda: self._create_edge(
                    dialog, source_select.value, target_select.value,
                    [ip.value for ip in allowed_ips if ip.value]
                )).props('color=primary')
        
        dialog.open()
    
    def _create_edge(self, dialog, source_id: str, target_id: str, allowed_ips: list) -> None:
        """Create a new edge."""
        if not source_id or not target_id:
            ui.notify('Please select both nodes', type='negative')
            return
        
        if source_id == target_id:
            ui.notify('Cannot connect node to itself', type='negative')
            return
        
        # Check for duplicate edge
        for edge in self._app_state.edges.values():
            if ((edge.source_id == source_id and edge.target_id == target_id) or
                (edge.source_id == target_id and edge.target_id == source_id)):
                ui.notify('Edge already exists between these nodes', type='negative')
                return
        
        dialog.close()
        
        # Create edge
        edge = EdgeModel()
        edge.source_id = source_id
        edge.target_id = target_id
        edge.allowed_ips = allowed_ips
        
        # Add to state
        cmd = AddEdgeCommand(self._app_state, edge)
        self._app_state.history.execute(cmd)
        
        ui.notify('Edge added', type='positive')
    
    def _handle_add_group(self) -> None:
        """Handle add group action."""
        # Create dialog for group properties
        with ui.dialog() as dialog, ui.card():
            ui.label('Add New Group').classes('text-h6')
            
            name_input = ui.input('Name', placeholder='group1').classes('w-full')
            topology_select = ui.select(
                'Topology', 
                options=['mesh', 'star', 'chain', 'single'],
                value='mesh'
            ).classes('w-full')
            color_input = ui.color_input('Color', value='#0080FF').classes('w-full')
            
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancel', on_click=dialog.close)
                ui.button('Add', on_click=lambda: self._create_group(
                    dialog, name_input.value, topology_select.value, color_input.value
                )).props('color=primary')
        
        dialog.open()
    
    def _create_group(self, dialog, name: str, topology: str, color: str) -> None:
        """Create a new group."""
        if not name:
            ui.notify('Name is required', type='negative')
            return
        
        # Check for duplicate name
        for group in self._app_state.groups.values():
            if group.name == name:
                ui.notify('Group name already exists', type='negative')
                return
        
        dialog.close()
        
        # Create group
        group = GroupModel()
        group.name = name
        group.topology = topology
        group.color = color
        
        # Add to state
        cmd = AddGroupCommand(self._app_state, group)
        self._app_state.history.execute(cmd)
        
        ui.notify(f'Group "{name}" added', type='positive')
    
    def _handle_delete(self) -> None:
        """Handle delete action."""
        selected = self._app_state.selected_elements
        if not selected:
            ui.notify('Nothing selected to delete', type='warning')
            return
        
        # Confirm deletion
        count = len(selected)
        with ui.dialog() as dialog, ui.card():
            ui.label(f'Delete {count} selected item(s)?')
            with ui.row():
                ui.button('Cancel', on_click=dialog.close)
                ui.button('Delete', on_click=lambda: self._delete_selected(dialog))\
                    .props('color=negative')
        
        dialog.open()
    
    def _delete_selected(self, dialog) -> None:
        """Delete selected items."""
        dialog.close()
        
        # Use batch command for multiple deletions
        if len(self._app_state.selected_elements) > 1:
            self._app_state.history.begin_batch('Delete multiple items')
        
        # Delete each selected item
        for element_id in list(self._app_state.selected_elements):
            if element_id in self._app_state.nodes:
                cmd = DeleteNodeCommand(self._app_state, element_id)
                self._app_state.history.execute(cmd)
            elif element_id in self._app_state.edges:
                cmd = DeleteEdgeCommand(self._app_state, element_id)
                self._app_state.history.execute(cmd)
            elif element_id in self._app_state.groups:
                cmd = DeleteGroupCommand(self._app_state, element_id)
                self._app_state.history.execute(cmd)
        
        # End batch
        if len(self._app_state.selected_elements) > 1:
            self._app_state.history.end_batch()
        
        ui.notify('Deleted', type='info')
    
    def _handle_layout(self) -> None:
        """Handle auto layout action."""
        if self._actions.get('layout'):
            self._actions['layout']()
        else:
            ui.notify('Auto layout applied', type='info')
    
    def _handle_fit(self) -> None:
        """Handle fit view action."""
        if self._actions.get('fit'):
            self._actions['fit']()
        else:
            ui.notify('View fitted', type='info')
    
    def _handle_validate(self) -> None:
        """Handle validate action."""
        if self._actions.get('validate'):
            self._actions['validate']()
    
    def _handle_export(self) -> None:
        """Handle export action."""
        if self._actions.get('export'):
            self._actions['export']()
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to state events."""
        # History events (no direct events, so we'll check periodically)
        ui.timer(0.5, self._update_button_states)
        
        # Selection events
        self._app_state.subscribe('selection_changed', self._on_selection_changed)
    
    def _update_button_states(self) -> None:
        """Update button enabled states."""
        # Update undo/redo
        can_undo = self._app_state.history.can_undo()
        can_redo = self._app_state.history.can_redo()
        
        if hasattr(self, '_undo_btn'):
            self._undo_btn.enabled = can_undo
            if can_undo:
                desc = self._app_state.history.get_undo_description()
                self._undo_btn.tooltip(f'Undo: {desc}' if desc else 'Undo')
        
        if hasattr(self, '_redo_btn'):
            self._redo_btn.enabled = can_redo
            if can_redo:
                desc = self._app_state.history.get_redo_description()
                self._redo_btn.tooltip(f'Redo: {desc}' if desc else 'Redo')
        
        # Update delete button
        if hasattr(self, '_delete_btn'):
            self._delete_btn.enabled = self._has_selection
    
    def _on_selection_changed(self, event) -> None:
        """Handle selection change."""
        self._has_selection = bool(event.data.get('selected', []))
        self._update_button_states()