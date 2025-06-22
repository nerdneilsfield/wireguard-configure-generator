"""
Pytest configuration and common fixtures for GUI tests.

This module provides shared fixtures and configuration for all GUI tests.
"""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, MagicMock
from datetime import datetime

# Import interfaces for mocking
from wg_mesh_gen.gui.interfaces.base import IModel
from wg_mesh_gen.gui.interfaces.models import INodeModel, IEdgeModel, IGroupModel
from wg_mesh_gen.gui.interfaces.state import ICommand, IHistoryManager, IAppState
from wg_mesh_gen.gui.interfaces.managers import IGraphManager, IConfigManager, IValidationManager
from wg_mesh_gen.gui.interfaces.components import IComponent, ICytoscapeWidget
from wg_mesh_gen.gui.interfaces.events import Event, IEventEmitter


# ========== Configuration ==========

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_data_dir():
    """Provide path to test data directory."""
    return Path(__file__).parent / 'test_data'


# ========== Model Fixtures ==========

@pytest.fixture
def sample_node_data():
    """Provide sample node data."""
    return {
        'id': 'node-1',
        'name': 'TestNode',
        'wireguard_ip': '10.0.0.1/24',
        'endpoints': {'default': 'example.com:51820'},
        'role': 'client',
        'enable_ip_forward': False,
        'group_id': None,
        'position': {'x': 100, 'y': 200},
        'metadata': {},
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }


@pytest.fixture
def sample_edge_data():
    """Provide sample edge data."""
    return {
        'id': 'edge-1',
        'source_id': 'node-1',
        'target_id': 'node-2',
        'edge_type': 'peer',
        'allowed_ips': ['10.0.0.2/32'],
        'endpoint_name': None,
        'persistent_keepalive': None,
        'metadata': {},
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }


@pytest.fixture
def sample_group_data():
    """Provide sample group data."""
    return {
        'id': 'group-1',
        'name': 'TestGroup',
        'color': '#FF0000',
        'topology': 'mesh',
        'mesh_endpoint': None,
        'nodes': [],
        'metadata': {},
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }


@pytest.fixture
def mock_node_model(sample_node_data):
    """Create a mock node model with sample data."""
    mock = Mock(spec=INodeModel)
    for key, value in sample_node_data.items():
        setattr(mock, key, value)
    
    # Add methods
    mock.add_endpoint = Mock()
    mock.remove_endpoint = Mock()
    mock.get_endpoint = Mock(return_value=sample_node_data['endpoints'].get('default'))
    mock.validate = Mock(return_value=[])
    mock.is_valid = Mock(return_value=True)
    mock.to_dict = Mock(return_value=sample_node_data)
    mock.clone = Mock(return_value=mock)
    
    return mock


@pytest.fixture
def mock_edge_model(sample_edge_data):
    """Create a mock edge model with sample data."""
    mock = Mock(spec=IEdgeModel)
    for key, value in sample_edge_data.items():
        setattr(mock, key, value)
    
    # Add methods
    mock.is_bidirectional = Mock(return_value=False)
    mock.add_allowed_ip = Mock()
    mock.remove_allowed_ip = Mock()
    mock.get_direction = Mock(return_value=(sample_edge_data['source_id'], sample_edge_data['target_id']))
    mock.validate = Mock(return_value=[])
    mock.is_valid = Mock(return_value=True)
    mock.to_dict = Mock(return_value=sample_edge_data)
    mock.clone = Mock(return_value=mock)
    
    return mock


@pytest.fixture
def mock_group_model(sample_group_data):
    """Create a mock group model with sample data."""
    mock = Mock(spec=IGroupModel)
    for key, value in sample_group_data.items():
        setattr(mock, key, value)
    
    # Add methods
    mock.add_node = Mock()
    mock.remove_node = Mock()
    mock.has_node = Mock(return_value=False)
    mock.get_node_count = Mock(return_value=0)
    mock.validate = Mock(return_value=[])
    mock.is_valid = Mock(return_value=True)
    mock.to_dict = Mock(return_value=sample_group_data)
    mock.clone = Mock(return_value=mock)
    
    return mock


