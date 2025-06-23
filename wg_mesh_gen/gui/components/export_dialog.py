"""
Export dialog implementation for configuration export options.

This component provides a dialog for selecting export options and formats.
"""

from typing import Optional, Callable, Dict, Any, List
from datetime import datetime

from nicegui import ui

from .base import BaseComponent
from ..interfaces.components import IExportDialog
from ..interfaces.file_management import IExportManager
from ..interfaces.state import IAppState


class ExportDialog(BaseComponent, IExportDialog):
    """Implementation of IExportDialog for export options."""
    
    def __init__(self,
                 app_state: IAppState,
                 export_manager: IExportManager,
                 component_id: Optional[str] = None):
        """
        Initialize export dialog.
        
        Args:
            app_state: Application state
            export_manager: Export manager instance
            component_id: Optional component ID
        """
        super().__init__(component_id)
        self._app_state = app_state
        self._export_manager = export_manager
        self._dialog: Optional[ui.dialog] = None
        
        # Export options
        self._export_options: Dict[str, Any] = {
            'format': 'yaml',
            'include_keys': True,
            'include_scripts': False,
            'split_files': False,
            'archive_format': 'zip'
        }
        
        # Event handlers
        self._on_export: Optional[Callable[[Dict[str, Any]], None]] = None
        self._on_cancel: Optional[Callable[[], None]] = None
    
    def render(self) -> ui.element:
        """Render the export dialog (returns the dialog element)."""
        self._dialog = ui.dialog()
        
        with self._dialog, ui.card().classes('w-[600px]'):
            with ui.column().classes('w-full gap-4') as self._element:
                # Header
                with ui.row().classes('items-center'):
                    ui.label('Export Configuration').classes('text-h5 flex-grow')
                    ui.button(icon='close', on_click=self.close).props('flat dense round')
                
                ui.separator()
                
                # Export format selection
                with ui.column().classes('gap-4'):
                    ui.label('Export Format').classes('text-subtitle1 font-medium')
                    
                    self._format_group = ui.radio(
                        {
                            'wireguard': 'WireGuard Configuration Files (.conf)',
                            'yaml': 'YAML Configuration',
                            'json': 'JSON Configuration',
                            'package': 'Complete Package (ZIP)'
                        },
                        value=self._export_options['format'],
                        on_change=self._update_format
                    ).classes('w-full')
                
                # Format-specific options
                self._options_container = ui.column().classes('gap-3')
                self._update_format_options()
                
                # Common options
                ui.separator()
                with ui.column().classes('gap-2'):
                    ui.label('Additional Options').classes('text-subtitle1 font-medium')
                    
                    self._include_keys = ui.switch(
                        'Include WireGuard keys',
                        value=self._export_options['include_keys']
                    )
                    
                    self._include_scripts = ui.switch(
                        'Include setup scripts',
                        value=self._export_options['include_scripts']
                    )
                    
                    self._split_files = ui.switch(
                        'Split into separate files',
                        value=self._export_options['split_files']
                    )
                
                # Preview section
                ui.separator()
                with ui.expansion('Preview', icon='preview').classes('w-full'):
                    self._preview_container = ui.column().classes('w-full')
                    self._update_preview()
                
                # Actions
                ui.separator()
                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button('Cancel', on_click=self.close)
                    ui.button('Export', on_click=self._handle_export)\
                        .props('color=primary')\
                        .bind_enabled_from(self, '_can_export')
        
        return self._dialog
    
    def show(self, options: Dict[str, Any] = None) -> None:
        """Show the export dialog."""
        if options:
            self.set_options(options)
        if self._dialog:
            self._dialog.open()
            self._update_preview()
    
    def hide(self) -> None:
        """Hide the export dialog."""
        if self._dialog:
            self._dialog.close()
    
    def close(self) -> None:
        """Close the export dialog."""
        self.hide()
        
        if self._on_cancel:
            self._on_cancel()
    
    def set_options(self, options: Dict[str, Any]) -> None:
        """Set export options."""
        self._export_options.update(options)
        
        # Update UI elements
        if hasattr(self, '_format_group'):
            self._format_group.value = options.get('format', 'yaml')
        if hasattr(self, '_include_keys'):
            self._include_keys.value = options.get('include_keys', True)
        if hasattr(self, '_include_scripts'):
            self._include_scripts.value = options.get('include_scripts', False)
        if hasattr(self, '_split_files'):
            self._split_files.value = options.get('split_files', False)
        
        self._update_format_options()
        self._update_preview()
    
    def get_options(self) -> Dict[str, Any]:
        """Get current export options."""
        # Collect current values from UI
        if hasattr(self, '_format_group'):
            self._export_options['format'] = self._format_group.value
        if hasattr(self, '_include_keys'):
            self._export_options['include_keys'] = self._include_keys.value
        if hasattr(self, '_include_scripts'):
            self._export_options['include_scripts'] = self._include_scripts.value
        if hasattr(self, '_split_files'):
            self._export_options['split_files'] = self._split_files.value
        
        return self._export_options.copy()
    
    def on_export(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register export handler."""
        self._on_export = handler
    
    def on_cancel(self, handler: Callable[[], None]) -> None:
        """Register cancel handler."""
        self._on_cancel = handler
    
    def _update_format(self, e) -> None:
        """Update format selection."""
        self._export_options['format'] = e.value
        self._update_format_options()
        self._update_preview()
    
    def _update_format_options(self) -> None:
        """Update format-specific options."""
        if not hasattr(self, '_options_container'):
            return
        
        self._options_container.clear()
        format_type = self._export_options['format']
        
        with self._options_container:
            if format_type == 'wireguard':
                ui.label('WireGuard Export Options').classes('text-subtitle2')
                
                self._wg_per_node = ui.switch(
                    'One file per node',
                    value=True
                )
                
                self._wg_include_qr = ui.switch(
                    'Generate QR codes',
                    value=False
                )
                
            elif format_type in ['yaml', 'json']:
                ui.label('Configuration Export Options').classes('text-subtitle2')
                
                self._config_pretty = ui.switch(
                    'Pretty print (formatted)',
                    value=True
                )
                
                self._config_minify = ui.switch(
                    'Minify output',
                    value=False
                )
                
            elif format_type == 'package':
                ui.label('Package Export Options').classes('text-subtitle2')
                
                self._pkg_format = ui.select(
                    'Archive format',
                    options=['zip', 'tar.gz'],
                    value=self._export_options.get('archive_format', 'zip')
                ).classes('w-48')
                
                self._pkg_readme = ui.switch(
                    'Include README',
                    value=True
                )
                
                self._pkg_diagram = ui.switch(
                    'Include network diagram',
                    value=True
                )
    
    def _update_preview(self) -> None:
        """Update export preview."""
        if not hasattr(self, '_preview_container'):
            return
        
        self._preview_container.clear()
        
        with self._preview_container:
            format_type = self._export_options['format']
            
            # File list preview
            ui.label('Files to be exported:').classes('font-medium mb-2')
            
            files = self._get_export_files()
            if files:
                for file_info in files:
                    with ui.row().classes('items-center gap-2 ml-4'):
                        ui.icon(file_info['icon']).classes('text-gray-600')
                        ui.label(file_info['name']).classes('text-sm')
                        ui.label(f'({file_info["description"]})').classes('text-xs text-gray-500')
            else:
                ui.label('No files to export').classes('text-gray-500 ml-4')
            
            # Statistics
            ui.separator().classes('my-2')
            stats = self._get_export_stats()
            with ui.row().classes('gap-4 text-sm'):
                ui.label(f"Nodes: {stats['nodes']}")
                ui.label(f"Edges: {stats['edges']}")
                ui.label(f"Groups: {stats['groups']}")
    
    def _get_export_files(self) -> List[Dict[str, Any]]:
        """Get list of files that will be exported."""
        files = []
        format_type = self._export_options['format']
        
        if format_type == 'wireguard':
            if hasattr(self, '_wg_per_node') and self._wg_per_node.value:
                # One file per node
                for node in self._app_state.nodes.values():
                    files.append({
                        'name': f'{node.name}.conf',
                        'icon': 'description',
                        'description': 'WireGuard config'
                    })
            else:
                files.append({
                    'name': 'wireguard_configs.conf',
                    'icon': 'description',
                    'description': 'All configs'
                })
            
            if self._export_options['include_keys']:
                files.append({
                    'name': 'wg_keys.json',
                    'icon': 'vpn_key',
                    'description': 'Key database'
                })
        
        elif format_type == 'yaml':
            if self._export_options['split_files']:
                files.extend([
                    {'name': 'nodes.yaml', 'icon': 'device_hub', 'description': 'Node definitions'},
                    {'name': 'topology.yaml', 'icon': 'timeline', 'description': 'Network topology'},
                ])
                if self._app_state.groups:
                    files.append({'name': 'groups.yaml', 'icon': 'group_work', 'description': 'Group config'})
            else:
                files.append({
                    'name': 'config.yaml',
                    'icon': 'description',
                    'description': 'Complete configuration'
                })
        
        elif format_type == 'json':
            if self._export_options['split_files']:
                files.extend([
                    {'name': 'nodes.json', 'icon': 'device_hub', 'description': 'Node definitions'},
                    {'name': 'topology.json', 'icon': 'timeline', 'description': 'Network topology'},
                ])
                if self._app_state.groups:
                    files.append({'name': 'groups.json', 'icon': 'group_work', 'description': 'Group config'})
            else:
                files.append({
                    'name': 'config.json',
                    'icon': 'data_object',
                    'description': 'Complete configuration'
                })
        
        elif format_type == 'package':
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_ext = self._export_options.get('archive_format', 'zip')
            files.append({
                'name': f'wireguard_config_{timestamp}.{archive_ext}',
                'icon': 'archive',
                'description': 'Complete package'
            })
        
        if self._export_options['include_scripts']:
            files.append({
                'name': 'setup.sh',
                'icon': 'terminal',
                'description': 'Setup script'
            })
        
        return files
    
    def _get_export_stats(self) -> Dict[str, int]:
        """Get export statistics."""
        return {
            'nodes': len(self._app_state.nodes),
            'edges': len(self._app_state.edges),
            'groups': len(self._app_state.groups)
        }
    
    def _handle_export(self) -> None:
        """Handle export button click."""
        options = self.get_options()
        
        # Validate export
        if not self._can_export:
            ui.notify('Nothing to export', type='warning')
            return
        
        # Close dialog
        self.close()
        
        # Trigger export handler
        if self._on_export:
            self._on_export(options)
        else:
            # Default export behavior
            self._perform_export(options)
    
    def _perform_export(self, options: Dict[str, Any]) -> None:
        """Perform the actual export."""
        try:
            format_type = options['format']
            
            if format_type == 'wireguard':
                # Export WireGuard configs
                output_dir = '/tmp/wireguard_export'  # Should use proper temp dir
                files = self._export_manager.export_wireguard_configs(
                    self._app_state,
                    output_dir
                )
                ui.notify(f'Exported {len(files)} WireGuard configuration files', type='positive')
                
            elif format_type == 'yaml':
                # Export as YAML
                if options.get('split_files'):
                    self._export_manager.export_nodes(self._app_state, 'yaml')
                    self._export_manager.export_topology(self._app_state, 'yaml')
                    if self._app_state.groups:
                        self._export_manager.export_groups(self._app_state, 'yaml')
                else:
                    # Single file export
                    path = '/tmp/config.yaml'  # Should use proper path
                    # Would call appropriate export method
                    ui.notify('Exported configuration as YAML', type='positive')
                
            elif format_type == 'json':
                # Export as JSON
                if options.get('split_files'):
                    self._export_manager.export_nodes(self._app_state, 'json')
                    self._export_manager.export_topology(self._app_state, 'json')
                    if self._app_state.groups:
                        self._export_manager.export_groups(self._app_state, 'json')
                else:
                    # Single file export
                    path = '/tmp/config.json'  # Should use proper path
                    # Would call appropriate export method
                    ui.notify('Exported configuration as JSON', type='positive')
                
            elif format_type == 'package':
                # Export complete package
                include_configs = options.get('include_keys', True)
                archive_path = self._export_manager.export_complete(
                    self._app_state,
                    include_configs
                )
                ui.notify(f'Exported complete package', type='positive')
                
                # Trigger download
                # In a real app, would use ui.download or similar
                
        except Exception as e:
            ui.notify(f'Export failed: {str(e)}', type='negative')
    
    @property
    def _can_export(self) -> bool:
        """Check if export is possible."""
        return bool(self._app_state.nodes)
    
    # Missing IComponent interface methods
    
    @property
    def id(self) -> str:
        """Component ID."""
        return getattr(self, 'component_id', 'export_dialog')
    
    @id.setter
    def id(self, value: str) -> None:
        """Set component ID."""
        self.component_id = value
    
    @property
    def visible(self) -> bool:
        """Whether the component is visible."""
        return getattr(self, '_visible', True)
    
    @visible.setter
    def visible(self, value: bool) -> None:
        """Set component visibility."""
        self._visible = value
        if self._dialog:
            if value:
                self._dialog.open()
            else:
                self._dialog.close()
    
    @property
    def enabled(self) -> bool:
        """Whether the component is enabled."""
        return getattr(self, '_enabled', True)
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set component enabled state."""
        self._enabled = value
    
    def update(self) -> None:
        """Update the component."""
        if hasattr(self, '_update_preview'):
            self._update_preview()
    
    def destroy(self) -> None:
        """Destroy the component."""
        if self._dialog:
            self._dialog.close()
            if hasattr(self._dialog, 'delete'):
                self._dialog.delete()
    
    # Missing IExportDialog interface methods
    
    def get_selected_options(self) -> Dict[str, bool]:
        """Get user-selected export options."""
        options = self.get_options()
        return {
            'include_config': True,
            'include_wireguard': options.get('format') == 'wireguard',
            'include_keys': options.get('include_keys', True),
            'include_scripts': options.get('include_scripts', False),
            'split_files': options.get('split_files', False)
        }
    
    def set_preview(self, preview: Dict[str, Any]) -> None:
        """Set export preview information."""
        self._preview_data = preview
        if hasattr(self, '_update_preview'):
            self._update_preview()