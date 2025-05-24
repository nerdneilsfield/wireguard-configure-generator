"""
Singleton logger implementation for WireGuard mesh generator
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class SingletonLogger:
    """Singleton logger class ensuring only one logger instance exists"""
    
    _instance = None
    _logger = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is None:
            self._setup_logger()
    
    def _setup_logger(self):
        """Setup the logger with default configuration"""
        self._logger = logging.getLogger('wg_mesh_gen')
        self._logger.setLevel(logging.INFO)
        
        # Avoid duplicate handlers
        if not self._logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            
            self._logger.addHandler(console_handler)
    
    @property
    def logger(self):
        """Get the logger instance"""
        return self._logger
    
    def set_level(self, level: str):
        """Set logging level"""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if level.upper() in level_map:
            self._logger.setLevel(level_map[level.upper()])
            for handler in self._logger.handlers:
                handler.setLevel(level_map[level.upper()])
    
    def add_file_handler(self, log_file: str):
        """Add file handler to logger"""
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(self._logger.level)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        self._logger.addHandler(file_handler)
    
    def info(self, message: str):
        """Log info message"""
        self._logger.info(message)
    
    def debug(self, message: str):
        """Log debug message"""
        self._logger.debug(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self._logger.warning(message)
    
    def error(self, message: str):
        """Log error message"""
        self._logger.error(message)
    
    def critical(self, message: str):
        """Log critical message"""
        self._logger.critical(message)


def get_logger() -> SingletonLogger:
    """Get the singleton logger instance"""
    return SingletonLogger()


def setup_logging(verbose: bool = False, log_file: Optional[str] = None):
    """Setup logging configuration"""
    logger = get_logger()
    
    if verbose:
        logger.set_level('DEBUG')
        logger.info("启用详细日志输出模式")
    else:
        logger.set_level('INFO')
    
    if log_file:
        logger.add_file_handler(log_file)
        logger.info(f"日志将保存到文件: {log_file}")
