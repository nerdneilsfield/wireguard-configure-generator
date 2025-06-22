"""
MenuBar implementation with file operations and other menu items.

This component provides a traditional menu bar interface.
"""

from typing import Dict, Optional, Callable, List

from nicegui import ui

from .base import BaseComponent
from ..interfaces.components import IMenuBar


class MenuBar(BaseComponent, IMenuBar):
    """Implementation of IMenuBar for application menus."""
    
    def __init__(self, 
                 app_state,
                 component_id: Optional[str] = None):
        """
        Initialize menu bar.
        
        Args:
            app_state: Application state
            component_id: Optional component ID
        """
        super().__init__(component_id)
        self._app_state = app_state
        self._menus: Dict[str, Dict[str, any]] = {}
        self._items: Dict[str, Dict[str, any]] = {}
    
    def render(self) -> ui.element:
        """Render the menu bar."""
        with ui.header().classes('bg-primary') as container:
            with ui.row().classes('items-center') as self._element:
                # App title
                ui.label('WireGuard Configuration Editor').classes('text-h6 text-white')
                
                # Spacer
                ui.space()
                
                # Menu items
                self._create_file_menu()
                self._create_edit_menu()
                self._create_view_menu()
                self._create_tools_menu()
                self._create_help_menu()
        
        return container
    
    def _create_file_menu(self) -> None:
        """Create File menu."""
        with ui.button('File', icon='menu').props('flat color=white'):
            with ui.menu() as menu:
                ui.menu_item('New Project', lambda: self._trigger_action('file.new'))\
                    .props('icon=add')
                ui.menu_item('Open...', lambda: self._trigger_action('file.open'))\
                    .props('icon=folder_open')
                ui.separator()
                ui.menu_item('Save', lambda: self._trigger_action('file.save'))\
                    .props('icon=save')
                ui.menu_item('Save As...', lambda: self._trigger_action('file.save_as'))\
                    .props('icon=save_as')
                ui.separator()
                ui.menu_item('Import', lambda: self._show_import_submenu())\
                    .props('icon=upload')
                ui.menu_item('Export', lambda: self._show_export_submenu())\
                    .props('icon=download')
                ui.separator()
                ui.menu_item('Recent Files', lambda: self._show_recent_files())\
                    .props('icon=history')
                ui.separator()
                ui.menu_item('Exit', lambda: self._trigger_action('file.exit'))\
                    .props('icon=exit_to_app')
        
        self._menus['file'] = menu
    
    def _create_edit_menu(self) -> None:
        """Create Edit menu."""
        with ui.button('Edit', icon='edit').props('flat color=white'):
            with ui.menu() as menu:
                ui.menu_item('Undo', lambda: self._trigger_action('edit.undo'))\
                    .props('icon=undo')
                ui.menu_item('Redo', lambda: self._trigger_action('edit.redo'))\
                    .props('icon=redo')
                ui.separator()
                ui.menu_item('Cut', lambda: self._trigger_action('edit.cut'))\
                    .props('icon=cut')
                ui.menu_item('Copy', lambda: self._trigger_action('edit.copy'))\
                    .props('icon=copy')
                ui.menu_item('Paste', lambda: self._trigger_action('edit.paste'))\
                    .props('icon=paste')
                ui.separator()
                ui.menu_item('Select All', lambda: self._trigger_action('edit.select_all'))\
                    .props('icon=select_all')
                ui.menu_item('Clear Selection', lambda: self._trigger_action('edit.clear_selection'))\
                    .props('icon=clear')
                ui.separator()
                ui.menu_item('Find...', lambda: self._trigger_action('edit.find'))\
                    .props('icon=search')
        
        self._menus['edit'] = menu
    
    def _create_view_menu(self) -> None:
        """Create View menu."""
        with ui.button('View', icon='visibility').props('flat color=white'):
            with ui.menu() as menu:
                ui.menu_item('Zoom In', lambda: self._trigger_action('view.zoom_in'))\
                    .props('icon=zoom_in')
                ui.menu_item('Zoom Out', lambda: self._trigger_action('view.zoom_out'))\
                    .props('icon=zoom_out')
                ui.menu_item('Fit to Window', lambda: self._trigger_action('view.fit'))\
                    .props('icon=fit_screen')
                ui.separator()
                ui.menu_item('Show Grid', lambda: self._trigger_action('view.grid'))\
                    .props('icon=grid_on')
                ui.menu_item('Show Labels', lambda: self._trigger_action('view.labels'))\
                    .props('icon=label')
                ui.separator()
                ui.menu_item('Layout', lambda: self._show_layout_submenu())\
                    .props('icon=auto_fix_high')
                ui.separator()
                ui.menu_item('Refresh', lambda: self._trigger_action('view.refresh'))\
                    .props('icon=refresh')
        
        self._menus['view'] = menu
    
    def _create_tools_menu(self) -> None:
        """Create Tools menu."""
        with ui.button('Tools', icon='build').props('flat color=white'):
            with ui.menu() as menu:
                ui.menu_item('Validate Configuration', lambda: self._trigger_action('tools.validate'))\
                    .props('icon=fact_check')
                ui.menu_item('Generate Keys', lambda: self._trigger_action('tools.generate_keys'))\
                    .props('icon=vpn_key')
                ui.separator()
                ui.menu_item('Network Statistics', lambda: self._trigger_action('tools.statistics'))\
                    .props('icon=analytics')
                ui.menu_item('Test Connectivity', lambda: self._trigger_action('tools.test_connectivity'))\
                    .props('icon=network_check')
                ui.separator()
                ui.menu_item('Options...', lambda: self._trigger_action('tools.options'))\
                    .props('icon=settings')
        
        self._menus['tools'] = menu
    
    def _create_help_menu(self) -> None:
        """Create Help menu."""
        with ui.button('Help', icon='help').props('flat color=white'):
            with ui.menu() as menu:
                ui.menu_item('Documentation', lambda: self._trigger_action('help.docs'))\
                    .props('icon=menu_book')
                ui.menu_item('Keyboard Shortcuts', lambda: self._trigger_action('help.shortcuts'))\
                    .props('icon=keyboard')
                ui.separator()
                ui.menu_item('Report Issue', lambda: self._trigger_action('help.report_issue'))\
                    .props('icon=bug_report')
                ui.menu_item('About', lambda: self._trigger_action('help.about'))\
                    .props('icon=info')
        
        self._menus['help'] = menu
    
    def _show_import_submenu(self) -> None:
        """Show import submenu."""
        with ui.dialog() as dialog, ui.card():
            ui.label('Import Configuration').classes('text-h6')
            
            with ui.column().classes('gap-2'):
                ui.button('Import Nodes & Topology', 
                         on_click=lambda: self._import_action('nodes_topology', dialog))\
                    .props('icon=upload_file outline').classes('w-64')
                ui.button('Import Group Configuration', 
                         on_click=lambda: self._import_action('groups', dialog))\
                    .props('icon=group_work outline').classes('w-64')
                ui.button('Import Key Database', 
                         on_click=lambda: self._import_action('keys', dialog))\
                    .props('icon=vpn_key outline').classes('w-64')
                ui.button('Import Complete Project', 
                         on_click=lambda: self._import_action('project', dialog))\
                    .props('icon=archive outline').classes('w-64')
            
            ui.button('Cancel', on_click=dialog.close).classes('mt-4')
        
        dialog.open()
    
    def _show_export_submenu(self) -> None:
        """Show export submenu."""
        with ui.dialog() as dialog, ui.card():
            ui.label('Export Configuration').classes('text-h6')
            
            with ui.column().classes('gap-2'):
                ui.button('Export WireGuard Configs', 
                         on_click=lambda: self._export_action('wireguard', dialog))\
                    .props('icon=settings_ethernet outline').classes('w-64')
                ui.button('Export as YAML', 
                         on_click=lambda: self._export_action('yaml', dialog))\
                    .props('icon=code outline').classes('w-64')
                ui.button('Export as JSON', 
                         on_click=lambda: self._export_action('json', dialog))\
                    .props('icon=data_object outline').classes('w-64')
                ui.button('Export Network Diagram', 
                         on_click=lambda: self._export_action('diagram', dialog))\
                    .props('icon=image outline').classes('w-64')
                ui.button('Export Complete Package', 
                         on_click=lambda: self._export_action('package', dialog))\
                    .props('icon=archive outline').classes('w-64')
            
            ui.button('Cancel', on_click=dialog.close).classes('mt-4')
        
        dialog.open()
    
    def _show_layout_submenu(self) -> None:
        """Show layout submenu."""
        with ui.dialog() as dialog, ui.card():
            ui.label('Choose Layout').classes('text-h6')
            
            layouts = [
                ('Force Directed', 'force', 'Organic layout using physics simulation'),
                ('Hierarchical', 'hierarchical', 'Tree-like layout with levels'),
                ('Circular', 'circular', 'Nodes arranged in a circle'),
                ('Grid', 'grid', 'Nodes arranged in a grid'),
                ('Group-based', 'group', 'Layout respecting group boundaries')
            ]
            
            with ui.column().classes('gap-2'):
                for name, layout_id, description in layouts:
                    with ui.row().classes('items-center gap-4 p-2 hover:bg-gray-100 cursor-pointer')\
                        .on('click', lambda lid=layout_id: self._apply_layout(lid, dialog)):
                        ui.icon('auto_fix_high').classes('text-2xl')
                        with ui.column():
                            ui.label(name).classes('font-medium')
                            ui.label(description).classes('text-caption text-gray-600')
            
            ui.button('Cancel', on_click=dialog.close).classes('mt-4')
        
        dialog.open()
    
    def _show_recent_files(self) -> None:
        """Show recent files dialog."""
        # Get recent files from settings/storage
        recent_files = self._get_recent_files()
        
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label('Recent Files').classes('text-h6')
            
            if recent_files:
                with ui.column().classes('gap-2 max-h-96 overflow-auto'):
                    for file_path in recent_files:
                        with ui.row().classes('items-center gap-2 p-2 hover:bg-gray-100 cursor-pointer')\
                            .on('click', lambda fp=file_path: self._open_recent_file(fp, dialog)):
                            ui.icon('description').classes('text-gray-600')
                            ui.label(file_path).classes('text-sm truncate')
            else:
                ui.label('No recent files').classes('text-gray-500')
            
            ui.button('Close', on_click=dialog.close).classes('mt-4')
        
        dialog.open()
    
    def add_menu(self, menu_id: str, label: str, items: List[Dict[str, any]]) -> None:
        """Add a new menu."""
        # Would need to implement dynamic menu creation
        pass
    
    def add_menu_item(self, menu_id: str, item_id: str, label: str,
                     handler: Optional[Callable] = None,
                     icon: Optional[str] = None) -> None:
        """Add an item to a menu."""
        if menu_id not in self._items:
            self._items[menu_id] = {}
        
        self._items[menu_id][item_id] = {
            'label': label,
            'handler': handler,
            'icon': icon
        }
    
    def remove_menu_item(self, menu_id: str, item_id: str) -> None:
        """Remove a menu item."""
        if menu_id in self._items and item_id in self._items[menu_id]:
            del self._items[menu_id][item_id]
    
    def enable_menu_item(self, menu_id: str, item_id: str) -> None:
        """Enable a menu item."""
        # Would need to track menu item references
        pass
    
    def disable_menu_item(self, menu_id: str, item_id: str) -> None:
        """Disable a menu item."""
        # Would need to track menu item references
        pass
    
    def update_menu_item(self, menu_id: str, item_id: str, 
                        label: Optional[str] = None,
                        handler: Optional[Callable] = None) -> None:
        """Update a menu item."""
        if menu_id in self._items and item_id in self._items[menu_id]:
            if label:
                self._items[menu_id][item_id]['label'] = label
            if handler:
                self._items[menu_id][item_id]['handler'] = handler
    
    def _trigger_action(self, action_id: str) -> None:
        """Trigger a menu action."""
        menu_id, item_id = action_id.split('.')
        
        # Check for registered handler
        if menu_id in self._items and item_id in self._items[menu_id]:
            handler = self._items[menu_id][item_id].get('handler')
            if handler:
                handler()
                return
        
        # Default handlers
        if action_id == 'file.new':
            self._handle_new_project()
        elif action_id == 'file.exit':
            self._handle_exit()
        elif action_id == 'edit.undo':
            self._app_state.history.undo()
        elif action_id == 'edit.redo':
            self._app_state.history.redo()
        elif action_id == 'edit.select_all':
            self._select_all()
        elif action_id == 'edit.clear_selection':
            self._app_state.clear_selection()
        elif action_id == 'help.about':
            self._show_about()
        else:
            ui.notify(f'Action not implemented: {action_id}', type='warning')
    
    def _handle_new_project(self) -> None:
        """Handle new project action."""
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
        """Create new project."""
        if dialog:
            dialog.close()
        
        self._app_state.nodes.clear()
        self._app_state.edges.clear()
        self._app_state.groups.clear()
        self._app_state.clear_selection()
        self._app_state.history.clear()
        self._app_state.mark_clean()
        
        ui.notify('New project created', type='positive')
    
    def _handle_exit(self) -> None:
        """Handle exit action."""
        if self._app_state.is_dirty:
            with ui.dialog() as dialog, ui.card():
                ui.label('Save changes before exiting?')
                with ui.row():
                    ui.button("Don't Save", on_click=lambda: ui.run_javascript('window.close()'))
                    ui.button('Cancel', on_click=dialog.close)
                    ui.button('Save', on_click=lambda: self._save_and_exit(dialog))\
                        .props('color=primary')
            dialog.open()
        else:
            ui.run_javascript('window.close()')
    
    def _save_and_exit(self, dialog) -> None:
        """Save and exit."""
        dialog.close()
        # Trigger save action
        self._trigger_action('file.save')
        # Then exit
        ui.run_javascript('window.close()')
    
    def _select_all(self) -> None:
        """Select all elements."""
        all_ids = list(self._app_state.nodes.keys()) + list(self._app_state.edges.keys())
        self._app_state.set_selection(set(all_ids))
    
    def _show_about(self) -> None:
        """Show about dialog."""
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            with ui.column().classes('items-center gap-4'):
                ui.icon('router').classes('text-6xl text-primary')
                ui.label('WireGuard Configuration Editor').classes('text-h5')
                ui.label('Version 1.0.0').classes('text-subtitle1')
                ui.separator()
                ui.label('A visual editor for WireGuard network configurations')\
                    .classes('text-center')
                ui.label('Built with NiceGUI and Cytoscape.js').classes('text-caption')
                
                with ui.row().classes('gap-4 mt-4'):
                    ui.link('Documentation', 'https://github.com/your-repo', new_tab=True)
                    ui.link('Report Issue', 'https://github.com/your-repo/issues', new_tab=True)
                
                ui.button('Close', on_click=dialog.close).classes('mt-4')
        
        dialog.open()
    
    def _import_action(self, import_type: str, dialog) -> None:
        """Handle import action."""
        dialog.close()
        self._trigger_action(f'file.import.{import_type}')
    
    def _export_action(self, export_type: str, dialog) -> None:
        """Handle export action."""
        dialog.close()
        self._trigger_action(f'file.export.{export_type}')
    
    def _apply_layout(self, layout_id: str, dialog) -> None:
        """Apply layout."""
        dialog.close()
        self._trigger_action(f'view.layout.{layout_id}')
        ui.notify(f'Applied {layout_id} layout', type='info')
    
    def _get_recent_files(self) -> List[str]:
        """Get list of recent files."""
        # TODO: Implement proper recent files tracking
        return [
            '/home/user/configs/network1.yaml',
            '/home/user/configs/network2.yaml',
            '/home/user/configs/test_topology.json'
        ]
    
    def _open_recent_file(self, file_path: str, dialog) -> None:
        """Open a recent file."""
        dialog.close()
        # Trigger open with file path
        if 'file.open' in self._items.get('file', {}):
            handler = self._items['file']['file.open'].get('handler')
            if handler:
                handler(file_path)
        else:
            ui.notify(f'Opening: {file_path}', type='info')
    
    def add_separator(self, menu_id: str) -> None:
        """Add a separator to a menu."""
        # This would add a separator at runtime
        # Since we're using static menus, this is a no-op for now
        pass
    
    def set_item_enabled(self, menu_id: str, item_id: str, enabled: bool) -> None:
        """Set whether a menu item is enabled."""
        # Would need to track menu item element references
        # and update their disabled state
        if enabled:
            self.enable_menu_item(menu_id, item_id)
        else:
            self.disable_menu_item(menu_id, item_id)