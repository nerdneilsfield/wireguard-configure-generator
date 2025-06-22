"""
Export manager implementation for configuration export functionality.

This module provides capabilities to export configurations in various formats
and package them for distribution.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from ..interfaces.file_management import IExportManager
from ..interfaces.state import IAppState
from ..interfaces.managers import IConfigManager
from .file_manager import FileManager
from ...render import ConfigRenderer
from ...builder import build_from_data
from ...group_network_builder import GroupNetworkBuilder
from ...simple_storage import SimpleKeyStorage as SimpleStorage
from ...logger import get_logger


class ExportManager(IExportManager):
    """Implementation of IExportManager for configuration export."""
    
    def __init__(self,
                 file_manager: FileManager,
                 config_manager: IConfigManager):
        """
        Initialize the export manager.
        
        Args:
            file_manager: File manager instance
            config_manager: Configuration manager instance
        """
        self._logger = get_logger()
        self._file_manager = file_manager
        self._config_manager = config_manager
        
        # Export formats configuration
        self._export_formats = {
            'nodes_yaml': {
                'name': 'Nodes Configuration (YAML)',
                'extension': '.yaml',
                'exporter': self._export_nodes_yaml
            },
            'nodes_json': {
                'name': 'Nodes Configuration (JSON)',
                'extension': '.json',
                'exporter': self._export_nodes_json
            },
            'topology_yaml': {
                'name': 'Topology Configuration (YAML)',
                'extension': '.yaml',
                'exporter': self._export_topology_yaml
            },
            'topology_json': {
                'name': 'Topology Configuration (JSON)',
                'extension': '.json',
                'exporter': self._export_topology_json
            },
            'group_yaml': {
                'name': 'Group Configuration (YAML)',
                'extension': '.yaml',
                'exporter': self._export_group_yaml
            },
            'group_json': {
                'name': 'Group Configuration (JSON)',
                'extension': '.json',
                'exporter': self._export_group_json
            },
            'wireguard': {
                'name': 'WireGuard Configurations',
                'extension': '.conf',
                'exporter': self._export_wireguard_configs
            },
            'complete_package': {
                'name': 'Complete Configuration Package',
                'extension': '.zip',
                'exporter': self._export_complete_package
            }
        }
    
    def export_nodes(self, app_state: IAppState, format: str = 'yaml') -> str:
        """
        Export nodes configuration.
        
        Args:
            app_state: Application state
            format: Export format ('yaml' or 'json')
            
        Returns:
            Path to exported file
        """
        export_key = f'nodes_{format}'
        if export_key not in self._export_formats:
            raise ValueError(f"Unsupported format: {format}")
        
        return self._export_formats[export_key]['exporter'](app_state)
    
    def export_topology(self, app_state: IAppState, format: str = 'yaml') -> str:
        """
        Export topology configuration.
        
        Args:
            app_state: Application state
            format: Export format ('yaml' or 'json')
            
        Returns:
            Path to exported file
        """
        export_key = f'topology_{format}'
        if export_key not in self._export_formats:
            raise ValueError(f"Unsupported format: {format}")
        
        return self._export_formats[export_key]['exporter'](app_state)
    
    def export_groups(self, app_state: IAppState, format: str = 'yaml') -> str:
        """
        Export groups configuration.
        
        Args:
            app_state: Application state
            format: Export format ('yaml' or 'json')
            
        Returns:
            Path to exported file
        """
        export_key = f'group_{format}'
        if export_key not in self._export_formats:
            raise ValueError(f"Unsupported format: {format}")
        
        return self._export_formats[export_key]['exporter'](app_state)
    
    def export_wireguard_configs(self, app_state: IAppState, output_dir: str) -> List[str]:
        """
        Export WireGuard configuration files.
        
        Args:
            app_state: Application state
            output_dir: Output directory
            
        Returns:
            List of generated file paths
        """
        return self._export_wireguard_configs(app_state, output_dir)
    
    def export_complete(self, app_state: IAppState, include_configs: bool = True) -> str:
        """
        Export complete configuration package.
        
        Args:
            app_state: Application state
            include_configs: Include generated WireGuard configs
            
        Returns:
            Path to archive file
        """
        return self._export_complete_package(app_state, include_configs)
    
    def get_export_formats(self) -> Dict[str, str]:
        """
        Get available export formats.
        
        Returns:
            Dictionary of format ID to description
        """
        return {
            format_id: format_info['name']
            for format_id, format_info in self._export_formats.items()
        }
    
    def _export_nodes_yaml(self, app_state: IAppState) -> str:
        """Export nodes as YAML."""
        data = self._config_manager.export_configuration(app_state)
        nodes_data = data.get('nodes', {})
        
        # Create temp file
        temp_dir = self._file_manager.get_temp_directory()
        output_path = Path(temp_dir) / "nodes.yaml"
        
        # Save using YAML
        import yaml
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(nodes_data, f, default_flow_style=False, allow_unicode=True)
        
        self._logger.info(f"Exported nodes to YAML: {output_path}")
        return str(output_path)
    
    def _export_nodes_json(self, app_state: IAppState) -> str:
        """Export nodes as JSON."""
        data = self._config_manager.export_configuration(app_state)
        nodes_data = data.get('nodes', {})
        
        # Create temp file
        temp_dir = self._file_manager.get_temp_directory()
        output_path = Path(temp_dir) / "nodes.json"
        
        # Save using JSON
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(nodes_data, f, indent=2, ensure_ascii=False)
        
        self._logger.info(f"Exported nodes to JSON: {output_path}")
        return str(output_path)
    
    def _export_topology_yaml(self, app_state: IAppState) -> str:
        """Export topology as YAML."""
        data = self._config_manager.export_configuration(app_state)
        topology_data = data.get('topology', {})
        
        # Create temp file
        temp_dir = self._file_manager.get_temp_directory()
        output_path = Path(temp_dir) / "topology.yaml"
        
        # Save using YAML
        import yaml
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(topology_data, f, default_flow_style=False, allow_unicode=True)
        
        self._logger.info(f"Exported topology to YAML: {output_path}")
        return str(output_path)
    
    def _export_topology_json(self, app_state: IAppState) -> str:
        """Export topology as JSON."""
        data = self._config_manager.export_configuration(app_state)
        topology_data = data.get('topology', {})
        
        # Create temp file
        temp_dir = self._file_manager.get_temp_directory()
        output_path = Path(temp_dir) / "topology.json"
        
        # Save using JSON
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(topology_data, f, indent=2, ensure_ascii=False)
        
        self._logger.info(f"Exported topology to JSON: {output_path}")
        return str(output_path)
    
    def _export_group_yaml(self, app_state: IAppState) -> str:
        """Export groups as YAML."""
        data = self._config_manager.export_configuration(app_state)
        groups_data = data.get('groups', {})
        
        # Create temp file
        temp_dir = self._file_manager.get_temp_directory()
        output_path = Path(temp_dir) / "group_config.yaml"
        
        # Save using YAML
        import yaml
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(groups_data, f, default_flow_style=False, allow_unicode=True)
        
        self._logger.info(f"Exported groups to YAML: {output_path}")
        return str(output_path)
    
    def _export_group_json(self, app_state: IAppState) -> str:
        """Export groups as JSON."""
        data = self._config_manager.export_configuration(app_state)
        groups_data = data.get('groups', {})
        
        # Create temp file
        temp_dir = self._file_manager.get_temp_directory()
        output_path = Path(temp_dir) / "group_config.json"
        
        # Save using JSON
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(groups_data, f, indent=2, ensure_ascii=False)
        
        self._logger.info(f"Exported groups to JSON: {output_path}")
        return str(output_path)
    
    def _export_wireguard_configs(self, app_state: IAppState, output_dir: Optional[str] = None) -> List[str]:
        """Export WireGuard configuration files."""
        # Use provided directory or create temp
        if not output_dir:
            output_dir = self._file_manager.get_temp_directory()
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Convert state to CLI format
        config_data = self._config_manager.export_configuration(app_state)
        nodes_list = config_data['nodes'].get('nodes', [])
        peers_list = config_data['topology'].get('peers', [])
        
        # Initialize key storage
        keys_file = output_path / "wg_keys.json"
        storage = SimpleStorage(str(keys_file))
        
        # Generate keys for nodes without them
        for node in app_state.nodes.values():
            if 'private_key' not in node.metadata or 'public_key' not in node.metadata:
                # Generate new keys
                private_key, public_key = self._generate_wireguard_keys()
                node.metadata['private_key'] = private_key
                node.metadata['public_key'] = public_key
                
                # Store keys
                storage.set(f"{node.name}_private_key", private_key)
                storage.set(f"{node.name}_public_key", public_key)
            else:
                # Store existing keys
                storage.set(f"{node.name}_private_key", node.metadata['private_key'])
                storage.set(f"{node.name}_public_key", node.metadata['public_key'])
        
        # Build full configuration
        nodes_data = {'nodes': nodes_list}
        topology_data = {'peers': peers_list}
        build_result = build_from_data(
            nodes_data, 
            topology_data, 
            output_dir=str(output_path),
            auto_generate_keys=False,  # We handle keys ourselves
            db_path=str(keys_file)
        )
        configs = build_result['configs']
        
        # Render configurations
        generated_files = []
        renderer = ConfigRenderer()
        
        for node_name, config in configs.items():
            config_file = output_path / f"{node_name}.conf"
            # Use renderer to create the config file
            renderer.render_config(node_name, config, str(output_path))
            generated_files.append(str(config_file))
            self._logger.info(f"Generated WireGuard config: {config_file}")
        
        # Also save the keys file
        generated_files.append(str(keys_file))
        
        return generated_files
    
    def _export_complete_package(self, app_state: IAppState, include_configs: bool = True) -> str:
        """Export complete configuration package."""
        # Create temporary directory for package contents
        package_dir = Path(self._file_manager.get_temp_directory())
        
        # Export all configuration files
        files_to_archive = {}
        
        # Export nodes configuration
        nodes_path = self._export_nodes_yaml(app_state)
        files_to_archive['nodes.yaml'] = nodes_path
        
        # Export topology if we have edges
        if app_state.edges:
            topology_path = self._export_topology_yaml(app_state)
            files_to_archive['topology.yaml'] = topology_path
        
        # Export groups if we have them
        if app_state.groups:
            groups_path = self._export_group_yaml(app_state)
            files_to_archive['group_config.yaml'] = groups_path
        
        # Generate and include WireGuard configs if requested
        if include_configs:
            wg_output_dir = package_dir / "wireguard_configs"
            wg_files = self._export_wireguard_configs(app_state, str(wg_output_dir))
            
            for wg_file in wg_files:
                relative_path = Path(wg_file).relative_to(package_dir)
                files_to_archive[str(relative_path)] = wg_file
        
        # Create README
        readme_path = package_dir / "README.txt"
        self._create_package_readme(readme_path, app_state, include_configs)
        files_to_archive['README.txt'] = str(readme_path)
        
        # Create archive
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"wireguard_config_{timestamp}.zip"
        archive_path = package_dir.parent / archive_name
        
        self._file_manager.create_archive(files_to_archive, str(archive_path), 'zip')
        
        self._logger.info(f"Created configuration package: {archive_path}")
        return str(archive_path)
    
    def _generate_wireguard_keys(self) -> tuple[str, str]:
        """Generate a WireGuard key pair."""
        import subprocess
        import base64
        
        try:
            # Try to use wg command
            private_key_proc = subprocess.run(
                ['wg', 'genkey'],
                capture_output=True,
                text=True,
                check=True
            )
            private_key = private_key_proc.stdout.strip()
            
            public_key_proc = subprocess.run(
                ['wg', 'pubkey'],
                input=private_key,
                capture_output=True,
                text=True,
                check=True
            )
            public_key = public_key_proc.stdout.strip()
            
            return private_key, public_key
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback: generate mock keys for demonstration
            # In production, you'd want proper key generation
            import secrets
            private_bytes = secrets.token_bytes(32)
            private_key = base64.b64encode(private_bytes).decode('ascii')
            
            # Mock public key (in reality, this would be derived from private key)
            public_bytes = secrets.token_bytes(32)
            public_key = base64.b64encode(public_bytes).decode('ascii')
            
            self._logger.warning("Using mock key generation - install wireguard-tools for proper keys")
            return private_key, public_key
    
    def _create_package_readme(self, readme_path: Path, app_state: IAppState, include_configs: bool) -> None:
        """Create a README file for the package."""
        content = [
            "WireGuard Configuration Package",
            "=" * 30,
            "",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Package Contents:",
            "-" * 20,
        ]
        
        # List configuration files
        content.append("- nodes.yaml: Node definitions")
        
        if app_state.edges:
            content.append("- topology.yaml: Network topology (peer connections)")
        
        if app_state.groups:
            content.append("- group_config.yaml: Group-based network configuration")
        
        if include_configs:
            content.extend([
                "- wireguard_configs/: Generated WireGuard configuration files",
                "  - *.conf: Individual node configurations",
                "  - wg_keys.json: WireGuard key storage",
            ])
        
        # Add statistics
        content.extend([
            "",
            "Configuration Summary:",
            "-" * 20,
            f"Total Nodes: {len(app_state.nodes)}",
            f"Total Connections: {len(app_state.edges)}",
            f"Total Groups: {len(app_state.groups)}",
        ])
        
        # Add usage instructions
        content.extend([
            "",
            "Usage Instructions:",
            "-" * 20,
            "1. To use the generated WireGuard configurations:",
            "   - Copy the .conf files to /etc/wireguard/",
            "   - Start WireGuard: wg-quick up <interface-name>",
            "",
            "2. To modify the configuration:",
            "   - Edit the YAML files as needed",
            "   - Regenerate using: python -m wg_mesh_gen.cli gen --nodes-file nodes.yaml --topo-file topology.yaml",
            "",
            "3. To import into the GUI:",
            "   - Use the Import Wizard in the WireGuard Visual Configuration Editor",
            "   - Select the appropriate YAML files",
        ])
        
        # Write README
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
    
    # Missing interface methods implementation
    
    def export_project_config(self, state: IAppState, format: str = 'yaml') -> Dict[str, str]:
        """Export current project configuration."""
        files = {}
        
        # Export nodes
        if state.nodes:
            filename = f'nodes.{format}'
            content = self.export_nodes(state, format)
            files[filename] = content
        
        # Export topology
        if state.edges:
            filename = f'topology.{format}'
            content = self.export_topology(state, format)
            files[filename] = content
        
        # Export groups if any
        if state.groups:
            filename = f'groups.{format}'
            content = self.export_groups(state, format)
            files[filename] = content
        
        return files
    
    def export_wireguard_configs(self, state: IAppState, 
                               include_scripts: bool = True) -> Dict[str, str]:
        """Generate and export WireGuard configurations."""
        files = {}
        
        # Generate configs using ConfigManager
        temp_dir = self._file_manager.get_temp_directory()
        config_files = self._config_manager.generate_wireguard_configs(state, Path(temp_dir))
        
        # Read generated files
        for node_name, file_path in config_files.items():
            content = file_path.read_text()
            files[f'{node_name}.conf'] = content
        
        # Include setup scripts if requested
        if include_scripts:
            files['setup.sh'] = self._generate_setup_script(state)
            files['teardown.sh'] = self._generate_teardown_script(state)
        
        return files
    
    def export_key_database(self, state: IAppState) -> str:
        """Export key database."""
        keys = {}
        
        # Extract keys from nodes
        for node in state.nodes.values():
            if 'private_key' in node.metadata or 'public_key' in node.metadata:
                keys[node.name] = {
                    'private_key': node.metadata.get('private_key', ''),
                    'public_key': node.metadata.get('public_key', '')
                }
        
        return json.dumps(keys, indent=2)
    
    def create_export_package(self, state: IAppState, 
                            options: Dict[str, bool]) -> Path:
        """Create complete export package."""
        # Create temporary directory for package
        temp_dir = Path(self._file_manager.get_temp_directory())
        package_dir = temp_dir / 'wireguard_config_export'
        package_dir.mkdir(exist_ok=True)
        
        # Export configurations if requested
        if options.get('include_config', True):
            config_files = self.export_project_config(state)
            for filename, content in config_files.items():
                (package_dir / filename).write_text(content)
        
        # Export WireGuard configs if requested
        if options.get('include_wireguard', True):
            wg_dir = package_dir / 'wireguard'
            wg_dir.mkdir(exist_ok=True)
            wg_files = self.export_wireguard_configs(state, include_scripts=True)
            for filename, content in wg_files.items():
                (wg_dir / filename).write_text(content)
        
        # Export keys if requested
        if options.get('include_keys', True):
            keys_content = self.export_key_database(state)
            (package_dir / 'wg_keys.json').write_text(keys_content)
        
        # Create README
        self._create_package_readme(package_dir / 'README.md', state, True)
        
        # Create ZIP archive
        archive_path = temp_dir / 'wireguard_config_export.zip'
        import shutil
        shutil.make_archive(str(archive_path.with_suffix('')), 'zip', package_dir)
        
        return archive_path
    
    def export_visualization(self, state: IAppState, 
                           format: str = 'png') -> bytes:
        """Export network visualization."""
        # This would integrate with the visualization component
        # For now, return empty bytes as placeholder
        self._logger.warning(f"Visualization export for format {format} not yet implemented")
        return b''
    
    def get_export_preview(self, state: IAppState, 
                         options: Dict[str, bool]) -> Dict[str, Any]:
        """Get preview of what will be exported."""
        preview = {
            'files': [],
            'total_size': 0,
            'node_count': len(state.nodes),
            'edge_count': len(state.edges),
            'group_count': len(state.groups)
        }
        
        # Preview configuration files
        if options.get('include_config', True):
            if state.nodes:
                preview['files'].append({'name': 'nodes.yaml', 'type': 'config'})
            if state.edges:
                preview['files'].append({'name': 'topology.yaml', 'type': 'config'})
            if state.groups:
                preview['files'].append({'name': 'groups.yaml', 'type': 'config'})
        
        # Preview WireGuard configs
        if options.get('include_wireguard', True):
            for node in state.nodes.values():
                preview['files'].append({'name': f'{node.name}.conf', 'type': 'wireguard'})
            preview['files'].append({'name': 'setup.sh', 'type': 'script'})
            preview['files'].append({'name': 'teardown.sh', 'type': 'script'})
        
        # Preview keys
        if options.get('include_keys', True):
            preview['files'].append({'name': 'wg_keys.json', 'type': 'keys'})
        
        # README is always included
        preview['files'].append({'name': 'README.md', 'type': 'documentation'})
        
        return preview
    
    def _generate_setup_script(self, state: IAppState) -> str:
        """Generate setup script for WireGuard interfaces."""
        lines = [
            "#!/bin/bash",
            "# WireGuard Setup Script",
            f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "set -e",
            "",
            "echo 'Setting up WireGuard interfaces...'",
            ""
        ]
        
        for node in state.nodes.values():
            lines.extend([
                f"# Setup {node.name}",
                f"echo 'Starting {node.name}...'",
                f"wg-quick up {node.name}",
                ""
            ])
        
        lines.append("echo 'All interfaces started successfully!'")
        return '\n'.join(lines)
    
    def _generate_teardown_script(self, state: IAppState) -> str:
        """Generate teardown script for WireGuard interfaces."""
        lines = [
            "#!/bin/bash",
            "# WireGuard Teardown Script",
            f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "echo 'Stopping WireGuard interfaces...'",
            ""
        ]
        
        for node in state.nodes.values():
            lines.extend([
                f"# Stop {node.name}",
                f"echo 'Stopping {node.name}...'",
                f"wg-quick down {node.name} || true",
                ""
            ])
        
        lines.append("echo 'All interfaces stopped!'")
        return '\n'.join(lines)