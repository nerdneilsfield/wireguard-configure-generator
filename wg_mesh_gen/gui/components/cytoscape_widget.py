"""
Cytoscape.js widget implementation for network visualization.

This component provides the main network graph visualization using Cytoscape.js.
"""

from typing import Dict, List, Optional, Any, Callable
import json
import uuid
from nicegui import ui
from nicegui.elements.mixins.value_element import ValueElement

from .base import BaseComponent
from ..interfaces.components import ICytoscapeWidget
from ..interfaces.state import IAppState
from ..interfaces.models import INodeModel, IEdgeModel
from ...logger import get_logger


class CytoscapeWidget(BaseComponent, ICytoscapeWidget, ValueElement):
    """
    Implementation of ICytoscapeWidget using Cytoscape.js.
    
    This widget provides:
    - Interactive network visualization
    - Drag and drop node positioning
    - Node/edge selection and editing
    - Multiple layout algorithms
    - Zoom and pan controls
    - Context menus
    """
    
    def __init__(self, state: IAppState, component_id: Optional[str] = None, **kwargs):
        """
        Initialize the Cytoscape widget.
        
        Args:
            state: Application state
            component_id: Optional component ID
            **kwargs: Additional widget options
        """
        # Initialize logger first
        self._logger = get_logger()
        
        # Generate unique container ID first (before anything else)
        self._container_id = f'cy-{uuid.uuid4().hex[:8]}'
        
        # Initialize parent classes
        BaseComponent.__init__(self, component_id)
        ValueElement.__init__(self, tag='div', value=None, **kwargs)
        self._state = state
        self._selected_elements: List[str] = []
        self._callbacks: Dict[str, List[Callable]] = {
            'node_click': [],
            'edge_click': [],
            'canvas_click': [],
            'node_drag': [],
            'selection_change': []
        }
        self._on_background_click: Optional[Callable[[], None]] = None
        
        # Default styles
        self._styles = self._get_default_styles()
        
        # Initialize Cytoscape
        self._initialize_cytoscape()
    
    def render(self) -> ui.element:
        """Render the component (returns self as it's already an element)."""
        return self
    
    # IComponent interface properties
    @property
    def id(self) -> str:
        """Component ID."""
        return getattr(self, 'component_id', self._container_id)
    
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
        # Use JavaScript to control visibility  
        element_id = self._container_id
        display = 'block' if value else 'none'
        ui.run_javascript(f'''
            const elements = document.querySelectorAll('[data-component-id="{element_id}"], #{element_id}');
            elements.forEach(el => {{
                el.style.display = '{display}';
            }});
        ''')
    
    @property
    def enabled(self) -> bool:
        """Whether the component is enabled."""
        return getattr(self, '_enabled', True)
    
    @enabled.setter  
    def enabled(self, value: bool) -> None:
        """Set component enabled state."""
        self._enabled = value
        # For graph components, enabled affects interaction
        ui.run_javascript(f'''
            if (window.cy_{self._container_id}) {{
                window.cy_{self._container_id}.{'enable' if value else 'disable'}User();
            }}
        ''')
    
    def update(self) -> None:
        """Update the component."""
        self.refresh()
    
    def destroy(self) -> None:
        """Destroy the component."""
        ui.run_javascript(f'''
            if (window.cy_{self._container_id}) {{
                window.cy_{self._container_id}.destroy();
                delete window.cy_{self._container_id};
            }}
        ''')
        if hasattr(self, 'delete'):
            self.delete()
        
    def _initialize_cytoscape(self) -> None:
        """Initialize Cytoscape.js instance."""
        # Create container with proper sizing
        self.classes('w-full h-full')
        self.style('min-height: 600px')
        
        # Set the container ID for the element
        try:
            self.props(id=self._container_id)
        except Exception:
            # Fallback if props doesn't work
            pass
        
        # Load Cytoscape.js library if not already loaded
        ui.run_javascript('''
            if (!window.cytoscape) {
                const script = document.createElement('script');
                script.src = 'https://unpkg.com/cytoscape@3.23.0/dist/cytoscape.min.js';
                document.head.appendChild(script);
                console.log('Loading Cytoscape.js library...');
            } else {
                console.log('Cytoscape.js already loaded');
            }
        ''')
        
        # Wait a moment for the library to load, then initialize
        ui.timer(1.0, self._create_cytoscape_instance, once=True)
    
    def _create_cytoscape_instance(self) -> None:
        """Create the actual Cytoscape instance after library is loaded."""
        # Initialize Cytoscape with configuration
        config = {
            'container': f'#{self._container_id}',
            'elements': self._get_elements_data(),
            'style': self._styles,
            'layout': {'name': 'cose'},
            'wheelSensitivity': 0.2,
            'minZoom': 0.1,
            'maxZoom': 3
        }
        
        # Add JavaScript initialization
        ui.run_javascript(f'''
            (function() {{
                // Check if Cytoscape.js is loaded
                if (!window.cytoscape) {{
                    console.error('Cytoscape.js library not loaded');
                    return;
                }}
                
                // Wait for container to be ready
                const container = document.getElementById('{self._container_id}');
                if (!container) {{
                    console.log('Container not ready, retrying...');
                    setTimeout(arguments.callee, 100);
                    return;
                }}
                
                console.log('Initializing Cytoscape instance for container:', '{self._container_id}');
                console.log('Config:', {json.dumps(config)});
                
                // Initialize Cytoscape
                const cy = cytoscape({json.dumps(config)});
                
                // Store instance globally for access
                window.cy_{self._container_id} = cy;
                
                // Setup event handlers
                cy.on('tap', 'node', function(evt) {{
                    const node = evt.target;
                    window.nicegui.emit('{self._container_id}', 'node_click', {{
                        id: node.id(),
                        data: node.data()
                    }});
                }});
                
                cy.on('tap', 'edge', function(evt) {{
                    const edge = evt.target;
                    window.nicegui.emit('{self._container_id}', 'edge_click', {{
                        id: edge.id(),
                        data: edge.data()
                    }});
                }});
                
                cy.on('tap', function(evt) {{
                    if (evt.target === cy) {{
                        window.nicegui.emit('{self._container_id}', 'canvas_click', {{}});
                    }}
                }});
                
                cy.on('dragend', 'node', function(evt) {{
                    const node = evt.target;
                    window.nicegui.emit('{self._container_id}', 'node_drag', {{
                        id: node.id(),
                        position: node.position()
                    }});
                }});
                
                cy.on('select unselect', function() {{
                    const selected = cy.$(':selected').map(ele => ele.id());
                    window.nicegui.emit('{self._container_id}', 'selection_change', {{
                        selected: selected
                    }});
                }});
            }})();
        ''')
        
        # Setup event listeners
        self.on('node_click', self._handle_node_click)
        self.on('edge_click', self._handle_edge_click)
        self.on('canvas_click', self._handle_canvas_click)
        self.on('node_drag', self._handle_node_drag)
        self.on('selection_change', self._handle_selection_change)
        
    def _get_default_styles(self) -> List[Dict[str, Any]]:
        """Get default Cytoscape styles."""
        return [
            {
                'selector': 'node',
                'style': {
                    'label': 'data(label)',
                    'background-color': '#666',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'width': 60,
                    'height': 60,
                    'font-size': 12,
                    'text-wrap': 'wrap',
                    'text-max-width': 80
                }
            },
            {
                'selector': 'node[role="relay"]',
                'style': {
                    'background-color': '#2196F3',
                    'shape': 'hexagon',
                    'width': 80,
                    'height': 80
                }
            },
            {
                'selector': 'node:selected',
                'style': {
                    'background-color': '#FFC107',
                    'border-width': 3,
                    'border-color': '#FF9800'
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
                    'line-color': '#4CAF50',
                    'target-arrow-color': '#4CAF50',
                    'width': 4
                }
            },
            {
                'selector': 'edge[type="star"]',
                'style': {
                    'line-color': '#2196F3',
                    'target-arrow-color': '#2196F3',
                    'line-style': 'dashed'
                }
            },
            {
                'selector': 'edge:selected',
                'style': {
                    'line-color': '#FFC107',
                    'target-arrow-color': '#FFC107',
                    'width': 5
                }
            }
        ]
    
    def _get_elements_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get elements data from application state."""
        nodes = []
        edges = []
        
        # Check if state is initialized
        if not hasattr(self, '_state') or self._state is None:
            return {'nodes': [], 'edges': []}
        
        # Convert nodes
        for node in self._state.nodes.values():
            nodes.append({
                'data': {
                    'id': node.id,
                    'label': node.name,
                    'role': node.role,
                    'wireguard_ip': node.wireguard_ip
                },
                'position': node.metadata.get('position', {'x': 100, 'y': 100})
            })
        
        # Convert edges
        for edge in self._state.edges.values():
            edges.append({
                'data': {
                    'id': edge.id,
                    'source': edge.source_id,
                    'target': edge.target_id,
                    'type': edge.edge_type
                }
            })
        
        return {'nodes': nodes, 'edges': edges}
    
    def refresh(self) -> None:
        """Refresh the visualization with current state data."""
        container_id = self._container_id
        elements = self._get_elements_data()
        
        # Debug logging
        self._logger.info(f"Refreshing Cytoscape with {len(elements.get('nodes', []))} nodes and {len(elements.get('edges', []))} edges")
        if elements.get('nodes'):
            self._logger.info(f"First node: {elements['nodes'][0]}")
        
        ui.run_javascript(f'''
            console.log('Cytoscape refresh called for container:', '{container_id}');
            console.log('Elements data:', {json.dumps(elements)});
            
            const cy = window.cy_{container_id};
            if (cy) {{
                console.log('Cytoscape instance found, updating elements');
                // Update elements
                cy.json({{ elements: {json.dumps(elements)} }});
                
                console.log('Elements updated, node count:', cy.nodes().length);
                console.log('Elements updated, edge count:', cy.edges().length);
                
                // Reapply layout if needed
                if (cy.nodes().length > 0) {{
                    console.log('Applying layout');
                    cy.layout({{ name: 'cose', animate: true }}).run();
                }}
            }} else {{
                console.error('Cytoscape instance not found for container:', '{container_id}');
            }}
        ''')
    
    def apply_layout(self, layout_name: str, options: Optional[Dict[str, Any]] = None) -> None:
        """Apply a layout algorithm to arrange nodes."""
        container_id = self._container_id
        layout_options = options or {}
        layout_options['name'] = layout_name
        
        ui.run_javascript(f'''
            const cy = window.cy_{container_id};
            if (cy) {{
                cy.layout({json.dumps(layout_options)}).run();
            }}
        ''')
    
    def center_on_elements(self, element_ids: Optional[List[str]] = None) -> None:
        """Center the view on specific elements or all elements."""
        container_id = self._container_id
        
        if element_ids:
            selector = ','.join(f'#{id}' for id in element_ids)
            ui.run_javascript(f'''
                const cy = window.cy_{container_id};
                if (cy) {{
                    cy.fit(cy.$('{selector}'), 50);
                }}
            ''')
        else:
            ui.run_javascript(f'''
                const cy = window.cy_{container_id};
                if (cy) {{
                    cy.fit(50);
                }}
            ''')
    
    def get_selected_elements(self) -> List[str]:
        """Get currently selected element IDs."""
        return self._selected_elements.copy()
    
    def select_elements(self, element_ids: List[str]) -> None:
        """Select specific elements."""
        container_id = self._container_id
        selector = ','.join(f'#{id}' for id in element_ids)
        
        ui.run_javascript(f'''
            const cy = window.cy_{container_id};
            if (cy) {{
                cy.$(':selected').unselect();
                cy.$('{selector}').select();
            }}
        ''')
    
    def clear_selection(self) -> None:
        """Clear all selections."""
        container_id = self._container_id
        
        ui.run_javascript(f'''
            const cy = window.cy_{container_id};
            if (cy) {{
                cy.$(':selected').unselect();
            }}
        ''')
    
    def set_zoom(self, zoom_level: float) -> None:
        """Set the zoom level."""
        container_id = self._container_id
        
        ui.run_javascript(f'''
            const cy = window.cy_{container_id};
            if (cy) {{
                cy.zoom({zoom_level});
            }}
        ''')
    
    def fit_to_viewport(self, padding: int = 50) -> None:
        """Fit all elements to viewport."""
        container_id = self._container_id
        
        ui.run_javascript(f'''
            const cy = window.cy_{container_id};
            if (cy) {{
                cy.fit({padding});
            }}
        ''')
    
    def highlight_path(self, node_ids: List[str]) -> None:
        """Highlight a path through the network."""
        container_id = self._container_id
        
        # Build edge selectors for path
        edge_selectors = []
        for i in range(len(node_ids) - 1):
            edge_selectors.append(f'edge[source="{node_ids[i]}"][target="{node_ids[i+1]}"]')
            edge_selectors.append(f'edge[source="{node_ids[i+1]}"][target="{node_ids[i]}"]')
        
        ui.run_javascript(f'''
            const cy = window.cy_{container_id};
            if (cy) {{
                // Reset all styles
                cy.elements().removeClass('highlighted dimmed');
                
                // Dim all elements
                cy.elements().addClass('dimmed');
                
                // Highlight path nodes
                const nodeSelector = {json.dumps(','.join(f'#{id}' for id in node_ids))};
                cy.$(nodeSelector).removeClass('dimmed').addClass('highlighted');
                
                // Highlight path edges
                const edgeSelector = {json.dumps(','.join(edge_selectors))};
                cy.$(edgeSelector).removeClass('dimmed').addClass('highlighted');
            }}
        ''')
    
    def export_image(self, format: str = 'png') -> str:
        """Export the current view as an image."""
        container_id = self._container_id
        
        # This returns a promise, so we'd need to handle it asynchronously
        # For now, return a placeholder
        self._logger.warning("Image export not fully implemented in this version")
        return ""
    
    def update_styles(self, styles: List[Dict[str, Any]]) -> None:
        """Update the visualization styles."""
        container_id = self._container_id
        self._styles = styles
        
        ui.run_javascript(f'''
            const cy = window.cy_{container_id};
            if (cy) {{
                cy.style({json.dumps(styles)});
            }}
        ''')
    
    def set_layout(self, layout_name: str) -> None:
        """Set the layout algorithm for the graph."""
        container_id = self._container_id
        self._current_layout = layout_name
        
        # Map layout names to Cytoscape.js layouts
        layout_map = {
            'force': 'cose',
            'circular': 'circle', 
            'grid': 'grid',
            'hierarchical': 'dagre',
            'random': 'random',
            'preset': 'preset'
        }
        
        cytoscape_layout = layout_map.get(layout_name, 'cose')
        
        ui.run_javascript(f'''
            const cy = window.cy_{container_id};
            if (cy) {{
                const layout = cy.layout({{
                    name: '{cytoscape_layout}',
                    animate: true,
                    animationDuration: 500
                }});
                layout.run();
            }}
        ''')
    
    def on_node_click(self, callback: Callable[[str, INodeModel], None]) -> None:
        """Register callback for node click events."""
        self._callbacks['node_click'].append(callback)
    
    def on_edge_click(self, callback: Callable[[str, IEdgeModel], None]) -> None:
        """Register callback for edge click events."""
        self._callbacks['edge_click'].append(callback)
    
    def on_canvas_click(self, callback: Callable[[Dict[str, float]], None]) -> None:
        """Register callback for canvas click events."""
        self._callbacks['canvas_click'].append(callback)
    
    def on_selection_change(self, callback: Callable[[List[str]], None]) -> None:
        """Register callback for selection change events."""
        self._callbacks['selection_change'].append(callback)
    
    # Event handlers
    
    def _handle_node_click(self, event: Dict[str, Any]) -> None:
        """Handle node click events."""
        if not hasattr(event, 'msg') or 'id' not in event.msg:
            return
        
        node_id = event.msg['id']
        node = self._state.nodes.get(node_id)
        
        if node:
            for callback in self._callbacks['node_click']:
                callback(node_id, node)
    
    def _handle_edge_click(self, event: Dict[str, Any]) -> None:
        """Handle edge click events."""
        if not hasattr(event, 'msg') or 'id' not in event.msg:
            return
        
        edge_id = event.msg['id']
        edge = self._state.edges.get(edge_id)
        
        if edge:
            for callback in self._callbacks['edge_click']:
                callback(edge_id, edge)
    
    def _handle_canvas_click(self, event: Dict[str, Any]) -> None:
        """Handle canvas click events."""
        # Canvas clicks don't have position in this implementation
        # Could be enhanced to get click coordinates
        position = {'x': 0, 'y': 0}
        
        for callback in self._callbacks['canvas_click']:
            callback(position)
    
    def _handle_node_drag(self, event: Dict[str, Any]) -> None:
        """Handle node drag events."""
        if not hasattr(event, 'msg') or 'id' not in event.msg or 'position' not in event.msg:
            return
        
        node_id = event.msg['id']
        position = event.msg['position']
        
        # Update node position in state
        node = self._state.nodes.get(node_id)
        if node:
            node.metadata['position'] = position
            
            for callback in self._callbacks['node_drag']:
                callback(node_id, position)
    
    def _handle_selection_change(self, event: Dict[str, Any]) -> None:
        """Handle selection change events."""
        if not hasattr(event, 'msg') or 'selected' not in event.msg:
            return
        
        self._selected_elements = event.msg['selected']
        
        for callback in self._callbacks['selection_change']:
            callback(self._selected_elements)
    
    # Missing ICytoscapeWidget interface methods
    
    def add_node(self, node_id: str, label: str, 
                wireguard_ip: Optional[str] = None,
                role: str = 'client',
                group: Optional[str] = None,
                position: Optional[Dict[str, float]] = None) -> None:
        """Add a node to the graph."""
        container_id = self._container_id
        
        # Use provided position or default
        pos = position or {'x': 100, 'y': 100}
        
        node_data = {
            'id': node_id,
            'label': label,
            'role': role,
            'wireguard_ip': wireguard_ip,
            'group': group
        }
        
        ui.run_javascript(f'''
            if (window.cy_{container_id}) {{
                window.cy_{container_id}.add({{
                    data: {json.dumps(node_data)},
                    position: {json.dumps(pos)}
                }});
            }}
        ''')
    
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> None:
        """Update node properties."""
        container_id = self._container_id
        ui.run_javascript(f'''
            if (window.cy_{container_id}) {{
                const node = window.cy_{container_id}.getElementById('{node_id}');
                if (node) {{
                    node.data({json.dumps(updates)});
                }}
            }}
        ''')
    
    def delete_node(self, node_id: str) -> None:
        """Delete a node from the graph."""
        container_id = self._container_id
        ui.run_javascript(f'''
            if (window.cy_{container_id}) {{
                const node = window.cy_{container_id}.getElementById('{node_id}');
                if (node) {{
                    node.remove();
                }}
            }}
        ''')
    
    def add_edge(self, edge_id: str, source: str, target: str,
                edge_type: str = 'peer',
                allowed_ips: Optional[List[str]] = None) -> None:
        """Add an edge to the graph."""
        container_id = self._container_id
        edge_data = {
            'id': edge_id,
            'source': source,
            'target': target,
            'type': edge_type,
            'allowed_ips': allowed_ips or []
        }
        ui.run_javascript(f'''
            if (window.cy_{container_id}) {{
                window.cy_{container_id}.add({{
                    data: {json.dumps(edge_data)}
                }});
            }}
        ''')
    
    def update_edge(self, edge_id: str, updates: Dict[str, Any]) -> None:
        """Update edge properties."""
        container_id = self._container_id
        ui.run_javascript(f'''
            if (window.cy_{container_id}) {{
                const edge = window.cy_{container_id}.getElementById('{edge_id}');
                if (edge) {{
                    edge.data({json.dumps(updates)});
                }}
            }}
        ''')
    
    def delete_edge(self, edge_id: str) -> None:
        """Delete an edge from the graph."""
        container_id = self._container_id
        ui.run_javascript(f'''
            if (window.cy_{container_id}) {{
                const edge = window.cy_{container_id}.getElementById('{edge_id}');
                if (edge) {{
                    edge.remove();
                }}
            }}
        ''')
    
    def fit_view(self, padding: int = 50) -> None:
        """Fit the graph view to show all elements."""
        # This is already implemented as fit_to_viewport
        self.fit_to_viewport(padding)
    
    def get_elements(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all graph elements."""
        # This is already implemented as _get_elements_data
        return self._get_elements_data()
    
    def clear(self) -> None:
        """Clear all elements from the graph."""
        container_id = self._container_id
        ui.run_javascript(f'''
            if (window.cy_{container_id}) {{
                window.cy_{container_id}.elements().remove();
            }}
        ''')
    
    def set_style(self, element_id: str, style: Dict[str, Any]) -> None:
        """Set custom style for an element."""
        container_id = self._container_id
        ui.run_javascript(f'''
            if (window.cy_{container_id}) {{
                const element = window.cy_{container_id}.getElementById('{element_id}');
                if (element) {{
                    element.style({json.dumps(style)});
                }}
            }}
        ''')
    
    def highlight_elements(self, element_ids: List[str]) -> None:
        """Highlight specific elements."""
        container_id = self._container_id
        ui.run_javascript(f'''
            if (window.cy_{container_id}) {{
                const elements = window.cy_{container_id}.elements();
                elements.removeClass('highlighted');
                const ids = {json.dumps(element_ids)};
                ids.forEach(id => {{
                    const element = window.cy_{container_id}.getElementById(id);
                    if (element) {{
                        element.addClass('highlighted');
                    }}
                }});
            }}
        ''')
    
    def unhighlight_all(self) -> None:
        """Remove all highlights."""
        container_id = self._container_id
        ui.run_javascript(f'''
            if (window.cy_{container_id}) {{
                window.cy_{container_id}.elements().removeClass('highlighted');
            }}
        ''')
    
    def on_node_drag_end(self, handler: Callable[[str, Dict[str, float]], None]) -> None:
        """Register node drag end handler."""
        self._callbacks['node_drag'].append(handler)
    
    def on_background_click(self, handler: Callable[[], None]) -> None:
        """Register background click handler."""
        # Store the handler and register with canvas click
        self._on_background_click = handler
        self.on_canvas_click(lambda pos: handler())
    
    def on_node_drag(self, handler: Callable[[str, Dict[str, float]], None]) -> None:
        """Register node drag handler."""
        self._callbacks['node_drag'].append(handler)