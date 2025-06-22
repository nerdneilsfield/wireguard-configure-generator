#!/usr/bin/env python3
"""
Demo application to test the WireGuard Visual Configuration Editor.

This demonstrates all the components working together.
"""

from nicegui import ui

# Import all the components and dependencies
from wg_mesh_gen.gui.models import NodeModel, EdgeModel, GroupModel
from wg_mesh_gen.gui.state import AppState
from wg_mesh_gen.gui.managers import ValidationManager, GraphManager, ConfigManager
from wg_mesh_gen.gui.file_management import FileManager, ImportWizard, ExportManager
from wg_mesh_gen.gui.components import (
    CytoscapeWidget, PropertyPanel, NodeTree, ToolBar, 
    MenuBar, FileUploadComponent, ExportDialog
)


class WireGuardEditor:
    """Main application class for the WireGuard Visual Configuration Editor."""
    
    def __init__(self):
        """Initialize the application."""
        # Core state and managers
        self.app_state = AppState()
        self.validation_manager = ValidationManager()
        self.graph_manager = GraphManager()
        self.config_manager = ConfigManager()
        self.file_manager = FileManager()
        self.import_wizard = ImportWizard(
            self.file_manager, 
            self.config_manager, 
            self.validation_manager
        )
        self.export_manager = ExportManager(
            self.file_manager,
            self.config_manager
        )
        
        # UI components
        self.cytoscape: Optional[CytoscapeWidget] = None
        self.property_panel: Optional[PropertyPanel] = None
        self.node_tree: Optional[NodeTree] = None
        self.toolbar: Optional[ToolBar] = None
        self.menubar: Optional[MenuBar] = None
        self.export_dialog: Optional[ExportDialog] = None
        
        # Create sample data for demo
        self._create_sample_data()
    
    def _create_sample_data(self):
        """Create sample nodes and edges for demonstration."""
        # Create a relay node
        relay = NodeModel()
        relay.name = "relay1"
        relay.role = "relay"
        relay.wireguard_ip = "10.0.0.1/24"
        relay.endpoints = {"default": "relay.example.com:51820"}
        self.app_state.add_node(relay)
        
        # Create client nodes
        for i in range(2, 5):
            client = NodeModel()
            client.name = f"client{i-1}"
            client.role = "client"
            client.wireguard_ip = f"10.0.0.{i}/24"
            self.app_state.add_node(client)
        
        # Create edges (star topology)
        for client_id in list(self.app_state.nodes.keys())[1:]:
            edge = EdgeModel()
            edge.source_id = relay.id
            edge.target_id = client_id
            edge.allowed_ips = ["10.0.0.0/24"]
            self.app_state.add_edge(edge)
        
        # Create a group
        group = GroupModel()
        group.name = "main_network"
        group.topology = "star"
        group.color = "#4CAF50"
        for node_id in self.app_state.nodes.keys():
            group.add_node(node_id)
        self.app_state.add_group(group)
    
    def create_ui(self):
        """Create the main UI."""
        # Set page config
        ui.page_title('WireGuard Configuration Editor')
        
        # Create menu bar
        self.menubar = MenuBar(self.app_state)
        self.menubar.render()
        
        # Register menu handlers
        self.menubar.add_menu_item('file', 'open', 'Open', self._handle_open)
        self.menubar.add_menu_item('file', 'save', 'Save', self._handle_save)
        self.menubar.add_menu_item('file', 'import.nodes_topology', 'Import', self._handle_import)
        self.menubar.add_menu_item('file', 'export.package', 'Export', self._handle_export)
        self.menubar.add_menu_item('tools', 'validate', 'Validate', self._handle_validate)
        self.menubar.add_menu_item('view', 'layout.force', 'Force Layout', 
                                  lambda: self._apply_layout('force'))
        
        # Create toolbar
        with ui.row().classes('w-full'):
            self.toolbar = ToolBar(self.app_state)
            toolbar_element = self.toolbar.render()
            
            # Register toolbar handlers
            self.toolbar.set_action_handler('open', self._handle_open)
            self.toolbar.set_action_handler('save', self._handle_save)
            self.toolbar.set_action_handler('validate', self._handle_validate)
            self.toolbar.set_action_handler('export', self._handle_export)
            self.toolbar.set_action_handler('layout', lambda: self._apply_layout('force'))
            self.toolbar.set_action_handler('fit', self._fit_view)
        
        # Main content area
        with ui.row().classes('w-full flex-grow'):
            # Left panel - Node tree
            with ui.column().classes('h-full'):
                self.node_tree = NodeTree(self.app_state)
                self.node_tree.render()
                
                # Connect node tree events
                self.node_tree.on_node_select(self._on_node_select)
                self.node_tree.on_node_double_click(self._on_node_double_click)
            
            # Center - Graph view
            with ui.column().classes('flex-grow h-full'):
                # Graph container
                self.cytoscape = CytoscapeWidget(self.app_state, height="calc(100vh - 200px)")
                self.cytoscape.render()
                
                # Connect graph events
                self.cytoscape.on_node_click(self._on_graph_node_click)
                self.cytoscape.on_edge_click(self._on_graph_edge_click)
                self.cytoscape.on_background_click(self._on_graph_background_click)
                self.cytoscape.on_node_drag(self._on_node_drag)
                
                # Status bar
                with ui.row().classes('w-full items-center p-2 bg-gray-100'):
                    self.status_label = ui.label('Ready').classes('flex-grow')
                    self.node_count = ui.label(f'Nodes: {len(self.app_state.nodes)}')
                    self.edge_count = ui.label(f'Edges: {len(self.app_state.edges)}')
            
            # Right panel - Properties
            with ui.column().classes('h-full'):
                self.property_panel = PropertyPanel(self.app_state)
                self.property_panel.render()
                
                # Connect property panel events
                self.property_panel.on_save(self._on_properties_saved)
                self.property_panel.on_delete(self._on_element_delete)
        
        # Create export dialog (hidden initially)
        self.export_dialog = ExportDialog(self.app_state, self.export_manager)
        self.export_dialog.render()
        self.export_dialog.on_export(self._perform_export)
        
        # Subscribe to state changes
        self._subscribe_to_state_changes()
        
        # Initial layout
        ui.timer(1.0, lambda: self._apply_layout('force'), once=True)
    
    def _subscribe_to_state_changes(self):
        """Subscribe to application state changes."""
        # Update counts when nodes/edges change
        self.app_state.subscribe('node_added', lambda e: self._update_counts())
        self.app_state.subscribe('node_removed', lambda e: self._update_counts())
        self.app_state.subscribe('edge_added', lambda e: self._update_counts())
        self.app_state.subscribe('edge_removed', lambda e: self._update_counts())
        
        # Update status on state changes
        self.app_state.subscribe('state_dirty', lambda e: self._update_status('Modified'))
        self.app_state.subscribe('state_clean', lambda e: self._update_status('Ready'))
    
    def _update_counts(self):
        """Update node and edge counts."""
        self.node_count.text = f'Nodes: {len(self.app_state.nodes)}'
        self.edge_count.text = f'Edges: {len(self.app_state.edges)}'
    
    def _update_status(self, message: str):
        """Update status bar message."""
        self.status_label.text = message
    
    def _on_node_select(self, node_id: str):
        """Handle node selection from tree."""
        self.property_panel.load_properties(node_id)
        self.cytoscape.center_on_node(node_id)
    
    def _on_node_double_click(self, node_id: str):
        """Handle node double-click from tree."""
        self.cytoscape.center_on_node(node_id)
        self.cytoscape.set_selection([node_id])
    
    def _on_graph_node_click(self, node_id: str):
        """Handle node click from graph."""
        self.property_panel.load_properties(node_id)
    
    def _on_graph_edge_click(self, edge_id: str):
        """Handle edge click from graph."""
        self.property_panel.load_properties(edge_id)
    
    def _on_graph_background_click(self):
        """Handle background click from graph."""
        self.property_panel.clear()
    
    def _on_node_drag(self, node_id: str, position: Dict[str, float]):
        """Handle node drag from graph."""
        # Position is already updated in state by CytoscapeWidget
        pass
    
    def _on_properties_saved(self, element_id: str, properties: Dict[str, Any]):
        """Handle properties saved."""
        self._update_status('Properties saved')
    
    def _on_element_delete(self, element_id: str):
        """Handle element deletion."""
        if element_id in self.app_state.nodes:
            self.app_state.remove_node(element_id)
        elif element_id in self.app_state.edges:
            self.app_state.remove_edge(element_id)
        elif element_id in self.app_state.groups:
            self.app_state.remove_group(element_id)
    
    def _handle_open(self):
        """Handle open file action."""
        # Create file upload dialog
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
                session_id = self.import_wizard.start_import()
                for file_info in files:
                    self.import_wizard.add_file(
                        session_id, 
                        file_info['temp_path'],
                        file_info['config_type']
                    )
                # Execute import
                if self.import_wizard.execute_import(session_id, self.app_state):
                    ui.notify('Configuration imported successfully', type='positive')
                    self._apply_layout('force')
            
            upload.on_upload(handle_upload)
            
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Cancel', on_click=dialog.close)
        
        dialog.open()
    
    def _handle_save(self):
        """Handle save file action."""
        # For demo, just show notification
        ui.notify('Configuration saved', type='positive')
        self.app_state.mark_clean()
    
    def _handle_import(self):
        """Handle import action."""
        self._handle_open()
    
    def _handle_export(self):
        """Handle export action."""
        self.export_dialog.show()
    
    def _perform_export(self, options: Dict[str, Any]):
        """Perform the actual export."""
        ui.notify(f'Exporting as {options["format"]}...', type='info')
        # Actual export would happen here
    
    def _handle_validate(self):
        """Handle validate action."""
        errors = self.validation_manager.validate_configuration(self.app_state)
        
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
    
    def _apply_layout(self, layout_name: str):
        """Apply a layout to the graph."""
        self.graph_manager.apply_layout(self.app_state, layout_name)
        self.cytoscape.set_layout(layout_name)
        ui.notify(f'Applied {layout_name} layout', type='info')
    
    def _fit_view(self):
        """Fit graph to viewport."""
        self.cytoscape.fit_to_viewport()


def create_demo_app():
    """Create and run the demo application."""
    # Create app instance
    app = WireGuardEditor()
    
    # Create UI
    app.create_ui()
    
    # Add some custom CSS
    ui.add_head_html('''
    <style>
        .nicegui-content {
            padding: 0 !important;
        }
        body {
            margin: 0;
            overflow: hidden;
        }
    </style>
    ''')


# Create the demo page
@ui.page('/')
def main():
    create_demo_app()


if __name__ == '__main__':
    # Run the application
    ui.run(
        title='WireGuard Configuration Editor',
        port=8080,
        reload=False
    )