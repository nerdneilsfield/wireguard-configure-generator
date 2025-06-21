#!/usr/bin/env python3
"""
Debug the super complex configuration issue
"""

import yaml
import traceback
from wg_mesh_gen.validator import validate_and_load_config
from wg_mesh_gen.builder import build_peer_configs

try:
    # Load and validate
    nodes, peers = validate_and_load_config(
        "examples/super_complex_nodes.yaml",
        "examples/super_complex_topology.yaml"
    )
    
    print(f"Loaded {len(nodes)} nodes and {len(peers)} peers")
    
    # Check node structure
    print("\nFirst node structure:")
    print(nodes[0])
    
    print("\nFirst peer structure:")
    print(peers[0])
    
    # Try to build configs
    result = build_peer_configs(
        "examples/super_complex_nodes.yaml",
        "examples/super_complex_topology.yaml",
        output_dir="out/super_complex_test",
        auto_generate_keys=True
    )
    
    print("\nBuild successful!")
    
except Exception as e:
    print(f"\nError occurred: {e}")
    print("\nFull traceback:")
    traceback.print_exc()