"""
Unified validation module for configuration files
"""

from typing import Dict, List, Any, Tuple
from .file_utils import load_config
from .data_utils import validate_schema
from .logger import get_logger


def validate_and_load_config(nodes_file: str, topology_file: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Unified validation and loading pipeline for configuration files.
    
    Args:
        nodes_file: Path to nodes configuration file
        topology_file: Path to topology configuration file
        
    Returns:
        Tuple of (nodes, peers) after validation
        
    Raises:
        ValueError: If validation fails
    """
    logger = get_logger()
    logger.info("开始统一配置验证和加载")
    
    # Step 1: Load raw configuration data
    logger.info(f"加载节点配置文件: {nodes_file}")
    nodes_data = load_config(nodes_file)
    
    logger.info(f"加载拓扑配置文件: {topology_file}")
    topology_data = load_config(topology_file)
    
    # Step 2: Schema validation
    logger.info("执行 JSON Schema 验证")
    validate_schema(nodes_data, "nodes.schema.json")
    validate_schema(topology_data, "topology.schema.json")
    
    # Extract nodes and peers
    nodes = nodes_data.get('nodes', [])
    peers = topology_data.get('peers', [])
    
    logger.info(f"成功加载 {len(nodes)} 个节点配置")
    logger.info(f"成功加载 {len(peers)} 个对等连接配置")
    
    # Step 3: Business logic validation
    logger.info("执行业务逻辑验证")
    validate_business_logic(nodes, peers)
    
    logger.info("配置验证和加载完成")
    return nodes, peers


def validate_business_logic(nodes: List[Dict[str, Any]], peers: List[Dict[str, Any]]) -> bool:
    """
    Validate business logic for nodes and peers configuration.
    
    Args:
        nodes: List of node configurations
        peers: List of peer connections
        
    Returns:
        True if validation passes
        
    Raises:
        ValueError: If validation fails
    """
    logger = get_logger()
    
    # Create node name lookup
    node_names = {node['name'] for node in nodes}
    
    # Validate all nodes have unique names
    if len(node_names) != len(nodes):
        raise ValueError("节点名称必须唯一")
    
    # Validate all peer references exist
    for peer in peers:
        from_node = peer.get('from')
        to_node = peer.get('to')
        
        if from_node not in node_names:
            raise ValueError(f"对等连接引用了不存在的节点: {from_node}")
        
        if to_node not in node_names:
            raise ValueError(f"对等连接引用了不存在的节点: {to_node}")
        
        if from_node == to_node:
            raise ValueError(f"节点不能连接到自己: {from_node}")
    
    # Validate WireGuard IPs
    wireguard_ips = set()
    for node in nodes:
        wg_ip = node.get('wireguard_ip')
        if wg_ip:
            # Extract IP without CIDR
            ip_addr = wg_ip.split('/')[0]
            if ip_addr in wireguard_ips:
                raise ValueError(f"WireGuard IP 地址重复: {ip_addr}")
            wireguard_ips.add(ip_addr)
    
    # Validate endpoints format in peers
    for peer in peers:
        endpoint = peer.get('endpoint')
        if endpoint:
            # Just validate it's a valid endpoint format (host:port)
            if ':' not in endpoint:
                raise ValueError(f"端点格式无效，应为 host:port 格式: {endpoint}")
    
    logger.info("业务逻辑验证通过")
    return True


def validate_node_connectivity(nodes: List[Dict[str, Any]], peers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate and analyze network connectivity.
    
    Args:
        nodes: List of node configurations
        peers: List of peer connections
        
    Returns:
        Dictionary with connectivity analysis
    """
    logger = get_logger()
    logger.info("分析网络连通性")
    
    # Build adjacency list
    adjacency = {node['name']: set() for node in nodes}
    
    for peer in peers:
        adjacency[peer['from']].add(peer['to'])
        adjacency[peer['to']].add(peer['from'])
    
    # Find isolated nodes
    isolated_nodes = [node for node, neighbors in adjacency.items() if not neighbors]
    
    # Check if network is fully connected (using BFS)
    if nodes and not isolated_nodes:
        visited = set()
        queue = [nodes[0]['name']]
        visited.add(nodes[0]['name'])
        
        while queue:
            current = queue.pop(0)
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        is_connected = len(visited) == len(nodes)
    else:
        is_connected = False
    
    analysis = {
        'is_connected': is_connected,
        'isolated_nodes': isolated_nodes,
        'node_count': len(nodes),
        'edge_count': len(peers),
        'average_degree': sum(len(neighbors) for neighbors in adjacency.values()) / len(nodes) if nodes else 0
    }
    
    logger.info(f"连通性分析完成: {analysis}")
    return analysis