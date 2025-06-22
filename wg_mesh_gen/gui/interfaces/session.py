"""
Session management interfaces.

This module defines interfaces for session management.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pathlib import Path


class ISessionManager(ABC):
    """Interface for session management."""
    
    @abstractmethod
    def create_session(self, name: Optional[str] = None) -> str:
        """
        Create a new session.
        
        Args:
            name: Optional session name
            
        Returns:
            Session ID
        """
        pass
    
    @abstractmethod
    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load an existing session.
        
        Args:
            session_id: Session to load
            
        Returns:
            Session data or None if not found
        """
        pass
    
    @abstractmethod
    def save_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Save session data.
        
        Args:
            session_id: Session to save
            data: Session data
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session to delete
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all available sessions.
        
        Returns:
            List of session metadata
        """
        pass
    
    @abstractmethod
    def get_session_path(self, session_id: str) -> Path:
        """
        Get the file path for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Path to session file
        """
        pass
    
    @abstractmethod
    def cleanup_sessions(self, max_age_days: int = 30) -> int:
        """
        Clean up old sessions.
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Number of sessions deleted
        """
        pass