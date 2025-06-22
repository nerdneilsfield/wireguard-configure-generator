"""
Main entry point for the WireGuard Visual Configuration Editor GUI.

This module provides the main application class and entry point.
"""

import sys
import os
from pathlib import Path
from typing import Optional
import click
from nicegui import ui, app

from .app import WireGuardEditorApp
from ..logger import get_logger


def setup_app_directories():
    """Setup application directories for config and data storage."""
    # Get user config directory
    if sys.platform == "win32":
        config_dir = Path(os.environ.get('APPDATA', '')) / 'WireGuardEditor'
    else:
        config_dir = Path.home() / '.config' / 'wireguard-editor'
    
    # Create directories
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / 'sessions').mkdir(exist_ok=True)
    (config_dir / 'templates').mkdir(exist_ok=True)
    (config_dir / 'exports').mkdir(exist_ok=True)
    
    return config_dir


@click.command()
@click.option('--host', default='127.0.0.1', help='Host to bind to')
@click.option('--port', default=8080, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
@click.option('--dark-mode', is_flag=True, help='Start in dark mode')
@click.option('--config-dir', type=click.Path(), help='Configuration directory')
@click.option('--log-level', default='INFO', 
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Logging level')
def main(host: str, port: int, reload: bool, dark_mode: bool, 
         config_dir: Optional[str], log_level: str):
    """Launch the WireGuard Visual Configuration Editor GUI."""
    # Setup logging
    import logging
    logging.basicConfig(level=getattr(logging, log_level))
    logger = get_logger()
    logger.info("Starting WireGuard Visual Configuration Editor GUI")
    
    # Setup directories
    if config_dir:
        app_config_dir = Path(config_dir)
        app_config_dir.mkdir(parents=True, exist_ok=True)
    else:
        app_config_dir = setup_app_directories()
    
    logger.info(f"Using config directory: {app_config_dir}")
    
    # Configure NiceGUI app
    app.native.window_args['resizable'] = True
    app.native.window_args['title'] = 'WireGuard Configuration Editor'
    app.native.start_args['debug'] = reload
    
    # Create application instance with configuration
    editor_app = WireGuardEditorApp(config_dir=app_config_dir)
    
    # Store dark mode preference for use in pages
    app_dark_mode = dark_mode
    
    # Define routes
    @ui.page('/')
    async def index():
        """Main application page."""
        # Store app configuration in user storage within page context
        app.storage.user['config_dir'] = str(app_config_dir)
        app.storage.user['dark_mode'] = app_dark_mode
        await editor_app.create_ui()
    
    @ui.page('/session/{session_id}')
    async def session(session_id: str):
        """Session-specific page."""
        # Store app configuration in user storage within page context
        app.storage.user['config_dir'] = str(app_config_dir)
        app.storage.user['dark_mode'] = app_dark_mode
        await editor_app.create_ui(session_id=session_id)
    
    # Start the application
    logger.info(f"Starting GUI server on {host}:{port}")
    
    # Generate a storage secret for user sessions
    import secrets
    storage_secret = secrets.token_urlsafe(32)
    
    ui.run(
        host=host,
        port=port,
        reload=reload,
        title='WireGuard Configuration Editor',
        favicon='🔐',
        dark=dark_mode,
        storage_secret=storage_secret
    )


if __name__ == '__main__':
    main()