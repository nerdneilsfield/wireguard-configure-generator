"""
Cytoscape widget implementation for network graph visualization.

This component provides an interactive network graph using Cytoscape.js
integrated with NiceGUI.
"""

from typing import Dict, List, Optional, Callable, Any, Set
import json

from nicegui import ui, run

from .base import BaseComponent
from ..interfaces.components import ICytoscapeWidget
from ..interfaces.state import IAppState
from ..interfaces.events import Event


class CytoscapeWidget(BaseComponent, ICytoscapeWidget):
    """Implementation of ICytoscapeWidget using Cytoscape.js."""
    
    def __init__(self, 
                 app_state: IAppState,
                 width: str = "100%",
                 height: str = "600px",
                 component_id: Optional[str] = None):
        """
        Initialize Cytoscape widget.
        
        Args:
            app_state: Application state
            width: Widget width
            height: Widget height
            component_id: Optional component ID
        """
        super().__init__(component_id)
        self._app_state = app_state
        self._width = width
        self._height = height
        self._selected_elements: Set[str] = set()
        
        # Event handlers
        self._on_node_click: Optional[Callable[[str], None]] = None
        self._on_edge_click: Optional[Callable[[str], None]] = None
        self._on_background_click: Optional[Callable[[], None]] = None
        self._on_node_drag: Optional[Callable[[str, Dict[str, float]], None]] = None
        
        # Subscribe to app state events
        self._subscribe_to_events()
    
    def render(self) -> ui.element:
        """Render the Cytoscape widget."""
        # Create container
        with ui.column().classes('w-full') as container:
            # Add Cytoscape.js script if not already loaded
            ui.run_javascript('''
                if (!window.cytoscape) {
                    const script = document.createElement('script');
                    script.src = 'https://unpkg.com/cytoscape@3.23.0/dist/cytoscape.min.js';
                    document.head.appendChild(script);
                }
            ''')
            
            # Create the Cytoscape container
            self._element = ui.html(f'<div id="cy-{self._id}" style="width: {self._width}; height: {self._height}; border: 1px solid #ccc;"></div>')
            
            # Initialize Cytoscape after a short delay to ensure scripts are loaded
            ui.timer(0.5, self._initialize_cytoscape, once=True)
        
        return container
    
    def _initialize_cytoscape(self) -> None:
        """Initialize Cytoscape.js instance."""
        # Generate initial elements from app state
        elements = self._generate_elements()
        
        # Cytoscape initialization code
        init_code = f'''
            // Wait for Cytoscape to be available
            if (window.cytoscape) {{
                const cy = cytoscape({{
                    container: document.getElementById('cy-{self._id}'),
                    elements: {json.dumps(elements)},
                    style: [
                        {{
                            selector: 'node',
                            style: {{
                                'label': 'data(label)',
                                'background-color': 'data(color)',
                                'text-valign': 'center',
                                'text-halign': 'center',
                                'width': 60,
                                'height': 60,
                                'font-size': 12,
                                'border-width': 2,
                                'border-color': '#666'
                            }}
                        }},
                        {{
                            selector: 'node[role="relay"]',
                            style: {{
                                'background-color': '#4CAF50',
                                'shape': 'diamond',
                                'width': 80,
                                'height': 80
                            }}
                        }},
                        {{
                            selector: 'node[role="client"]',
                            style: {{
                                'background-color': '#2196F3',
                                'shape': 'ellipse'
                            }}
                        }},
                        {{
                            selector: 'edge',
                            style: {{
                                'width': 3,
                                'line-color': '#999',
                                'target-arrow-color': '#999',
                                'target-arrow-shape': 'triangle',
                                'curve-style': 'bezier'
                            }}
                        }},
                        {{
                            selector: ':selected',
                            style: {{
                                'background-color': '#FFA726',
                                'line-color': '#FFA726',
                                'target-arrow-color': '#FFA726'
                            }}
                        }}
                    ],
                    layout: {{
                        name: 'cose',
                        animate: true,
                        randomize: false,
                        fit: true,
                        padding: 50
                    }},
                    userZoomingEnabled: true,
                    userPanningEnabled: true,
                    boxSelectionEnabled: true
                }});
                
                // Store reference
                window['cy_{self._id}'] = cy;
                
                // Event handlers
                cy.on('tap', 'node', function(evt) {{
                    const node = evt.target;
                    pywebview.api.call_method('{self._id}', '_handle_node_click', [node.id()]);
                }});
                
                cy.on('tap', 'edge', function(evt) {{
                    const edge = evt.target;
                    pywebview.api.call_method('{self._id}', '_handle_edge_click', [edge.id()]);
                }});
                
                cy.on('tap', function(evt) {{
                    if (evt.target === cy) {{
                        pywebview.api.call_method('{self._id}', '_handle_background_click', []);
                    }}
                }});
                
                cy.on('dragfree', 'node', function(evt) {{
                    const node = evt.target;
                    const pos = node.position();
                    pywebview.api.call_method('{self._id}', '_handle_node_drag', [node.id(), pos]);
                }});
            }}
        '''
        
        ui.run_javascript(init_code)
    
    def _generate_elements(self) -> List[Dict[str, Any]]:
        """Generate Cytoscape elements from app state."""
        elements = []
        
        # Add nodes
        for node_id, node in self._app_state.nodes.items():
            position = node.metadata.get('position', {})
            element = {
                'data': {
                    'id': node_id,
                    'label': node.name,
                    'role': node.role,
                    'wireguard_ip': node.wireguard_ip,
                    'color': '#4CAF50' if node.role == 'relay' else '#2196F3'
                }
            }
            
            if position:
                element['position'] = {'x': position.get('x', 0), 'y': position.get('y', 0)}
            
            elements.append(element)
        
        # Add edges
        for edge_id, edge in self._app_state.edges.items():
            elements.append({
                'data': {
                    'id': edge_id,
                    'source': edge.source_id,
                    'target': edge.target_id
                }
            })
        
        return elements
    
    def add_node(self, node_id: str, label: str, 
                wireguard_ip: Optional[str] = None,
                role: str = 'client', 
                group: Optional[str] = None,
                position: Optional[Dict[str, float]] = None) -> None:
        """Add a node to the graph."""
        element = {
            'data': {
                'id': node_id,
                'label': label,
                'role': role,
                'wireguard_ip': wireguard_ip,
                'group': group,
                'color': '#4CAF50' if role == 'relay' else '#2196F3'
            }
        }
        
        if position:
            element['position'] = position
        
        js_code = f'''
            const cy = window['cy_{self._id}'];
            if (cy) {{
                cy.add({json.dumps(element)});
            }}
        '''
        ui.run_javascript(js_code)
    
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> None:
        """Update node properties."""
        js_code = f'''
            const cy = window['cy_{self._id}'];
            if (cy) {{
                const node = cy.getElementById('{node_id}');
                if (node) {{
                    const data = {json.dumps(updates)};
                    Object.keys(data).forEach(key => {{
                        node.data(key, data[key]);
                    }});
                    
                    // Update color based on role
                    if (data.role) {{
                        node.data('color', data.role === 'relay' ? '#4CAF50' : '#2196F3');
                    }}
                }}
            }}
        '''
        ui.run_javascript(js_code)
    
    def delete_node(self, node_id: str) -> None:
        """Delete a node from the graph."""
        js_code = f'''
            const cy = window['cy_{self._id}'];
            if (cy) {{
                const node = cy.getElementById('{node_id}');
                if (node) {{
                    cy.remove(node);
                }}
            }}
        '''
        ui.run_javascript(js_code)
    
    def add_edge(self, edge_id: str, source_id: str, target_id: str,
                allowed_ips: Optional[List[str]] = None) -> None:
        """Add an edge to the graph."""
        element = {
            'data': {
                'id': edge_id,
                'source': source_id,
                'target': target_id,
                'allowed_ips': allowed_ips
            }
        }
        
        js_code = f'''
            const cy = window['cy_{self._id}'];
            if (cy) {{
                cy.add({json.dumps(element)});
            }}
        '''
        ui.run_javascript(js_code)
    
    def update_edge(self, edge_id: str, updates: Dict[str, Any]) -> None:
        """Update edge properties."""
        js_code = f'''
            const cy = window['cy_{self._id}'];
            if (cy) {{
                const edge = cy.getElementById('{edge_id}');
                if (edge) {{
                    const data = {json.dumps(updates)};
                    Object.keys(data).forEach(key => {{
                        edge.data(key, data[key]);
                    }});
                }}
            }}
        '''
        ui.run_javascript(js_code)
    
    def delete_edge(self, edge_id: str) -> None:
        """Delete an edge from the graph."""
        js_code = f'''
            const cy = window['cy_{self._id}'];
            if (cy) {{
                const edge = cy.getElementById('{edge_id}');
                if (edge) {{
                    cy.remove(edge);
                }}
            }}
        '''
        ui.run_javascript(js_code)
    
    def set_layout(self, layout_name: str, options: Optional[Dict[str, Any]] = None) -> None:
        """Apply a layout algorithm."""
        layout_options = options or {}
        layout_config = {
            'name': layout_name,
            'animate': True,
            'animationDuration': 500,
            'fit': True,
            'padding': 50,
            **layout_options
        }
        
        js_code = f'''
            const cy = window['cy_{self._id}'];
            if (cy) {{
                const layout = cy.layout({json.dumps(layout_config)});
                layout.run();
            }}
        '''
        ui.run_javascript(js_code)
    
    def fit_to_viewport(self, padding: int = 50) -> None:
        """Fit graph to viewport."""
        js_code = f'''
            const cy = window['cy_{self._id}'];
            if (cy) {{
                cy.fit(cy.elements(), {padding});
            }}
        '''
        ui.run_javascript(js_code)
    
    def center_on_node(self, node_id: str) -> None:
        """Center viewport on a specific node."""
        js_code = f'''
            const cy = window['cy_{self._id}'];
            if (cy) {{
                const node = cy.getElementById('{node_id}');
                if (node) {{
                    cy.animate({{
                        center: {{ eles: node }},
                        zoom: cy.zoom(),
                        duration: 500
                    }});
                }}
            }}
        '''
        ui.run_javascript(js_code)
    
    def get_selected_elements(self) -> List[str]:
        """Get list of selected element IDs."""
        return list(self._selected_elements)
    
    def set_selection(self, element_ids: List[str]) -> None:
        """Set the selected elements."""
        self._selected_elements = set(element_ids)
        
        js_code = f'''
            const cy = window['cy_{self._id}'];
            if (cy) {{
                // Clear current selection
                cy.elements().unselect();
                
                // Select specified elements
                const ids = {json.dumps(element_ids)};
                ids.forEach(id => {{
                    const ele = cy.getElementById(id);
                    if (ele) {{
                        ele.select();
                    }}
                }});
            }}
        '''
        ui.run_javascript(js_code)
    
    def clear_selection(self) -> None:
        """Clear all selections."""
        self._selected_elements.clear()
        
        js_code = f'''
            const cy = window['cy_{self._id}'];
            if (cy) {{
                cy.elements().unselect();
            }}
        '''
        ui.run_javascript(js_code)
    
    def export_image(self, format: str = 'png') -> str:
        """Export graph as image."""
        # This would need to be implemented with proper async handling
        # For now, return a placeholder
        return f"graph_export.{format}"
    
    def on_node_click(self, handler: Callable[[str], None]) -> None:
        """Register node click handler."""
        self._on_node_click = handler
    
    def on_edge_click(self, handler: Callable[[str], None]) -> None:
        """Register edge click handler."""
        self._on_edge_click = handler
    
    def on_background_click(self, handler: Callable[[], None]) -> None:
        """Register background click handler."""
        self._on_background_click = handler
    
    def on_node_drag(self, handler: Callable[[str, Dict[str, float]], None]) -> None:
        """Register node drag handler."""
        self._on_node_drag = handler
    
    def _handle_node_click(self, node_id: str) -> None:
        """Handle node click event."""
        if node_id in self._selected_elements:
            self._selected_elements.remove(node_id)
        else:
            self._selected_elements.add(node_id)
        
        if self._on_node_click:
            self._on_node_click(node_id)
    
    def _handle_edge_click(self, edge_id: str) -> None:
        """Handle edge click event."""
        if edge_id in self._selected_elements:
            self._selected_elements.remove(edge_id)
        else:
            self._selected_elements.add(edge_id)
        
        if self._on_edge_click:
            self._on_edge_click(edge_id)
    
    def _handle_background_click(self) -> None:
        """Handle background click event."""
        self.clear_selection()
        
        if self._on_background_click:
            self._on_background_click()
    
    def _handle_node_drag(self, node_id: str, position: Dict[str, float]) -> None:
        """Handle node drag event."""
        # Update node position in app state
        if node_id in self._app_state.nodes:
            self._app_state.update_node(node_id, {'position': position})
        
        if self._on_node_drag:
            self._on_node_drag(node_id, position)
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to app state events."""
        # Node events
        self._app_state.subscribe('node_added', self._on_node_added)
        self._app_state.subscribe('node_updated', self._on_node_updated)
        self._app_state.subscribe('node_removed', self._on_node_removed)
        
        # Edge events
        self._app_state.subscribe('edge_added', self._on_edge_added)
        self._app_state.subscribe('edge_updated', self._on_edge_updated)
        self._app_state.subscribe('edge_removed', self._on_edge_removed)
        
        # Selection events
        self._app_state.subscribe('selection_changed', self._on_selection_changed)
    
    def _on_node_added(self, event: Event) -> None:
        """Handle node added event."""
        node = event.data['node']
        self.add_node(
            node.id, 
            node.name, 
            node.wireguard_ip,
            node.role,
            node.group_id,
            node.metadata.get('position')
        )
    
    def _on_node_updated(self, event: Event) -> None:
        """Handle node updated event."""
        node_id = event.data['node_id']
        updates = event.data['updates']
        self.update_node(node_id, updates)
    
    def _on_node_removed(self, event: Event) -> None:
        """Handle node removed event."""
        node_id = event.data['node_id']
        self.delete_node(node_id)
    
    def _on_edge_added(self, event: Event) -> None:
        """Handle edge added event."""
        edge = event.data['edge']
        self.add_edge(edge.id, edge.source_id, edge.target_id, edge.allowed_ips)
    
    def _on_edge_updated(self, event: Event) -> None:
        """Handle edge updated event."""
        edge_id = event.data['edge_id']
        updates = event.data['updates']
        self.update_edge(edge_id, updates)
    
    def _on_edge_removed(self, event: Event) -> None:
        """Handle edge removed event."""
        edge_id = event.data['edge_id']
        self.delete_edge(edge_id)
    
    def _on_selection_changed(self, event: Event) -> None:
        """Handle selection changed event."""
        selected = event.data['selected']
        self.set_selection(selected)
    
    def destroy(self) -> None:
        """Clean up the component."""
        # Unsubscribe from events
        self._app_state.unsubscribe('node_added', self._on_node_added)
        self._app_state.unsubscribe('node_updated', self._on_node_updated)
        self._app_state.unsubscribe('node_removed', self._on_node_removed)
        self._app_state.unsubscribe('edge_added', self._on_edge_added)
        self._app_state.unsubscribe('edge_updated', self._on_edge_updated)
        self._app_state.unsubscribe('edge_removed', self._on_edge_removed)
        self._app_state.unsubscribe('selection_changed', self._on_selection_changed)
        
        # Clean up Cytoscape instance
        js_code = f'''
            const cy = window['cy_{self._id}'];
            if (cy) {{
                cy.destroy();
                delete window['cy_{self._id}'];
            }}
        '''
        ui.run_javascript(js_code)
        
        # Call parent destroy
        super().destroy()