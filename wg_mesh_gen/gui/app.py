"""
Main application class for the WireGuard Visual Configuration Editor.

This module provides the core application logic and UI orchestration.
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import json
from datetime import datetime

from nicegui import ui, app
from nicegui.events import KeyEventArguments

from .models import NodeModel, EdgeModel, GroupModel
from .state import AppState
from .managers import ValidationManager, GraphManager, ConfigManager, CommandManager
from .file_management import FileManager, ImportWizard, ExportManager
from .components import (
    CytoscapeWidget, PropertyPanel, NodeTree, ToolBar,
    MenuBar, FileUploadComponent, ExportDialog, HelpDialog, StatusBar
)
from .interfaces.session import ISessionManager
from ..logger import get_logger


logger = get_logger()


class WireGuardEditorApp:
    """Main application class for the WireGuard Visual Configuration Editor."""
    
    def __init__(self, config_dir: Path):
        """
        Initialize the application.
        
        Args:
            config_dir: Configuration directory path
        """
        self.config_dir = config_dir
        self.sessions_dir = config_dir / 'sessions'
        self.sessions_dir.mkdir(exist_ok=True)
        
        # Core managers (shared across sessions)
        self.file_manager = FileManager(str(config_dir / 'uploads'))
        self.validation_manager = ValidationManager()
        self.graph_manager = GraphManager()
        
        # Session data
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.current_session_id: Optional[str] = None
        
        # UI components references
        self.ui_components: Dict[str, Any] = {}
        
        # Keyboard shortcuts
        self._setup_keyboard_shortcuts()
        
        logger.info(f"WireGuard Editor initialized with config dir: {config_dir}")
    
    async def create_ui(self, session_id: Optional[str] = None) -> None:
        """
        Create the main UI for a session.
        
        Args:
            session_id: Optional session ID to load
        """
        # Get or create session
        if session_id:
            session = await self._load_session(session_id)
            if not session:
                ui.notify(f"Session {session_id} not found", type='negative')
                session_id = None
        
        if not session_id:
            session_id = await self._create_session()
        
        self.current_session_id = session_id
        session = self.sessions[session_id]
        
        # Set page config
        ui.page_title(f'WireGuard Editor - {session["name"]}')
        
        # Apply dark mode if configured
        if app.storage.user.get('dark_mode', False):
            ui.dark_mode().enable()
        
        # Create menu bar
        menubar = MenuBar(session['app_state'])
        menubar.render()
        self.ui_components['menubar'] = menubar
        
        # Register menu handlers
        self._setup_menu_handlers(menubar, session)
        
        # Create toolbar
        with ui.row().classes('w-full p-2 bg-gray-50 dark:bg-gray-800'):
            toolbar = ToolBar(session['app_state'])
            toolbar.render()
            self.ui_components['toolbar'] = toolbar
            
            # Register toolbar handlers
            self._setup_toolbar_handlers(toolbar, session)
        
        # Main content area
        with ui.row().classes('w-full flex-grow p-0'):
            # Left panel - Node tree
            with ui.column().classes('w-64 h-full bg-white dark:bg-gray-900 border-r'):
                with ui.scroll_area().classes('h-full'):
                    node_tree = NodeTree(session['app_state'])
                    node_tree.render()
                    self.ui_components['node_tree'] = node_tree
                    
                    # Connect node tree events
                    node_tree.on_node_select(lambda nid: self._on_node_select(session, nid))
                    node_tree.on_node_double_click(lambda nid: self._on_node_double_click(session, nid))
            
            # Center - Graph view
            with ui.column().classes('flex-grow h-full'):
                # Graph container
                cytoscape = CytoscapeWidget(
                    session['app_state']
                )
                cytoscape.style('height: calc(100vh - 140px)')
                cytoscape.render()
                self.ui_components['cytoscape'] = cytoscape
                
                # Connect graph events
                cytoscape.on_node_click(lambda nid: self._on_graph_node_click(session, nid))
                cytoscape.on_edge_click(lambda eid: self._on_graph_edge_click(session, eid))
                cytoscape.on_background_click(lambda: self._on_graph_background_click(session))
                cytoscape.on_node_drag(lambda nid, pos: self._on_node_drag(session, nid, pos))
                
                # Status bar
                status_bar = StatusBar(session['app_state'])
                status_bar.render()
                self.ui_components['status_bar'] = status_bar
            
            # Right panel - Properties
            with ui.column().classes('w-80 h-full bg-white dark:bg-gray-900 border-l'):
                with ui.scroll_area().classes('h-full p-4'):
                    property_panel = PropertyPanel(session['app_state'])
                    property_panel.render()
                    self.ui_components['property_panel'] = property_panel
                    
                    # Connect property panel events
                    property_panel.on_save(lambda eid, props: self._on_properties_saved(session, eid, props))
                    property_panel.on_delete(lambda eid: self._on_element_delete(session, eid))
        
        # Create dialogs (hidden initially)
        self._create_dialogs(session)
        
        # Subscribe to state changes
        self._subscribe_to_state_changes(session)
        
        # Load last saved state if exists
        await self._load_session_state(session)
        
        # Initial layout
        ui.timer(0.5, lambda: self._apply_layout(session, 'force'), once=True)
        
        # Auto-save timer
        ui.timer(30.0, lambda: asyncio.create_task(self._auto_save_session(session)))
        
        logger.info(f"UI created for session {session_id}")
    
    def _setup_keyboard_shortcuts(self) -> None:
        """Setup global keyboard shortcuts."""
        shortcuts = {
            'ctrl+s': 'save',
            'ctrl+o': 'open',
            'ctrl+z': 'undo',
            'ctrl+y': 'redo',
            'ctrl+shift+z': 'redo',
            'ctrl+n': 'new_node',
            'ctrl+e': 'new_edge',
            'ctrl+g': 'new_group',
            'ctrl+v': 'validate',
            'ctrl+shift+e': 'export',
            'f1': 'help',
            'delete': 'delete_selected',
            'ctrl+a': 'select_all',
            'escape': 'clear_selection'
        }
        
        async def handle_key(e: KeyEventArguments) -> None:
            """Handle keyboard shortcuts."""
            if not self.current_session_id:
                return
            
            session = self.sessions.get(self.current_session_id)
            if not session:
                return
            
            # Build key combination
            key_combo = ''
            if e.action.modifiers.ctrl:
                key_combo += 'ctrl+'
            if e.action.modifiers.shift:
                key_combo += 'shift+'
            if e.action.modifiers.alt:
                key_combo += 'alt+'
            key_combo += e.key.name.lower()
            
            # Handle shortcut
            action = shortcuts.get(key_combo)
            if action:
                await self._handle_shortcut(session, action)
        
        ui.keyboard(on_key=handle_key)
    
    async def _handle_shortcut(self, session: Dict[str, Any], action: str) -> None:
        """Handle keyboard shortcut action."""
        logger.debug(f"Handling shortcut: {action}")
        
        if action == 'save':
            await self._handle_save(session)
        elif action == 'open':
            self._handle_open(session)
        elif action == 'undo':
            session['command_manager'].undo()
        elif action == 'redo':
            session['command_manager'].redo()
        elif action == 'new_node':
            self._create_new_node(session)
        elif action == 'new_edge':
            self._create_new_edge(session)
        elif action == 'new_group':
            self._create_new_group(session)
        elif action == 'validate':
            self._handle_validate(session)
        elif action == 'export':
            self._handle_export(session)
        elif action == 'help':
            self._show_help()
        elif action == 'delete_selected':
            self._delete_selected(session)
        elif action == 'select_all':
            self._select_all(session)
        elif action == 'clear_selection':
            self._clear_selection(session)
    
    async def _create_session(self) -> str:
        """Create a new session."""
        import uuid
        session_id = str(uuid.uuid4())
        
        # Create session data
        session = {
            'id': session_id,
            'name': f'Session {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            'created_at': datetime.now().isoformat(),
            'app_state': AppState(),
            'config_manager': ConfigManager(),
            'command_manager': CommandManager(),
            'import_wizard': None,  # Created on demand
            'export_manager': None,  # Created on demand
            'modified': False
        }
        
        # Initialize import/export managers
        session['import_wizard'] = ImportWizard(
            self.file_manager,
            session['config_manager'],
            self.validation_manager
        )
        session['export_manager'] = ExportManager(
            self.file_manager,
            session['config_manager']
        )
        
        self.sessions[session_id] = session
        
        # Save session metadata
        await self._save_session_metadata(session)
        
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    async def _load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load an existing session."""
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r') as f:
                metadata = json.load(f)
            
            # Create session with loaded metadata
            session = {
                'id': session_id,
                'name': metadata.get('name', 'Unknown Session'),
                'created_at': metadata.get('created_at', datetime.now().isoformat()),
                'app_state': AppState(),
                'config_manager': ConfigManager(),
                'command_manager': CommandManager(),
                'import_wizard': None,
                'export_manager': None,
                'modified': False
            }
            
            # Initialize managers
            session['import_wizard'] = ImportWizard(
                self.file_manager,
                session['config_manager'],
                self.validation_manager
            )
            session['export_manager'] = ExportManager(
                self.file_manager,
                session['config_manager']
            )
            
            self.sessions[session_id] = session
            
            logger.info(f"Loaded session: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None
    
    async def _save_session_metadata(self, session: Dict[str, Any]) -> None:
        """Save session metadata."""
        metadata = {
            'id': session['id'],
            'name': session['name'],
            'created_at': session['created_at'],
            'last_modified': datetime.now().isoformat()
        }
        
        session_file = self.sessions_dir / f"{session['id']}.json"
        with open(session_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    async def _save_session_state(self, session: Dict[str, Any]) -> None:
        """Save session state."""
        state_file = self.sessions_dir / f"{session['id']}_state.json"
        
        # Serialize app state
        state_data = {
            'nodes': {nid: node.to_dict() for nid, node in session['app_state'].nodes.items()},
            'edges': {eid: edge.to_dict() for eid, edge in session['app_state'].edges.items()},
            'groups': {gid: group.to_dict() for gid, group in session['app_state'].groups.items()}
        }
        
        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=2)
        
        session['modified'] = False
        logger.debug(f"Saved session state: {session['id']}")
    
    async def _load_session_state(self, session: Dict[str, Any]) -> None:
        """Load session state."""
        state_file = self.sessions_dir / f"{session['id']}_state.json"
        
        if not state_file.exists():
            return
        
        try:
            with open(state_file, 'r') as f:
                state_data = json.load(f)
            
            # Clear current state
            session['app_state'].clear()
            
            # Load nodes
            for node_data in state_data.get('nodes', {}).values():
                node = NodeModel.from_dict(node_data)
                session['app_state'].add_node(node)
            
            # Load edges
            for edge_data in state_data.get('edges', {}).values():
                edge = EdgeModel.from_dict(edge_data)
                session['app_state'].add_edge(edge)
            
            # Load groups
            for group_data in state_data.get('groups', {}).values():
                group = GroupModel.from_dict(group_data)
                session['app_state'].add_group(group)
            
            logger.info(f"Loaded session state: {session['id']}")
            
        except Exception as e:
            logger.error(f"Failed to load session state: {e}")
    
    async def _auto_save_session(self, session: Dict[str, Any]) -> None:
        """Auto-save session if modified."""
        if session.get('modified', False):
            await self._save_session_state(session)
            # Note: Cannot use ui.notify in background tasks due to slot context
            self._logger.info(f"Auto-saved session {session.get('id', 'unknown')}")
    
    def _setup_menu_handlers(self, menubar: MenuBar, session: Dict[str, Any]) -> None:
        """Setup menu bar handlers."""
        # File menu
        menubar.add_menu_item('file', 'new', 'New', lambda: self._handle_new(session))
        menubar.add_menu_item('file', 'open', 'Open', lambda: self._handle_open(session))
        menubar.add_menu_item('file', 'save', 'Save', lambda: asyncio.create_task(self._handle_save(session)))
        menubar.add_menu_item('file', 'import.nodes_topology', 'Import', lambda: self._handle_import(session))
        menubar.add_menu_item('file', 'export.package', 'Export', lambda: self._handle_export(session))
        
        # Edit menu
        menubar.add_menu_item('edit', 'undo', 'Undo', lambda: session['command_manager'].undo())
        menubar.add_menu_item('edit', 'redo', 'Redo', lambda: session['command_manager'].redo())
        menubar.add_menu_item('edit', 'delete', 'Delete Selected', lambda: self._delete_selected(session))
        
        # Tools menu
        menubar.add_menu_item('tools', 'validate', 'Validate', lambda: self._handle_validate(session))
        menubar.add_menu_item('tools', 'generate_keys', 'Generate Keys', lambda: self._generate_keys(session))
        
        # View menu
        menubar.add_menu_item('view', 'layout.force', 'Force Layout', lambda: self._apply_layout(session, 'force'))
        menubar.add_menu_item('view', 'layout.circle', 'Circle Layout', lambda: self._apply_layout(session, 'circle'))
        menubar.add_menu_item('view', 'layout.grid', 'Grid Layout', lambda: self._apply_layout(session, 'grid'))
        menubar.add_menu_item('view', 'fit', 'Fit to View', lambda: self._fit_view(session))
        
        # Help menu
        menubar.add_menu_item('help', 'shortcuts', 'Keyboard Shortcuts', self._show_shortcuts)
        menubar.add_menu_item('help', 'about', 'About', self._show_about)
    
    def _setup_toolbar_handlers(self, toolbar: ToolBar, session: Dict[str, Any]) -> None:
        """Setup toolbar handlers."""
        toolbar.set_action_handler('open', lambda: self._handle_open(session))
        toolbar.set_action_handler('save', lambda: asyncio.create_task(self._handle_save(session)))
        toolbar.set_action_handler('validate', lambda: self._handle_validate(session))
        toolbar.set_action_handler('export', lambda: self._handle_export(session))
        toolbar.set_action_handler('layout', lambda: self._apply_layout(session, 'force'))
        toolbar.set_action_handler('fit', lambda: self._fit_view(session))
        toolbar.set_action_handler('undo', lambda: session['command_manager'].undo())
        toolbar.set_action_handler('redo', lambda: session['command_manager'].redo())
    
    def _create_dialogs(self, session: Dict[str, Any]) -> None:
        """Create dialog components."""
        # Export dialog
        export_dialog = ExportDialog(session['app_state'], session['export_manager'])
        export_dialog.render()
        export_dialog.on_export(lambda opts: self._perform_export(session, opts))
        self.ui_components['export_dialog'] = export_dialog
        
        # Help dialog
        help_dialog = HelpDialog()
        help_dialog.render()
        self.ui_components['help_dialog'] = help_dialog
    
    def _subscribe_to_state_changes(self, session: Dict[str, Any]) -> None:
        """Subscribe to application state changes."""
        app_state = session['app_state']
        
        # Mark session as modified and refresh UI on changes
        def mark_modified_and_refresh(event):
            session['modified'] = True
            # Refresh graph visualization
            cytoscape = self.ui_components.get('cytoscape')
            if cytoscape:
                cytoscape.refresh()
            # Refresh node tree
            node_tree = self.ui_components.get('node_tree')
            if node_tree:
                node_tree.refresh()
        
        app_state.subscribe('node_added', mark_modified_and_refresh)
        app_state.subscribe('node_removed', mark_modified_and_refresh)
        app_state.subscribe('node_updated', mark_modified_and_refresh)
        app_state.subscribe('edge_added', mark_modified_and_refresh)
        app_state.subscribe('edge_removed', mark_modified_and_refresh)
        app_state.subscribe('edge_updated', mark_modified_and_refresh)
        app_state.subscribe('group_added', mark_modified_and_refresh)
        app_state.subscribe('group_removed', mark_modified_and_refresh)
        app_state.subscribe('group_updated', mark_modified_and_refresh)
    
    # Event handlers
    def _on_node_select(self, session: Dict[str, Any], node_id: str) -> None:
        """Handle node selection from tree."""
        property_panel = self.ui_components.get('property_panel')
        cytoscape = self.ui_components.get('cytoscape')
        
        if property_panel:
            property_panel.load_properties(node_id)
        if cytoscape:
            cytoscape.center_on_node(node_id)
    
    def _on_node_double_click(self, session: Dict[str, Any], node_id: str) -> None:
        """Handle node double-click from tree."""
        cytoscape = self.ui_components.get('cytoscape')
        if cytoscape:
            cytoscape.center_on_node(node_id)
            cytoscape.set_selection([node_id])
    
    def _on_graph_node_click(self, session: Dict[str, Any], node_id: str) -> None:
        """Handle node click from graph."""
        property_panel = self.ui_components.get('property_panel')
        if property_panel:
            property_panel.load_properties(node_id)
    
    def _on_graph_edge_click(self, session: Dict[str, Any], edge_id: str) -> None:
        """Handle edge click from graph."""
        property_panel = self.ui_components.get('property_panel')
        if property_panel:
            property_panel.load_properties(edge_id)
    
    def _on_graph_background_click(self, session: Dict[str, Any]) -> None:
        """Handle background click from graph."""
        property_panel = self.ui_components.get('property_panel')
        if property_panel:
            property_panel.clear()
    
    def _on_node_drag(self, session: Dict[str, Any], node_id: str, position: Dict[str, float]) -> None:
        """Handle node drag from graph."""
        # Position is already updated in state by CytoscapeWidget
        session['modified'] = True
    
    def _on_properties_saved(self, session: Dict[str, Any], element_id: str, properties: Dict[str, Any]) -> None:
        """Handle properties saved."""
        ui.notify('Properties saved', type='positive')
        session['modified'] = True
    
    def _on_element_delete(self, session: Dict[str, Any], element_id: str) -> None:
        """Handle element deletion."""
        app_state = session['app_state']
        
        if element_id in app_state.nodes:
            app_state.remove_node(element_id)
            ui.notify('Node deleted', type='info')
        elif element_id in app_state.edges:
            app_state.remove_edge(element_id)
            ui.notify('Edge deleted', type='info')
        elif element_id in app_state.groups:
            app_state.remove_group(element_id)
            ui.notify('Group deleted', type='info')
    
    # Action handlers
    def _handle_new(self, session: Dict[str, Any]) -> None:
        """Handle new configuration."""
        # Confirm if current session has changes
        if session.get('modified', False):
            with ui.dialog() as dialog, ui.card():
                ui.label('Save current changes?').classes('text-h6')
                ui.label('You have unsaved changes. Do you want to save them?')
                
                with ui.row().classes('gap-2 mt-4'):
                    ui.button('Save', on_click=lambda: [
                        asyncio.create_task(self._handle_save(session)),
                        dialog.close(),
                        self._create_new_configuration(session)
                    ]).props('color=primary')
                    ui.button('Discard', on_click=lambda: [
                        dialog.close(),
                        self._create_new_configuration(session)
                    ]).props('color=negative')
                    ui.button('Cancel', on_click=dialog.close)
            
            dialog.open()
        else:
            self._create_new_configuration(session)
    
    def _create_new_configuration(self, session: Dict[str, Any]) -> None:
        """Create new configuration."""
        session['app_state'].clear()
        session['command_manager'].clear()
        session['modified'] = False
        ui.notify('New configuration created', type='positive')
    
    def _handle_open(self, session: Dict[str, Any]) -> None:
        """Handle open file action."""
        with ui.dialog() as dialog, ui.card().classes('w-[600px]'):
            ui.label('Import Configuration').classes('text-h6')
            
            upload = FileUploadComponent(
                self.file_manager,
                accept=['.yaml', '.yml', '.json'],
                multiple=True
            )
            upload.render()
            
            def handle_upload(files):
                dialog.close()
                # Start import wizard
                import_session_id = session['import_wizard'].start_import()
                for file_info in files:
                    session['import_wizard'].add_file(
                        import_session_id,
                        file_info['temp_path'],
                        file_info['config_type']
                    )
                # Execute import
                if session['import_wizard'].execute_import(import_session_id, session['app_state']):
                    ui.notify('Configuration imported successfully', type='positive')
                    session['modified'] = True
                    self._apply_layout(session, 'force')
            
            upload.on_upload(handle_upload)
            
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
    
    async def _handle_save(self, session: Dict[str, Any]) -> None:
        """Handle save action."""
        await self._save_session_state(session)
        ui.notify('Configuration saved', type='positive')
    
    def _handle_import(self, session: Dict[str, Any]) -> None:
        """Handle import action."""
        self._handle_open(session)
    
    def _handle_export(self, session: Dict[str, Any]) -> None:
        """Handle export action."""
        export_dialog = self.ui_components.get('export_dialog')
        if export_dialog:
            export_dialog.show()
    
    def _perform_export(self, session: Dict[str, Any], options: Dict[str, Any]) -> None:
        """Perform the actual export."""
        ui.notify(f'Exporting as {options["format"]}...', type='info')
        # Export implementation would go here
    
    def _handle_validate(self, session: Dict[str, Any]) -> None:
        """Handle validate action."""
        errors = self.validation_manager.validate_configuration(session['app_state'])
        
        if errors:
            # Show validation errors
            with ui.dialog() as dialog, ui.card():
                ui.label('Validation Errors').classes('text-h6')
                with ui.column().classes('max-h-96 overflow-auto'):
                    for error in errors:
                        with ui.row().classes('items-start gap-2'):
                            ui.icon('error').classes('text-negative')
                            ui.label(error)
                ui.button('Close', on_click=dialog.close).classes('mt-4')
            dialog.open()
        else:
            ui.notify('Configuration is valid', type='positive')
    
    def _apply_layout(self, session: Dict[str, Any], layout_name: str) -> None:
        """Apply a layout to the graph."""
        cytoscape = self.ui_components.get('cytoscape')
        if cytoscape:
            self.graph_manager.apply_layout(session['app_state'], layout_name)
            cytoscape.set_layout(layout_name)
            ui.notify(f'Applied {layout_name} layout', type='info')
    
    def _fit_view(self, session: Dict[str, Any]) -> None:
        """Fit graph to viewport."""
        cytoscape = self.ui_components.get('cytoscape')
        if cytoscape:
            cytoscape.fit_to_viewport()
    
    def _create_new_node(self, session: Dict[str, Any]) -> None:
        """Create a new node."""
        # Show node creation dialog
        with ui.dialog() as dialog, ui.card():
            ui.label('Create New Node').classes('text-h6')
            
            name_input = ui.input('Node Name', placeholder='e.g., client1').classes('w-full')
            role_select = ui.select('Role', options=['client', 'relay'], value='client').classes('w-full')
            ip_input = ui.input('WireGuard IP', placeholder='e.g., 10.0.0.2/24').classes('w-full')
            
            def create():
                if not name_input.value:
                    ui.notify('Node name is required', type='negative')
                    return
                
                node = NodeModel()
                node.name = name_input.value
                node.role = role_select.value
                node.wireguard_ip = ip_input.value
                
                session['app_state'].add_node(node)
                dialog.close()
                ui.notify(f'Created node: {node.name}', type='positive')
            
            with ui.row().classes('gap-2 mt-4'):
                ui.button('Create', on_click=create).props('color=primary')
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
    
    def _create_new_edge(self, session: Dict[str, Any]) -> None:
        """Create a new edge."""
        nodes = list(session['app_state'].nodes.values())
        if len(nodes) < 2:
            ui.notify('Need at least 2 nodes to create an edge', type='warning')
            return
        
        with ui.dialog() as dialog, ui.card():
            ui.label('Create New Edge').classes('text-h6')
            
            node_options = {n.id: n.name for n in nodes}
            source_select = ui.select('Source Node', options=node_options).classes('w-full')
            target_select = ui.select('Target Node', options=node_options).classes('w-full')
            allowed_ips_input = ui.input('Allowed IPs', placeholder='e.g., 10.0.0.0/24').classes('w-full')
            
            def create():
                if not source_select.value or not target_select.value:
                    ui.notify('Both source and target nodes are required', type='negative')
                    return
                
                if source_select.value == target_select.value:
                    ui.notify('Source and target must be different', type='negative')
                    return
                
                edge = EdgeModel()
                edge.source_id = source_select.value
                edge.target_id = target_select.value
                if allowed_ips_input.value:
                    edge.allowed_ips = [ip.strip() for ip in allowed_ips_input.value.split(',')]
                
                session['app_state'].add_edge(edge)
                dialog.close()
                ui.notify('Created edge', type='positive')
            
            with ui.row().classes('gap-2 mt-4'):
                ui.button('Create', on_click=create).props('color=primary')
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
    
    def _create_new_group(self, session: Dict[str, Any]) -> None:
        """Create a new group."""
        with ui.dialog() as dialog, ui.card():
            ui.label('Create New Group').classes('text-h6')
            
            name_input = ui.input('Group Name', placeholder='e.g., main_network').classes('w-full')
            topology_select = ui.select(
                'Topology',
                options=['mesh', 'star', 'chain', 'single'],
                value='mesh'
            ).classes('w-full')
            color_input = ui.color_input('Color', value='#4CAF50').classes('w-full')
            
            def create():
                if not name_input.value:
                    ui.notify('Group name is required', type='negative')
                    return
                
                group = GroupModel()
                group.name = name_input.value
                group.topology = topology_select.value
                group.color = color_input.value
                
                session['app_state'].add_group(group)
                dialog.close()
                ui.notify(f'Created group: {group.name}', type='positive')
            
            with ui.row().classes('gap-2 mt-4'):
                ui.button('Create', on_click=create).props('color=primary')
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
    
    def _generate_keys(self, session: Dict[str, Any]) -> None:
        """Generate WireGuard keys for nodes."""
        nodes_without_keys = [
            node for node in session['app_state'].nodes.values()
            if not node.public_key
        ]
        
        if not nodes_without_keys:
            ui.notify('All nodes already have keys', type='info')
            return
        
        with ui.dialog() as dialog, ui.card():
            ui.label('Generate WireGuard Keys').classes('text-h6')
            ui.label(f'Generate keys for {len(nodes_without_keys)} nodes?')
            
            with ui.column().classes('max-h-48 overflow-auto mt-2'):
                for node in nodes_without_keys:
                    ui.label(f'• {node.name}').classes('text-sm')
            
            def generate():
                for node in nodes_without_keys:
                    # In real implementation, would use actual key generation
                    import secrets
                    node.public_key = secrets.token_urlsafe(32)
                    node.private_key = secrets.token_urlsafe(32)
                
                dialog.close()
                ui.notify(f'Generated keys for {len(nodes_without_keys)} nodes', type='positive')
                session['modified'] = True
            
            with ui.row().classes('gap-2 mt-4'):
                ui.button('Generate', on_click=generate).props('color=primary')
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
    
    def _delete_selected(self, session: Dict[str, Any]) -> None:
        """Delete selected elements."""
        cytoscape = self.ui_components.get('cytoscape')
        if not cytoscape:
            return
        
        selected = cytoscape.get_selection()
        if not selected:
            ui.notify('No elements selected', type='warning')
            return
        
        # Delete selected elements
        for element_id in selected:
            if element_id in session['app_state'].nodes:
                session['app_state'].remove_node(element_id)
            elif element_id in session['app_state'].edges:
                session['app_state'].remove_edge(element_id)
        
        ui.notify(f'Deleted {len(selected)} elements', type='info')
    
    def _select_all(self, session: Dict[str, Any]) -> None:
        """Select all elements."""
        cytoscape = self.ui_components.get('cytoscape')
        if cytoscape:
            all_elements = (
                list(session['app_state'].nodes.keys()) +
                list(session['app_state'].edges.keys())
            )
            cytoscape.set_selection(all_elements)
    
    def _clear_selection(self, session: Dict[str, Any]) -> None:
        """Clear selection."""
        cytoscape = self.ui_components.get('cytoscape')
        if cytoscape:
            cytoscape.clear_selection()
        
        property_panel = self.ui_components.get('property_panel')
        if property_panel:
            property_panel.clear()
    
    def _show_help(self) -> None:
        """Show help dialog."""
        help_dialog = self.ui_components.get('help_dialog')
        if help_dialog:
            help_dialog.show()
    
    def _show_shortcuts(self) -> None:
        """Show keyboard shortcuts."""
        with ui.dialog() as dialog, ui.card():
            ui.label('Keyboard Shortcuts').classes('text-h6')
            
            shortcuts = [
                ('Ctrl+S', 'Save configuration'),
                ('Ctrl+O', 'Open configuration'),
                ('Ctrl+Z', 'Undo'),
                ('Ctrl+Y', 'Redo'),
                ('Ctrl+N', 'New node'),
                ('Ctrl+E', 'New edge'),
                ('Ctrl+G', 'New group'),
                ('Ctrl+V', 'Validate configuration'),
                ('Ctrl+Shift+E', 'Export configuration'),
                ('F1', 'Show help'),
                ('Delete', 'Delete selected'),
                ('Ctrl+A', 'Select all'),
                ('Escape', 'Clear selection')
            ]
            
            with ui.column().classes('gap-2'):
                for key, desc in shortcuts:
                    with ui.row().classes('gap-4'):
                        ui.label(key).classes('font-mono bg-gray-100 px-2 py-1 rounded')
                        ui.label(desc)
            
            ui.button('Close', on_click=dialog.close).classes('mt-4')
        
        dialog.open()
    
    def _show_about(self) -> None:
        """Show about dialog."""
        with ui.dialog() as dialog, ui.card():
            ui.label('WireGuard Configuration Editor').classes('text-h5')
            ui.label('Version 1.0.0').classes('text-subtitle1 text-gray-600')
            
            ui.separator().classes('my-4')
            
            ui.label('A visual editor for WireGuard network configurations')
            ui.label('Supporting complex mesh topologies and group-based management')
            
            ui.separator().classes('my-4')
            
            with ui.column().classes('gap-1 text-sm'):
                ui.label('© 2024 WireGuard Configuration Generator')
                ui.label('Built with NiceGUI and Cytoscape.js')
            
            ui.button('Close', on_click=dialog.close).classes('mt-4')
        
        dialog.open()