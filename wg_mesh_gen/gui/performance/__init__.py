"""
Performance optimization module for WireGuard GUI.

This module provides caching and optimization features for handling large networks.
"""

from .cache import (
    GraphCache,
    RenderOptimizer,
    DataOptimizer,
    graph_cache,
    render_optimizer,
    data_optimizer
)

__all__ = [
    'GraphCache',
    'RenderOptimizer', 
    'DataOptimizer',
    'graph_cache',
    'render_optimizer',
    'data_optimizer'
]