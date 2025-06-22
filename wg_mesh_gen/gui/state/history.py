"""
History manager implementation for undo/redo functionality.
"""

from typing import List, Optional
from collections import deque

from ..interfaces.state import IHistoryManager, ICommand
from .commands import BatchCommand


class HistoryManager(IHistoryManager):
    """Implementation of IHistoryManager for command history management."""
    
    def __init__(self, history_limit: int = 100):
        """
        Initialize history manager.
        
        Args:
            history_limit: Maximum number of commands to keep in history
        """
        self._undo_stack: deque = deque(maxlen=history_limit)
        self._redo_stack: deque = deque(maxlen=history_limit)
        self._history_limit = history_limit
        self._batch_mode = False
        self._batch_commands: List[ICommand] = []
        self._batch_description = ""
    
    @property
    def history_limit(self) -> int:
        """Get history limit."""
        return self._history_limit
    
    @history_limit.setter
    def history_limit(self, value: int) -> None:
        """Set history limit."""
        if value <= 0:
            raise ValueError("History limit must be positive")
        
        self._history_limit = value
        
        # Resize stacks if needed
        if len(self._undo_stack) > value:
            # Keep most recent commands
            new_stack = deque(maxlen=value)
            for _ in range(value):
                if self._undo_stack:
                    new_stack.appendleft(self._undo_stack.pop())
            self._undo_stack = new_stack
        else:
            self._undo_stack = deque(self._undo_stack, maxlen=value)
        
        if len(self._redo_stack) > value:
            # Keep most recent commands
            new_stack = deque(maxlen=value)
            for _ in range(value):
                if self._redo_stack:
                    new_stack.appendleft(self._redo_stack.pop())
            self._redo_stack = new_stack
        else:
            self._redo_stack = deque(self._redo_stack, maxlen=value)
    
    def execute(self, command: ICommand) -> None:
        """
        Execute a command and add it to history.
        
        Args:
            command: Command to execute
        """
        # If in batch mode, accumulate commands
        if self._batch_mode:
            self._batch_commands.append(command)
            return
        
        # Execute the command
        command.execute()
        
        # Add to undo stack
        self._undo_stack.append(command)
        
        # Clear redo stack (new action invalidates redo history)
        self._redo_stack.clear()
    
    def undo(self) -> bool:
        """
        Undo the last command.
        
        Returns:
            True if a command was undone, False if history is empty
        """
        if not self.can_undo():
            return False
        
        # Get last command
        command = self._undo_stack.pop()
        
        # Undo it
        command.undo()
        
        # Add to redo stack
        self._redo_stack.append(command)
        
        return True
    
    def redo(self) -> bool:
        """
        Redo the last undone command.
        
        Returns:
            True if a command was redone, False if redo stack is empty
        """
        if not self.can_redo():
            return False
        
        # Get last undone command
        command = self._redo_stack.pop()
        
        # Re-execute it
        command.execute()
        
        # Add back to undo stack
        self._undo_stack.append(command)
        
        return True
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0
    
    def clear(self) -> None:
        """Clear all history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._batch_mode = False
        self._batch_commands.clear()
        self._batch_description = ""
    
    def get_undo_description(self) -> Optional[str]:
        """Get description of the command that would be undone."""
        if not self.can_undo():
            return None
        
        # Peek at the last command without removing it
        command = self._undo_stack[-1]
        return command.description
    
    def get_redo_description(self) -> Optional[str]:
        """Get description of the command that would be redone."""
        if not self.can_redo():
            return None
        
        # Peek at the last undone command without removing it
        command = self._redo_stack[-1]
        return command.description
    
    def begin_batch(self, description: str) -> None:
        """
        Begin a batch of commands that will be treated as one.
        
        Args:
            description: Description of the batch operation
        """
        if self._batch_mode:
            raise RuntimeError("Already in batch mode")
        
        self._batch_mode = True
        self._batch_commands = []
        self._batch_description = description
    
    def end_batch(self) -> None:
        """End the current batch of commands."""
        if not self._batch_mode:
            raise RuntimeError("Not in batch mode")
        
        self._batch_mode = False
        
        # If no commands were added, just clear and return
        if not self._batch_commands:
            self._batch_description = ""
            return
        
        # Create batch command if multiple commands
        if len(self._batch_commands) == 1:
            # Single command, execute it directly
            command = self._batch_commands[0]
        else:
            # Multiple commands, wrap in batch
            # Need app_state from first command
            first_cmd = self._batch_commands[0]
            app_state = getattr(first_cmd, '_app_state', None)
            if not app_state:
                raise RuntimeError("Cannot get app_state from commands")
            
            command = BatchCommand(
                app_state=app_state,
                commands=self._batch_commands,
                description=self._batch_description
            )
        
        # Execute the command/batch
        self.execute(command)
        
        # Clear batch state
        self._batch_commands = []
        self._batch_description = ""
    
    def get_history_size(self) -> int:
        """
        Get the current number of commands in history.
        
        Returns:
            Number of commands in undo stack
        """
        return len(self._undo_stack)
    
    def get_redo_size(self) -> int:
        """
        Get the current number of commands in redo stack.
        
        Returns:
            Number of commands in redo stack
        """
        return len(self._redo_stack)