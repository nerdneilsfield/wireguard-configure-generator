"""
Property panel implementation for editing node, edge, and group properties.

This component provides forms for editing properties of selected elements.
"""

from typing import Dict, List, Optional, Callable, Any
import ipaddress

from nicegui import ui

from .base import BaseComponent
from ..interfaces.components import IPropertyPanel
from ..interfaces.state import IAppState
from ..state import UpdateNodeCommand, UpdateEdgeCommand, UpdateGroupCommand


class PropertyPanel(BaseComponent, IPropertyPanel):
    """Implementation of IPropertyPanel for property editing."""
    
    def __init__(self, 
                 app_state: IAppState,
                 width: str = "300px",
                 component_id: Optional[str] = None):
        """
        Initialize property panel.
        
        Args:
            app_state: Application state
            width: Panel width
            component_id: Optional component ID
        """
        super().__init__(component_id)
        self._app_state = app_state
        self._width = width
        self._target_id: Optional[str] = None
        self._target_type: Optional[str] = None  # 'node', 'edge', or 'group'
        
        # Form inputs
        self._inputs: Dict[str, Any] = {}
        self._on_save: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self._on_delete: Optional[Callable[[str], None]] = None
        
        # Validation errors
        self._errors: Dict[str, str] = {}
    
    @property
    def target_id(self) -> Optional[str]:
        """Get target element ID."""
        return self._target_id
    
    @target_id.setter
    def target_id(self, value: Optional[str]) -> None:
        """Set target element ID."""
        self._target_id = value
        if value:
            self.load_properties(value)
        else:
            self.clear()
    
    def render(self) -> ui.element:
        """Render the property panel."""
        with ui.card().classes(f'w-[{self._width}]') as container:
            with ui.column().classes('w-full gap-4') as self._element:
                # Title
                self._title = ui.label('Properties').classes('text-h6')
                
                # Content will be dynamically created based on target
                self._content = ui.column().classes('w-full gap-2')
                
                # Action buttons
                with ui.row().classes('w-full justify-end gap-2') as self._actions:
                    self._save_btn = ui.button('Save', on_click=self._handle_save)\
                        .props('color=primary')\
                        .classes('px-4')
                    self._delete_btn = ui.button('Delete', on_click=self._handle_delete)\
                        .props('color=negative')\
                        .classes('px-4')
                
                # Initially hidden
                self._actions.visible = False
        
        return container
    
    def load_properties(self, element_id: str) -> None:
        """Load properties for an element."""
        self._target_id = element_id
        self._errors.clear()
        
        # Determine element type and load appropriate form
        if element_id in self._app_state.nodes:
            self._target_type = 'node'
            self._load_node_properties(self._app_state.nodes[element_id])
        elif element_id in self._app_state.edges:
            self._target_type = 'edge'
            self._load_edge_properties(self._app_state.edges[element_id])
        elif element_id in self._app_state.groups:
            self._target_type = 'group'
            self._load_group_properties(self._app_state.groups[element_id])
        else:
            self.clear()
    
    def _load_node_properties(self, node: Any) -> None:
        """Load node properties into form."""
        self._title.text = f'Node: {node.name}'
        self._content.clear()
        self._inputs.clear()
        
        with self._content:
            # Name input
            self._inputs['name'] = ui.input('Name', value=node.name)\
                .classes('w-full')\
                .on('blur', lambda: self._validate_field('name'))
            
            # Role selection
            self._inputs['role'] = ui.select(
                label='Role',
                options=['client', 'relay'],
                value=node.role
            ).classes('w-full')
            
            # WireGuard IP input
            self._inputs['wireguard_ip'] = ui.input(
                'WireGuard IP',
                value=node.wireguard_ip or '',
                placeholder='10.0.0.1/24'
            ).classes('w-full')\
             .on('blur', lambda: self._validate_field('wireguard_ip'))
            
            # Endpoint input (only for relay nodes)
            endpoint_container = ui.column().classes('w-full')
            with endpoint_container:
                self._inputs['endpoint'] = ui.input(
                    'Endpoint',
                    value=node.endpoint or '',
                    placeholder='example.com:51820'
                ).classes('w-full')\
                 .on('blur', lambda: self._validate_field('endpoint'))
            
            # Show/hide endpoint based on role
            def update_endpoint_visibility():
                endpoint_container.visible = self._inputs['role'].value == 'relay'
            
            self._inputs['role'].on('update:model-value', update_endpoint_visibility)
            update_endpoint_visibility()
            
            # Group assignment
            group_options = {'': 'No Group'}
            group_options.update({
                g.id: g.name for g in self._app_state.groups.values()
            })
            
            self._inputs['group_id'] = ui.select(
                label='Group',
                options=group_options,
                value=node.group_id or ''
            ).classes('w-full')
            
            # Metadata section
            ui.separator()
            ui.label('Metadata').classes('text-subtitle2')
            
            # Listen port
            self._inputs['listen_port'] = ui.number(
                'Listen Port',
                value=node.metadata.get('listen_port', 51820),
                min=1,
                max=65535
            ).classes('w-full')
            
            # Enable IP forwarding
            self._inputs['enable_ip_forward'] = ui.switch(
                'Enable IP Forwarding',
                value=node.metadata.get('enable_ip_forward', False)
            )
        
        self._actions.visible = True
    
    def _load_edge_properties(self, edge: Any) -> None:
        """Load edge properties into form."""
        source = self._app_state.nodes.get(edge.source_id)
        target = self._app_state.nodes.get(edge.target_id)
        
        source_name = source.name if source else edge.source_id
        target_name = target.name if target else edge.target_id
        
        self._title.text = f'Edge: {source_name} → {target_name}'
        self._content.clear()
        self._inputs.clear()
        
        with self._content:
            # Connection info (read-only)
            ui.label(f'From: {source_name}').classes('text-caption')
            ui.label(f'To: {target_name}').classes('text-caption')
            ui.separator()
            
            # Allowed IPs
            ui.label('Allowed IPs').classes('text-subtitle2')
            
            # Current allowed IPs
            self._inputs['allowed_ips'] = []
            allowed_ips_container = ui.column().classes('w-full gap-2')
            
            with allowed_ips_container:
                for i, ip in enumerate(edge.allowed_ips or []):
                    with ui.row().classes('w-full gap-2'):
                        ip_input = ui.input(
                            f'IP Range {i+1}',
                            value=ip
                        ).classes('flex-grow')\
                         .on('blur', lambda idx=i: self._validate_allowed_ip(idx))
                        
                        ui.button(
                            icon='delete',
                            on_click=lambda idx=i: self._remove_allowed_ip(idx)
                        ).props('flat dense')
                        
                        self._inputs['allowed_ips'].append(ip_input)
                
                # Add new IP button
                ui.button(
                    'Add IP Range',
                    icon='add',
                    on_click=lambda: self._add_allowed_ip(allowed_ips_container)
                ).props('flat')
            
            # Persistent keepalive
            ui.separator()
            self._inputs['persistent_keepalive'] = ui.number(
                'Persistent Keepalive (seconds)',
                value=edge.metadata.get('persistent_keepalive', 0),
                min=0
            ).classes('w-full')
            
            # Endpoint selection
            if source and source.endpoints:
                endpoint_options = list(source.endpoints.keys())
                current_endpoint = edge.metadata.get('endpoint_key', 'default')
                
                self._inputs['endpoint_key'] = ui.select(
                    label='Source Endpoint',
                    options=endpoint_options,
                    value=current_endpoint if current_endpoint in endpoint_options else endpoint_options[0]
                ).classes('w-full')
        
        self._actions.visible = True
    
    def _load_group_properties(self, group: Any) -> None:
        """Load group properties into form."""
        self._title.text = f'Group: {group.name}'
        self._content.clear()
        self._inputs.clear()
        
        with self._content:
            # Name input
            self._inputs['name'] = ui.input('Name', value=group.name)\
                .classes('w-full')\
                .on('blur', lambda: self._validate_field('name'))
            
            # Topology selection
            self._inputs['topology'] = ui.select(
                label='Topology',
                options=['mesh', 'star', 'chain', 'single'],
                value=group.topology
            ).classes('w-full')
            
            # Color picker
            self._inputs['color'] = ui.color_input(
                label='Color',
                value=group.color
            ).classes('w-full')
            
            # Mesh endpoint (only for mesh topology)
            mesh_container = ui.column().classes('w-full')
            with mesh_container:
                self._inputs['mesh_endpoint'] = ui.input(
                    'Mesh Endpoint Name',
                    value=group.mesh_endpoint or '',
                    placeholder='internal'
                ).classes('w-full')
            
            # Show/hide mesh endpoint based on topology
            def update_mesh_visibility():
                mesh_container.visible = self._inputs['topology'].value == 'mesh'
            
            self._inputs['topology'].on('update:model-value', update_mesh_visibility)
            update_mesh_visibility()
            
            # Group members
            ui.separator()
            ui.label('Group Members').classes('text-subtitle2')
            
            members_list = ui.column().classes('w-full gap-1')
            with members_list:
                for node_id in group.nodes:
                    node = self._app_state.nodes.get(node_id)
                    if node:
                        with ui.row().classes('w-full items-center'):
                            ui.icon('person').classes('text-lg')
                            ui.label(node.name).classes('flex-grow')
                
                if not group.nodes:
                    ui.label('No members').classes('text-caption text-gray-500')
            
            # Node count validation
            ui.label(f'Members: {len(group.nodes)}').classes('text-caption')
            
            # Topology constraints
            constraints = {
                'single': 'Requires exactly 1 node',
                'mesh': 'Requires at least 2 nodes',
                'star': 'Requires at least 3 nodes',
                'chain': 'Requires at least 2 nodes'
            }
            
            constraint_label = ui.label(constraints.get(group.topology, ''))\
                .classes('text-caption text-orange-600')
            
            def update_constraint():
                constraint_label.text = constraints.get(self._inputs['topology'].value, '')
            
            self._inputs['topology'].on('update:model-value', update_constraint)
        
        self._actions.visible = True
    
    def save_properties(self) -> Dict[str, Any]:
        """Save current property values."""
        if not self._target_id or not self._target_type:
            return {}
        
        # Validate all fields
        if not self._validate_all():
            ui.notify('Please fix validation errors', type='negative')
            return {}
        
        # Collect values based on type
        if self._target_type == 'node':
            return self._save_node_properties()
        elif self._target_type == 'edge':
            return self._save_edge_properties()
        elif self._target_type == 'group':
            return self._save_group_properties()
        
        return {}
    
    def _save_node_properties(self) -> Dict[str, Any]:
        """Collect node property values."""
        updates = {
            'name': self._inputs['name'].value,
            'role': self._inputs['role'].value,
            'wireguard_ip': self._inputs['wireguard_ip'].value or None,
            'group_id': self._inputs['group_id'].value or None
        }
        
        # Handle endpoint
        if self._inputs['role'].value == 'relay' and self._inputs['endpoint'].value:
            updates['endpoint'] = self._inputs['endpoint'].value
        
        # Metadata updates
        metadata_updates = {
            'listen_port': int(self._inputs['listen_port'].value),
            'enable_ip_forward': self._inputs['enable_ip_forward'].value
        }
        
        # Apply updates through command
        cmd = UpdateNodeCommand(
            self._app_state,
            self._target_id,
            {**updates, 'metadata': metadata_updates}
        )
        self._app_state.history.execute(cmd)
        
        return updates
    
    def _save_edge_properties(self) -> Dict[str, Any]:
        """Collect edge property values."""
        # Collect allowed IPs
        allowed_ips = []
        for ip_input in self._inputs.get('allowed_ips', []):
            if ip_input.value:
                allowed_ips.append(ip_input.value)
        
        updates = {
            'allowed_ips': allowed_ips
        }
        
        # Metadata updates
        metadata_updates = {
            'persistent_keepalive': int(self._inputs['persistent_keepalive'].value)
        }
        
        if 'endpoint_key' in self._inputs:
            metadata_updates['endpoint_key'] = self._inputs['endpoint_key'].value
        
        # Apply updates through command
        cmd = UpdateEdgeCommand(
            self._app_state,
            self._target_id,
            {**updates, 'metadata': metadata_updates}
        )
        self._app_state.history.execute(cmd)
        
        return updates
    
    def _save_group_properties(self) -> Dict[str, Any]:
        """Collect group property values."""
        updates = {
            'name': self._inputs['name'].value,
            'topology': self._inputs['topology'].value,
            'color': self._inputs['color'].value
        }
        
        if self._inputs['topology'].value == 'mesh':
            updates['mesh_endpoint'] = self._inputs['mesh_endpoint'].value or None
        
        # Apply updates through command
        cmd = UpdateGroupCommand(self._app_state, self._target_id, updates)
        self._app_state.history.execute(cmd)
        
        return updates
    
    def clear(self) -> None:
        """Clear the property panel."""
        self._target_id = None
        self._target_type = None
        self._title.text = 'Properties'
        self._content.clear()
        self._inputs.clear()
        self._errors.clear()
        self._actions.visible = False
    
    def on_save(self, handler: Callable[[str, Dict[str, Any]], None]) -> None:
        """Register save handler."""
        self._on_save = handler
    
    def on_delete(self, handler: Callable[[str], None]) -> None:
        """Register delete handler."""
        self._on_delete = handler
    
    def _handle_save(self) -> None:
        """Handle save button click."""
        properties = self.save_properties()
        if properties and self._on_save and self._target_id:
            self._on_save(self._target_id, properties)
            ui.notify('Properties saved', type='positive')
    
    def _handle_delete(self) -> None:
        """Handle delete button click."""
        if self._target_id and self._on_delete:
            # Confirm deletion
            with ui.dialog() as dialog, ui.card():
                ui.label(f'Delete this {self._target_type}?')
                with ui.row():
                    ui.button('Cancel', on_click=dialog.close)
                    ui.button('Delete', on_click=lambda: self._confirm_delete(dialog))\
                        .props('color=negative')
            
            dialog.open()
    
    def _confirm_delete(self, dialog) -> None:
        """Confirm and execute deletion."""
        dialog.close()
        
        if self._target_id and self._on_delete:
            self._on_delete(self._target_id)
            self.clear()
            ui.notify(f'{self._target_type.capitalize()} deleted', type='info')
    
    def _validate_field(self, field: str) -> bool:
        """Validate a specific field."""
        if field == 'name':
            value = self._inputs['name'].value
            if not value:
                self._show_error('name', 'Name is required')
                return False
            elif not value.replace('-', '').replace('_', '').isalnum():
                self._show_error('name', 'Name must be alphanumeric with - and _')
                return False
            else:
                self._clear_error('name')
                return True
        
        elif field == 'wireguard_ip':
            value = self._inputs['wireguard_ip'].value
            if value:
                try:
                    ipaddress.ip_network(value, strict=False)
                    self._clear_error('wireguard_ip')
                    return True
                except ValueError:
                    self._show_error('wireguard_ip', 'Invalid IP address format')
                    return False
            else:
                self._clear_error('wireguard_ip')
                return True
        
        elif field == 'endpoint':
            value = self._inputs['endpoint'].value
            if value and ':' not in value:
                self._show_error('endpoint', 'Endpoint must be in host:port format')
                return False
            else:
                self._clear_error('endpoint')
                return True
        
        return True
    
    def _validate_allowed_ip(self, index: int) -> bool:
        """Validate an allowed IP input."""
        if index < len(self._inputs.get('allowed_ips', [])):
            ip_input = self._inputs['allowed_ips'][index]
            value = ip_input.value
            
            if value:
                try:
                    ipaddress.ip_network(value, strict=False)
                    ip_input.error = False
                    return True
                except ValueError:
                    ip_input.error = 'Invalid IP network format'
                    return False
        
        return True
    
    def _validate_all(self) -> bool:
        """Validate all fields."""
        valid = True
        
        if self._target_type == 'node':
            valid &= self._validate_field('name')
            valid &= self._validate_field('wireguard_ip')
            if self._inputs['role'].value == 'relay':
                valid &= self._validate_field('endpoint')
        
        elif self._target_type == 'edge':
            for i in range(len(self._inputs.get('allowed_ips', []))):
                valid &= self._validate_allowed_ip(i)
        
        elif self._target_type == 'group':
            valid &= self._validate_field('name')
        
        return valid
    
    def _show_error(self, field: str, message: str) -> None:
        """Show error for a field."""
        if field in self._inputs:
            self._inputs[field].error = message
        self._errors[field] = message
    
    def _clear_error(self, field: str) -> None:
        """Clear error for a field."""
        if field in self._inputs:
            self._inputs[field].error = False
        self._errors.pop(field, None)
    
    def _add_allowed_ip(self, container) -> None:
        """Add a new allowed IP input."""
        with container:
            with ui.row().classes('w-full gap-2'):
                idx = len(self._inputs.get('allowed_ips', []))
                ip_input = ui.input(
                    f'IP Range {idx+1}',
                    value=''
                ).classes('flex-grow')\
                 .on('blur', lambda: self._validate_allowed_ip(idx))
                
                ui.button(
                    icon='delete',
                    on_click=lambda: self._remove_allowed_ip(idx)
                ).props('flat dense')
                
                self._inputs['allowed_ips'].append(ip_input)
    
    def _remove_allowed_ip(self, index: int) -> None:
        """Remove an allowed IP input."""
        if index < len(self._inputs.get('allowed_ips', [])):
            # Remove the input
            self._inputs['allowed_ips'].pop(index)
            
            # Rebuild the UI
            if self._target_id and self._target_type == 'edge':
                self.load_properties(self._target_id)
    
    # Missing IPropertyPanel interface methods
    
    def validate(self) -> List[str]:
        """Validate current property values."""
        errors = []
        
        if self._target_type == 'node':
            # Validate node properties
            if 'name' in self._inputs and not self._inputs['name'].value.strip():
                errors.append("Node name is required")
            
            if 'wireguard_ip' in self._inputs and self._inputs['wireguard_ip'].value:
                try:
                    ipaddress.ip_interface(self._inputs['wireguard_ip'].value)
                except ValueError:
                    errors.append("Invalid WireGuard IP format")
        
        elif self._target_type == 'edge':
            # Validate edge properties
            if 'allowed_ips' in self._inputs:
                for i, ip_input in enumerate(self._inputs['allowed_ips']):
                    if ip_input.value.strip():
                        try:
                            ipaddress.ip_network(ip_input.value, strict=False)
                        except ValueError:
                            errors.append(f"Invalid allowed IP format at position {i+1}")
        
        elif self._target_type == 'group':
            # Validate group properties
            if 'name' in self._inputs and not self._inputs['name'].value.strip():
                errors.append("Group name is required")
        
        return errors
    
    def reset(self) -> None:
        """Reset the panel to empty state."""
        self._target_id = None
        self._target_type = None
        self._inputs.clear()
        self._errors.clear()
        
        # Clear the UI
        if hasattr(self, '_element') and self._element:
            self._element.clear()
    
    def on_property_change(self, handler: Callable[[str, str, Any], None]) -> None:
        """Register property change handler."""
        # Store the handler for property change events
        self._on_property_change = handler
        
        # Set up property change listeners for existing inputs
        for prop_name, input_element in self._inputs.items():
            if hasattr(input_element, 'on'):
                input_element.on('update:model-value', 
                    lambda value, prop=prop_name: handler(self._target_id or '', prop, value))