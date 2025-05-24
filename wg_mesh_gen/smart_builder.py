#!/usr/bin/env python3
"""
智能配置构建器
支持多路径和动态路由优化
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from wg_mesh_gen.loader import load_nodes, load_topology
from wg_mesh_gen.storage import init_keystore, load_key, save_key
from wg_mesh_gen.crypto import gen_keypair


def build_smart_peer_configs(nodes_path: str,
                            topology_path: str,
                            db_url: str = 'sqlite:///wg_keys.db',
                            enable_multipath: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    """
    构建智能对等配置，支持多路径路由
    """
    nodes = load_nodes(nodes_path)
    peers = load_topology(topology_path)
    session = init_keystore(db_url)

    # Build lookup for nodes and keys
    node_map = {n['name']: n for n in nodes}
    key_map = {}
    for name in node_map:
        kp = load_key(session, name)
        if not kp:
            # Auto-generate keypair if missing
            private, public, psk = gen_keypair()
            save_key(session, name, private, public, psk)
            kp = load_key(session, name)
            print(f"Auto-generated keys for {name}")
        key_map[name] = kp

    # Group peers by source and destination
    route_groups = defaultdict(list)

    for rel in peers:
        src = rel['from']
        dst = rel['to']
        route_key = (src, dst)
        route_groups[route_key].append(rel)

    # Prepare container
    peer_configs: Dict[str, List[Dict[str, Any]]] = {n: [] for n in node_map}

    # Process each route group
    for (src, dst), relations in route_groups.items():
        if enable_multipath and len(relations) > 1:
            # Multiple paths available - create multipath config
            primary_rel = min(relations, key=lambda x: x.get('priority', 999))
            backup_rels = [r for r in relations if r != primary_rel]

            # Add primary route
            _add_peer_config(peer_configs, src, dst, primary_rel, node_map, key_map, is_primary=True)

            # Add backup routes with different metrics
            for backup_rel in backup_rels:
                _add_peer_config(peer_configs, src, dst, backup_rel, node_map, key_map, is_primary=False)
        else:
            # Single path
            rel = relations[0]
            _add_peer_config(peer_configs, src, dst, rel, node_map, key_map, is_primary=True)

    return peer_configs


def _add_peer_config(peer_configs: Dict[str, List[Dict[str, Any]]],
                    src: str, dst: str, rel: Dict[str, Any],
                    node_map: Dict[str, Any], key_map: Dict[str, Any],
                    is_primary: bool = True):
    """添加对等配置"""
    ep_name = rel['endpoint']
    allowed_ips = rel['allowed_ips']

    # Handle empty endpoint (for passive connections)
    if ep_name == "":
        # This is a passive connection (no endpoint, only keys)
        peer_config = {
            'peer_name': dst,
            'endpoint_name': '',
            'public_key': key_map[dst].public_key,
            'psk': key_map[dst].psk,
            'endpoint': '',  # No endpoint for passive connections
            'allowed_ips': allowed_ips,
            'keepalive': 0,  # No keepalive for passive connections
            'is_primary': is_primary,
            'priority': rel.get('priority', 1),
            'is_passive': True
        }
    else:
        # Find dst endpoint entry by name
        dst_node = node_map[dst]
        ep_entry = next((e for e in dst_node['endpoints'] if e['name'] == ep_name), None)
        if not ep_entry:
            raise ValueError(f"Endpoint '{ep_name}' not found for node '{dst}'")

        # Calculate keepalive based on priority
        base_keepalive = rel.get('keepalive', 25)
        if not is_primary:
            # Backup routes use longer keepalive to reduce overhead
            base_keepalive = base_keepalive * 2

        peer_config = {
            'peer_name': dst,
            'endpoint_name': ep_name,
            'public_key': key_map[dst].public_key,
            'psk': key_map[dst].psk,
            'endpoint': ep_entry['endpoint'],
            'allowed_ips': allowed_ips,
            'keepalive': base_keepalive,
            'is_primary': is_primary,
            'priority': rel.get('priority', 1),
            'is_passive': False
        }

    peer_configs[src].append(peer_config)


def generate_route_script(node_name: str, peer_configs: List[Dict[str, Any]]) -> str:
    """
    生成路由优化脚本
    """
    script_lines = [
        "#!/bin/bash",
        "# Auto-generated route optimization script",
        f"# For node: {node_name}",
        "",
        "# Function to test route latency",
        "test_route() {",
        "    local target_ip=$1",
        "    local route_name=$2",
        "    local ping_result=$(ping -c 3 -W 1 $target_ip 2>/dev/null | grep 'avg')",
        "    if [ $? -eq 0 ]; then",
        "        local avg_time=$(echo $ping_result | cut -d'/' -f5)",
        "        echo \"Route $route_name: ${avg_time}ms\"",
        "        echo $avg_time",
        "    else",
        "        echo \"Route $route_name: FAILED\"",
        "        echo 9999",
        "    fi",
        "}",
        "",
        "# Test all available routes",
    ]

    # Group peers by target network
    target_groups = defaultdict(list)
    for peer in peer_configs:
        if not peer.get('is_primary', True):
            continue  # Skip backup routes for now

        for allowed_ip in peer['allowed_ips']:
            if '/' in allowed_ip:
                network = allowed_ip.split('/')[0]
                target_groups[network].append(peer)

    for network, peers in target_groups.items():
        if len(peers) > 1:  # Multiple routes available
            script_lines.extend([
                f"",
                f"echo \"Testing routes to {network}...\"",
            ])

            for i, peer in enumerate(peers):
                via_node = peer['peer_name']
                script_lines.append(f"route_{i}_time=$(test_route {network} \"via_{via_node}\")")

            # Add route selection logic
            script_lines.extend([
                "",
                "# Select best route (lowest latency)",
                f"best_route=0",
                f"best_time=$route_0_time",
            ])

            for i in range(1, len(peers)):
                script_lines.extend([
                    f"if (( $(echo \"$route_{i}_time < $best_time\" | bc -l) )); then",
                    f"    best_route={i}",
                    f"    best_time=$route_{i}_time",
                    f"fi",
                ])

            script_lines.extend([
                "",
                f"echo \"Best route to {network}: Route $best_route (${{best_time}}ms)\"",
                "",
            ])

    script_lines.extend([
        "",
        "echo \"Route optimization complete.\"",
        "# TODO: Update WireGuard configuration based on results",
    ])

    return "\n".join(script_lines)


def build_multipath_topology(base_topology: Dict[str, Any]) -> Dict[str, Any]:
    """
    从基础拓扑生成多路径拓扑
    """
    peers = base_topology.get('peers', [])
    multipath_peers = []

    # 识别需要多路径的连接
    relay_connections = defaultdict(list)

    for peer in peers:
        src, dst = peer['from'], peer['to']
        if peer.get('endpoint') == 'relay':
            # 这是到中继的连接，可能需要多路径
            relay_connections[src].append(peer)
        else:
            # 直接连接，保持不变
            multipath_peers.append(peer)

    # 为每个客户端添加到所有中继的连接
    relays = ['D', 'H']  # 硬编码中继节点

    for src, existing_connections in relay_connections.items():
        connected_relays = {conn['to'] for conn in existing_connections}

        for relay in relays:
            if relay not in connected_relays:
                # 添加到这个中继的备用连接
                base_conn = existing_connections[0] if existing_connections else None
                if base_conn:
                    backup_conn = base_conn.copy()
                    backup_conn['to'] = relay
                    backup_conn['priority'] = 2  # 备用路由
                    multipath_peers.append(backup_conn)

        # 添加现有连接，设置优先级
        for i, conn in enumerate(existing_connections):
            conn['priority'] = 1  # 主路由
            multipath_peers.append(conn)

    return {'peers': multipath_peers}


if __name__ == "__main__":
    # 测试智能配置构建
    configs = build_smart_peer_configs(
        "examples/nodes_mesh_relay.json",
        "examples/topology_multipath.json",
        enable_multipath=True
    )

    # 生成路由脚本示例
    for node_name, peer_list in configs.items():
        if node_name == 'A':  # 只为节点A生成示例
            script = generate_route_script(node_name, peer_list)
            print(f"Route optimization script for {node_name}:")
            print(script)
            break
