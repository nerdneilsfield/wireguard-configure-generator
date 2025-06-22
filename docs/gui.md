# WireGuard Visual Configuration Editor - Development Plan

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Detailed TODOs](#detailed-todos)
3. [API & Interface Design](#api--interface-design)
4. [Test Specifications](#test-specifications)
5. [Implementation Plan](#implementation-plan)

## Quick TODO Checklist

### Phase 0: Proof of Concept (2 days) ✅ COMPLETED
- [x] Create minimal NiceGUI app with Cytoscape.js integration
- [x] Implement basic node add/delete functionality
- [x] Test graph visualization works correctly
- [x] Validate the technical approach

**POC Results:**
- Successfully integrated NiceGUI with Cytoscape.js
- Interactive graph visualization working smoothly
- Bidirectional Python-JavaScript communication established
- Basic CRUD operations for nodes and edges functional
- Event handling system operational
- Technical approach validated and ready for full implementation

### Phase 1: Interfaces & Tests First (3 days)
- [ ] Define all interfaces in `wg_mesh_gen/gui/interfaces/`
- [ ] Create test stubs for all interfaces
- [ ] Write comprehensive test cases (without implementation)
- [ ] Set up test infrastructure (pytest, mocks, fixtures)
- [ ] Get approval on interfaces and test design

### Phase 2: Core Implementation (5 days)
- [ ] Implement models to pass tests
- [ ] Implement managers to pass tests  
- [ ] Implement state management to pass tests
- [ ] Integrate with existing wg_mesh_gen modules
- [ ] Ensure all unit tests pass

### Phase 3: UI Components (5 days)
- [ ] Implement Cytoscape widget with tests
- [ ] Build property panels with tests
- [ ] Create node tree component with tests
- [ ] Implement toolbar and dialogs with tests
- [ ] Integration testing for UI components

### Phase 4: Polish & Deploy (3 days)
- [ ] Add auto-layout algorithms
- [ ] Implement import/export functionality
- [ ] Create deployment scripts
- [ ] Write user documentation
- [ ] End-to-end testing

## Architecture Overview

### Technology Stack
- **Frontend**: NiceGUI + Cytoscape.js
- **Backend**: Python with existing wg_mesh_gen modules
- **Data Storage**: In-memory with file persistence
- **Deployment**: Local/Web/Docker

### Component Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    UI Layer (NiceGUI)                    │
├─────────────────────────────────────────────────────────┤
│                 Business Logic Layer                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ GraphManager│  │ConfigManager │  │ StateManager  │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
├─────────────────────────────────────────────────────────┤
│                    Data Layer                            │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ NodeModel   │  │ GroupModel   │  │ TopologyModel │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
├─────────────────────────────────────────────────────────┤
│              Integration Layer                           │
│         Existing wg_mesh_gen modules                     │
└─────────────────────────────────────────────────────────┘
```

## Detailed TODOs

### Phase 1: Core Infrastructure (Week 1)

#### 1.1 Project Setup
- [ ] Create new module `wg_mesh_gen/gui/` directory structure
- [ ] Add GUI dependencies to pyproject.toml (nicegui>=1.4.0)
- [ ] Create `__init__.py` files for all submodules
- [ ] Setup logging configuration for GUI module
- [ ] Create GUI-specific configuration file structure

#### 1.2 Data Models
- [ ] Create `wg_mesh_gen/gui/models/base.py`
  - [ ] Define BaseModel with id, created_at, updated_at
  - [ ] Implement model validation base class
  - [ ] Add serialization/deserialization methods
  
- [ ] Create `wg_mesh_gen/gui/models/node.py`
  - [ ] Define NodeModel class with properties:
    - id: str (unique identifier)
    - name: str (display name)
    - wireguard_ip: str (IP address with subnet)
    - endpoints: Dict[str, str] (endpoint_name -> address:port)
    - role: str (client/relay)
    - enable_ip_forward: bool
    - group_id: Optional[str]
    - position: Dict[str, float] (x, y coordinates)
    - metadata: Dict[str, Any]
  - [ ] Implement validation methods
  - [ ] Add endpoint management methods
  
- [ ] Create `wg_mesh_gen/gui/models/edge.py`
  - [ ] Define EdgeModel class with properties:
    - id: str
    - source_id: str
    - target_id: str
    - edge_type: str (peer/mesh/star/relay)
    - allowed_ips: List[str]
    - endpoint_name: Optional[str]
    - persistent_keepalive: Optional[int]
    - metadata: Dict[str, Any]
  - [ ] Implement validation for allowed_ips
  - [ ] Add bidirectional edge detection
  
- [ ] Create `wg_mesh_gen/gui/models/group.py`
  - [ ] Define GroupModel class with properties:
    - id: str
    - name: str
    - color: str (for visualization)
    - topology: str (mesh/star/chain/single)
    - mesh_endpoint: Optional[str]
    - nodes: List[str] (node IDs)
    - metadata: Dict[str, Any]
  - [ ] Implement node membership management
  - [ ] Add topology validation

#### 1.3 State Management
- [ ] Create `wg_mesh_gen/gui/state/app_state.py`
  - [ ] Define AppState class:
    ```python
    class AppState:
        nodes: Dict[str, NodeModel]
        edges: Dict[str, EdgeModel]
        groups: Dict[str, GroupModel]
        selected_elements: Set[str]
        undo_stack: List[Command]
        redo_stack: List[Command]
        dirty: bool
        current_file: Optional[str]
    ```
  - [ ] Implement state change notifications
  - [ ] Add state validation methods
  
- [ ] Create `wg_mesh_gen/gui/state/commands.py`
  - [ ] Define Command base class with execute/undo methods
  - [ ] Implement AddNodeCommand
  - [ ] Implement UpdateNodeCommand
  - [ ] Implement DeleteNodeCommand
  - [ ] Implement AddEdgeCommand
  - [ ] Implement UpdateEdgeCommand
  - [ ] Implement DeleteEdgeCommand
  - [ ] Implement AddGroupCommand
  - [ ] Implement UpdateGroupCommand
  - [ ] Implement DeleteGroupCommand
  - [ ] Implement MoveNodeToGroupCommand
  
- [ ] Create `wg_mesh_gen/gui/state/history.py`
  - [ ] Implement HistoryManager with undo/redo
  - [ ] Add command batching support
  - [ ] Implement history size limits
  - [ ] Add history persistence

#### 1.4 Cytoscape.js Integration
- [ ] Create `wg_mesh_gen/gui/components/cytoscape_widget.py`
  - [ ] Define CytoscapeWidget class extending ui.element
  - [ ] Implement JavaScript component loading
  - [ ] Add Python-to-JS method bindings:
    - add_node(node_data)
    - update_node(node_id, updates)
    - delete_node(node_id)
    - add_edge(edge_data)
    - update_edge(edge_id, updates)
    - delete_edge(edge_id)
    - set_layout(layout_name, options)
    - fit_view()
    - export_image(format)
  - [ ] Implement JS-to-Python event handlers:
    - on_node_click(handler)
    - on_node_double_click(handler)
    - on_node_right_click(handler)
    - on_edge_click(handler)
    - on_canvas_click(handler)
    - on_node_drag_end(handler)
    - on_selection_change(handler)
  
- [ ] Create `wg_mesh_gen/gui/components/cytoscape_widget.js`
  - [ ] Define Vue component for Cytoscape integration
  - [ ] Implement graph initialization
  - [ ] Add node/edge styling
  - [ ] Implement layout algorithms
  - [ ] Add interaction handlers
  - [ ] Implement graph manipulation methods

### Phase 2: Core UI Components (Week 2)

#### 2.1 Main Application Window
- [ ] Create `wg_mesh_gen/gui/app.py`
  - [ ] Define WireGuardVisualEditor main class
  - [ ] Implement application initialization
  - [ ] Setup main window layout
  - [ ] Add menu bar creation
  - [ ] Implement status bar
  
- [ ] Create `wg_mesh_gen/gui/layouts/main_layout.py`
  - [ ] Implement responsive splitter layout
  - [ ] Add panel collapse/expand functionality
  - [ ] Implement layout persistence
  - [ ] Add keyboard shortcuts

#### 2.2 Toolbar Component
- [ ] Create `wg_mesh_gen/gui/components/toolbar.py`
  - [ ] Implement ToolbarComponent class
  - [ ] Add buttons:
    - [ ] New Configuration
    - [ ] Open Configuration
    - [ ] Save Configuration
    - [ ] Export Configurations
    - [ ] Undo/Redo
    - [ ] Add Node
    - [ ] Add Group
    - [ ] Auto Layout
    - [ ] Validate
    - [ ] Simulate
  - [ ] Add button state management
  - [ ] Implement tooltips

#### 2.3 Node Tree Component
- [ ] Create `wg_mesh_gen/gui/components/node_tree.py`
  - [ ] Implement NodeTreeComponent class
  - [ ] Add tree structure rendering
  - [ ] Implement drag-and-drop support
  - [ ] Add context menus
  - [ ] Implement search/filter
  - [ ] Add node icons based on role
  - [ ] Implement multi-selection

#### 2.4 Properties Panel
- [ ] Create `wg_mesh_gen/gui/components/properties_panel.py`
  - [ ] Define PropertiesPanel base class
  - [ ] Implement dynamic form generation
  - [ ] Add validation indicators
  
- [ ] Create `wg_mesh_gen/gui/components/node_properties.py`
  - [ ] Implement NodePropertiesPanel
  - [ ] Add fields:
    - Name (editable)
    - IP Address (with validation)
    - Endpoints (dynamic list)
    - Role selection
    - IP Forwarding toggle
    - Group assignment
  - [ ] Implement real-time validation
  - [ ] Add apply/cancel buttons
  
- [ ] Create `wg_mesh_gen/gui/components/edge_properties.py`
  - [ ] Implement EdgePropertiesPanel
  - [ ] Add fields:
    - Source/Target (read-only)
    - Connection Type
    - Allowed IPs (list editor)
    - Endpoint selection
    - Persistent Keepalive
  - [ ] Implement subnet validation
  - [ ] Add IP calculator helper
  
- [ ] Create `wg_mesh_gen/gui/components/group_properties.py`
  - [ ] Implement GroupPropertiesPanel
  - [ ] Add fields:
    - Group Name
    - Topology Type
    - Mesh Endpoint
    - Color Picker
    - Member Nodes (list)
  - [ ] Add topology preview
  - [ ] Implement member management

#### 2.5 YAML/JSON Editor
- [ ] Create `wg_mesh_gen/gui/components/config_editor.py`
  - [ ] Implement ConfigEditor with syntax highlighting
  - [ ] Add YAML/JSON format toggle
  - [ ] Implement real-time validation
  - [ ] Add error highlighting
  - [ ] Implement sync with visual editor
  - [ ] Add format/beautify function
  - [ ] Implement search/replace

### Phase 3: Business Logic (Week 3)

#### 3.1 Graph Manager
- [ ] Create `wg_mesh_gen/gui/managers/graph_manager.py`
  - [ ] Define GraphManager class:
    ```python
    class GraphManager:
        def __init__(self, app_state: AppState, cytoscape_widget: CytoscapeWidget):
            pass
            
        def add_node(self, node: NodeModel) -> None:
            pass
            
        def update_node(self, node_id: str, updates: Dict) -> None:
            pass
            
        def delete_node(self, node_id: str) -> None:
            pass
            
        def add_edge(self, edge: EdgeModel) -> None:
            pass
            
        def update_edge(self, edge_id: str, updates: Dict) -> None:
            pass
            
        def delete_edge(self, edge_id: str) -> None:
            pass
            
        def apply_layout(self, layout_type: str, options: Dict) -> None:
            pass
            
        def sync_from_state(self) -> None:
            pass
    ```
  - [ ] Implement graph-to-state synchronization
  - [ ] Add visual feedback methods
  - [ ] Implement selection management
  - [ ] Add graph export functionality

#### 3.2 Configuration Manager
- [ ] Create `wg_mesh_gen/gui/managers/config_manager.py`
  - [ ] Define ConfigManager class:
    ```python
    class ConfigManager:
        def state_to_yaml(self, state: AppState) -> str:
            pass
            
        def yaml_to_state(self, yaml_content: str) -> AppState:
            pass
            
        def state_to_json(self, state: AppState) -> str:
            pass
            
        def json_to_state(self, json_content: str) -> AppState:
            pass
            
        def validate_state(self, state: AppState) -> List[ValidationError]:
            pass
            
        def export_wireguard_configs(self, state: AppState, output_dir: str) -> None:
            pass
    ```
  - [ ] Implement group configuration handling
  - [ ] Add routing rules processing
  - [ ] Implement backward compatibility
  - [ ] Add configuration migration

#### 3.3 Validation Manager
- [ ] Create `wg_mesh_gen/gui/managers/validation_manager.py`
  - [ ] Define ValidationManager class
  - [ ] Implement real-time validation rules:
    - [ ] IP address format validation
    - [ ] IP subnet overlap detection
    - [ ] Endpoint format validation
    - [ ] Port range validation
    - [ ] Group topology validation
    - [ ] Routing loop detection
  - [ ] Add visual feedback integration
  - [ ] Implement validation caching

#### 3.4 File Manager
- [ ] Create `wg_mesh_gen/gui/managers/file_manager.py`
  - [ ] Define FileManager class:
    ```python
    class FileManager:
        def new_configuration(self) -> None:
            pass
            
        def open_configuration(self, file_path: str) -> None:
            pass
            
        def save_configuration(self, file_path: Optional[str] = None) -> None:
            pass
            
        def export_configuration(self, format: str, output_path: str) -> None:
            pass
            
        def import_legacy_config(self, nodes_file: str, topo_file: str) -> None:
            pass
    ```
  - [ ] Implement file dialogs
  - [ ] Add recent files tracking
  - [ ] Implement auto-save
  - [ ] Add file watching

### Phase 4: Integration & Advanced Features (Week 4)

#### 4.1 Integration Layer
- [ ] Create `wg_mesh_gen/gui/integration/config_bridge.py`
  - [ ] Implement bridge to existing modules:
    ```python
    class ConfigBridge:
        def use_group_network_builder(self, state: AppState) -> Tuple[List, List]:
            pass
            
        def use_validator(self, state: AppState) -> bool:
            pass
            
        def use_simulator(self, state: AppState) -> SimulationResult:
            pass
            
        def use_visualizer(self, state: AppState) -> bytes:
            pass
    ```
  - [ ] Add error handling
  - [ ] Implement data transformation
  - [ ] Add compatibility layer

#### 4.2 Event System
- [ ] Create `wg_mesh_gen/gui/events/event_bus.py`
  - [ ] Define EventBus class
  - [ ] Implement event registration
  - [ ] Add event dispatching
  - [ ] Implement event priorities
  
- [ ] Create `wg_mesh_gen/gui/events/app_events.py`
  - [ ] Define event types:
    - NodeAddedEvent
    - NodeUpdatedEvent
    - NodeDeletedEvent
    - EdgeAddedEvent
    - EdgeUpdatedEvent
    - EdgeDeletedEvent
    - SelectionChangedEvent
    - StateChangedEvent
    - ValidationErrorEvent

#### 4.3 Dialogs
- [ ] Create `wg_mesh_gen/gui/dialogs/node_dialog.py`
  - [ ] Implement add/edit node dialog
  - [ ] Add form validation
  - [ ] Implement endpoint management
  
- [ ] Create `wg_mesh_gen/gui/dialogs/group_dialog.py`
  - [ ] Implement create/edit group dialog
  - [ ] Add member selection
  - [ ] Implement topology preview
  
- [ ] Create `wg_mesh_gen/gui/dialogs/import_dialog.py`
  - [ ] Implement import wizard
  - [ ] Add format detection
  - [ ] Show import preview
  
- [ ] Create `wg_mesh_gen/gui/dialogs/export_dialog.py`
  - [ ] Implement export options
  - [ ] Add format selection
  - [ ] Show export preview

#### 4.4 Auto Layout
- [ ] Create `wg_mesh_gen/gui/layout/layout_engine.py`
  - [ ] Define LayoutEngine class
  - [ ] Implement layout algorithms:
    - [ ] Hierarchical (for star topology)
    - [ ] Force-directed (for mesh)
    - [ ] Geographic (if coordinates available)
    - [ ] Circular
    - [ ] Grid
  - [ ] Add layout constraints
  - [ ] Implement incremental layout

#### 4.5 Simulation Integration
- [ ] Create `wg_mesh_gen/gui/features/simulation_panel.py`
  - [ ] Implement simulation control panel
  - [ ] Add test selection
  - [ ] Show results visually
  - [ ] Implement failure simulation
  - [ ] Add performance metrics display

## API & Interface Design

### Core Interfaces

#### 1. Model Interfaces
```python
# wg_mesh_gen/gui/interfaces/models.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IModel(ABC):
    """Base interface for all models"""
    
    @abstractmethod
    def validate(self) -> List[str]:
        """Validate model and return list of errors"""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        pass
    
    @abstractmethod
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load model from dictionary"""
        pass

class INode(IModel):
    """Node model interface"""
    
    @property
    @abstractmethod
    def id(self) -> str:
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def wireguard_ip(self) -> str:
        pass
    
    @abstractmethod
    def add_endpoint(self, name: str, address: str) -> None:
        pass
    
    @abstractmethod
    def remove_endpoint(self, name: str) -> None:
        pass

class IEdge(IModel):
    """Edge model interface"""
    
    @property
    @abstractmethod
    def source_id(self) -> str:
        pass
    
    @property
    @abstractmethod
    def target_id(self) -> str:
        pass
    
    @property
    @abstractmethod
    def allowed_ips(self) -> List[str]:
        pass
    
    @abstractmethod
    def add_allowed_ip(self, subnet: str) -> None:
        pass

class IGroup(IModel):
    """Group model interface"""
    
    @property
    @abstractmethod
    def topology(self) -> str:
        pass
    
    @abstractmethod
    def add_node(self, node_id: str) -> None:
        pass
    
    @abstractmethod
    def remove_node(self, node_id: str) -> None:
        pass
```

#### 2. Manager Interfaces
```python
# wg_mesh_gen/gui/interfaces/managers.py
from abc import ABC, abstractmethod

class IGraphManager(ABC):
    """Graph visualization manager interface"""
    
    @abstractmethod
    def add_node(self, node: INode) -> None:
        pass
    
    @abstractmethod
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> None:
        pass
    
    @abstractmethod
    def delete_node(self, node_id: str) -> None:
        pass
    
    @abstractmethod
    def add_edge(self, edge: IEdge) -> None:
        pass
    
    @abstractmethod
    def get_selected_elements(self) -> List[str]:
        pass

class IConfigManager(ABC):
    """Configuration manager interface"""
    
    @abstractmethod
    def load_from_yaml(self, yaml_content: str) -> IAppState:
        pass
    
    @abstractmethod
    def save_to_yaml(self, state: IAppState) -> str:
        pass
    
    @abstractmethod
    def validate(self, state: IAppState) -> List[ValidationError]:
        pass

class IStateManager(ABC):
    """Application state manager interface"""
    
    @abstractmethod
    def execute_command(self, command: ICommand) -> None:
        pass
    
    @abstractmethod
    def undo(self) -> None:
        pass
    
    @abstractmethod
    def redo(self) -> None:
        pass
    
    @abstractmethod
    def get_state(self) -> IAppState:
        pass
```

#### 3. Component Interfaces
```python
# wg_mesh_gen/gui/interfaces/components.py
from abc import ABC, abstractmethod

class IComponent(ABC):
    """Base UI component interface"""
    
    @abstractmethod
    def create(self) -> None:
        """Create and initialize component"""
        pass
    
    @abstractmethod
    def destroy(self) -> None:
        """Clean up component resources"""
        pass
    
    @abstractmethod
    def update(self) -> None:
        """Update component display"""
        pass

class IPropertyEditor(IComponent):
    """Property editor interface"""
    
    @abstractmethod
    def load_element(self, element_id: str) -> None:
        pass
    
    @abstractmethod
    def save_changes(self) -> None:
        pass
    
    @abstractmethod
    def cancel_changes(self) -> None:
        pass

class ITreeView(IComponent):
    """Tree view interface"""
    
    @abstractmethod
    def add_node(self, node: INode, parent_id: Optional[str]) -> None:
        pass
    
    @abstractmethod
    def remove_node(self, node_id: str) -> None:
        pass
    
    @abstractmethod
    def on_selection_change(self, handler: Callable) -> None:
        pass
```

### REST API (for Web Mode)

```python
# wg_mesh_gen/gui/api/routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1")

class NodeCreate(BaseModel):
    name: str
    wireguard_ip: str
    endpoints: Dict[str, str]
    role: str = "client"
    group_id: Optional[str] = None

class EdgeCreate(BaseModel):
    source_id: str
    target_id: str
    allowed_ips: List[str]
    edge_type: str = "peer"

@router.post("/nodes")
async def create_node(node: NodeCreate):
    """Create a new node"""
    pass

@router.get("/nodes/{node_id}")
async def get_node(node_id: str):
    """Get node details"""
    pass

@router.put("/nodes/{node_id}")
async def update_node(node_id: str, updates: Dict[str, Any]):
    """Update node properties"""
    pass

@router.delete("/nodes/{node_id}")
async def delete_node(node_id: str):
    """Delete a node"""
    pass

@router.post("/edges")
async def create_edge(edge: EdgeCreate):
    """Create a new edge"""
    pass

@router.get("/graph")
async def get_graph():
    """Get entire graph state"""
    pass

@router.post("/validate")
async def validate_configuration():
    """Validate current configuration"""
    pass

@router.post("/export")
async def export_configuration(format: str = "yaml"):
    """Export configuration in specified format"""
    pass
```

## Test Specifications

### Unit Tests

#### 1. Model Tests
```python
# tests/gui/test_models.py
import pytest
from wg_mesh_gen.gui.models import NodeModel, EdgeModel, GroupModel

class TestNodeModel:
    def test_create_node_with_valid_data(self):
        """Test creating a node with valid data"""
        node = NodeModel(
            name="test-node",
            wireguard_ip="10.0.0.1/24",
            endpoints={"public": "192.168.1.1:51820"}
        )
        assert node.name == "test-node"
        assert node.wireguard_ip == "10.0.0.1/24"
        assert len(node.endpoints) == 1
    
    def test_invalid_ip_address_raises_error(self):
        """Test that invalid IP address raises validation error"""
        with pytest.raises(ValueError):
            NodeModel(name="test", wireguard_ip="invalid-ip")
    
    def test_add_endpoint(self):
        """Test adding endpoint to node"""
        node = NodeModel(name="test", wireguard_ip="10.0.0.1/24")
        node.add_endpoint("mesh", "192.168.1.1:51820")
        assert "mesh" in node.endpoints
        assert node.endpoints["mesh"] == "192.168.1.1:51820"
    
    def test_invalid_endpoint_format_raises_error(self):
        """Test that invalid endpoint format raises error"""
        node = NodeModel(name="test", wireguard_ip="10.0.0.1/24")
        with pytest.raises(ValueError):
            node.add_endpoint("bad", "no-port-specified")
    
    def test_node_serialization(self):
        """Test node serialization to dict"""
        node = NodeModel(
            name="test",
            wireguard_ip="10.0.0.1/24",
            role="relay",
            enable_ip_forward=True
        )
        data = node.to_dict()
        assert data["name"] == "test"
        assert data["role"] == "relay"
        assert data["enable_ip_forward"] is True
    
    def test_node_deserialization(self):
        """Test node deserialization from dict"""
        data = {
            "id": "node-1",
            "name": "test",
            "wireguard_ip": "10.0.0.1/24",
            "endpoints": {"public": "1.2.3.4:51820"},
            "role": "client"
        }
        node = NodeModel.from_dict(data)
        assert node.id == "node-1"
        assert node.name == "test"

class TestEdgeModel:
    def test_create_edge_with_valid_data(self):
        """Test creating edge with valid data"""
        edge = EdgeModel(
            source_id="node1",
            target_id="node2",
            allowed_ips=["10.0.0.2/32"]
        )
        assert edge.source_id == "node1"
        assert edge.target_id == "node2"
        assert len(edge.allowed_ips) == 1
    
    def test_invalid_allowed_ip_raises_error(self):
        """Test that invalid allowed IP raises error"""
        with pytest.raises(ValueError):
            EdgeModel(
                source_id="node1",
                target_id="node2",
                allowed_ips=["not-an-ip"]
            )
    
    def test_add_allowed_ip(self):
        """Test adding allowed IP to edge"""
        edge = EdgeModel(source_id="n1", target_id="n2")
        edge.add_allowed_ip("10.0.0.0/24")
        assert "10.0.0.0/24" in edge.allowed_ips
    
    def test_duplicate_allowed_ip_ignored(self):
        """Test that duplicate allowed IPs are ignored"""
        edge = EdgeModel(
            source_id="n1",
            target_id="n2",
            allowed_ips=["10.0.0.0/24"]
        )
        edge.add_allowed_ip("10.0.0.0/24")
        assert len(edge.allowed_ips) == 1

class TestGroupModel:
    def test_create_group_with_valid_data(self):
        """Test creating group with valid data"""
        group = GroupModel(
            name="office",
            topology="mesh",
            nodes=["node1", "node2"]
        )
        assert group.name == "office"
        assert group.topology == "mesh"
        assert len(group.nodes) == 2
    
    def test_invalid_topology_raises_error(self):
        """Test that invalid topology raises error"""
        with pytest.raises(ValueError):
            GroupModel(name="test", topology="invalid-topology")
    
    def test_add_node_to_group(self):
        """Test adding node to group"""
        group = GroupModel(name="test", topology="star")
        group.add_node("node1")
        assert "node1" in group.nodes
    
    def test_remove_node_from_group(self):
        """Test removing node from group"""
        group = GroupModel(name="test", topology="star", nodes=["n1", "n2"])
        group.remove_node("n1")
        assert "n1" not in group.nodes
        assert len(group.nodes) == 1
```

#### 2. Manager Tests
```python
# tests/gui/test_managers.py
import pytest
from unittest.mock import Mock, MagicMock
from wg_mesh_gen.gui.managers import GraphManager, ConfigManager, StateManager

class TestGraphManager:
    @pytest.fixture
    def graph_manager(self):
        app_state = Mock()
        cytoscape_widget = Mock()
        return GraphManager(app_state, cytoscape_widget)
    
    def test_add_node_updates_state_and_widget(self, graph_manager):
        """Test that adding node updates both state and widget"""
        node = Mock(id="node1")
        graph_manager.add_node(node)
        
        graph_manager.app_state.add_node.assert_called_once_with(node)
        graph_manager.cytoscape_widget.add_node.assert_called_once()
    
    def test_delete_node_removes_connected_edges(self, graph_manager):
        """Test that deleting node also removes its edges"""
        graph_manager.app_state.get_edges_for_node.return_value = ["edge1", "edge2"]
        
        graph_manager.delete_node("node1")
        
        assert graph_manager.app_state.delete_edge.call_count == 2
        graph_manager.app_state.delete_node.assert_called_once_with("node1")
    
    def test_apply_layout_updates_positions(self, graph_manager):
        """Test that applying layout updates node positions"""
        graph_manager.cytoscape_widget.apply_layout.return_value = {
            "node1": {"x": 100, "y": 200},
            "node2": {"x": 300, "y": 400}
        }
        
        graph_manager.apply_layout("hierarchical", {})
        
        assert graph_manager.app_state.update_node_position.call_count == 2

class TestConfigManager:
    @pytest.fixture
    def config_manager(self):
        return ConfigManager()
    
    def test_yaml_to_state_parses_valid_yaml(self, config_manager):
        """Test parsing valid YAML to state"""
        yaml_content = """
        nodes:
          office:
            - name: PC1
              wireguard_ip: 10.0.0.1/24
        groups:
          - name: office
            nodes: [PC1]
            topology: mesh
        """
        state = config_manager.yaml_to_state(yaml_content)
        assert len(state.nodes) == 1
        assert len(state.groups) == 1
    
    def test_state_to_yaml_generates_valid_yaml(self, config_manager):
        """Test generating YAML from state"""
        state = Mock()
        state.nodes = {"n1": Mock(name="PC1", wireguard_ip="10.0.0.1/24")}
        state.groups = {"g1": Mock(name="office", topology="mesh")}
        
        yaml_content = config_manager.state_to_yaml(state)
        assert "PC1" in yaml_content
        assert "office" in yaml_content
    
    def test_validate_state_detects_ip_conflicts(self, config_manager):
        """Test validation detects IP conflicts"""
        state = Mock()
        state.nodes = {
            "n1": Mock(wireguard_ip="10.0.0.1/24"),
            "n2": Mock(wireguard_ip="10.0.0.1/24")  # Duplicate IP
        }
        
        errors = config_manager.validate_state(state)
        assert len(errors) > 0
        assert any("IP conflict" in str(e) for e in errors)
```

#### 3. Component Tests
```python
# tests/gui/test_components.py
import pytest
from unittest.mock import Mock, patch
from wg_mesh_gen.gui.components import NodeTreeComponent, PropertiesPanel

class TestNodeTreeComponent:
    @pytest.fixture
    def tree_component(self):
        with patch('nicegui.ui'):
            return NodeTreeComponent()
    
    def test_add_node_creates_tree_item(self, tree_component):
        """Test adding node creates tree item"""
        node = Mock(id="n1", name="Node1", group_id=None)
        tree_component.add_node(node)
        
        assert "n1" in tree_component._tree_items
        assert tree_component._tree_items["n1"].label == "Node1"
    
    def test_drag_drop_changes_group(self, tree_component):
        """Test drag and drop changes node group"""
        # Setup
        tree_component.on_drop = Mock()
        node = Mock(id="n1", group_id=None)
        group = Mock(id="g1", name="Group1")
        
        # Simulate drag and drop
        tree_component._handle_drop("n1", "g1")
        
        tree_component.on_drop.assert_called_once_with("n1", "g1")
    
    def test_context_menu_shows_options(self, tree_component):
        """Test right-click shows context menu"""
        node = Mock(id="n1")
        tree_component.add_node(node)
        
        # Simulate right-click
        menu = tree_component._create_context_menu("n1")
        
        assert any("Delete" in item.text for item in menu.items)
        assert any("Duplicate" in item.text for item in menu.items)

class TestPropertiesPanel:
    @pytest.fixture
    def properties_panel(self):
        with patch('nicegui.ui'):
            return PropertiesPanel()
    
    def test_load_node_shows_node_fields(self, properties_panel):
        """Test loading node shows appropriate fields"""
        node = Mock(
            id="n1",
            name="Node1",
            wireguard_ip="10.0.0.1/24",
            endpoints={"public": "1.2.3.4:51820"}
        )
        
        properties_panel.load_element(node)
        
        assert properties_panel._current_element == node
        assert any(f.label == "Name" for f in properties_panel._fields)
        assert any(f.label == "IP Address" for f in properties_panel._fields)
    
    def test_validation_shows_errors(self, properties_panel):
        """Test validation shows errors for invalid data"""
        node = Mock(wireguard_ip="10.0.0.1/24")
        properties_panel.load_element(node)
        
        # Enter invalid IP
        ip_field = next(f for f in properties_panel._fields if f.label == "IP Address")
        ip_field.value = "invalid-ip"
        
        properties_panel._validate()
        
        assert ip_field.error == "Invalid IP address format"
```

### Integration Tests

```python
# tests/gui/test_integration.py
import pytest
from wg_mesh_gen.gui.app import WireGuardVisualEditor

class TestAppIntegration:
    @pytest.fixture
    def app(self):
        return WireGuardVisualEditor()
    
    def test_create_node_flow(self, app):
        """Test complete flow of creating a node"""
        # Start with empty state
        assert len(app.state.nodes) == 0
        
        # Create node through UI
        app.toolbar.add_node_button.click()
        dialog = app.get_active_dialog()
        dialog.name_field.value = "TestNode"
        dialog.ip_field.value = "10.0.0.1/24"
        dialog.ok_button.click()
        
        # Verify node created
        assert len(app.state.nodes) == 1
        node = list(app.state.nodes.values())[0]
        assert node.name == "TestNode"
        
        # Verify graph updated
        assert len(app.graph.nodes) == 1
        
        # Verify can undo
        app.toolbar.undo_button.click()
        assert len(app.state.nodes) == 0
    
    def test_import_export_cycle(self, app):
        """Test importing and exporting configuration"""
        # Import test configuration
        yaml_content = """
        nodes:
          office:
            - name: PC1
              wireguard_ip: 10.0.0.1/24
        """
        app.import_yaml(yaml_content)
        
        # Verify imported correctly
        assert len(app.state.nodes) == 1
        
        # Export and verify
        exported = app.export_yaml()
        assert "PC1" in exported
        assert "10.0.0.1/24" in exported
    
    def test_group_operations(self, app):
        """Test group creation and management"""
        # Create nodes
        node1 = app.create_node("Node1", "10.0.0.1/24")
        node2 = app.create_node("Node2", "10.0.0.2/24")
        
        # Create group
        app.create_group("TestGroup", "mesh", [node1.id, node2.id])
        
        # Verify group created
        assert len(app.state.groups) == 1
        group = list(app.state.groups.values())[0]
        assert len(group.nodes) == 2
        
        # Verify mesh topology created edges
        edges = [e for e in app.state.edges.values() 
                if e.source_id in [node1.id, node2.id]]
        assert len(edges) == 2  # Bidirectional
```

### End-to-End Tests

```python
# tests/gui/test_e2e.py
import pytest
from playwright.sync_api import Page, expect

class TestE2E:
    def test_complete_workflow(self, page: Page):
        """Test complete workflow from creation to export"""
        # Navigate to app
        page.goto("http://localhost:8080")
        
        # Create a new configuration
        page.click("button:has-text('New')")
        
        # Add first node
        page.click("button:has-text('Add Node')")
        page.fill("input[placeholder='Node name']", "Office-Gateway")
        page.fill("input[placeholder='IP address']", "10.0.0.1/24")
        page.click("button:has-text('OK')")
        
        # Verify node appears in graph
        expect(page.locator("text=Office-Gateway")).to_be_visible()
        
        # Add second node
        page.click("button:has-text('Add Node')")
        page.fill("input[placeholder='Node name']", "Office-PC1")
        page.fill("input[placeholder='IP address']", "10.0.0.10/24")
        page.click("button:has-text('OK')")
        
        # Create connection by dragging
        gateway = page.locator("text=Office-Gateway")
        pc1 = page.locator("text=Office-PC1")
        gateway.drag_to(pc1)
        
        # Configure connection
        page.fill("input[placeholder='Allowed IPs']", "10.0.0.10/32")
        page.click("button:has-text('Apply')")
        
        # Export configuration
        page.click("button:has-text('Export')")
        page.click("text=Download YAML")
        
        # Verify download started
        download = page.wait_for_download()
        assert download.suggested_filename == "wireguard-config.yaml"
```

## Implementation Plan

### Phase 1: Foundation (Week 1)
1. **Day 1-2**: Project setup and core data models
   - Create directory structure
   - Implement base models with validation
   - Write comprehensive model tests

2. **Day 3-4**: State management and command pattern
   - Implement AppState and command classes
   - Add undo/redo functionality
   - Write state management tests

3. **Day 5**: Cytoscape.js integration
   - Create custom NiceGUI element
   - Implement basic graph operations
   - Test graph interactions

### Phase 2: Core UI (Week 2)
1. **Day 1-2**: Main application window and layout
   - Implement responsive layout
   - Add toolbar and panels
   - Create basic navigation

2. **Day 3-4**: Component implementation
   - Node tree with drag-and-drop
   - Properties panels
   - YAML/JSON editor

3. **Day 5**: Component integration
   - Wire up all components
   - Add event handling
   - Test UI interactions

### Phase 3: Business Logic (Week 3)
1. **Day 1-2**: Manager implementation
   - GraphManager for visualization
   - ConfigManager for import/export
   - ValidationManager for real-time validation

2. **Day 3-4**: Integration layer
   - Bridge to existing modules
   - Data transformation
   - Error handling

3. **Day 5**: Testing and refinement
   - Integration tests
   - Bug fixes
   - Performance optimization

### Phase 4: Advanced Features (Week 4)
1. **Day 1-2**: Advanced UI features
   - Dialogs and wizards
   - Auto-layout algorithms
   - Visual feedback

2. **Day 3-4**: Simulation and validation
   - Visual simulation integration
   - Advanced validation rules
   - Error visualization

3. **Day 5**: Deployment and documentation
   - Deployment scripts
   - User documentation
   - Final testing

## Development Guidelines

### 1. Test-Driven Development
- Write tests first for all new features
- Maintain >80% test coverage
- Use mocks for external dependencies
- Test both happy path and error cases

### 2. Code Organization
- One class per file
- Clear separation of concerns
- Use dependency injection
- Follow SOLID principles

### 3. Documentation
- Docstrings for all public methods
- Type hints for all parameters
- README for each module
- API documentation

### 4. Performance Considerations
- Lazy loading for large configurations
- Debounce graph updates
- Cache validation results
- Use virtual scrolling for lists

### 5. Security
- Input validation on all user data
- Sanitize file paths
- No eval() or exec() usage
- Secure WebSocket connections

## Next Steps

1. **Review and Approval**: Review this plan and provide feedback
2. **Environment Setup**: Set up development environment with NiceGUI
3. **Prototype**: Create minimal proof-of-concept
4. **Iterate**: Implement features incrementally with continuous testing

This plan provides a solid foundation for building a professional WireGuard visual configuration editor with comprehensive testing and clean architecture.