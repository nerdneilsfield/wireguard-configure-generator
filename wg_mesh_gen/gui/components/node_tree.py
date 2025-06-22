"""
Node tree implementation for hierarchical view of nodes and groups.

This component provides a tree view of the network structure.
"""

from typing import Dict, List, Optional, Callable, Any

from nicegui import ui

from .base import BaseComponent
from ..interfaces.components import INodeTree
from ..interfaces.state import IAppState


class NodeTree(BaseComponent, INodeTree):
    """Implementation of INodeTree for hierarchical node view."""
    
    def __init__(self, 
                 app_state: IAppState,
                 width: str = "250px",
                 component_id: Optional[str] = None):
        """
        Initialize node tree.
        
        Args:
            app_state: Application state
            width: Tree width
            component_id: Optional component ID
        """
        super().__init__(component_id)
        self._app_state = app_state
        self._width = width
        self._selected_node_id: Optional[str] = None
        self._expanded_groups: set = set()
        
        # Event handlers
        self._on_select: Optional[Callable[[str], None]] = None
        self._on_double_click: Optional[Callable[[str], None]] = None
        
        # Tree items
        self._tree_items: Dict[str, Any] = {}
        
        # Subscribe to app state events
        self._subscribe_to_events()
    
    def render(self) -> ui.element:
        """Render the node tree."""
        with ui.card().classes(f'w-[{self._width}]') as container:
            with ui.column().classes('w-full') as self._element:
                # Title
                ui.label('Network Structure').classes('text-h6 mb-2')
                
                # Search input
                self._search_input = ui.input(
                    placeholder='Search nodes...',
                    on_change=self._filter_tree
                ).classes('w-full mb-2').props('outlined dense')
                
                # Tree container
                self._tree_container = ui.column().classes('w-full')
                
                # Build initial tree
                self._build_tree()
        
        return container
    
    def _build_tree(self) -> None:
        """Build the tree structure."""
        self._tree_container.clear()
        self._tree_items.clear()
        
        with self._tree_container:
            # Add ungrouped nodes first
            ungrouped_nodes = []
            grouped_node_ids = set()
            
            # Collect grouped node IDs
            for group in self._app_state.groups.values():
                grouped_node_ids.update(group.nodes)
            
            # Find ungrouped nodes
            for node_id, node in self._app_state.nodes.items():
                if node_id not in grouped_node_ids:
                    ungrouped_nodes.append(node)
            
            # Add ungrouped nodes
            if ungrouped_nodes:
                with ui.expansion(
                    'Ungrouped Nodes',
                    icon='folder_open',
                    value=True
                ).classes('w-full') as exp:
                    for node in sorted(ungrouped_nodes, key=lambda n: n.name):
                        self._add_node_item(node)
            
            # Add groups
            for group in sorted(self._app_state.groups.values(), key=lambda g: g.name):
                self._add_group_item(group)
    
    def _add_group_item(self, group: Any) -> None:
        """Add a group item to the tree."""
        is_expanded = group.id in self._expanded_groups
        
        with ui.expansion(
            group.name,
            icon='group_work',
            value=is_expanded,
            on_value_change=lambda e: self._toggle_group(group.id, e.value)
        ).classes('w-full') as exp:
            # Set group color
            exp.style(f'border-left: 4px solid {group.color}')
            
            # Group info
            with ui.row().classes('w-full items-center text-caption px-2'):
                ui.label(f'Topology: {group.topology}')
                ui.label(f'({len(group.nodes)} nodes)')
            
            # Add nodes in group
            for node_id in group.nodes:
                node = self._app_state.nodes.get(node_id)
                if node:
                    self._add_node_item(node, is_grouped=True)
        
        self._tree_items[group.id] = exp
    
    def _add_node_item(self, node: Any, is_grouped: bool = False) -> None:
        """Add a node item to the tree."""
        icon = 'router' if node.role == 'relay' else 'computer'
        indent = 'ml-4' if is_grouped else ''
        
        with ui.row().classes(f'w-full items-center p-2 hover:bg-gray-100 cursor-pointer {indent}') as item:
            # Selection indicator
            selected = self._selected_node_id == node.id
            if selected:
                item.classes('bg-blue-50')
            
            # Node icon
            ui.icon(icon).classes('text-lg')
            
            # Node info
            with ui.column().classes('flex-grow'):
                ui.label(node.name).classes('font-medium')
                if node.wireguard_ip:
                    ui.label(node.wireguard_ip).classes('text-caption text-gray-600')
            
            # Status indicator
            if node.endpoint:
                ui.icon('cloud').classes('text-green-500 text-sm').tooltip('Has endpoint')
            
            # Click handler
            item.on('click', lambda: self._select_node(node.id))
            
            # Double-click handler
            item.on('dblclick', lambda: self._double_click_node(node.id))
        
        self._tree_items[node.id] = item
    
    def add_node(self, node_id: str, parent_id: Optional[str] = None) -> None:
        """Add a node to the tree."""
        # Rebuild tree to reflect changes
        self._build_tree()
    
    def remove_node(self, node_id: str) -> None:
        """Remove a node from the tree."""
        # Rebuild tree to reflect changes
        self._build_tree()
        
        # Clear selection if removed node was selected
        if self._selected_node_id == node_id:
            self._selected_node_id = None
    
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> None:
        """Update node display."""
        # Rebuild tree to reflect changes
        self._build_tree()
    
    def select_node(self, node_id: str) -> None:
        """Select a node in the tree."""
        self._select_node(node_id)
    
    def get_selected_node(self) -> Optional[str]:
        """Get currently selected node ID."""
        return self._selected_node_id
    
    def expand_all(self) -> None:
        """Expand all groups."""
        for group_id in self._app_state.groups.keys():
            self._expanded_groups.add(group_id)
        self._build_tree()
    
    def collapse_all(self) -> None:
        """Collapse all groups."""
        self._expanded_groups.clear()
        self._build_tree()
    
    def filter_nodes(self, search_term: str) -> None:
        """Filter nodes by search term."""
        self._search_input.value = search_term
        self._filter_tree()
    
    def on_node_select(self, handler: Callable[[str], None]) -> None:
        """Register node selection handler."""
        self._on_select = handler
    
    def on_node_double_click(self, handler: Callable[[str], None]) -> None:
        """Register node double-click handler."""
        self._on_double_click = handler
    
    def _select_node(self, node_id: str) -> None:
        """Handle node selection."""
        self._selected_node_id = node_id
        
        # Update visual selection
        for item_id, item in self._tree_items.items():
            if hasattr(item, 'classes'):
                if item_id == node_id:
                    # Add selection styling
                    if 'bg-blue-50' not in item.classes:
                        item.classes(add='bg-blue-50')
                else:
                    # Remove selection styling
                    item.classes(remove='bg-blue-50')
        
        # Update app state selection
        self._app_state.set_selection({node_id})
        
        # Call handler
        if self._on_select:
            self._on_select(node_id)
    
    def _double_click_node(self, node_id: str) -> None:
        """Handle node double-click."""
        if self._on_double_click:
            self._on_double_click(node_id)
    
    def _toggle_group(self, group_id: str, expanded: bool) -> None:
        """Toggle group expansion state."""
        if expanded:
            self._expanded_groups.add(group_id)
        else:
            self._expanded_groups.discard(group_id)
    
    def _filter_tree(self) -> None:
        """Filter tree based on search input."""
        search_term = self._search_input.value.lower()
        
        if not search_term:
            # Show all items
            for item in self._tree_items.values():
                if hasattr(item, 'visible'):
                    item.visible = True
        else:
            # Filter items
            for item_id, item in self._tree_items.items():
                if hasattr(item, 'visible'):
                    # Check if node/group matches search
                    if item_id in self._app_state.nodes:
                        node = self._app_state.nodes[item_id]
                        match = (search_term in node.name.lower() or 
                                (node.wireguard_ip and search_term in node.wireguard_ip.lower()))
                        item.visible = match
                    elif item_id in self._app_state.groups:
                        group = self._app_state.groups[item_id]
                        match = search_term in group.name.lower()
                        item.visible = match
                        
                        # If group matches, expand it
                        if match and item_id not in self._expanded_groups:
                            self._expanded_groups.add(item_id)
                            self._build_tree()
                            return
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to app state events."""
        self._app_state.subscribe('node_added', lambda e: self._build_tree())
        self._app_state.subscribe('node_updated', lambda e: self._build_tree())
        self._app_state.subscribe('node_removed', lambda e: self._build_tree())
        self._app_state.subscribe('group_added', lambda e: self._build_tree())
        self._app_state.subscribe('group_updated', lambda e: self._build_tree())
        self._app_state.subscribe('group_removed', lambda e: self._build_tree())
        self._app_state.subscribe('selection_changed', self._on_selection_changed)
    
    def _on_selection_changed(self, event: Any) -> None:
        """Handle selection change from app state."""
        selected = event.data.get('selected', [])
        if selected and len(selected) == 1:
            # Single selection
            selected_id = selected[0]
            if selected_id != self._selected_node_id and selected_id in self._app_state.nodes:
                self._select_node(selected_id)
        else:
            # Clear selection
            self._selected_node_id = None
            for item in self._tree_items.values():
                if hasattr(item, 'classes'):
                    item.classes(remove='bg-blue-50')
    
    # Missing interface methods implementation
    
    def expand_node(self, node_id: str) -> None:
        """Expand a node (for groups)."""
        if node_id in self._app_state.groups:
            self._expanded_groups.add(node_id)
            self._build_tree()
    
    def collapse_node(self, node_id: str) -> None:
        """Collapse a node (for groups)."""
        if node_id in self._app_state.groups:
            self._expanded_groups.discard(node_id)
            self._build_tree()
    
    def get_selected(self) -> List[str]:
        """Get selected node IDs."""
        if self._selected_node_id:
            return [self._selected_node_id]
        return []
    
    def move_node(self, node_id: str, new_parent_id: Optional[str]) -> None:
        """Move a node to a new parent (group)."""
        # Implementation would handle moving nodes between groups
        # For now, we'll just rebuild the tree
        self._build_tree()
    
    def on_node_drop(self, handler: Callable[[str, Optional[str]], None]) -> None:
        """Register handler for node drop events."""
        # This would be used for drag-and-drop support
        pass
    
    def on_selection_change(self, handler: Callable[[List[str]], None]) -> None:
        """Register selection change handler."""
        # Wrap single node handler to work with list
        def wrapped_handler(node_id: str) -> None:
            handler([node_id] if node_id else [])
        self.on_node_select(wrapped_handler)