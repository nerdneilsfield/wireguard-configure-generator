"""
Minimap component for network visualization overview.

This component provides a miniature view of the entire network graph.
"""

from typing import Optional, Dict, Any, Callable
import json
from nicegui import ui

from ..interfaces.components import IComponent
from ..interfaces.state import IAppState
from ...logger import get_logger


class Minimap(IComponent):
    """
    Minimap component providing an overview of the network.
    
    This component:
    - Shows a miniature view of the entire network
    - Highlights the current viewport
    - Allows clicking to navigate
    - Updates in sync with the main graph
    """
    
    def __init__(self, state: IAppState, cytoscape_id: str, size: int = 200):
        """
        Initialize the minimap.
        
        Args:
            state: Application state
            cytoscape_id: ID of the main Cytoscape widget
            size: Size of the minimap (square)
        """
        self._logger = get_logger()
        self._state = state
        self._cytoscape_id = cytoscape_id
        self._size = size
        self._container: Optional[ui.element] = None
    
    def render(self) -> ui.element:
        """Render the minimap component."""
        with ui.card().classes(f'w-{self._size}px h-{self._size}px p-2') as self._container:
            self._container.style(f'''
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 1000;
                background: rgba(255, 255, 255, 0.95);
                border: 1px solid #ddd;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ''')
            
            # Minimap canvas
            canvas_id = f'minimap-{self._cytoscape_id}'
            with ui.element('div').classes('w-full h-full') as canvas:
                canvas._props['id'] = canvas_id
            
            # Initialize minimap
            self._initialize_minimap(canvas_id)
        
        return self._container
    
    def _initialize_minimap(self, canvas_id: str) -> None:
        """Initialize the minimap visualization."""
        # This is a simplified minimap implementation
        # In a full implementation, you might use a library like cytoscape-navigator
        
        ui.run_javascript(f'''
            (function() {{
                // Wait for main Cytoscape instance
                const waitForCy = setInterval(() => {{
                    const mainCy = window.cy_{self._cytoscape_id};
                    if (!mainCy) return;
                    
                    clearInterval(waitForCy);
                    
                    // Create minimap container
                    const container = document.getElementById('{canvas_id}');
                    if (!container) return;
                    
                    // Create canvas element
                    const canvas = document.createElement('canvas');
                    canvas.width = {self._size - 16};  // Account for padding
                    canvas.height = {self._size - 16};
                    canvas.style.width = '100%';
                    canvas.style.height = '100%';
                    canvas.style.cursor = 'pointer';
                    container.appendChild(canvas);
                    
                    const ctx = canvas.getContext('2d');
                    
                    // Function to draw minimap
                    function drawMinimap() {{
                        // Clear canvas
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        
                        // Get graph bounds
                        const elements = mainCy.elements();
                        if (elements.length === 0) return;
                        
                        const bb = elements.boundingBox();
                        const padding = 20;
                        
                        // Calculate scale
                        const graphWidth = bb.w + padding * 2;
                        const graphHeight = bb.h + padding * 2;
                        const scale = Math.min(
                            canvas.width / graphWidth,
                            canvas.height / graphHeight
                        ) * 0.9;
                        
                        // Center offset
                        const offsetX = (canvas.width - graphWidth * scale) / 2;
                        const offsetY = (canvas.height - graphHeight * scale) / 2;
                        
                        // Draw edges
                        ctx.strokeStyle = '#ccc';
                        ctx.lineWidth = 1;
                        mainCy.edges().forEach(edge => {{
                            const source = edge.source().position();
                            const target = edge.target().position();
                            
                            ctx.beginPath();
                            ctx.moveTo(
                                (source.x - bb.x1 + padding) * scale + offsetX,
                                (source.y - bb.y1 + padding) * scale + offsetY
                            );
                            ctx.lineTo(
                                (target.x - bb.x1 + padding) * scale + offsetX,
                                (target.y - bb.y1 + padding) * scale + offsetY
                            );
                            ctx.stroke();
                        }});
                        
                        // Draw nodes
                        mainCy.nodes().forEach(node => {{
                            const pos = node.position();
                            const x = (pos.x - bb.x1 + padding) * scale + offsetX;
                            const y = (pos.y - bb.y1 + padding) * scale + offsetY;
                            
                            ctx.fillStyle = node.data('role') === 'relay' ? '#2196F3' : '#666';
                            ctx.beginPath();
                            ctx.arc(x, y, 3, 0, 2 * Math.PI);
                            ctx.fill();
                        }});
                        
                        // Draw viewport rectangle
                        const extent = mainCy.extent();
                        ctx.strokeStyle = '#FFC107';
                        ctx.lineWidth = 2;
                        ctx.strokeRect(
                            (extent.x1 - bb.x1 + padding) * scale + offsetX,
                            (extent.y1 - bb.y1 + padding) * scale + offsetY,
                            (extent.x2 - extent.x1) * scale,
                            (extent.y2 - extent.y1) * scale
                        );
                        
                        // Store transformation for click handling
                        canvas._transform = {{
                            scale: scale,
                            offsetX: offsetX,
                            offsetY: offsetY,
                            bbX1: bb.x1 - padding,
                            bbY1: bb.y1 - padding
                        }};
                    }}
                    
                    // Handle click to navigate
                    canvas.addEventListener('click', (e) => {{
                        const rect = canvas.getBoundingClientRect();
                        const x = e.clientX - rect.left;
                        const y = e.clientY - rect.top;
                        
                        if (canvas._transform) {{
                            const t = canvas._transform;
                            const graphX = (x - t.offsetX) / t.scale + t.bbX1;
                            const graphY = (y - t.offsetY) / t.scale + t.bbY1;
                            
                            mainCy.center({{
                                eles: mainCy.collection(),
                                x: graphX,
                                y: graphY
                            }});
                        }}
                    }});
                    
                    // Update minimap on graph changes
                    mainCy.on('add remove position viewport', drawMinimap);
                    
                    // Initial draw
                    drawMinimap();
                    
                    // Store minimap reference
                    window.minimap_{self._cytoscape_id} = {{
                        canvas: canvas,
                        draw: drawMinimap
                    }};
                }}, 100);
            }})();
        ''')
    
    def update(self) -> None:
        """Update the minimap display."""
        ui.run_javascript(f'''
            const minimap = window.minimap_{self._cytoscape_id};
            if (minimap && minimap.draw) {{
                minimap.draw();
            }}
        ''')
    
    def show(self) -> None:
        """Show the minimap."""
        if self._container:
            self._container.style('display: block')
    
    def hide(self) -> None:
        """Hide the minimap."""
        if self._container:
            self._container.style('display: none')
    
    def set_size(self, size: int) -> None:
        """Change the minimap size."""
        self._size = size
        if self._container:
            self._container.classes(f'w-{size}px h-{size}px', remove='w-* h-*')
            self.update()