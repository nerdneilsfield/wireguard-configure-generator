"""
File management interfaces for the GUI module.

These interfaces handle file upload, download, and format detection.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, Dict, List, Optional, Tuple, Any
from pathlib import Path
from enum import Enum


class FileType(Enum):
    """Supported file types for import/export."""
    NODES_CONFIG = "nodes"
    TOPOLOGY_CONFIG = "topology"
    GROUP_CONFIG = "group"
    KEY_DATABASE = "keys"
    WIREGUARD_CONFIG = "wireguard"
    UNKNOWN = "unknown"


class IFileManager(ABC):
    """Interface for file upload/download operations."""
    
    @abstractmethod
    def detect_file_type(self, file_path: Path) -> FileType:
        """
        Detect the type of uploaded file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected file type
        """
        pass
    
    @abstractmethod
    def validate_file(self, file_path: Path, file_type: FileType) -> List[str]:
        """
        Validate uploaded file content.
        
        Args:
            file_path: Path to the file
            file_type: Expected file type
            
        Returns:
            List of validation errors (empty if valid)
        """
        pass
    
    @abstractmethod
    def save_uploaded_file(self, file_data: BinaryIO, filename: str) -> Path:
        """
        Save uploaded file to temporary location.
        
        Args:
            file_data: File data stream
            filename: Original filename
            
        Returns:
            Path to saved temporary file
        """
        pass
    
    @abstractmethod
    def create_download_file(self, content: str, filename: str, 
                           content_type: str = 'text/plain') -> Tuple[Path, str]:
        """
        Create a file for download.
        
        Args:
            content: File content
            filename: Desired filename
            content_type: MIME type
            
        Returns:
            Tuple of (file path, content type)
        """
        pass
    
    @abstractmethod
    def create_zip_archive(self, files: Dict[str, str], archive_name: str) -> Path:
        """
        Create a ZIP archive of multiple files.
        
        Args:
            files: Dict mapping filenames to content
            archive_name: Name for the ZIP file
            
        Returns:
            Path to created ZIP file
        """
        pass
    
    @abstractmethod
    def cleanup_temporary_files(self, session_id: str) -> None:
        """
        Clean up temporary files for a session.
        
        Args:
            session_id: User session identifier
        """
        pass
    
    @abstractmethod
    def get_file_size_limit(self) -> int:
        """
        Get maximum allowed file size in bytes.
        
        Returns:
            Size limit in bytes
        """
        pass
    
    @abstractmethod
    def is_allowed_extension(self, filename: str) -> bool:
        """
        Check if file extension is allowed.
        
        Args:
            filename: Name of the file
            
        Returns:
            True if extension is allowed
        """
        pass


class IImportWizard(ABC):
    """Interface for guided import process."""
    
    @abstractmethod
    def start_import(self, file_paths: List[Path]) -> str:
        """
        Start import wizard with uploaded files.
        
        Args:
            file_paths: List of uploaded file paths
            
        Returns:
            Import session ID
        """
        pass
    
    @abstractmethod
    def detect_import_type(self, session_id: str) -> Dict[str, Any]:
        """
        Detect and analyze import configuration.
        
        Args:
            session_id: Import session ID
            
        Returns:
            Dict with detected configuration:
            - type: 'traditional' or 'group'
            - files: Dict of file types to paths
            - warnings: List of warnings
            - suggestions: List of suggestions
        """
        pass
    
    @abstractmethod
    def preview_import(self, session_id: str) -> Dict[str, Any]:
        """
        Generate preview of what will be imported.
        
        Args:
            session_id: Import session ID
            
        Returns:
            Preview data with nodes, edges, groups counts
        """
        pass
    
    @abstractmethod
    def execute_import(self, session_id: str, options: Dict[str, Any]) -> bool:
        """
        Execute the import with given options.
        
        Args:
            session_id: Import session ID
            options: Import options (merge/replace, key handling, etc.)
            
        Returns:
            True if import successful
        """
        pass
    
    @abstractmethod
    def get_import_errors(self, session_id: str) -> List[str]:
        """
        Get errors from import process.
        
        Args:
            session_id: Import session ID
            
        Returns:
            List of error messages
        """
        pass
    
    @abstractmethod
    def cleanup_import_session(self, session_id: str) -> None:
        """
        Clean up import session data.
        
        Args:
            session_id: Import session ID
        """
        pass


class IExportManager(ABC):
    """Interface for export and packaging operations."""
    
    @abstractmethod
    def export_project_config(self, state: 'IAppState', format: str = 'yaml') -> Dict[str, str]:
        """
        Export current project configuration.
        
        Args:
            state: Application state
            format: Export format ('yaml' or 'json')
            
        Returns:
            Dict mapping filenames to content
        """
        pass
    
    @abstractmethod
    def export_wireguard_configs(self, state: 'IAppState', 
                               include_scripts: bool = True) -> Dict[str, str]:
        """
        Generate and export WireGuard configurations.
        
        Args:
            state: Application state
            include_scripts: Include setup scripts
            
        Returns:
            Dict mapping filenames to content
        """
        pass
    
    @abstractmethod
    def export_key_database(self, state: 'IAppState') -> str:
        """
        Export key database.
        
        Args:
            state: Application state
            
        Returns:
            JSON content of key database
        """
        pass
    
    @abstractmethod
    def create_export_package(self, state: 'IAppState', 
                            options: Dict[str, bool]) -> Path:
        """
        Create complete export package.
        
        Args:
            state: Application state
            options: Export options:
                - include_config: Include source configs
                - include_wireguard: Include generated configs
                - include_keys: Include key database
                - include_visualization: Include network diagram
                
        Returns:
            Path to created package (ZIP file)
        """
        pass
    
    @abstractmethod
    def export_visualization(self, state: 'IAppState', 
                           format: str = 'png') -> bytes:
        """
        Export network visualization.
        
        Args:
            state: Application state
            format: Image format ('png', 'svg', 'pdf')
            
        Returns:
            Image data as bytes
        """
        pass
    
    @abstractmethod
    def get_export_preview(self, state: 'IAppState', 
                         options: Dict[str, bool]) -> Dict[str, Any]:
        """
        Get preview of what will be exported.
        
        Args:
            state: Application state
            options: Export options
            
        Returns:
            Preview information including file list and sizes
        """
        pass