#!/usr/bin/env python3
"""
Fix the endpoints format in the nodes file
"""

import yaml

# Read the file
with open('super_complex_nodes.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Fix endpoints format
for node in data['nodes']:
    if 'endpoints' in node and isinstance(node['endpoints'], list):
        # Convert from object format to string format
        new_endpoints = []
        for endpoint in node['endpoints']:
            if isinstance(endpoint, dict) and 'endpoint' in endpoint:
                new_endpoints.append(endpoint['endpoint'])
            elif isinstance(endpoint, str):
                new_endpoints.append(endpoint)
        if new_endpoints:
            node['endpoints'] = new_endpoints

# Write back
with open('super_complex_nodes.yaml', 'w') as f:
    yaml.dump(data, f, default_flow_style=False, sort_keys=False)