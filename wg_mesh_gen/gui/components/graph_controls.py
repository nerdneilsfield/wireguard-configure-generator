"""
Graph control components for advanced visualization features.

This module provides zoom, pan, and layout controls for the network graph.
"""

from typing import Optional, Callable, Dict, Any, List
from nicegui import ui

from ..interfaces.components import IComponent
from ..interfaces.state import IAppState
from ...logger import get_logger


class GraphControls(IComponent):
    """
    Graph control panel with zoom, pan, and layout options.
    
    Features:
    - Zoom in/out/fit controls
    - Layout algorithm selection
    - View presets (overview, selected, path)
    - Export options
    """
    
    def __init__(self, state: IAppState, cytoscape_id: str):
        """
        Initialize graph controls.
        
        Args:
            state: Application state
            cytoscape_id: ID of the Cytoscape widget to control
        """
        self._logger = get_logger()
        self._state = state
        self._cytoscape_id = cytoscape_id
        self._container: Optional[ui.element] = None
        
        # Layout presets
        self._layout_presets = {
            'Force-Directed': {
                'name': 'cose',
                'animate': True,
                'animationDuration': 1000,
                'nodeRepulsion': 400000,
                'idealEdgeLength': 100
            },
            'Hierarchical': {
                'name': 'breadthfirst',
                'directed': True,
                'spacingFactor': 1.5,
                'animate': True
            },
            'Circle': {
                'name': 'circle',
                'animate': True,
                'animationDuration': 800
            },
            'Grid': {
                'name': 'grid',
                'animate': True,
                'animationDuration': 800,
                'avoidOverlap': True
            },
            'Concentric': {
                'name': 'concentric',
                'animate': True,
                'levelWidth': function(nodes) { return 2; }
            }
        }
    
    def render(self) -> ui.element:
        """Render the graph controls."""
        with ui.card().classes('p-2') as self._container:
            with ui.row().classes('gap-2 items-center'):
                # Zoom controls
                ui.label('Zoom:').classes('text-sm')
                
                ui.button(
                    icon='zoom_in',
                    on_click=self._zoom_in
                ).props('flat dense round').tooltip('Zoom In')
                
                ui.button(
                    icon='zoom_out', 
                    on_click=self._zoom_out
                ).props('flat dense round').tooltip('Zoom Out')
                
                ui.button(
                    icon='fit_screen',
                    on_click=self._fit_to_screen
                ).props('flat dense round').tooltip('Fit to Screen')
                
                ui.button(
                    icon='center_focus_strong',
                    on_click=self._center_selected
                ).props('flat dense round').tooltip('Center on Selected')
                
                ui.separator().props('vertical')
                
                # Layout selector
                ui.label('Layout:').classes('text-sm')
                self._layout_select = ui.select(
                    list(self._layout_presets.keys()),
                    value='Force-Directed',
                    on_change=self._apply_layout
                ).classes('w-32')
                
                ui.separator().props('vertical')
                
                # View presets
                ui.label('View:').classes('text-sm')
                
                ui.button(
                    icon='panorama',
                    on_click=self._show_overview
                ).props('flat dense round').tooltip('Overview')
                
                ui.button(
                    icon='filter_center_focus',
                    on_click=self._focus_selection
                ).props('flat dense round').tooltip('Focus Selection')
                
                ui.button(
                    icon='route',
                    on_click=self._show_paths
                ).props('flat dense round').tooltip('Show Paths')
                
                ui.separator().props('vertical')
                
                # Additional options
                with ui.menu() as menu:
                    ui.menu_item('Reset View', on_click=self._reset_view)
                    ui.menu_item('Toggle Labels', on_click=self._toggle_labels)
                    ui.menu_item('Toggle Animations', on_click=self._toggle_animations)
                    ui.separator()
                    ui.menu_item('Export as PNG', on_click=self._export_png)
                    ui.menu_item('Export as SVG', on_click=self._export_svg)
                
                ui.button(
                    icon='more_vert'
                ).props('flat dense round').on('click', menu.open)
        
        return self._container
    
    def _zoom_in(self) -> None:
        """Zoom in by 25%."""
        ui.run_javascript(f'''
            const cy = window.cy_{self._cytoscape_id};
            if (cy) {{
                const currentZoom = cy.zoom();
                cy.zoom({{
                    level: currentZoom * 1.25,
                    renderedPosition: {{ x: cy.width() / 2, y: cy.height() / 2 }}
                }});
            }}
        ''')
    
    def _zoom_out(self) -> None:
        """Zoom out by 25%."""
        ui.run_javascript(f'''
            const cy = window.cy_{self._cytoscape_id};
            if (cy) {{
                const currentZoom = cy.zoom();
                cy.zoom({{
                    level: currentZoom * 0.75,
                    renderedPosition: {{ x: cy.width() / 2, y: cy.height() / 2 }}
                }});
            }}
        ''')
    
    def _fit_to_screen(self) -> None:
        """Fit all elements to screen."""
        ui.run_javascript(f'''
            const cy = window.cy_{self._cytoscape_id};
            if (cy) {{
                cy.fit(50);
            }}
        ''')
    
    def _center_selected(self) -> None:
        """Center view on selected elements."""
        ui.run_javascript(f'''
            const cy = window.cy_{self._cytoscape_id};
            if (cy) {{
                const selected = cy.$(':selected');
                if (selected.length > 0) {{
                    cy.fit(selected, 100);
                }} else {{
                    window.nicegui.notify('No elements selected');
                }}
            }}
        ''')
    
    def _apply_layout(self, event: Any = None) -> None:
        """Apply selected layout algorithm."""
        layout_name = self._layout_select.value
        layout_options = self._layout_presets.get(layout_name, {})
        
        # Convert function to string for JavaScript
        layout_json = {}
        for key, value in layout_options.items():
            if callable(value):
                # Skip functions for now
                continue
            layout_json[key] = value
        
        ui.run_javascript(f'''
            const cy = window.cy_{self._cytoscape_id};
            if (cy) {{
                const layout = cy.layout({layout_json});
                layout.run();
            }}
        ''')
        
        self._logger.info(f"Applied {layout_name} layout")
    
    def _show_overview(self) -> None:
        """Show complete network overview."""
        ui.run_javascript(f'''
            const cy = window.cy_{self._cytoscape_id};
            if (cy) {{
                // Reset any filters or highlights
                cy.elements().removeClass('highlighted dimmed');
                cy.fit(50);
            }}
        ''')
    
    def _focus_selection(self) -> None:
        """Focus on selected elements and their neighbors."""
        ui.run_javascript(f'''
            const cy = window.cy_{self._cytoscape_id};
            if (cy) {{
                const selected = cy.$(':selected');
                if (selected.length === 0) {{
                    window.nicegui.notify('No elements selected');
                    return;
                }}
                
                // Get neighborhood
                const neighborhood = selected.closedNeighborhood();
                
                // Dim other elements
                cy.elements().addClass('dimmed');
                neighborhood.removeClass('dimmed').addClass('highlighted');
                
                // Fit to neighborhood
                cy.fit(neighborhood, 100);
            }}
        ''')
    
    def _show_paths(self) -> None:
        """Show shortest paths between selected nodes."""
        ui.run_javascript(f'''
            const cy = window.cy_{self._cytoscape_id};
            if (cy) {{
                const selectedNodes = cy.$('node:selected');
                if (selectedNodes.length !== 2) {{
                    window.nicegui.notify('Select exactly 2 nodes to show path');
                    return;
                }}
                
                // Calculate shortest path
                const dijkstra = cy.elements().dijkstra(selectedNodes[0]);
                const path = dijkstra.pathTo(selectedNodes[1]);
                
                if (path.length > 0) {{
                    // Highlight path
                    cy.elements().addClass('dimmed');
                    path.removeClass('dimmed').addClass('highlighted');
                    cy.fit(path, 100);
                }} else {{
                    window.nicegui.notify('No path found between selected nodes');
                }}
            }}
        ''')
    
    def _reset_view(self) -> None:
        """Reset view to default."""
        ui.run_javascript(f'''
            const cy = window.cy_{self._cytoscape_id};
            if (cy) {{
                // Clear all classes
                cy.elements().removeClass('highlighted dimmed hidden');
                // Reset zoom and pan
                cy.zoom(1);
                cy.center();
            }}
        ''')
    
    def _toggle_labels(self) -> None:
        """Toggle node labels visibility."""
        ui.run_javascript(f'''
            const cy = window.cy_{self._cytoscape_id};
            if (cy) {{
                const labelsHidden = cy.scratch('labelsHidden') || false;
                
                if (labelsHidden) {{
                    // Show labels
                    cy.style()
                        .selector('node')
                        .style('label', 'data(label)')
                        .update();
                }} else {{
                    // Hide labels
                    cy.style()
                        .selector('node')
                        .style('label', '')
                        .update();
                }}
                
                cy.scratch('labelsHidden', !labelsHidden);
            }}
        ''')
    
    def _toggle_animations(self) -> None:
        """Toggle layout animations."""
        ui.run_javascript(f'''
            const cy = window.cy_{self._cytoscape_id};
            if (cy) {{
                const animationsEnabled = cy.scratch('animationsEnabled') !== false;
                cy.scratch('animationsEnabled', !animationsEnabled);
                
                window.nicegui.notify(
                    animationsEnabled ? 'Animations disabled' : 'Animations enabled'
                );
            }}
        ''')
    
    def _export_png(self) -> None:
        """Export graph as PNG."""
        ui.run_javascript(f'''
            const cy = window.cy_{self._cytoscape_id};
            if (cy) {{
                const png = cy.png({{
                    output: 'blob',
                    bg: 'white',
                    scale: 2
                }});
                
                // Create download link
                const link = document.createElement('a');
                link.href = URL.createObjectURL(png);
                link.download = 'wireguard-network.png';
                link.click();
            }}
        ''')
    
    def _export_svg(self) -> None:
        """Export graph as SVG."""
        ui.run_javascript(f'''
            const cy = window.cy_{self._cytoscape_id};
            if (cy) {{
                // Note: This requires cytoscape-svg extension
                window.nicegui.notify('SVG export requires additional extension');
            }}
        ''')


