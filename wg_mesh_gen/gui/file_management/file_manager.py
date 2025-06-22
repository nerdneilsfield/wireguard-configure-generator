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
from typing import Dict, List, Any, Optional, BinaryIO, Tuple
import json
import yaml
import mimetypes

from ..interfaces.file_management import IFileManager, FileType
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
    
    def _detect_file_type_str(self, file_path: str) -> str:
        """
        Detect the type of configuration file using ConfigAdapter.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File type identifier
        """
        self._logger.info(f"Detecting file type for: {file_path}")
        
        path = Path(file_path)
        
        # Special cases based on extension
        if path.suffix == '.conf':
            return 'wireguard'
        
        # Special case for keys based on filename
        if 'key' in path.name.lower():
            return 'wg_keys'
        
        # Use ConfigAdapter for standard formats
        try:
            from ...adapters import ConfigAdapter
            config_adapter = ConfigAdapter(None)  # No CLI adapter needed for detection
            
            file_type = config_adapter.detect_file_type(path)
            
            # Map ConfigAdapter types to our internal types
            type_mapping = {
                'nodes': 'nodes',
                'topology': 'topology', 
                'group': 'group_config',
                'unknown': 'unknown'
            }
            
            return type_mapping.get(file_type, 'unknown')
            
        except Exception as e:
            self._logger.error(f"Error detecting file type: {e}")
            return 'unknown'
    
    def detect_file_type(self, file_path: Path) -> FileType:
        """Detect the type of uploaded file (interface method)."""
        str_type = self._detect_file_type_str(str(file_path))
        type_mapping = {
            'nodes': FileType.NODES_CONFIG,
            'topology': FileType.TOPOLOGY_CONFIG,
            'group_config': FileType.GROUP_CONFIG,
            'wg_keys': FileType.KEY_DATABASE,
            'wireguard': FileType.WIREGUARD_CONFIG,
            'unknown': FileType.UNKNOWN
        }
        return type_mapping.get(str_type, FileType.UNKNOWN)
    
    def validate_file(self, file_path: Path, file_type: FileType) -> List[str]:
        """Validate uploaded file content (interface method)."""
        # Map FileType enum to string
        type_mapping = {
            FileType.NODES_CONFIG: 'nodes',
            FileType.TOPOLOGY_CONFIG: 'topology',
            FileType.GROUP_CONFIG: 'group_config',
            FileType.KEY_DATABASE: 'wg_keys',
            FileType.WIREGUARD_CONFIG: 'wireguard'
        }
        expected_type = type_mapping.get(file_type)
        return self._validate_file_impl(str(file_path), expected_type)
    
    def _validate_file_impl(self, file_path: str, expected_type: Optional[str] = None) -> List[str]:
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
            expected_type = self._detect_file_type_str(file_path)
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
        """Validate a nodes configuration file using CLI validators."""
        errors = []
        
        try:
            from ...adapters import ConfigAdapter, CLIAdapter
            config_adapter = ConfigAdapter(CLIAdapter())
            
            # Use CLI loader which includes validation
            nodes = config_adapter.load_nodes_file(Path(file_path))
            
            # If we got here, the file is valid
            self._logger.info(f"Successfully validated nodes file with {len(nodes)} nodes")
            
        except Exception as e:
            errors.append(f"Validation failed: {str(e)}")
        
        return errors
    
    def _validate_topology_file(self, file_path: str) -> List[str]:
        """Validate a topology configuration file using CLI validators."""
        errors = []
        
        try:
            from ...adapters import ConfigAdapter, CLIAdapter
            config_adapter = ConfigAdapter(CLIAdapter())
            
            # Use CLI loader which includes validation
            edges = config_adapter.load_topology_file(Path(file_path))
            
            # If we got here, the file is valid
            self._logger.info(f"Successfully validated topology file with {len(edges)} edges")
            
        except Exception as e:
            errors.append(f"Validation failed: {str(e)}")
        
        return errors
    
    def _validate_group_file(self, file_path: str) -> List[str]:
        """Validate a group configuration file using CLI validators."""
        errors = []
        
        try:
            from ...adapters import ConfigAdapter, CLIAdapter
            config_adapter = ConfigAdapter(CLIAdapter())
            
            # Use CLI loader which includes validation
            nodes, edges, groups = config_adapter.load_group_configuration(Path(file_path))
            
            # If we got here, the file is valid
            self._logger.info(f"Successfully validated group file with {len(groups)} groups")
            
        except Exception as e:
            errors.append(f"Validation failed: {str(e)}")
        
        return errors
    
    def _validate_keys_file(self, file_path: str) -> List[str]:
        """Validate a WireGuard keys file."""
        errors = []
        
        try:
            from ...adapters import ConfigAdapter, CLIAdapter
            config_adapter = ConfigAdapter(CLIAdapter())
            
            # Load and validate structure
            data = config_adapter.load_json_file(Path(file_path))
            
            if not isinstance(data, dict):
                errors.append("Keys file must contain a dictionary")
                return errors
            
            # Validate each entry  
            for node_name, key_data in data.items():
                if not isinstance(key_data, dict):
                    errors.append(f"Key data for '{node_name}' must be a dictionary")
                    continue
                
                if 'private_key' not in key_data:
                    errors.append(f"Missing 'private_key' for node '{node_name}'")
                
                if 'public_key' not in key_data:
                    errors.append(f"Missing 'public_key' for node '{node_name}'")
            
            if not errors:
                self._logger.info(f"Successfully validated keys file with {len(data)} entries")
            
        except Exception as e:
            errors.append(f"Failed to validate keys file: {str(e)}")
        
        return errors
    
    # Interface method implementations for IFileManager
    
    def save_uploaded_file(self, file_data: BinaryIO, filename: str) -> Path:
        """Save uploaded file to temporary location."""
        file_path = self.upload_file(file_data, filename)
        return Path(file_path)
    
    def create_download_file(self, content: str, filename: str, 
                           content_type: str = 'text/plain') -> Tuple[Path, str]:
        """Create a file for download."""
        temp_path = Path(self.get_temp_directory()) / filename
        temp_path.write_text(content, encoding='utf-8')
        return temp_path, content_type
    
    def create_zip_archive(self, files: Dict[str, str], archive_name: str) -> Path:
        """Create a ZIP archive of multiple files."""
        temp_dir = Path(self.get_temp_directory())
        archive_path = temp_dir / archive_name
        
        # Write files to temp directory
        file_paths = {}
        for filename, content in files.items():
            file_path = temp_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            file_paths[filename] = str(file_path)
        
        # Create archive
        self.create_archive(file_paths, str(archive_path), format='zip')
        return archive_path
    
    def cleanup_temporary_files(self, session_id: str) -> None:
        """Clean up temporary files for a session."""
        # For now, just call the general cleanup
        self.cleanup_temp_files(older_than_seconds=0)
    
    def get_file_size_limit(self) -> int:
        """Get maximum allowed file size in bytes."""
        return 10 * 1024 * 1024  # 10 MB
    
    def is_allowed_extension(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        allowed_extensions = {'.yaml', '.yml', '.json', '.conf', '.txt'}
        return Path(filename).suffix.lower() in allowed_extensions