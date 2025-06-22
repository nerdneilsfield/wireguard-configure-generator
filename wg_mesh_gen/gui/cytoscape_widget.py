"""
Cytoscape.js widget for NiceGUI
"""
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from nicegui import ui


class CytoscapeWidget(ui.element, component='cytoscape_widget.js'):
    """Interactive graph visualization widget using Cytoscape.js"""
    
    def __init__(self) -> None:
        super().__init__()
        
        # Initialize properties
        self._props['elements'] = {'nodes': [], 'edges': []}
        self._props['style'] = self._default_style()
        self._props['layout'] = {'name': 'cose'}
        
        # Event handlers
        self._node_click_handler: Optional[Callable] = None
        self._edge_click_handler: Optional[Callable] = None
        self._canvas_click_handler: Optional[Callable] = None
        self._node_drag_handler: Optional[Callable] = None
        self._selection_handler: Optional[Callable] = None
        
        # Setup event listeners
        self.on('node-click', self._on_node_click)
        self.on('edge-click', self._on_edge_click)
        self.on('canvas-click', self._on_canvas_click)
        self.on('node-drag-end', self._on_node_drag)
        self.on('selection-change', self._on_selection_change)
    
    def _default_style(self) -> List[Dict[str, Any]]:
        """Default Cytoscape styles"""
        return [
            {
                'selector': 'node',
                'style': {
                    'background-color': '#666',
                    'label': 'data(label)',
                    'color': '#fff',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'width': 40,
                    'height': 40
                }
            },
            {
                'selector': 'node[role="relay"]',
                'style': {
                    'background-color': '#dc3545',
                    'shape': 'star',
                    'width': 50,
                    'height': 50
                }
            },
            {
                'selector': 'node:selected',
                'style': {
                    'background-color': '#0d6efd',
                    'border-width': 3,
                    'border-color': '#0d6efd'
                }
            },
            {
                'selector': 'edge',
                'style': {
                    'width': 3,
                    'line-color': '#ccc',
                    'target-arrow-color': '#ccc',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier'
                }
            },
            {
                'selector': 'edge[type="mesh"]',
                'style': {
                    'line-color': '#28a745',
                    'target-arrow-color': '#28a745'
                }
            },
            {
                'selector': 'edge[type="star"]',
                'style': {
                    'line-color': '#ffc107',
                    'target-arrow-color': '#ffc107',
                    'line-style': 'dashed'
                }
            },
            {
                'selector': 'edge:selected',
                'style': {
                    'line-color': '#0d6efd',
                    'target-arrow-color': '#0d6efd',
                    'width': 4
                }
            }
        ]
    
    def add_node(self, node_id: str, label: str, 
                 wireguard_ip: Optional[str] = None,
                 role: str = 'client',
                 group: Optional[str] = None,
                 position: Optional[Dict[str, float]] = None) -> None:
        """Add a node to the graph"""
        node_data = {
            'data': {
                'id': node_id,
                'label': label,
                'role': role,
                'group': group,
                'wireguard_ip': wireguard_ip
            },
            'position': position or {'x': 100, 'y': 100}
        }
        
        # Update internal state
        self._props['elements']['nodes'].append(node_data)
        
        # Call JavaScript method
        self.run_method('addNode', node_data)
    
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> None:
        """Update node properties"""
        self.run_method('updateNode', node_id, updates)
        
        # Update internal state
        for node in self._props['elements']['nodes']:
            if node['data']['id'] == node_id:
                if 'data' in updates:
                    node['data'].update(updates['data'])
                if 'position' in updates:
                    node['position'] = updates['position']
                break
    
    def delete_node(self, node_id: str) -> None:
        """Delete a node from the graph"""
        self.run_method('deleteNode', node_id)
        
        # Update internal state
        self._props['elements']['nodes'] = [
            n for n in self._props['elements']['nodes'] 
            if n['data']['id'] != node_id
        ]
        # Also remove connected edges
        self._props['elements']['edges'] = [
            e for e in self._props['elements']['edges']
            if e['data']['source'] != node_id and e['data']['target'] != node_id
        ]
    
    def add_edge(self, edge_id: str, source: str, target: str,
                 edge_type: str = 'peer',
                 allowed_ips: Optional[List[str]] = None) -> None:
        """Add an edge to the graph"""
        edge_data = {
            'data': {
                'id': edge_id,
                'source': source,
                'target': target,
                'type': edge_type,
                'allowed_ips': allowed_ips or []
            }
        }
        
        # Update internal state
        self._props['elements']['edges'].append(edge_data)
        
        # Call JavaScript method
        self.run_method('addEdge', edge_data)
    
    def update_edge(self, edge_id: str, updates: Dict[str, Any]) -> None:
        """Update edge properties"""
        self.run_method('updateEdge', edge_id, updates)
        
        # Update internal state
        for edge in self._props['elements']['edges']:
            if edge['data']['id'] == edge_id:
                if 'data' in updates:
                    edge['data'].update(updates['data'])
                break
    
    def delete_edge(self, edge_id: str) -> None:
        """Delete an edge from the graph"""
        self.run_method('deleteEdge', edge_id)
        
        # Update internal state
        self._props['elements']['edges'] = [
            e for e in self._props['elements']['edges']
            if e['data']['id'] != edge_id
        ]
    
    def apply_layout(self, layout_name: str = 'cose', 
                     options: Optional[Dict[str, Any]] = None) -> None:
        """Apply a layout algorithm to the graph"""
        self.run_method('applyLayout', layout_name, options or {})
    
    def fit_view(self) -> None:
        """Fit all elements in the viewport"""
        self.run_method('fitView')
    
    def clear(self) -> None:
        """Clear all elements from the graph"""
        self._props['elements'] = {'nodes': [], 'edges': []}
        self.update()
    
    def get_elements(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get current graph elements"""
        return self._props['elements']
    
    # Event handler setters
    def on_node_click(self, handler: Callable) -> None:
        """Set handler for node click events"""
        self._node_click_handler = handler
    
    def on_edge_click(self, handler: Callable) -> None:
        """Set handler for edge click events"""
        self._edge_click_handler = handler
    
    def on_canvas_click(self, handler: Callable) -> None:
        """Set handler for canvas click events"""
        self._canvas_click_handler = handler
    
    def on_node_drag_end(self, handler: Callable) -> None:
        """Set handler for node drag end events"""
        self._node_drag_handler = handler
    
    def on_selection_change(self, handler: Callable) -> None:
        """Set handler for selection change events"""
        self._selection_handler = handler
    
    # Internal event handlers
    def _on_node_click(self, e) -> None:
        if self._node_click_handler:
            self._node_click_handler(e.args)
    
    def _on_edge_click(self, e) -> None:
        if self._edge_click_handler:
            self._edge_click_handler(e.args)
    
    def _on_canvas_click(self, e) -> None:
        if self._canvas_click_handler:
            self._canvas_click_handler(e.args)
    
    def _on_node_drag(self, e) -> None:
        if self._node_drag_handler:
            self._node_drag_handler(e.args)
    
    def _on_selection_change(self, e) -> None:
        if self._selection_handler:
            self._selection_handler(e.args)