"""
WireGuard Mesh Configuration Generator

A tool for generating WireGuard mesh network configurations with support for:
- Mesh topology with relay nodes
- Automatic key generation and management
- Route optimization
- Configuration file generation
- Network visualization
"""

__version__ = "1.0.0"
__author__ = "WireGuard Mesh Generator"

from .cli import main
from .builder import build_peer_configs
from .visualizer import visualize
from .loader import load_nodes, load_topology
from .utils import load_config, save_yaml

__all__ = [
    "main",
    "build_peer_configs", 
    "visualize",
    "load_nodes",
    "load_topology",
    "load_config",
    "save_yaml"
]
