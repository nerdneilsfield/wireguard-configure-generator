"""
Help dialog implementation for showing application help and documentation.

This component provides help content and user guidance.
"""

from typing import Optional, Callable, Dict, Any
from nicegui import ui

from .base import BaseComponent
from ..interfaces.components import IDialog


class HelpDialog(BaseComponent, IDialog):
    """Implementation of help dialog for application documentation."""
    
    def __init__(self, component_id: Optional[str] = None):
        """
        Initialize help dialog.
        
        Args:
            component_id: Optional component ID
        """
        super().__init__(component_id)
        self._dialog: Optional[ui.dialog] = None
        self._current_tab = 'getting_started'
        
        # Event handlers
        self._on_close: Optional[Callable[[], None]] = None
    
    def render(self) -> ui.element:
        """Render the help dialog."""
        self._dialog = ui.dialog()
        
        with self._dialog, ui.card().classes('w-[800px] h-[600px]'):
            with ui.column().classes('w-full h-full') as self._element:
                # Header
                with ui.row().classes('items-center mb-4'):
                    ui.label('Help & Documentation').classes('text-h5 flex-grow')
                    ui.button(icon='close', on_click=self.close).props('flat dense round')
                
                ui.separator()
                
                # Content area with tabs
                with ui.tabs().classes('w-full').bind_value_to(self, '_current_tab') as tabs:
                    ui.tab('getting_started', label='Getting Started', icon='play_circle')
                    ui.tab('interface', label='Interface Guide', icon='dashboard')
                    ui.tab('concepts', label='Concepts', icon='school')
                    ui.tab('workflows', label='Common Workflows', icon='timeline')
                    ui.tab('troubleshooting', label='Troubleshooting', icon='build')
                
                with ui.tab_panels(tabs, value=self._current_tab).classes('w-full flex-grow'):
                    with ui.tab_panel('getting_started'):
                        self._render_getting_started()
                    
                    with ui.tab_panel('interface'):
                        self._render_interface_guide()
                    
                    with ui.tab_panel('concepts'):
                        self._render_concepts()
                    
                    with ui.tab_panel('workflows'):
                        self._render_workflows()
                    
                    with ui.tab_panel('troubleshooting'):
                        self._render_troubleshooting()
        
        return self._dialog
    
    def _render_getting_started(self) -> None:
        """Render getting started content."""
        with ui.scroll_area().classes('w-full h-full p-4'):
            ui.markdown("""
# Getting Started with WireGuard Configuration Editor

Welcome to the WireGuard Configuration Editor! This tool helps you visually create and manage
complex WireGuard network configurations.

## Quick Start

1. **Create Nodes**: Add WireGuard nodes (clients and relays) to your network
2. **Connect Nodes**: Create connections between nodes by adding edges
3. **Configure Groups**: Organize nodes into groups with specific topologies
4. **Validate**: Check your configuration for errors
5. **Export**: Generate WireGuard configuration files

## Key Features

- **Visual Network Design**: Drag-and-drop interface for network topology
- **Group Management**: Organize nodes with mesh, star, chain, or single topologies
- **Multiple Endpoints**: Support for nodes with different endpoints for different peers
- **Validation**: Comprehensive configuration validation
- **Import/Export**: Support for YAML, JSON, and WireGuard formats

## Basic Workflow

### 1. Adding Nodes
- Click the "+" button in the toolbar or press Ctrl+N
- Specify node name, role (client/relay), and IP address
- Nodes appear in both the graph view and node tree

### 2. Creating Connections
- Select two nodes and press Ctrl+E
- Or drag from one node to another in the graph
- Configure allowed IPs for the connection

### 3. Using Groups
- Create a group with Ctrl+G
- Drag nodes into the group
- Choose topology (mesh, star, chain, single)
- The editor automatically creates appropriate connections

### 4. Generating Configurations
- Validate your network with Ctrl+V
- Export configurations with Ctrl+Shift+E
- Choose format and options in the export dialog
            """)
    
    def _render_interface_guide(self) -> None:
        """Render interface guide content."""
        with ui.scroll_area().classes('w-full h-full p-4'):
            ui.markdown("""
# Interface Guide

## Main Components

### 1. Menu Bar
- **File**: New, Open, Save, Import, Export
- **Edit**: Undo/Redo, Delete, Select
- **Tools**: Validate, Generate Keys
- **View**: Layout options, Zoom controls
- **Help**: Documentation and shortcuts

### 2. Toolbar
Quick access to common actions:
- Open/Save configurations
- Validate network
- Export configurations
- Layout controls
- Undo/Redo

### 3. Node Tree (Left Panel)
Hierarchical view of your network:
- Groups with their nodes
- Expand/collapse groups
- Double-click to focus on node
- Drag nodes between groups

### 4. Graph View (Center)
Visual network representation:
- Drag nodes to reposition
- Click to select
- Double-click to edit
- Zoom with mouse wheel
- Pan by dragging background

### 5. Properties Panel (Right)
Edit selected element properties:
- Node configuration
- Edge settings
- Group properties
- Real-time validation

### 6. Status Bar
Shows current state:
- Node and edge counts
- Validation status
- Last action performed

## Mouse Controls

- **Left Click**: Select element
- **Double Click**: Edit element
- **Right Click**: Context menu
- **Drag Node**: Reposition
- **Drag Background**: Pan view
- **Scroll Wheel**: Zoom in/out
- **Ctrl+Click**: Multi-select

## Color Coding

- **Blue**: Client nodes
- **Green**: Relay nodes
- **Red**: Invalid/error state
- **Yellow**: Warning state
- **Gray**: Disabled/inactive
            """)
    
    def _render_concepts(self) -> None:
        """Render concepts content."""
        with ui.scroll_area().classes('w-full h-full p-4'):
            ui.markdown("""
# WireGuard Concepts

## Node Types

### Client Nodes
- End devices in your network
- Usually behind NAT
- Connect through relay nodes
- Cannot accept incoming connections

### Relay Nodes
- Publicly accessible servers
- Have static endpoints
- Route traffic between clients
- Bridge different network segments

## Connection Types

### Direct Connections
- Peer-to-peer between nodes
- Requires at least one public endpoint
- Lower latency, higher performance

### Relayed Connections
- Traffic routed through relay node
- Works behind NAT/firewall
- Slightly higher latency

## Group Topologies

### Mesh Topology
- Every node connects to every other node
- Maximum redundancy
- Higher overhead
- Best for small groups

### Star Topology
- All nodes connect to central relay
- Efficient for client-server setups
- Single point of failure
- Easy to manage

### Chain Topology
- Nodes connected in sequence
- Useful for VPN chains
- Each node depends on previous
- Linear traffic flow

### Single Topology
- Standalone node configuration
- No automatic connections
- Manual edge creation required

## Allowed IPs

Determines which traffic goes through VPN:
- `0.0.0.0/0`: All IPv4 traffic
- `10.0.0.0/24`: Specific subnet
- Multiple ranges supported
- Must not overlap between peers

## Endpoints

Node connection addresses:
- Format: `hostname:port` or `IP:port`
- Relay nodes need public endpoints
- Clients can be behind NAT
- Multiple endpoints per node supported
            """)
    
    def _render_workflows(self) -> None:
        """Render common workflows content."""
        with ui.scroll_area().classes('w-full h-full p-4'):
            ui.markdown("""
# Common Workflows

## Setting Up a Basic VPN

### 1. Client-Server VPN
```
1. Create relay node with public endpoint
2. Create client nodes
3. Add both to a group with star topology
4. Configure allowed IPs (0.0.0.0/0 for full tunnel)
5. Generate and export configurations
```

### 2. Site-to-Site VPN
```
1. Create relay nodes for each site
2. Connect relays in mesh topology
3. Add local clients to each site
4. Configure subnet routing
5. Export configurations
```

## Advanced Configurations

### Multi-Region Setup
```
1. Create relay nodes in each region
2. Connect relays in mesh topology
3. Create region groups
4. Add clients to nearest region
5. Configure geo-based routing
```

### High Availability
```
1. Deploy multiple relay nodes
2. Configure mesh between relays
3. Set multiple endpoints on clients
4. Use keepalive for failover
5. Test failover scenarios
```

## Import Existing Configuration

### From WireGuard Files
```
1. Click Import or press Ctrl+O
2. Select .conf files
3. Review detected topology
4. Adjust as needed
5. Save in editor format
```

### From YAML/JSON
```
1. Prepare nodes.yaml and topology.yaml
2. Import both files
3. Editor recreates visual layout
4. Modify as needed
5. Export back to any format
```

## Troubleshooting Connections

### Validation Errors
```
1. Run validation (Ctrl+V)
2. Click on error to highlight element
3. Fix in properties panel
4. Re-validate until clean
```

### Connection Issues
```
1. Check endpoint accessibility
2. Verify allowed IPs don't overlap
3. Ensure keys are generated
4. Test with simple topology first
5. Check firewall rules
```
            """)
    
    def _render_troubleshooting(self) -> None:
        """Render troubleshooting content."""
        with ui.scroll_area().classes('w-full h-full p-4'):
            ui.markdown("""
# Troubleshooting Guide

## Common Issues

### Import Failures

**Problem**: File import fails with format error
- Check file is valid YAML/JSON
- Ensure required fields present
- Validate against schema
- Try importing one file at a time

**Problem**: Imported topology looks wrong
- Verify node names match
- Check group definitions
- Review edge connections
- Use layout options to reorganize

### Validation Errors

**Problem**: "Duplicate endpoint" error
- Each endpoint must be unique
- Check relay nodes have different ports
- Use DNS names if sharing IPs

**Problem**: "Overlapping allowed IPs"
- Review all edge configurations
- Ensure no IP ranges overlap
- Use more specific subnets
- Check group topology settings

**Problem**: "Missing endpoint for relay"
- Relay nodes require public endpoints
- Format: `host:port`
- Ensure DNS resolves
- Default port is 51820

### Export Issues

**Problem**: Export button disabled
- Need at least one node
- Check validation status
- Ensure configuration is valid

**Problem**: Generated configs look wrong
- Verify node properties
- Check edge directions
- Review allowed IPs
- Validate before export

### Performance Issues

**Problem**: Large networks lag
- Use simplified layout
- Disable animations
- Group nodes logically
- Hide unnecessary details

**Problem**: Slow file operations
- Break large configs into groups
- Import in batches
- Use native file browser
- Clear temporary files

## Getting Help

### Error Messages
- Click on errors for details
- Hover for tooltips
- Check validation panel
- Review properties

### Support Resources
- GitHub Issues
- Documentation
- Community Forums
- Video Tutorials

### Debug Information
- Check browser console (F12)
- Export debug logs
- Include configuration
- Describe steps to reproduce
            """)
    
    def show(self) -> None:
        """Show the help dialog."""
        if self._dialog:
            self._dialog.open()
    
    def close(self) -> None:
        """Close the help dialog."""
        if self._dialog:
            self._dialog.close()
        
        if self._on_close:
            self._on_close()
    
    def on_close(self, handler: Callable[[], None]) -> None:
        """Register close handler."""
        self._on_close = handler