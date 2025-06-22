"""
Search panel component for finding nodes and edges in the network.

This component provides search and filter functionality.
"""

from typing import List, Dict, Optional, Callable, Any
from nicegui import ui

from ..interfaces.components import IComponent
from ..interfaces.state import IAppState
from ..interfaces.models import INodeModel, IEdgeModel
from ...logger import get_logger


class SearchPanel(IComponent):
    """
    Search panel for finding elements in the network.
    
    Features:
    - Search by name, IP, or other properties
    - Filter by node role or edge type
    - Quick navigation to results
    - Highlighting of search results
    """
    
    def __init__(self, state: IAppState):
        """
        Initialize the search panel.
        
        Args:
            state: Application state
        """
        self._logger = get_logger()
        self._state = state
        self._search_results: List[Dict[str, Any]] = []
        self._on_result_click: Optional[Callable[[str, str], None]] = None
        
        # UI elements
        self._container: Optional[ui.element] = None
        self._results_container: Optional[ui.element] = None
        self._search_input: Optional[ui.input] = None
    
    def render(self) -> ui.element:
        """Render the search panel."""
        with ui.card().classes('w-full max-w-md') as self._container:
            with ui.column().classes('w-full gap-4'):
                # Search header
                ui.label('Search Network').classes('text-h6')
                
                # Search input with filters
                with ui.row().classes('w-full gap-2'):
                    self._search_input = ui.input(
                        placeholder='Search nodes, edges, IPs...',
                        on_change=self._perform_search
                    ).classes('flex-grow').props('clearable')
                    
                    # Search button
                    ui.button(
                        icon='search',
                        on_click=self._perform_search
                    ).props('flat')
                
                # Filter options
                with ui.expansion('Filters', icon='filter_list').classes('w-full'):
                    with ui.column().classes('w-full gap-2'):
                        # Element type filter
                        self._type_filter = ui.select(
                            ['All', 'Nodes', 'Edges'],
                            value='All',
                            label='Element Type',
                            on_change=self._perform_search
                        ).classes('w-full')
                        
                        # Node role filter
                        self._role_filter = ui.select(
                            ['All', 'client', 'relay'],
                            value='All',
                            label='Node Role',
                            on_change=self._perform_search
                        ).classes('w-full')
                        
                        # Edge type filter
                        self._edge_type_filter = ui.select(
                            ['All', 'peer', 'mesh', 'star', 'relay'],
                            value='All',
                            label='Edge Type',
                            on_change=self._perform_search
                        ).classes('w-full')
                
                # Results area
                ui.separator()
                self._results_label = ui.label('Results').classes('text-subtitle1')
                
                # Results container with scroll
                self._results_container = ui.column().classes('w-full gap-2 max-h-96 overflow-y-auto')
                
                # Initial state
                self._show_empty_state()
        
        return self._container
    
    def _show_empty_state(self) -> None:
        """Show empty state in results."""
        self._results_container.clear()
        with self._results_container:
            ui.label('Enter search terms to find elements').classes('text-gray-500')
    
    def _perform_search(self) -> None:
        """Perform search based on current criteria."""
        query = self._search_input.value.lower() if self._search_input.value else ''
        
        if not query:
            self._show_empty_state()
            return
        
        self._search_results.clear()
        
        # Search based on type filter
        search_type = self._type_filter.value
        
        if search_type in ['All', 'Nodes']:
            self._search_nodes(query)
        
        if search_type in ['All', 'Edges']:
            self._search_edges(query)
        
        # Update results display
        self._display_results()
    
    def _search_nodes(self, query: str) -> None:
        """Search nodes based on query."""
        role_filter = self._role_filter.value
        
        for node in self._state.nodes.values():
            # Apply role filter
            if role_filter != 'All' and node.role != role_filter:
                continue
            
            # Check various properties
            matches = False
            match_reason = ''
            
            # Search by name
            if query in node.name.lower():
                matches = True
                match_reason = f'Name: {node.name}'
            
            # Search by IP
            elif node.wireguard_ip and query in node.wireguard_ip.lower():
                matches = True
                match_reason = f'IP: {node.wireguard_ip}'
            
            # Search by endpoint
            elif any(query in endpoint.lower() for endpoint in node.endpoints.values()):
                matches = True
                endpoint_match = next(e for e in node.endpoints.values() if query in e.lower())
                match_reason = f'Endpoint: {endpoint_match}'
            
            # Search in group memberships
            elif any(query in group.name.lower() for group in self._state.groups.values() if node.name in group.nodes):
                matches = True
                group_match = next(g for g in self._state.groups.values() if node.name in g.nodes and query in g.name.lower())
                match_reason = f'Group: {group_match.name}'
            
            if matches:
                self._search_results.append({
                    'type': 'node',
                    'id': node.id,
                    'name': node.name,
                    'role': node.role,
                    'match_reason': match_reason,
                    'element': node
                })
    
    def _search_edges(self, query: str) -> None:
        """Search edges based on query."""
        edge_type_filter = self._edge_type_filter.value
        
        for edge in self._state.edges.values():
            # Apply edge type filter
            if edge_type_filter != 'All' and edge.edge_type != edge_type_filter:
                continue
            
            # Get connected nodes
            source = self._state.nodes.get(edge.source_id)
            target = self._state.nodes.get(edge.target_id)
            
            if not source or not target:
                continue
            
            matches = False
            match_reason = ''
            
            # Search by node names
            edge_name = f'{source.name} → {target.name}'
            if query in edge_name.lower():
                matches = True
                match_reason = edge_name
            
            # Search by allowed IPs
            elif edge.allowed_ips and any(query in ip.lower() for ip in edge.allowed_ips):
                matches = True
                ip_match = next(ip for ip in edge.allowed_ips if query in ip.lower())
                match_reason = f'Allowed IP: {ip_match}'
            
            # Search by edge type
            elif query in edge.edge_type.lower():
                matches = True
                match_reason = f'Type: {edge.edge_type}'
            
            if matches:
                self._search_results.append({
                    'type': 'edge',
                    'id': edge.id,
                    'name': edge_name,
                    'edge_type': edge.edge_type,
                    'match_reason': match_reason,
                    'element': edge
                })
    
    def _display_results(self) -> None:
        """Display search results."""
        self._results_container.clear()
        
        # Update results count
        self._results_label.text = f'Results ({len(self._search_results)})'
        
        if not self._search_results:
            with self._results_container:
                ui.label('No results found').classes('text-gray-500')
            return
        
        # Display each result
        with self._results_container:
            for result in self._search_results:
                with ui.card().classes('w-full cursor-pointer hover:bg-gray-50') as card:
                    card.on('click', lambda r=result: self._handle_result_click(r))
                    
                    with ui.column().classes('w-full gap-1'):
                        # Result header with icon
                        with ui.row().classes('w-full items-center gap-2'):
                            # Icon based on type
                            if result['type'] == 'node':
                                icon = 'device_hub' if result['role'] == 'relay' else 'computer'
                                color = 'text-blue-500' if result['role'] == 'relay' else 'text-gray-600'
                            else:
                                icon = 'swap_horiz'
                                color = 'text-green-500'
                            
                            ui.icon(icon).classes(f'{color} text-lg')
                            ui.label(result['name']).classes('font-medium flex-grow')
                        
                        # Match reason
                        ui.label(result['match_reason']).classes('text-sm text-gray-600')
                        
                        # Additional info
                        if result['type'] == 'node':
                            element = result['element']
                            if element.wireguard_ip:
                                ui.label(f'IP: {element.wireguard_ip}').classes('text-xs text-gray-500')
                        else:
                            ui.label(f'Type: {result["edge_type"]}').classes('text-xs text-gray-500')
    
    def _handle_result_click(self, result: Dict[str, Any]) -> None:
        """Handle clicking on a search result."""
        if self._on_result_click:
            self._on_result_click(result['type'], result['id'])
        
        # Log the action
        self._logger.info(f"Search result clicked: {result['type']} {result['id']}")
    
    def on_result_click(self, callback: Callable[[str, str], None]) -> None:
        """
        Register callback for result click events.
        
        Args:
            callback: Function called with (element_type, element_id)
        """
        self._on_result_click = callback
    
    def clear_search(self) -> None:
        """Clear search input and results."""
        if self._search_input:
            self._search_input.value = ''
        self._search_results.clear()
        self._show_empty_state()
    
    def focus(self) -> None:
        """Focus the search input."""
        if self._search_input:
            ui.run_javascript(f'document.querySelector("#{self._search_input.id} input").focus()')