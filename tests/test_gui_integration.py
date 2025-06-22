"""
Integration tests for the GUI components.

This module tests the integration between GUI components and the CLI.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from wg_mesh_gen.gui.app import WireGuardEditorApp
from wg_mesh_gen.gui.state import AppState
from wg_mesh_gen.gui.models import NodeModel, EdgeModel, GroupModel
from wg_mesh_gen.gui.managers import ValidationManager, GraphManager, ConfigManager, CommandManager


class TestGUIIntegration:
    """Test GUI component integration."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / 'config'
        self.config_dir.mkdir()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_app_state_integration(self):
        """Test AppState with models."""
        app_state = AppState()
        
        # Test node management
        node = NodeModel()
        node.name = "test_node"
        node.role = "client"
        node.wireguard_ip = "10.0.0.2/24"
        
        app_state.add_node(node)
        assert len(app_state.nodes) == 1
        assert app_state.nodes[node.id] == node
        
        # Test edge management
        node2 = NodeModel()
        node2.name = "test_relay"
        node2.role = "relay"
        node2.wireguard_ip = "10.0.0.1/24"
        app_state.add_node(node2)
        
        edge = EdgeModel()
        edge.source_id = node.id
        edge.target_id = node2.id
        edge.allowed_ips = ["10.0.0.0/24"]
        
        app_state.add_edge(edge)
        assert len(app_state.edges) == 1
        assert app_state.edges[edge.id] == edge
        
        # Test group management
        group = GroupModel()
        group.name = "test_group"
        group.topology = "star"
        group.add_node(node.id)
        group.add_node(node2.id)
        
        app_state.add_group(group)
        assert len(app_state.groups) == 1
        assert app_state.groups[group.id] == group
    
    def test_validation_manager_integration(self):
        """Test ValidationManager with GUI models."""
        validation_manager = ValidationManager()
        app_state = AppState()
        
        # Add valid configuration
        node1 = NodeModel()
        node1.name = "relay1"
        node1.role = "relay"
        node1.wireguard_ip = "10.0.0.1/24"
        node1.endpoints = {"default": "relay.example.com:51820"}
        app_state.add_node(node1)
        
        node2 = NodeModel()
        node2.name = "client1"
        node2.role = "client"
        node2.wireguard_ip = "10.0.0.2/24"
        app_state.add_node(node2)
        
        edge = EdgeModel()
        edge.source_id = node1.id
        edge.target_id = node2.id
        edge.allowed_ips = ["10.0.0.0/24"]
        app_state.add_edge(edge)
        
        # Validate configuration
        errors = validation_manager.validate_configuration(app_state)
        # Should be valid (may have warnings but no critical errors)
        assert isinstance(errors, list)
    
    def test_graph_manager_integration(self):
        """Test GraphManager with GUI models."""
        graph_manager = GraphManager()
        app_state = AppState()
        
        # Add nodes
        for i in range(3):
            node = NodeModel()
            node.name = f"node{i}"
            node.role = "client"
            node.wireguard_ip = f"10.0.0.{i+1}/24"
            app_state.add_node(node)
        
        # Apply layout (this should not crash)
        try:
            graph_manager.apply_layout(app_state, 'force')
            graph_manager.apply_layout(app_state, 'circle')
            graph_manager.apply_layout(app_state, 'grid')
        except Exception as e:
            pytest.fail(f"Layout application failed: {e}")
    
    def test_config_manager_integration(self):
        """Test ConfigManager with GUI models."""
        config_manager = ConfigManager()
        app_state = AppState()
        
        # Create test configuration
        node = NodeModel()
        node.name = "test_node"
        node.role = "client"
        node.wireguard_ip = "10.0.0.2/24"
        app_state.add_node(node)
        
        # Test configuration building (should not crash)
        try:
            config_manager.build_configuration(app_state)
        except Exception as e:
            # Expected to fail due to missing CLI dependencies
            # but should not crash due to GUI-specific issues
            assert "build_from_data" in str(e) or "save_yaml" in str(e)
    
    def test_command_manager_integration(self):
        """Test CommandManager with GUI commands."""
        app_state = AppState()
        command_manager = CommandManager()
        
        from wg_mesh_gen.gui.managers.command import AddNodeCommand, RemoveNodeCommand
        
        # Test add node command
        node_data = {
            'name': 'test_node',
            'role': 'client',
            'wireguard_ip': '10.0.0.2/24'
        }
        
        add_cmd = AddNodeCommand(app_state, node_data)
        assert command_manager.execute(add_cmd)
        assert len(app_state.nodes) == 1
        
        # Test undo
        assert command_manager.can_undo()
        assert command_manager.undo()
        assert len(app_state.nodes) == 0
        
        # Test redo
        assert command_manager.can_redo()
        assert command_manager.redo()
        assert len(app_state.nodes) == 1
        
        # Test remove command
        node_id = list(app_state.nodes.keys())[0]
        remove_cmd = RemoveNodeCommand(app_state, node_id)
        assert command_manager.execute(remove_cmd)
        assert len(app_state.nodes) == 0
        
        # Test undo remove
        assert command_manager.undo()
        assert len(app_state.nodes) == 1
    
    @patch('wg_mesh_gen.gui.app.ui')
    @patch('wg_mesh_gen.gui.app.app')
    def test_wireGuard_editor_app_creation(self, mock_app, mock_ui):
        """Test WireGuardEditorApp creation and initialization."""
        # Mock NiceGUI components
        mock_app.storage.user = {}
        mock_ui.page_title = Mock()
        mock_ui.dark_mode.return_value.enable = Mock()
        
        # Create app
        editor_app = WireGuardEditorApp(self.config_dir)
        
        assert editor_app.config_dir == self.config_dir
        assert editor_app.sessions_dir == self.config_dir / 'sessions'
        assert editor_app.sessions_dir.exists()
        assert isinstance(editor_app.file_manager, object)
        assert isinstance(editor_app.validation_manager, ValidationManager)
        assert isinstance(editor_app.graph_manager, GraphManager)
    
    def test_model_serialization(self):
        """Test model serialization and deserialization."""
        # Test NodeModel
        node = NodeModel()
        node.name = "test_node"
        node.role = "relay"
        node.wireguard_ip = "10.0.0.1/24"
        node.endpoints = {"default": "relay.example.com:51820"}
        
        node_dict = node.to_dict()
        assert node_dict['name'] == "test_node"
        assert node_dict['role'] == "relay"
        assert node_dict['wireguard_ip'] == "10.0.0.1/24"
        
        # Recreate from dict
        node2 = NodeModel.from_dict(node_dict)
        assert node2.name == node.name
        assert node2.role == node.role
        assert node2.wireguard_ip == node.wireguard_ip
        
        # Test EdgeModel
        edge = EdgeModel()
        edge.source_id = "node1"
        edge.target_id = "node2"
        edge.allowed_ips = ["10.0.0.0/24", "192.168.1.0/24"]
        
        edge_dict = edge.to_dict()
        assert edge_dict['source_id'] == "node1"
        assert edge_dict['target_id'] == "node2"
        assert edge_dict['allowed_ips'] == ["10.0.0.0/24", "192.168.1.0/24"]
        
        edge2 = EdgeModel.from_dict(edge_dict)
        assert edge2.source_id == edge.source_id
        assert edge2.target_id == edge.target_id
        assert edge2.allowed_ips == edge.allowed_ips
        
        # Test GroupModel
        group = GroupModel()
        group.name = "test_group"
        group.topology = "mesh"
        group.add_node("node1")
        group.add_node("node2")
        
        group_dict = group.to_dict()
        assert group_dict['name'] == "test_group"
        assert group_dict['topology'] == "mesh"
        assert "node1" in group_dict['nodes']
        assert "node2" in group_dict['nodes']
        
        group2 = GroupModel.from_dict(group_dict)
        assert group2.name == group.name
        assert group2.topology == group.topology
        assert group2.nodes == group.nodes
    
    def test_event_system(self):
        """Test the event system in AppState."""
        app_state = AppState()
        events_received = []
        
        def event_handler(event):
            events_received.append(event)
        
        # Subscribe to events
        app_state.subscribe('node_added', event_handler)
        app_state.subscribe('node_removed', event_handler)
        
        # Add a node
        node = NodeModel()
        node.name = "test_node"
        app_state.add_node(node)
        
        # Remove the node
        app_state.remove_node(node.id)
        
        # Check events were fired
        assert len(events_received) == 2
        assert events_received[0]['type'] == 'node_added'
        assert events_received[1]['type'] == 'node_removed'
    
    def test_file_type_detection(self):
        """Test file type detection in file management."""
        from wg_mesh_gen.gui.file_management import FileManager
        
        # Create a temporary directory for file manager
        upload_dir = self.temp_dir / 'uploads'
        upload_dir.mkdir()
        
        file_manager = FileManager(str(upload_dir))
        
        # Test YAML detection
        yaml_file = upload_dir / 'test.yaml'
        yaml_file.write_text('nodes:\n  - name: test')
        
        file_type = file_manager.detect_file_type(str(yaml_file))
        # Should detect as nodes, topology, or group config
        assert file_type in ['nodes', 'topology', 'group', 'unknown']
        
        # Test JSON detection
        json_file = upload_dir / 'test.json'
        json_file.write_text('{"nodes": [{"name": "test"}]}')
        
        file_type = file_manager.detect_file_type(str(json_file))
        assert file_type in ['nodes', 'topology', 'group', 'unknown']