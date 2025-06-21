#!/usr/bin/env python3
"""
Generate super complex topology for testing
"""

import yaml
import itertools

def generate_topology():
    peers = []
    
    # Core nodes
    core_nodes = [
        "CORE-US-EAST", "CORE-US-WEST", "CORE-EU-CENTRAL",
        "CORE-EU-NORTH", "CORE-ASIA-PACIFIC", "CORE-SOUTH-AMERICA"
    ]
    
    # Aggregation nodes by region
    agg_nodes = {
        "US-EAST": ["AGG-USE-DC1", "AGG-USE-DC2", "AGG-USE-DC3"],
        "US-WEST": ["AGG-USW-DC1", "AGG-USW-DC2", "AGG-USW-DC3"],
        "EU-CENTRAL": ["AGG-EUC-DC1", "AGG-EUC-DC2", "AGG-EUC-DC3"],
        "EU-NORTH": ["AGG-EUN-DC1", "AGG-EUN-DC2"],
        "ASIA-PACIFIC": ["AGG-AP-DC1", "AGG-AP-DC2", "AGG-AP-DC3", "AGG-AP-DC4"],
        "SOUTH-AMERICA": ["AGG-SA-DC1", "AGG-SA-DC2"]
    }
    
    # Access nodes by region
    acc_nodes = {
        "US-EAST": [f"ACC-USE-{i}" for i in range(1, 6)],
        "US-WEST": [f"ACC-USW-{i}" for i in range(1, 6)],
        "EU-CENTRAL": [f"ACC-EUC-{i}" for i in range(1, 6)],
        "EU-NORTH": [f"ACC-EUN-{i}" for i in range(1, 6)],
        "ASIA-PACIFIC": [f"ACC-AP-{i}" for i in range(1, 6)],
        "SOUTH-AMERICA": [f"ACC-SA-{i}" for i in range(1, 6)]
    }
    
    # Client nodes by region
    client_nodes = {
        "US-EAST": [f"CLIENT-USE-{i:03d}" for i in range(1, 11)],
        "US-WEST": [f"CLIENT-USW-{i:03d}" for i in range(1, 11)],
        "EU-CENTRAL": [f"CLIENT-EUC-{i:03d}" for i in range(1, 9)],
        "EU-NORTH": [f"CLIENT-EUN-{i:03d}" for i in range(1, 9)],
        "ASIA-PACIFIC": [f"CLIENT-AP-{i:03d}" for i in range(1, 9)],
        "SOUTH-AMERICA": [f"CLIENT-SA-{i:03d}" for i in range(1, 7)]
    }
    
    # 1. Core mesh - full connectivity between all core nodes
    for i, core1 in enumerate(core_nodes):
        for core2 in core_nodes[i+1:]:
            peers.append({
                "from": core1,
                "to": core2,
                "endpoint": f"{core2.lower().replace('-', '.')}.example.com:51820",
                "persistent_keepalive": 25
            })
    
    # 2. Core to Aggregation - each aggregation connects to 2-3 core nodes
    core_agg_mapping = {
        "US-EAST": ["CORE-US-EAST", "CORE-US-WEST", "CORE-EU-CENTRAL"],
        "US-WEST": ["CORE-US-WEST", "CORE-US-EAST", "CORE-ASIA-PACIFIC"],
        "EU-CENTRAL": ["CORE-EU-CENTRAL", "CORE-EU-NORTH", "CORE-US-EAST"],
        "EU-NORTH": ["CORE-EU-NORTH", "CORE-EU-CENTRAL"],
        "ASIA-PACIFIC": ["CORE-ASIA-PACIFIC", "CORE-US-WEST", "CORE-EU-CENTRAL"],
        "SOUTH-AMERICA": ["CORE-SOUTH-AMERICA", "CORE-US-EAST", "CORE-EU-CENTRAL"]
    }
    
    for region, cores in core_agg_mapping.items():
        for agg in agg_nodes.get(region, []):
            for core in cores:
                peers.append({
                    "from": agg,
                    "to": core,
                    "endpoint": f"{core.lower().replace('-', '.')}.example.com:51820",
                    "allowed_ips": ["10.0.0.0/16"],
                    "persistent_keepalive": 25
                })
    
    # 3. Aggregation to Access - each access connects to 2 aggregation nodes in same region
    for region in agg_nodes:
        aggs = agg_nodes[region]
        accs = acc_nodes.get(region, [])
        
        for i, acc in enumerate(accs):
            # Connect to primary and backup aggregation
            primary_agg = aggs[i % len(aggs)]
            backup_agg = aggs[(i + 1) % len(aggs)]
            
            peers.append({
                "from": acc,
                "to": primary_agg,
                "endpoint": f"{primary_agg.lower().replace('-', '.')}.example.com:51820",
                "allowed_ips": ["10.0.0.0/12"]
            })
            
            peers.append({
                "from": acc,
                "to": backup_agg,
                "endpoint": f"{backup_agg.lower().replace('-', '.')}.example.com:51820",
                "allowed_ips": ["10.0.0.0/12"]
            })
    
    # 4. Access to Client - each client connects to 1-2 access nodes
    for region in acc_nodes:
        accs = acc_nodes[region]
        clients = client_nodes.get(region, [])
        
        for i, client in enumerate(clients):
            # Primary access node
            primary_acc = accs[i % len(accs)]
            peers.append({
                "from": client,
                "to": primary_acc,
                "endpoint": f"{primary_acc.lower().replace('-', '.')}.example.com:51820",
                "allowed_ips": ["0.0.0.0/0"]
            })
            
            # Some clients get backup access for redundancy
            if i % 3 == 0:  # Every third client gets redundancy
                backup_acc = accs[(i + 1) % len(accs)]
                peers.append({
                    "from": client,
                    "to": backup_acc,
                    "endpoint": f"{backup_acc.lower().replace('-', '.')}.example.com:51820",
                    "allowed_ips": ["0.0.0.0/0"]
                })
    
    # 5. Cross-region connections for redundancy
    # US-EAST <-> EU-CENTRAL direct link
    peers.append({
        "from": "AGG-USE-DC1",
        "to": "AGG-EUC-DC1",
        "endpoint": "agg-euc-dc1.example.com:51820",
        "persistent_keepalive": 25
    })
    
    # US-WEST <-> ASIA-PACIFIC direct link
    peers.append({
        "from": "AGG-USW-DC1",
        "to": "AGG-AP-DC1",
        "endpoint": "agg-ap-dc1.example.com:51820",
        "persistent_keepalive": 25
    })
    
    # EU-CENTRAL <-> ASIA-PACIFIC direct link
    peers.append({
        "from": "AGG-EUC-DC2",
        "to": "AGG-AP-DC2",
        "endpoint": "agg-ap-dc2.example.com:51820",
        "persistent_keepalive": 25
    })
    
    # 6. Special test scenarios
    # Isolated node - no connections
    # (no peers for TEST-ISOLATED-NODE)
    
    # High latency simulation
    peers.append({
        "from": "TEST-HIGH-LATENCY",
        "to": "CORE-ASIA-PACIFIC",
        "endpoint": "core-asia-pac.example.com:51820",
        "allowed_ips": ["0.0.0.0/0"]
    })
    
    # Packet loss simulation
    peers.append({
        "from": "TEST-PACKET-LOSS",
        "to": "AGG-SA-DC1",
        "endpoint": "agg-sa-dc1.example.com:51820",
        "allowed_ips": ["0.0.0.0/0"]
    })
    
    # Low bandwidth simulation
    peers.append({
        "from": "TEST-LOW-BANDWIDTH",
        "to": "ACC-USE-1",
        "endpoint": "acc-use-1.example.com:51820",
        "allowed_ips": ["0.0.0.0/0"]
    })
    
    # 7. Add some mesh connections between aggregation nodes in same region
    for region, aggs in agg_nodes.items():
        if len(aggs) > 1:
            for i in range(len(aggs)):
                for j in range(i + 1, len(aggs)):
                    peers.append({
                        "from": aggs[i],
                        "to": aggs[j],
                        "endpoint": f"{aggs[j].lower().replace('-', '.')}.example.com:51820"
                    })
    
    return {"peers": peers}

if __name__ == "__main__":
    topology = generate_topology()
    
    # Save to file
    with open("super_complex_topology.yaml", "w") as f:
        yaml.dump(topology, f, default_flow_style=False, sort_keys=False)
    
    print(f"Generated topology with {len(topology['peers'])} connections")
    
    # Print statistics
    from collections import defaultdict
    connection_count = defaultdict(int)
    for peer in topology['peers']:
        connection_count[peer['from']] += 1
        connection_count[peer['to']] += 1
    
    print("\nConnection statistics:")
    print(f"Total unique nodes: {len(connection_count)}")
    print(f"Average connections per node: {sum(connection_count.values()) / len(connection_count):.1f}")
    print(f"Max connections: {max(connection_count.values())} (node: {max(connection_count, key=connection_count.get)})")
    print(f"Min connections: {min(connection_count.values())}")