class PerformanceMonitor(IComponent):
    """
    Performance monitoring component for large networks.
    
    Shows FPS, node count, edge count, and rendering performance.
    """
    
    def __init__(self, state: IAppState, cytoscape_id: str):
        """Initialize performance monitor."""
        self._logger = get_logger()
        self._state = state
        self._cytoscape_id = cytoscape_id
        self._container: Optional[ui.element] = None
        self._stats: Dict[str, Any] = {
            'fps': 0,
            'nodes': 0,
            'edges': 0,
            'render_time': 0
        }
    
    def render(self) -> ui.element:
        """Render performance monitor."""
        with ui.card().classes('p-2 text-xs') as self._container:
            self._container.style('''
                position: fixed;
                top: 10px;
                right: 10px;
                min-width: 150px;
                opacity: 0.8;
                z-index: 1000;
            ''')
            
            with ui.column().classes('gap-1'):
                self._fps_label = ui.label('FPS: --')
                self._nodes_label = ui.label(f'Nodes: {len(self._state.nodes)}')
                self._edges_label = ui.label(f'Edges: {len(self._state.edges)}')
                self._render_label = ui.label('Render: -- ms')
            
            # Start monitoring
            self._start_monitoring()
        
        return self._container
    
    def _start_monitoring(self) -> None:
        """Start performance monitoring."""
        ui.run_javascript(f'''
            (function() {{
                const cy = window.cy_{self._cytoscape_id};
                if (!cy) return;
                
                let lastTime = performance.now();
                let frameCount = 0;
                
                function updateStats() {{
                    const currentTime = performance.now();
                    const deltaTime = currentTime - lastTime;
                    
                    frameCount++;
                    
                    // Update FPS every second
                    if (deltaTime >= 1000) {{
                        const fps = Math.round(frameCount * 1000 / deltaTime);
                        
                        // Send stats to Python
                        window.nicegui.emit('{self._container.id}', 'update_stats', {{
                            fps: fps,
                            nodes: cy.nodes().length,
                            edges: cy.edges().length,
                            render_time: Math.round(cy.scratch('lastRenderTime') || 0)
                        }});
                        
                        frameCount = 0;
                        lastTime = currentTime;
                    }}
                    
                    requestAnimationFrame(updateStats);
                }}
                
                // Track render time
                cy.on('render', function() {{
                    const start = performance.now();
                    requestAnimationFrame(() => {{
                        cy.scratch('lastRenderTime', performance.now() - start);
                    }});
                }});
                
                updateStats();
            }})();
        ''')
        
        # Handle stats updates
        self._container.on('update_stats', self._update_display)
    
    def _update_display(self, event: Any) -> None:
        """Update performance display."""
        stats = event.msg
        self._fps_label.text = f"FPS: {stats['fps']}"
        self._nodes_label.text = f"Nodes: {stats['nodes']}"
        self._edges_label.text = f"Edges: {stats['edges']}"
        self._render_label.text = f"Render: {stats['render_time']} ms"