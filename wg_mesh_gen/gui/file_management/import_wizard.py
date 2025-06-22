"""
Import wizard implementation for guided configuration import.

This module provides a wizard interface for importing various configuration
files with validation and preview capabilities.
"""

from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field

from ..interfaces.file_management import IImportWizard
from ..interfaces.state import IAppState
from ..interfaces.managers import IValidationManager, IConfigManager
from .file_manager import FileManager
from ...logger import get_logger


@dataclass
class ImportSession:
    """Represents an import wizard session."""
    session_id: str
    files: Dict[str, str] = field(default_factory=dict)  # type -> file_path
    validated_data: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, List[str]] = field(default_factory=dict)
    warnings: Dict[str, List[str]] = field(default_factory=dict)
    preview_data: Optional[Dict[str, Any]] = None
    import_options: Dict[str, Any] = field(default_factory=dict)


class ImportWizard(IImportWizard):
    """Implementation of IImportWizard for guided import process."""
    
    def __init__(self, 
                 file_manager: FileManager,
                 config_manager: IConfigManager,
                 validation_manager: IValidationManager):
        """
        Initialize the import wizard.
        
        Args:
            file_manager: File manager instance
            config_manager: Configuration manager instance
            validation_manager: Validation manager instance
        """
        self._logger = get_logger()
        self._file_manager = file_manager
        self._config_manager = config_manager
        self._validation_manager = validation_manager
        self._sessions: Dict[str, ImportSession] = {}
    
    def start_import(self) -> str:
        """
        Start a new import session.
        
        Returns:
            Session ID
        """
        import uuid
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = ImportSession(session_id=session_id)
        self._logger.info(f"Started import session: {session_id}")
        return session_id
    
    def add_file(self, session_id: str, file_path: str, file_type: Optional[str] = None) -> None:
        """
        Add a file to the import session.
        
        Args:
            session_id: Import session ID
            file_path: Path to the file
            file_type: Optional file type hint
        """
        session = self._get_session(session_id)
        
        # Detect file type if not specified
        if not file_type:
            file_type = self._file_manager.detect_file_type(file_path)
            if file_type == 'unknown':
                raise ValueError(f"Unable to detect file type for: {file_path}")
        
        # Validate file
        errors = self._file_manager.validate_file(file_path, file_type)
        if errors:
            session.errors[file_type] = errors
            self._logger.warning(f"File validation errors for {file_type}: {errors}")
        
        # Store file
        session.files[file_type] = file_path
        self._logger.info(f"Added {file_type} file to session {session_id}: {file_path}")
    
    def validate_import(self, session_id: str) -> Dict[str, List[str]]:
        """
        Validate all files in the import session.
        
        Args:
            session_id: Import session ID
            
        Returns:
            Dictionary of validation results by file type
        """
        session = self._get_session(session_id)
        validation_results = {}
        
        # Clear previous validation
        session.errors.clear()
        session.warnings.clear()
        session.validated_data.clear()
        
        # Validate each file
        for file_type, file_path in session.files.items():
            self._logger.info(f"Validating {file_type} file: {file_path}")
            
            try:
                # Load and parse file
                if file_type == 'nodes':
                    data = self._config_manager.load_nodes_config(file_path)
                    session.validated_data['nodes'] = data
                    
                elif file_type == 'topology':
                    data = self._config_manager.load_topology_config(file_path)
                    session.validated_data['topology'] = data
                    
                elif file_type == 'group_config':
                    data = self._config_manager.load_group_config(file_path)
                    session.validated_data['groups'] = data
                    
                elif file_type == 'wg_keys':
                    # Load keys file
                    import json
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    session.validated_data['keys'] = data
                
                # Validate data
                errors = self._validation_manager.validate_import_data(
                    session.validated_data.get(file_type, {}), 
                    file_type
                )
                
                if errors:
                    session.errors[file_type] = errors
                    validation_results[file_type] = errors
                else:
                    validation_results[file_type] = []
                    
            except Exception as e:
                error_msg = f"Failed to validate {file_type}: {str(e)}"
                session.errors[file_type] = [error_msg]
                validation_results[file_type] = [error_msg]
                self._logger.error(error_msg)
        
        # Cross-file validation
        cross_errors = self._validate_cross_file_consistency(session)
        if cross_errors:
            session.errors['cross_validation'] = cross_errors
            validation_results['cross_validation'] = cross_errors
        
        return validation_results
    
    def preview_import(self, session_id: str) -> Dict[str, Any]:
        """
        Generate a preview of what will be imported.
        
        Args:
            session_id: Import session ID
            
        Returns:
            Preview data showing what will be imported
        """
        session = self._get_session(session_id)
        
        preview = {
            'nodes': [],
            'edges': [],
            'groups': [],
            'keys': {},
            'summary': {}
        }
        
        # Process nodes
        if 'nodes' in session.validated_data:
            nodes_data = session.validated_data['nodes']
            for node in nodes_data.get('nodes', []):
                preview['nodes'].append({
                    'name': node['name'],
                    'role': node.get('role', 'client'),
                    'has_endpoint': bool(node.get('endpoints')),
                    'has_wireguard_ip': bool(node.get('wireguard_ip'))
                })
        
        # Process topology
        if 'topology' in session.validated_data:
            topo_data = session.validated_data['topology']
            for peer in topo_data.get('peers', []):
                preview['edges'].append({
                    'from': peer['from'],
                    'to': peer['to'],
                    'has_allowed_ips': bool(peer.get('allowed_ips'))
                })
        
        # Process groups
        if 'groups' in session.validated_data:
            groups_data = session.validated_data['groups']
            for group in groups_data.get('groups', []):
                preview['groups'].append({
                    'name': group['name'],
                    'topology': group['topology'],
                    'node_count': len(group.get('nodes', []))
                })
        
        # Process keys
        if 'keys' in session.validated_data:
            keys_data = session.validated_data['keys']
            # Count key pairs
            private_keys = [k for k in keys_data if k.endswith('_private_key')]
            public_keys = [k for k in keys_data if k.endswith('_public_key')]
            preview['keys'] = {
                'private_key_count': len(private_keys),
                'public_key_count': len(public_keys),
                'nodes_with_keys': list(set(k.replace('_private_key', '').replace('_public_key', '') 
                                           for k in keys_data.keys()))
            }
        
        # Generate summary
        preview['summary'] = {
            'total_nodes': len(preview['nodes']),
            'total_edges': len(preview['edges']),
            'total_groups': len(preview['groups']),
            'has_keys': bool(preview['keys']),
            'import_mode': session.import_options.get('mode', 'replace')
        }
        
        session.preview_data = preview
        return preview
    
    def get_import_options(self, session_id: str) -> Dict[str, Any]:
        """
        Get available import options.
        
        Args:
            session_id: Import session ID
            
        Returns:
            Dictionary of import options
        """
        session = self._get_session(session_id)
        
        return {
            'mode': {
                'current': session.import_options.get('mode', 'replace'),
                'available': ['replace', 'merge', 'append'],
                'description': 'How to handle existing configuration'
            },
            'skip_validation': {
                'current': session.import_options.get('skip_validation', False),
                'description': 'Skip validation during import (not recommended)'
            },
            'auto_layout': {
                'current': session.import_options.get('auto_layout', True),
                'description': 'Automatically layout nodes after import'
            },
            'preserve_keys': {
                'current': session.import_options.get('preserve_keys', True),
                'description': 'Preserve existing WireGuard keys when merging'
            }
        }
    
    def set_import_option(self, session_id: str, option: str, value: Any) -> None:
        """
        Set an import option.
        
        Args:
            session_id: Import session ID
            option: Option name
            value: Option value
        """
        session = self._get_session(session_id)
        session.import_options[option] = value
        self._logger.info(f"Set import option {option} = {value} for session {session_id}")
    
    def execute_import(self, session_id: str, app_state: IAppState) -> bool:
        """
        Execute the import operation.
        
        Args:
            session_id: Import session ID
            app_state: Application state to import into
            
        Returns:
            True if successful
        """
        session = self._get_session(session_id)
        
        # Check for errors
        if session.errors and not session.import_options.get('skip_validation', False):
            self._logger.error(f"Cannot import due to validation errors: {session.errors}")
            return False
        
        try:
            import_mode = session.import_options.get('mode', 'replace')
            
            # Handle different import modes
            if import_mode == 'replace':
                # Clear existing state
                app_state.nodes.clear()
                app_state.edges.clear()
                app_state.groups.clear()
                app_state.clear_selection()
            
            # Import using config manager
            self._config_manager.import_from_cli(
                app_state,
                nodes_file=session.files.get('nodes'),
                topology_file=session.files.get('topology'),
                group_file=session.files.get('group_config')
            )
            
            # Import keys if provided
            if 'keys' in session.validated_data:
                self._import_keys(app_state, session.validated_data['keys'])
            
            # Auto-layout if requested
            if session.import_options.get('auto_layout', True):
                # This would be done through the GraphManager in the UI
                pass
            
            # Mark state as clean
            app_state.mark_clean()
            
            self._logger.info(f"Import completed successfully for session {session_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Import failed: {str(e)}")
            return False
    
    def cancel_import(self, session_id: str) -> None:
        """
        Cancel an import session.
        
        Args:
            session_id: Import session ID
        """
        if session_id in self._sessions:
            session = self._sessions[session_id]
            
            # Clean up temporary files
            for file_path in session.files.values():
                try:
                    Path(file_path).unlink(missing_ok=True)
                except Exception as e:
                    self._logger.warning(f"Failed to delete temp file {file_path}: {e}")
            
            # Remove session
            del self._sessions[session_id]
            self._logger.info(f"Cancelled import session: {session_id}")
    
    def _get_session(self, session_id: str) -> ImportSession:
        """Get an import session by ID."""
        if session_id not in self._sessions:
            raise ValueError(f"Invalid session ID: {session_id}")
        return self._sessions[session_id]
    
    def _validate_cross_file_consistency(self, session: ImportSession) -> List[str]:
        """Validate consistency across multiple files."""
        errors = []
        
        # Get all node names from different sources
        node_names_from_nodes = set()
        node_names_from_topology = set()
        node_names_from_groups = set()
        
        # Extract node names from nodes file
        if 'nodes' in session.validated_data:
            nodes_data = session.validated_data['nodes']
            for node in nodes_data.get('nodes', []):
                node_names_from_nodes.add(node['name'])
        
        # Extract node names from topology
        if 'topology' in session.validated_data:
            topo_data = session.validated_data['topology']
            for peer in topo_data.get('peers', []):
                node_names_from_topology.add(peer['from'])
                node_names_from_topology.add(peer['to'])
        
        # Extract node names from groups
        if 'groups' in session.validated_data:
            groups_data = session.validated_data['groups']
            for group in groups_data.get('groups', []):
                node_names_from_groups.update(group.get('nodes', []))
        
        # Cross-validation checks
        if node_names_from_nodes and node_names_from_topology:
            # Check topology references exist in nodes
            missing_in_nodes = node_names_from_topology - node_names_from_nodes
            if missing_in_nodes:
                errors.append(f"Topology references non-existent nodes: {', '.join(missing_in_nodes)}")
        
        if node_names_from_nodes and node_names_from_groups:
            # Check group references exist in nodes
            missing_in_nodes = node_names_from_groups - node_names_from_nodes
            if missing_in_nodes:
                errors.append(f"Groups reference non-existent nodes: {', '.join(missing_in_nodes)}")
        
        # If we have groups but no explicit nodes/topology, that's OK (groups will create them)
        if node_names_from_groups and not node_names_from_nodes and not node_names_from_topology:
            session.warnings['info'] = ["Group configuration will create nodes and topology"]
        
        # Check for conflicts between topology and groups
        if 'topology' in session.validated_data and 'groups' in session.validated_data:
            session.warnings['conflict'] = [
                "Both topology and group configurations provided. Group topology will take precedence."
            ]
        
        return errors
    
    def _import_keys(self, app_state: IAppState, keys_data: Dict[str, str]) -> None:
        """Import WireGuard keys into app state."""
        # Group keys by node name
        node_keys = {}
        
        for key_name, key_value in keys_data.items():
            if key_name.endswith('_private_key'):
                node_name = key_name[:-12]  # Remove '_private_key'
                if node_name not in node_keys:
                    node_keys[node_name] = {}
                node_keys[node_name]['private_key'] = key_value
            elif key_name.endswith('_public_key'):
                node_name = key_name[:-11]  # Remove '_public_key'
                if node_name not in node_keys:
                    node_keys[node_name] = {}
                node_keys[node_name]['public_key'] = key_value
        
        # Apply keys to nodes
        for node in app_state.nodes.values():
            if node.name in node_keys:
                keys = node_keys[node.name]
                if 'private_key' in keys:
                    node.metadata['private_key'] = keys['private_key']
                if 'public_key' in keys:
                    node.metadata['public_key'] = keys['public_key']
                
                self._logger.info(f"Imported keys for node: {node.name}")