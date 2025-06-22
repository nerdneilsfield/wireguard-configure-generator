"""
File upload component implementation with drag-and-drop support.

This component provides a user-friendly file upload interface.
"""

from typing import Optional, Callable, List, Dict, Any
import base64
import json
import yaml
from pathlib import Path

from nicegui import ui, events

from .base import BaseComponent
from ..interfaces.components import IFileUploadComponent
from ..interfaces.file_management import IFileManager


class FileUploadComponent(BaseComponent, IFileUploadComponent):
    """Implementation of IFileUploadComponent with drag-and-drop."""
    
    def __init__(self,
                 file_manager: IFileManager,
                 accept: Optional[List[str]] = None,
                 multiple: bool = False,
                 max_size_mb: int = 10,
                 component_id: Optional[str] = None):
        """
        Initialize file upload component.
        
        Args:
            file_manager: File manager instance
            accept: List of accepted file extensions
            multiple: Allow multiple file selection
            max_size_mb: Maximum file size in MB
            component_id: Optional component ID
        """
        super().__init__(component_id)
        self._file_manager = file_manager
        self._accept = accept or ['.yaml', '.yml', '.json', '.conf']
        self._multiple = multiple
        self._max_size_mb = max_size_mb
        self._max_size_bytes = max_size_mb * 1024 * 1024
        
        # Event handlers
        self._on_upload: Optional[Callable[[List[Dict[str, Any]]], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        
        # Upload state
        self._uploading = False
        self._uploaded_files: List[Dict[str, Any]] = []
    
    def render(self) -> ui.element:
        """Render the file upload component."""
        with ui.column().classes('w-full') as container:
            # Upload area
            with ui.upload(
                on_upload=self._handle_upload,
                multiple=self._multiple,
                max_file_size=self._max_size_bytes,
                auto_upload=True
            ).classes('w-full').props(
                f'accept="{",".join(self._accept)}"'
            ) as self._element:
                # Custom upload UI
                with ui.column().classes(
                    'w-full h-48 border-2 border-dashed border-gray-300 '
                    'rounded-lg items-center justify-center gap-4 '
                    'hover:border-primary hover:bg-gray-50 transition-colors cursor-pointer'
                ):
                    ui.icon('cloud_upload').classes('text-6xl text-gray-400')
                    ui.label('Drop files here or click to browse').classes('text-lg text-gray-600')
                    ui.label(f'Accepted: {", ".join(self._accept)}').classes('text-sm text-gray-500')
                    ui.label(f'Max size: {self._max_size_mb}MB').classes('text-sm text-gray-500')
                    
                    # Progress indicator
                    self._progress = ui.spinner('dots', size='lg').classes('hidden')
                    self._progress_label = ui.label().classes('text-sm text-gray-600 hidden')
            
            # Uploaded files list
            self._files_container = ui.column().classes('w-full gap-2 mt-4')
            
        return container
    
    def _handle_upload(self, e: events.UploadEventArguments) -> None:
        """Handle file upload event."""
        try:
            self._uploading = True
            self._show_progress('Processing...')
            
            # Process uploaded file
            file_info = {
                'name': e.name,
                'size': len(e.content) if hasattr(e, 'content') else 0,
                'type': self._detect_file_type(e.name),
                'content': e.content.read() if hasattr(e.content, 'read') else e.content
            }
            
            # Validate file
            errors = self._validate_file(file_info)
            if errors:
                self._handle_error(f"Validation failed: {', '.join(errors)}")
                return
            
            # Save file temporarily
            if isinstance(file_info['content'], bytes):
                # Handle binary content
                temp_path = self._file_manager.upload_file(
                    file_info['content'],
                    file_info['name']
                )
            else:
                # Handle text content
                temp_path = self._file_manager.upload_file(
                    file_info['content'].encode('utf-8'),
                    file_info['name']
                )
            
            file_info['temp_path'] = temp_path
            
            # Detect configuration type
            file_info['config_type'] = self._file_manager.detect_file_type(temp_path)
            
            # Add to uploaded files
            self._uploaded_files.append(file_info)
            self._update_files_display()
            
            # Trigger upload handler
            if self._on_upload:
                self._on_upload([file_info])
            
            ui.notify(f'Uploaded: {file_info["name"]}', type='positive')
            
        except Exception as e:
            self._handle_error(f'Upload failed: {str(e)}')
        finally:
            self._uploading = False
            self._hide_progress()
    
    def _detect_file_type(self, filename: str) -> str:
        """Detect file type from filename."""
        path = Path(filename)
        extension = path.suffix.lower()
        
        if extension in ['.yaml', '.yml']:
            return 'yaml'
        elif extension == '.json':
            return 'json'
        elif extension == '.conf':
            return 'wireguard'
        else:
            return 'unknown'
    
    def _validate_file(self, file_info: Dict[str, Any]) -> List[str]:
        """Validate uploaded file."""
        errors = []
        
        # Check file extension
        filename = file_info['name']
        extension = Path(filename).suffix.lower()
        if extension not in self._accept:
            errors.append(f'File type {extension} not accepted')
        
        # Check file size
        if file_info['size'] > self._max_size_bytes:
            errors.append(f'File size exceeds {self._max_size_mb}MB limit')
        
        # Parse and validate content
        if file_info['type'] in ['yaml', 'json']:
            try:
                content = file_info['content']
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                
                if file_info['type'] == 'yaml':
                    data = yaml.safe_load(content)
                else:
                    data = json.loads(content)
                
                # Basic structure validation
                if not isinstance(data, dict):
                    errors.append('File must contain a JSON object or YAML mapping')
                
            except (yaml.YAMLError, json.JSONDecodeError) as e:
                errors.append(f'Invalid {file_info["type"].upper()} format: {str(e)}')
            except Exception as e:
                errors.append(f'Failed to parse file: {str(e)}')
        
        return errors
    
    def _update_files_display(self) -> None:
        """Update the uploaded files display."""
        self._files_container.clear()
        
        if not self._uploaded_files:
            return
        
        with self._files_container:
            ui.label('Uploaded Files').classes('text-subtitle2 mb-2')
            
            for file_info in self._uploaded_files:
                with ui.card().classes('w-full p-3'):
                    with ui.row().classes('items-center gap-3'):
                        # File icon
                        icon = self._get_file_icon(file_info['type'])
                        ui.icon(icon).classes('text-2xl text-gray-600')
                        
                        # File info
                        with ui.column().classes('flex-grow'):
                            ui.label(file_info['name']).classes('font-medium')
                            with ui.row().classes('gap-4 text-sm text-gray-600'):
                                ui.label(f"Type: {file_info['config_type']}")
                                ui.label(f"Size: {self._format_size(file_info['size'])}")
                        
                        # Actions
                        with ui.row().classes('gap-2'):
                            ui.button(
                                icon='visibility',
                                on_click=lambda f=file_info: self._preview_file(f)
                            ).props('flat dense round').tooltip('Preview')
                            
                            ui.button(
                                icon='delete',
                                on_click=lambda f=file_info: self._remove_file(f)
                            ).props('flat dense round color=negative').tooltip('Remove')
    
    def _get_file_icon(self, file_type: str) -> str:
        """Get icon for file type."""
        icons = {
            'yaml': 'code',
            'json': 'data_object',
            'wireguard': 'vpn_lock',
            'unknown': 'insert_drive_file'
        }
        return icons.get(file_type, 'insert_drive_file')
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size for display."""
        for unit in ['B', 'KB', 'MB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} GB"
    
    def _preview_file(self, file_info: Dict[str, Any]) -> None:
        """Preview uploaded file."""
        with ui.dialog() as dialog, ui.card().classes('w-[800px] max-h-[600px]'):
            with ui.column().classes('w-full'):
                # Header
                with ui.row().classes('items-center mb-4'):
                    ui.label(f'Preview: {file_info["name"]}').classes('text-h6 flex-grow')
                    ui.button(icon='close', on_click=dialog.close).props('flat dense round')
                
                # Content
                try:
                    with open(file_info['temp_path'], 'r') as f:
                        content = f.read()
                    
                    # Syntax highlighted preview
                    ui.markdown(f'```{file_info["type"]}\n{content}\n```')\
                        .classes('overflow-auto max-h-[400px]')
                    
                except Exception as e:
                    ui.label(f'Error reading file: {str(e)}').classes('text-negative')
                
                # Actions
                with ui.row().classes('justify-end gap-2 mt-4'):
                    ui.button('Import', on_click=lambda: self._import_file(file_info, dialog))\
                        .props('color=primary')
                    ui.button('Close', on_click=dialog.close)
        
        dialog.open()
    
    def _import_file(self, file_info: Dict[str, Any], dialog) -> None:
        """Import the file."""
        dialog.close()
        # This would trigger the actual import process
        ui.notify(f'Importing {file_info["name"]}...', type='info')
    
    def _remove_file(self, file_info: Dict[str, Any]) -> None:
        """Remove an uploaded file."""
        # Delete temp file
        try:
            self._file_manager.delete_file(file_info['temp_path'])
        except:
            pass
        
        # Remove from list
        self._uploaded_files.remove(file_info)
        self._update_files_display()
        
        ui.notify(f'Removed: {file_info["name"]}', type='info')
    
    def set_accept(self, extensions: List[str]) -> None:
        """Set accepted file extensions."""
        self._accept = extensions
        if self._element:
            self._element.props(f'accept="{",".join(extensions)}"')
    
    def set_max_size(self, size_mb: int) -> None:
        """Set maximum file size in MB."""
        self._max_size_mb = size_mb
        self._max_size_bytes = size_mb * 1024 * 1024
        if self._element:
            self._element.max_file_size = self._max_size_bytes
    
    def clear(self) -> None:
        """Clear all uploaded files."""
        # Delete all temp files
        for file_info in self._uploaded_files:
            try:
                self._file_manager.delete_file(file_info['temp_path'])
            except:
                pass
        
        self._uploaded_files.clear()
        self._update_files_display()
    
    def get_files(self) -> List[Dict[str, Any]]:
        """Get list of uploaded files."""
        return self._uploaded_files.copy()
    
    def on_upload(self, handler: Callable[[List[Dict[str, Any]]], None]) -> None:
        """Register upload handler."""
        self._on_upload = handler
    
    def on_error(self, handler: Callable[[str], None]) -> None:
        """Register error handler."""
        self._on_error = handler
    
    def _show_progress(self, message: str) -> None:
        """Show progress indicator."""
        self._progress.classes(remove='hidden')
        self._progress_label.text = message
        self._progress_label.classes(remove='hidden')
    
    def _hide_progress(self) -> None:
        """Hide progress indicator."""
        self._progress.classes(add='hidden')
        self._progress_label.classes(add='hidden')
    
    def _handle_error(self, message: str) -> None:
        """Handle upload error."""
        self._hide_progress()
        ui.notify(message, type='negative')
        
        if self._on_error:
            self._on_error(message)
    
    @property
    def accept(self) -> List[str]:
        """Get accepted file extensions."""
        return self._accept
    
    @property
    def multiple(self) -> bool:
        """Get multiple file selection setting."""
        return self._multiple
    
    @property
    def max_size(self) -> int:
        """Get maximum file size in MB."""
        return self._max_size_mb