# ========== State Fixtures ==========

@pytest.fixture
def mock_command():
    """Create a mock command."""
    mock = Mock(spec=ICommand)
    mock.description = 'Test Command'
    mock.can_execute = Mock(return_value=True)
    mock.can_undo = Mock(return_value=True)
    mock.execute = Mock()
    mock.undo = Mock()
    return mock


@pytest.fixture
def mock_history_manager():
    """Create a mock history manager."""
    mock = Mock(spec=IHistoryManager)
    mock.can_undo = Mock(return_value=False)
    mock.can_redo = Mock(return_value=False)
    mock.history_limit = 100
    mock.execute = Mock()
    mock.undo = Mock(return_value=False)
    mock.redo = Mock(return_value=False)
    mock.clear = Mock()
    mock.get_undo_description = Mock(return_value=None)
    mock.get_redo_description = Mock(return_value=None)
    mock.begin_batch = Mock()
    mock.end_batch = Mock()
    return mock


@pytest.fixture
def mock_app_state(mock_history_manager):
    """Create a mock application state."""
    mock = Mock(spec=IAppState)
    mock.nodes = {}
    mock.edges = {}
    mock.groups = {}
    mock.selected_elements = set()
    mock.history = mock_history_manager
    mock.is_dirty = False
    mock.current_file = None
    
    # Add methods
    mock.add_node = Mock()
    mock.update_node = Mock()
    mock.remove_node = Mock()
    mock.add_edge = Mock()
    mock.update_edge = Mock()
    mock.remove_edge = Mock()
    mock.add_group = Mock()
    mock.update_group = Mock()
    mock.remove_group = Mock()
    mock.select_element = Mock()
    mock.deselect_element = Mock()
    mock.clear_selection = Mock()
    mock.set_selection = Mock()
    mock.mark_clean = Mock()
    mock.subscribe = Mock()
    mock.unsubscribe = Mock()
    mock.get_edges_for_node = Mock(return_value=[])
    mock.get_nodes_in_group = Mock(return_value=[])
    
    return mock


# ========== Manager Fixtures ==========

@pytest.fixture
def mock_graph_manager():
    """Create a mock graph manager."""
    mock = Mock(spec=IGraphManager)
    mock.create_node = Mock()
    mock.create_edge = Mock()
    mock.create_group = Mock()
    mock.auto_layout = Mock()
    mock.apply_group_topology = Mock(return_value=[])
    mock.validate_topology = Mock(return_value=[])
    mock.find_path = Mock(return_value=None)
    mock.get_subnet_conflicts = Mock(return_value=[])
    mock.suggest_ip_address = Mock(return_value=None)
    return mock


@pytest.fixture
def mock_config_manager():
    """Create a mock config manager."""
    mock = Mock(spec=IConfigManager)
    mock.load_configuration = Mock()
    mock.save_configuration = Mock()
    mock.import_nodes = Mock(return_value=[])
    mock.import_topology = Mock(return_value=[])
    mock.import_group_config = Mock(return_value=([], [], {}))
    mock.export_nodes = Mock()
    mock.export_topology = Mock()
    mock.export_group_config = Mock()
    mock.generate_wireguard_configs = Mock(return_value={})
    mock.validate_configuration = Mock(return_value=[])
    return mock


@pytest.fixture
def mock_validation_manager():
    """Create a mock validation manager."""
    mock = Mock(spec=IValidationManager)
    mock.validate_ip_address = Mock(return_value=None)
    mock.validate_endpoint = Mock(return_value=None)
    mock.validate_allowed_ips = Mock(return_value=[])
    mock.validate_node_name = Mock(return_value=None)
    mock.validate_group_topology = Mock(return_value=None)
    mock.check_ip_conflicts = Mock(return_value=None)
    mock.check_subnet_overlaps = Mock(return_value=False)
    return mock


# ========== Component Fixtures ==========

