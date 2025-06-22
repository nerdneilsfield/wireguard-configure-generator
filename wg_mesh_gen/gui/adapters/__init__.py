"""
Adapter classes for integrating GUI with existing CLI functionality.

These adapters ensure we reuse existing CLI code instead of duplicating it.
"""

from .cli_adapter import CLIAdapter
from .config_adapter import ConfigAdapter
from .group_adapter import GroupAdapter

__all__ = ['CLIAdapter', 'ConfigAdapter', 'GroupAdapter']