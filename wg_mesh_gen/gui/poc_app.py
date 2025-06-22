#!/usr/bin/env python3
"""
Proof of Concept: WireGuard Visual Configuration Editor
This demonstrates the basic integration of NiceGUI with Cytoscape.js
"""
import uuid
from typing import Dict, Any, Optional
from nicegui import ui
from pathlib import Path

# Add the widget module to path
import sys
sys.path.append(str(Path(__file__).parent))

from cytoscape_widget import CytoscapeWidget


class WireGuardPOC:
    """Proof of concept for WireGuard visual editor"""
    
    def __init__(self):
        self.graph: Optional[CytoscapeWidget] = None
        self.selected_node: Optional[str] = None
        self.selected_edge: Optional[str] = None
        self.node_counter = 0
        
    def create_ui(self):
        """Create the main UI"""
        # Header
        with ui.header().classes('bg-blue-600 text-white'):
            ui.label('WireGuard Visual Configuration Editor - Proof of Concept').classes('text-2xl')
        
        # Main container
        with ui.row().classes('w-full'):
            # Left panel - Controls
            with ui.column().classes('w-64 p-4 bg-gray-100'):
                ui.label('Controls').classes('text-lg font-bold mb-4')
                
                # Node operations
                with ui.card().classes('mb-4'):
                    ui.label('Node Operations').classes('font-semibold')
                    
                    self.node_name_input = ui.input(
                        label='Node Name',
                        placeholder='Enter node name'
                    ).classes('w-full mb-2')
                    
                    self.node_ip_input = ui.input(
                        label='IP Address',
                        placeholder='10.0.0.1/24'
                    ).classes('w-full mb-2')
                    
                    ui.button('Add Node', on_click=self.add_node).classes('w-full')
                    ui.button('Delete Selected', on_click=self.delete_selected).classes('w-full mt-2')
                
                # Edge operations
                with ui.card().classes('mb-4'):
                    ui.label('Edge Operations').classes('font-semibold')
                    
                    self.edge_info = ui.label('Select two nodes to connect').classes('text-sm')
                    
                    ui.button('Connect Selected', on_click=self.connect_nodes).classes('w-full')
                
                # Layout options
                with ui.card():
                    ui.label('Layout').classes('font-semibold')
                    
                    ui.button('Force Layout', on_click=lambda: self.apply_layout('cose')).classes('w-full mb-1')
                    ui.button('Circle Layout', on_click=lambda: self.apply_layout('circle')).classes('w-full mb-1')
                    ui.button('Grid Layout', on_click=lambda: self.apply_layout('grid')).classes('w-full mb-1')
                    ui.button('Fit View', on_click=self.fit_view).classes('w-full')
            
            # Right panel - Graph canvas
            with ui.column().classes('flex-grow'):
                # Info bar
                with ui.row().classes('w-full p-2 bg-gray-200'):
                    self.status_label = ui.label('Click canvas to add nodes, or use the controls')
                
                # Graph container
                with ui.card().classes('w-full h-screen').style('height: calc(100vh - 200px)'):
                    self.graph = CytoscapeWidget()
                    
                    # Setup event handlers
                    self.graph.on_node_click(self.on_node_click)
                    self.graph.on_edge_click(self.on_edge_click)
                    self.graph.on_canvas_click(self.on_canvas_click)
                    self.graph.on_node_drag_end(self.on_node_drag)
                    self.graph.on_selection_change(self.on_selection_change)
        
        # Property panel (bottom)
        with ui.expansion('Properties', icon='settings').classes('w-full'):
            with ui.row().classes('w-full'):
                self.properties_container = ui.column().classes('w-full')
                self.update_properties_panel()
        
        # Add some demo data
        self.add_demo_data()
    
    def add_node(self) -> None:
        """Add a new node to the graph"""
        name = self.node_name_input.value.strip()
        ip = self.node_ip_input.value.strip()
        
        if not name:
            ui.notify('Please enter a node name', type='warning')
            return
        
        if not ip:
            ip = f'10.0.0.{self.node_counter + 1}/24'
        
        node_id = f'node_{uuid.uuid4().hex[:8]}'
        self.node_counter += 1
        
        # Determine role based on name
        role = 'relay' if 'relay' in name.lower() or 'gateway' in name.lower() else 'client'
        
        # Add to graph
        self.graph.add_node(
            node_id=node_id,
            label=name,
            wireguard_ip=ip,
            role=role,
            position={
                'x': 100 + (self.node_counter % 5) * 150,
                'y': 100 + (self.node_counter // 5) * 150
            }
        )
        
        # Clear inputs
        self.node_name_input.value = ''
        self.node_ip_input.value = ''
        
        ui.notify(f'Added node: {name}', type='positive')
        self.status_label.text = f'Added node: {name} ({ip})'
    
    def delete_selected(self) -> None:
        """Delete selected node or edge"""
        if self.selected_node:
            self.graph.delete_node(self.selected_node)
            ui.notify('Node deleted', type='info')
            self.selected_node = None
            self.update_properties_panel()
        elif self.selected_edge:
            self.graph.delete_edge(self.selected_edge)
            ui.notify('Edge deleted', type='info')
            self.selected_edge = None
            self.update_properties_panel()
        else:
            ui.notify('No element selected', type='warning')
    
    def connect_nodes(self) -> None:
        """Connect two selected nodes"""
        # This is a simplified version - in real app would track multiple selections
        ui.notify('Select nodes by clicking them, then click Connect', type='info')
    
    def apply_layout(self, layout_name: str) -> None:
        """Apply a layout algorithm"""
        options = {}
        if layout_name == 'circle':
            options = {'radius': 200}
        elif layout_name == 'grid':
            options = {'rows': 3}
        
        self.graph.apply_layout(layout_name, options)
        self.status_label.text = f'Applied {layout_name} layout'
    
    def fit_view(self) -> None:
        """Fit all elements in view"""
        self.graph.fit_view()
    
    # Event handlers
    def on_node_click(self, event: Dict[str, Any]) -> None:
        """Handle node click"""
        self.selected_node = event['id']
        self.selected_edge = None
        self.status_label.text = f"Selected node: {event['data']['label']}"
        self.update_properties_panel()
    
    def on_edge_click(self, event: Dict[str, Any]) -> None:
        """Handle edge click"""
        self.selected_edge = event['id']
        self.selected_node = None
        self.status_label.text = f"Selected edge: {event['source']} → {event['target']}"
        self.update_properties_panel()
    
    def on_canvas_click(self, event: Dict[str, Any]) -> None:
        """Handle canvas click - add node at position"""
        position = event['position']
        
        # Quick add node at clicked position
        node_id = f'node_{uuid.uuid4().hex[:8]}'
        name = f'Node{self.node_counter + 1}'
        self.node_counter += 1
        
        self.graph.add_node(
            node_id=node_id,
            label=name,
            wireguard_ip=f'10.0.0.{self.node_counter}/24',
            role='client',
            position=position
        )
        
        self.status_label.text = f'Added {name} at position'
    
    def on_node_drag(self, event: Dict[str, Any]) -> None:
        """Handle node drag end"""
        self.status_label.text = f"Moved node to new position"
    
    def on_selection_change(self, selected: list) -> None:
        """Handle selection change"""
        if len(selected) == 2:
            # Two nodes selected - can create edge
            nodes = [s for s in selected if s['type'] == 'node']
            if len(nodes) == 2:
                edge_id = f'edge_{uuid.uuid4().hex[:8]}'
                self.graph.add_edge(
                    edge_id=edge_id,
                    source=nodes[0]['id'],
                    target=nodes[1]['id'],
                    edge_type='peer'
                )
                ui.notify('Connected nodes', type='positive')
    
    def update_properties_panel(self) -> None:
        """Update the properties panel based on selection"""
        self.properties_container.clear()
        
        if self.selected_node:
            # Find node data
            nodes = self.graph.get_elements()['nodes']
            node_data = next((n for n in nodes if n['data']['id'] == self.selected_node), None)
            
            if node_data:
                with self.properties_container:
                    ui.label('Node Properties').classes('font-semibold mb-2')
                    
                    data = node_data['data']
                    ui.label(f"ID: {data['id']}")
                    ui.label(f"Name: {data['label']}")
                    ui.label(f"IP: {data.get('wireguard_ip', 'Not set')}")
                    ui.label(f"Role: {data.get('role', 'client')}")
                    
                    # Edit controls
                    new_name = ui.input('Name', value=data['label']).classes('mt-2')
                    new_ip = ui.input('IP Address', value=data.get('wireguard_ip', '')).classes('mt-1')
                    
                    def update_node():
                        self.graph.update_node(self.selected_node, {
                            'data': {
                                'label': new_name.value,
                                'wireguard_ip': new_ip.value
                            }
                        })
                        ui.notify('Node updated', type='positive')
                        self.update_properties_panel()
                    
                    ui.button('Update', on_click=update_node).classes('mt-2')
        
        elif self.selected_edge:
            # Find edge data
            edges = self.graph.get_elements()['edges']
            edge_data = next((e for e in edges if e['data']['id'] == self.selected_edge), None)
            
            if edge_data:
                with self.properties_container:
                    ui.label('Edge Properties').classes('font-semibold mb-2')
                    
                    data = edge_data['data']
                    ui.label(f"ID: {data['id']}")
                    ui.label(f"Source: {data['source']}")
                    ui.label(f"Target: {data['target']}")
                    ui.label(f"Type: {data.get('type', 'peer')}")
                    
                    # Allowed IPs
                    ui.label('Allowed IPs:').classes('mt-2')
                    allowed_ips = data.get('allowed_ips', [])
                    if allowed_ips:
                        for ip in allowed_ips:
                            ui.label(f"  • {ip}")
                    else:
                        ui.label('  None configured').classes('text-gray-500')
        
        else:
            with self.properties_container:
                ui.label('No element selected').classes('text-gray-500')
    
    def add_demo_data(self) -> None:
        """Add some demo nodes and edges"""
        # Add a few nodes
        nodes = [
            ('office-gw', 'Office Gateway', '10.0.0.1/24', 'relay', {'x': 400, 'y': 200}),
            ('office-pc1', 'Office PC1', '10.0.0.10/24', 'client', {'x': 200, 'y': 100}),
            ('office-pc2', 'Office PC2', '10.0.0.11/24', 'client', {'x': 200, 'y': 300}),
            ('cloud-server', 'Cloud Server', '10.0.1.10/24', 'client', {'x': 600, 'y': 200}),
        ]
        
        for node_id, label, ip, role, pos in nodes:
            self.graph.add_node(
                node_id=node_id,
                label=label,
                wireguard_ip=ip,
                role=role,
                position=pos
            )
        
        # Add some edges
        edges = [
            ('e1', 'office-pc1', 'office-gw', 'star', ['10.0.0.1/32']),
            ('e2', 'office-pc2', 'office-gw', 'star', ['10.0.0.1/32']),
            ('e3', 'office-gw', 'cloud-server', 'peer', ['10.0.1.10/32']),
        ]
        
        for edge_id, source, target, edge_type, allowed_ips in edges:
            self.graph.add_edge(
                edge_id=edge_id,
                source=source,
                target=target,
                edge_type=edge_type,
                allowed_ips=allowed_ips
            )
        
        # Apply layout
        self.apply_layout('cose')
        self.status_label.text = 'Demo data loaded'


def main():
    """Run the proof of concept"""
    app = WireGuardPOC()
    app.create_ui()
    
    ui.run(
        title='WireGuard Visual Editor POC',
        port=8080,
        show=True,
        reload=True
    )


if __name__ == '__main__':
    main()