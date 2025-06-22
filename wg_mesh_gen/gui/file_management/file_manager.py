"""
File manager implementation for handling file operations.

This module provides file upload, download, and management capabilities
for the GUI application.
"""

import os
import shutil
import tempfile
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, List, Any, Optional, BinaryIO
import json
import yaml
import mimetypes

from ..interfaces.file_management import IFileManager
from ..interfaces.state import IAppState
from ...logger import get_logger


class FileManager(IFileManager):
    """Implementation of IFileManager for file operations."""
    
    def __init__(self, upload_dir: Optional[str] = None):
        """
        Initialize the file manager.
        
        Args:
            upload_dir: Directory for storing uploaded files
        """
        self._logger = get_logger()
        
        # Create upload directory
        if upload_dir:
            self._upload_dir = Path(upload_dir)
        else:
            self._upload_dir = Path(tempfile.gettempdir()) / "wg_mesh_gen_uploads"
        
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        
        # File type mappings
        self._file_types = {
            'nodes': {
                'extensions': ['.yaml', '.yml', '.json'],
                'patterns': ['node', 'nodes'],
                'validator': self._validate_nodes_file
            },
            'topology': {
                'extensions': ['.yaml', '.yml', '.json'],
                'patterns': ['topo', 'topology', 'peer', 'peers'],
                'validator': self._validate_topology_file
            },
            'group_config': {
                'extensions': ['.yaml', '.yml', '.json'],
                'patterns': ['group', 'groups'],
                'validator': self._validate_group_file
            },
            'wg_keys': {
                'extensions': ['.json'],
                'patterns': ['key', 'keys', 'wg_key', 'wg_keys'],
                'validator': self._validate_keys_file
            },
            'wireguard': {
                'extensions': ['.conf'],
                'patterns': ['wg', 'wireguard'],
                'validator': None
            }
        }
    
    def upload_file(self, file_data: BinaryIO, filename: str) -> str:
        """
        Upload a file to temporary storage.
        
        Args:
            file_data: File data stream
            filename: Original filename
            
        Returns:
            Temporary file path
        """
        self._logger.info(f"Uploading file: {filename}")
        
        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        
        # Create unique file path
        temp_path = self._upload_dir / f"{os.urandom(8).hex()}_{safe_filename}"
        
        # Save file
        with open(temp_path, 'wb') as f:
            shutil.copyfileobj(file_data, f)
        
        self._logger.info(f"File uploaded to: {temp_path}")
        return str(temp_path)
    
    def download_file(self, file_path: str) -> BinaryIO:
        """
        Download a file from storage.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File data stream
        """
        self._logger.info(f"Downloading file: {file_path}")
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return open(path, 'rb')
    
    def delete_file(self, file_path: str) -> None:
        """
        Delete a file from storage.
        
        Args:
            file_path: Path to the file
        """
        self._logger.info(f"Deleting file: {file_path}")
        
        path = Path(file_path)
        if path.exists():
            path.unlink()
    
    def detect_file_type(self, file_path: str) -> str:
        """
        Detect the type of configuration file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File type identifier
        """
        self._logger.info(f"Detecting file type for: {file_path}")
        
        path = Path(file_path)
        filename = path.name.lower()
        extension = path.suffix.lower()
        
        # Check by filename patterns
        for file_type, config in self._file_types.items():
            for pattern in config['patterns']:
                if pattern in filename:
                    self._logger.info(f"Detected file type by pattern: {file_type}")
                    return file_type
        
        # Check by content
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Try to parse as YAML/JSON
            try:
                if extension in ['.yaml', '.yml']:
                    data = yaml.safe_load(content)
                elif extension == '.json':
                    data = json.loads(content)
                else:
                    # Try both
                    try:
                        data = yaml.safe_load(content)
                    except:
                        data = json.loads(content)
                
                # Detect by content structure
                if isinstance(data, dict):
                    if 'nodes' in data and isinstance(data['nodes'], list):
                        return 'nodes'
                    elif 'peers' in data and isinstance(data['peers'], list):
                        return 'topology'
                    elif 'groups' in data and isinstance(data['groups'], list):
                        return 'group_config'
                    elif all(key.endswith('_private_key') or key.endswith('_public_key') 
                            for key in data.keys()):
                        return 'wg_keys'
                
            except Exception as e:
                self._logger.debug(f"Failed to parse as YAML/JSON: {e}")
                
            # Check if it's a WireGuard config
            if '[Interface]' in content or '[Peer]' in content:
                return 'wireguard'
                
        except Exception as e:
            self._logger.error(f"Error detecting file type: {e}")
        
        return 'unknown'
    
    def validate_file(self, file_path: str, expected_type: Optional[str] = None) -> List[str]:
        """
        Validate a configuration file.
        
        Args:
            file_path: Path to the file
            expected_type: Expected file type
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Detect type if not specified
        if not expected_type:
            expected_type = self.detect_file_type(file_path)
            if expected_type == 'unknown':
                errors.append("Unable to detect file type")
                return errors
        
        # Get validator
        file_config = self._file_types.get(expected_type)
        if not file_config:
            errors.append(f"Unknown file type: {expected_type}")
            return errors
        
        validator = file_config['validator']
        if validator:
            try:
                validator_errors = validator(file_path)
                errors.extend(validator_errors)
            except Exception as e:
                errors.append(f"Validation error: {str(e)}")
        
        return errors
    
    def create_archive(self, files: Dict[str, str], archive_path: str, format: str = 'zip') -> str:
        """
        Create an archive containing multiple files.
        
        Args:
            files: Dictionary mapping archive paths to file paths
            archive_path: Path for the archive
            format: Archive format ('zip' or 'tar.gz')
            
        Returns:
            Path to created archive
        """
        self._logger.info(f"Creating {format} archive: {archive_path}")
        
        if format == 'zip':
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for archive_name, file_path in files.items():
                    zf.write(file_path, archive_name)
        
        elif format == 'tar.gz':
            with tarfile.open(archive_path, 'w:gz') as tf:
                for archive_name, file_path in files.items():
                    tf.add(file_path, arcname=archive_name)
        
        else:
            raise ValueError(f"Unsupported archive format: {format}")
        
        return archive_path
    
    def extract_archive(self, archive_path: str, extract_dir: str) -> List[str]:
        """
        Extract files from an archive.
        
        Args:
            archive_path: Path to the archive
            extract_dir: Directory to extract to
            
        Returns:
            List of extracted file paths
        """
        self._logger.info(f"Extracting archive: {archive_path}")
        
        extract_path = Path(extract_dir)
        extract_path.mkdir(parents=True, exist_ok=True)
        
        extracted_files = []
        
        # Detect archive type
        mime_type, _ = mimetypes.guess_type(archive_path)
        
        if archive_path.endswith('.zip') or mime_type == 'application/zip':
            with zipfile.ZipFile(archive_path, 'r') as zf:
                zf.extractall(extract_path)
                extracted_files = [str(extract_path / name) for name in zf.namelist()]
        
        elif archive_path.endswith(('.tar.gz', '.tgz')) or mime_type == 'application/x-gzip':
            with tarfile.open(archive_path, 'r:gz') as tf:
                tf.extractall(extract_path)
                extracted_files = [str(extract_path / member.name) for member in tf.getmembers()]
        
        else:
            raise ValueError(f"Unsupported archive format: {archive_path}")
        
        return extracted_files
    
    def get_temp_directory(self) -> str:
        """
        Get a temporary directory for file operations.
        
        Returns:
            Path to temporary directory
        """
        temp_dir = tempfile.mkdtemp(prefix="wg_mesh_gen_")
        self._logger.info(f"Created temporary directory: {temp_dir}")
        return temp_dir
    
    def cleanup_temp_files(self, older_than_seconds: int = 3600) -> None:
        """
        Clean up old temporary files.
        
        Args:
            older_than_seconds: Delete files older than this many seconds
        """
        self._logger.info(f"Cleaning up files older than {older_than_seconds} seconds")
        
        import time
        current_time = time.time()
        
        for file_path in self._upload_dir.iterdir():
            if file_path.is_file():
                age = current_time - file_path.stat().st_mtime
                if age > older_than_seconds:
                    try:
                        file_path.unlink()
                        self._logger.info(f"Deleted old file: {file_path}")
                    except Exception as e:
                        self._logger.error(f"Failed to delete {file_path}: {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename for safe storage."""
        # Remove path components
        filename = os.path.basename(filename)
        
        # Replace dangerous characters
        safe_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-')
        sanitized = ''.join(c if c in safe_chars else '_' for c in filename)
        
        # Ensure it has an extension
        if '.' not in sanitized:
            sanitized += '.unknown'
        
        return sanitized
    
    def _validate_nodes_file(self, file_path: str) -> List[str]:
        """Validate a nodes configuration file."""
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse file
            if file_path.endswith(('.yaml', '.yml')):
                data = yaml.safe_load(content)
            else:
                data = json.loads(content)
            
            # Check structure
            if not isinstance(data, dict):
                errors.append("File must contain a dictionary/object")
                return errors
            
            if 'nodes' not in data:
                errors.append("Missing 'nodes' field")
                return errors
            
            if not isinstance(data['nodes'], list):
                errors.append("'nodes' must be a list")
                return errors
            
            # Validate each node
            for i, node in enumerate(data['nodes']):
                if not isinstance(node, dict):
                    errors.append(f"Node {i}: must be a dictionary/object")
                    continue
                
                if 'name' not in node:
                    errors.append(f"Node {i}: missing required 'name' field")
                
                if 'role' in node and node['role'] not in ['client', 'relay']:
                    errors.append(f"Node {i}: invalid role '{node['role']}'")
            
        except Exception as e:
            errors.append(f"Failed to parse file: {str(e)}")
        
        return errors
    
    def _validate_topology_file(self, file_path: str) -> List[str]:
        """Validate a topology configuration file."""
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse file
            if file_path.endswith(('.yaml', '.yml')):
                data = yaml.safe_load(content)
            else:
                data = json.loads(content)
            
            # Check structure
            if not isinstance(data, dict):
                errors.append("File must contain a dictionary/object")
                return errors
            
            if 'peers' not in data:
                errors.append("Missing 'peers' field")
                return errors
            
            if not isinstance(data['peers'], list):
                errors.append("'peers' must be a list")
                return errors
            
            # Validate each peer
            for i, peer in enumerate(data['peers']):
                if not isinstance(peer, dict):
                    errors.append(f"Peer {i}: must be a dictionary/object")
                    continue
                
                if 'from' not in peer:
                    errors.append(f"Peer {i}: missing required 'from' field")
                
                if 'to' not in peer:
                    errors.append(f"Peer {i}: missing required 'to' field")
            
        except Exception as e:
            errors.append(f"Failed to parse file: {str(e)}")
        
        return errors
    
    def _validate_group_file(self, file_path: str) -> List[str]:
        """Validate a group configuration file."""
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse file
            if file_path.endswith(('.yaml', '.yml')):
                data = yaml.safe_load(content)
            else:
                data = json.loads(content)
            
            # Check structure
            if not isinstance(data, dict):
                errors.append("File must contain a dictionary/object")
                return errors
            
            if 'groups' not in data:
                errors.append("Missing 'groups' field")
                return errors
            
            if not isinstance(data['groups'], list):
                errors.append("'groups' must be a list")
                return errors
            
            # Validate each group
            valid_topologies = ['mesh', 'star', 'chain', 'single']
            for i, group in enumerate(data['groups']):
                if not isinstance(group, dict):
                    errors.append(f"Group {i}: must be a dictionary/object")
                    continue
                
                if 'name' not in group:
                    errors.append(f"Group {i}: missing required 'name' field")
                
                if 'topology' not in group:
                    errors.append(f"Group {i}: missing required 'topology' field")
                elif group['topology'] not in valid_topologies:
                    errors.append(f"Group {i}: invalid topology '{group['topology']}'")
                
                if 'nodes' not in group:
                    errors.append(f"Group {i}: missing required 'nodes' field")
                elif not isinstance(group['nodes'], list):
                    errors.append(f"Group {i}: 'nodes' must be a list")
            
        except Exception as e:
            errors.append(f"Failed to parse file: {str(e)}")
        
        return errors
    
    def _validate_keys_file(self, file_path: str) -> List[str]:
        """Validate a WireGuard keys file."""
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Must be JSON
            try:
                data = json.loads(content)
            except:
                errors.append("Keys file must be valid JSON")
                return errors
            
            # Check structure
            if not isinstance(data, dict):
                errors.append("File must contain a dictionary/object")
                return errors
            
            # Validate each key entry
            for key, value in data.items():
                if not key.endswith('_private_key') and not key.endswith('_public_key'):
                    errors.append(f"Invalid key name: {key}")
                
                if not isinstance(value, str):
                    errors.append(f"Key value for '{key}' must be a string")
                elif len(value) != 44:  # Base64 encoded 32-byte key
                    errors.append(f"Key '{key}' has invalid length")
            
        except Exception as e:
            errors.append(f"Failed to parse file: {str(e)}")
        
        return errors