@pytest.fixture
def mock_cytoscape_widget():
    """Create a mock Cytoscape widget."""
    mock = Mock(spec=ICytoscapeWidget)
    mock.id = 'cytoscape-1'
    mock.visible = True
    mock.enabled = True
    
    # Add methods
    mock.add_node = Mock()
    mock.update_node = Mock()
    mock.delete_node = Mock()
    mock.add_edge = Mock()
    mock.update_edge = Mock()
    mock.delete_edge = Mock()
    mock.apply_layout = Mock()
    mock.fit_view = Mock()
    mock.get_elements = Mock(return_value={'nodes': [], 'edges': []})
    mock.clear = Mock()
    mock.set_style = Mock()
    mock.highlight_elements = Mock()
    mock.unhighlight_all = Mock()
    mock.export_image = Mock(return_value=b'')
    mock.render = Mock()
    mock.update = Mock()
    mock.destroy = Mock()
    
    # Event handlers
    mock.on_node_click = Mock()
    mock.on_edge_click = Mock()
    mock.on_canvas_click = Mock()
    mock.on_node_drag_end = Mock()
    mock.on_selection_change = Mock()
    
    return mock


# ========== Event Fixtures ==========

@pytest.fixture
def mock_event_emitter():
    """Create a mock event emitter."""
    mock = Mock(spec=IEventEmitter)
    mock.emit = Mock()
    mock.on = Mock()
    mock.off = Mock()
    mock.once = Mock()
    mock.emit_async = Mock()
    mock.has_listeners = Mock(return_value=False)
    mock.remove_all_listeners = Mock()
    return mock


@pytest.fixture
def sample_event():
    """Create a sample event."""
    return Event(
        name='test_event',
        source=Mock(),
        data={'test': 'data'},
        timestamp=datetime.now().timestamp()
    )


# ========== Test Data Generators ==========

def generate_nodes(count: int) -> List[Dict[str, Any]]:
    """Generate sample node data."""
    nodes = []
    for i in range(count):
        nodes.append({
            'id': f'node-{i+1}',
            'name': f'Node{i+1}',
            'wireguard_ip': f'10.0.0.{i+1}/24',
            'endpoints': {'default': f'node{i+1}.example.com:51820'},
            'role': 'relay' if i % 5 == 0 else 'client',
            'enable_ip_forward': i % 5 == 0,
            'group_id': f'group-{i // 3 + 1}' if i % 2 == 0 else None,
            'position': {'x': (i % 5) * 100, 'y': (i // 5) * 100},
            'metadata': {}
        })
    return nodes


def generate_edges(nodes: List[Dict[str, Any]], density: float = 0.3) -> List[Dict[str, Any]]:
    """Generate sample edge data based on nodes."""
    import random
    edges = []
    edge_id = 1
    
    for i, source in enumerate(nodes):
        for j, target in enumerate(nodes[i+1:], start=i+1):
            if random.random() < density:
                edges.append({
                    'id': f'edge-{edge_id}',
                    'source_id': source['id'],
                    'target_id': target['id'],
                    'edge_type': random.choice(['peer', 'mesh', 'relay']),
                    'allowed_ips': [f"{target['wireguard_ip'].split('/')[0]}/32"],
                    'endpoint_name': None,
                    'persistent_keepalive': 25 if random.random() < 0.3 else None,
                    'metadata': {}
                })
                edge_id += 1
    
    return edges


# ========== Assertion Helpers ==========

def assert_valid_ip(ip: str) -> None:
    """Assert that an IP address is valid."""
    import ipaddress
    try:
        ipaddress.ip_interface(ip)
    except ValueError:
        pytest.fail(f"Invalid IP address: {ip}")


def assert_valid_endpoint(endpoint: str) -> None:
    """Assert that an endpoint is valid."""
    parts = endpoint.rsplit(':', 1)
    assert len(parts) == 2, f"Invalid endpoint format: {endpoint}"
    
    host, port = parts
    assert host, "Host cannot be empty"
    assert port.isdigit(), f"Port must be numeric: {port}"
    assert 1 <= int(port) <= 65535, f"Port out of range: {port}"


def assert_valid_color(color: str) -> None:
    """Assert that a color is valid hex format."""
    import re
    assert re.match(r'^#[0-9A-Fa-f]{6}$', color), f"Invalid hex color: {color}"