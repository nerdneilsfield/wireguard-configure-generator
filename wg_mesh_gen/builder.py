"""
WireGuard configuration builder
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from .validator import validate_and_load_config
from .crypto import generate_keypair, generate_preshared_key
from .simple_storage import SimpleKeyStorage
from .logger import get_logger
from .string_utils import mask_sensitive_info


def build_from_data(nodes_data: Dict[str, Any],
                   topology_data: Dict[str, Any],
                   output_dir: str = "out",
                   auto_generate_keys: bool = True,
                   db_path: str = "wg_keys.json") -> Dict[str, Any]:
    """
    Build WireGuard peer configurations from data dictionaries.
    
    Args:
        nodes_data: Nodes configuration data
        topology_data: Topology configuration data
        output_dir: Output directory for configuration files
        auto_generate_keys: Whether to auto-generate missing keys
        db_path: Path to key storage database
        
    Returns:
        Dictionary containing build results
    """
    logger = get_logger()
    logger.info("开始从数据构建WireGuard配置")
    
    # Extract nodes and peers
    nodes = nodes_data.get('nodes', [])
    peers = topology_data.get('peers', [])
    
    # Validate the data
    from .validator import validate_business_logic
    validate_business_logic(nodes, peers)
    
    # Use the common build logic
    return _build_configs(nodes, peers, output_dir, auto_generate_keys, db_path)


def build_peer_configs(nodes_file: str,
                      topology_file: str,
                      output_dir: str = "out",
                      auto_generate_keys: bool = True,
                      db_path: str = "wg_keys.json") -> Dict[str, Any]:
    """
    Build WireGuard peer configurations.

    Args:
        nodes_file: Path to nodes configuration file
        topology_file: Path to topology configuration file
        output_dir: Output directory for configuration files
        auto_generate_keys: Whether to auto-generate missing keys
        db_path: Path to key storage database

    Returns:
        Dictionary containing build results
    """
    logger = get_logger()
    logger.info("开始构建WireGuard配置")

    # Load and validate configurations in one step
    nodes, peers = validate_and_load_config(nodes_file, topology_file)
    
    # Use common build logic
    return _build_configs(nodes, peers, output_dir, auto_generate_keys, db_path)


def _build_configs(nodes: List[Dict[str, Any]], peers: List[Dict[str, Any]],
                  output_dir: str, auto_generate_keys: bool,
                  db_path: str) -> Dict[str, Any]:
    """Common configuration building logic."""
    logger = get_logger()
    
    # Initialize key storage
    key_storage = SimpleKeyStorage(db_path)
    try:
        # Generate or load keys for all nodes
        for node in nodes:
            node_name = node['name']

            # Check if keys already exist
            existing_keys = key_storage.get_keypair(node_name)

            if existing_keys:
                logger.debug(f"使用已存在的密钥对: {node_name}")
                private_key, public_key = existing_keys
                node['private_key'] = private_key
                node['public_key'] = public_key
            elif auto_generate_keys:
                logger.info(f"为节点 {node_name} 生成新密钥对")
                private_key, public_key = generate_keypair()

                # Store keys
                key_storage.store_keypair(node_name, private_key, public_key)

                node['private_key'] = private_key
                node['public_key'] = public_key

                logger.debug(f"节点 {node_name} 密钥生成完成")
                logger.debug(f"  公钥: {mask_sensitive_info(public_key)}")
            else:
                logger.error(f"节点 {node_name} 缺少密钥且未启用自动生成")
                raise ValueError(f"Node {node_name} missing keys and auto-generation disabled")

        # Build peer map for efficient lookup
        peer_map = _build_peer_map(peers)
        
        # Build peer configurations
        configs = {}

        for node in nodes:
            node_name = node['name']
            config = _build_node_config_optimized(node, nodes, peer_map)
            configs[node_name] = config

            logger.debug(f"节点 {node_name} 配置构建完成")

        logger.info(f"成功构建 {len(configs)} 个节点配置")

        return {
            'configs': configs,
            'nodes': nodes,
            'peers': peers,
            'output_dir': output_dir
        }
    finally:
        key_storage.close()


def _build_node_config(node: Dict[str, Any],
                      all_nodes: List[Dict[str, Any]],
                      peers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build configuration for a single node.

    Args:
        node: Node configuration
        all_nodes: All node configurations
        peers: All peer connections

    Returns:
        Node configuration with peer information
    """
    node_name = node['name']

    # Create node lookup
    node_lookup = {n['name']: n for n in all_nodes}

    # Find all peers for this node
    node_peers = []

    for peer in peers:
        if peer['from'] == node_name:
            # This node connects to peer['to']
            target_node = node_lookup[peer['to']]
            peer_config = {
                'name': target_node['name'],
                'public_key': target_node['public_key'],
                'endpoint': peer.get('endpoint'),
                'allowed_ips': peer.get('allowed_ips', []),
                'persistent_keepalive': peer.get('persistent_keepalive')
            }
            node_peers.append(peer_config)

        elif peer['to'] == node_name:
            # peer['from'] connects to this node
            source_node = node_lookup[peer['from']]
            peer_config = {
                'name': source_node['name'],
                'public_key': source_node['public_key'],
                'endpoint': None,  # Incoming connection
                'allowed_ips': peer.get('allowed_ips', []),
                'persistent_keepalive': peer.get('persistent_keepalive')
            }
            node_peers.append(peer_config)

    # Build final configuration
    config = {
        'interface': {
            'private_key': node['private_key'],
            'address': node.get('wireguard_ip'),
            'listen_port': node.get('listen_port'),
            'dns': node.get('dns'),
            'mtu': node.get('mtu'),
            'post_up': node.get('post_up'),
            'post_down': node.get('post_down')
        },
        'peers': node_peers
    }

    return config


def _build_peer_map(peers: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Build a peer map for efficient lookup, avoiding duplicates.
    
    IMPORTANT: This function only creates peer entries as explicitly defined in the topology.
    It does NOT automatically create bidirectional entries because AllowedIPs have different
    meanings in each direction.
    
    Args:
        peers: List of peer connections
        
    Returns:
        Dictionary mapping node names to their peer connections
    """
    peer_map = defaultdict(lambda: defaultdict(dict))
    
    for peer in peers:
        from_node = peer['from']
        to_node = peer['to']
        
        # Only create peer entry for the 'from' node
        # This represents an outgoing connection from 'from_node' to 'to_node'
        if to_node not in peer_map[from_node]:
            peer_map[from_node][to_node] = {
                'node': to_node,
                'direction': 'outgoing',
                'endpoint': peer.get('endpoint'),
                'allowed_ips': peer.get('allowed_ips', []),
                'persistent_keepalive': peer.get('persistent_keepalive')
            }
        else:
            # Merge allowed_ips if peer already exists
            existing = peer_map[from_node][to_node]
            existing_ips = set(existing.get('allowed_ips', []))
            new_ips = set(peer.get('allowed_ips', []))
            existing['allowed_ips'] = list(existing_ips | new_ips)
            # Update other fields if they're not None/empty in the new peer
            if peer.get('persistent_keepalive'):
                existing['persistent_keepalive'] = peer.get('persistent_keepalive')
        
        # NOTE: We do NOT automatically create a reverse entry for 'to_node'
        # If bidirectional communication is needed, it must be explicitly defined
        # in the topology with appropriate allowed_ips for each direction
    
    # Convert to the expected format
    result = {}
    for node, peers_dict in peer_map.items():
        result[node] = list(peers_dict.values())
    
    return result


def _build_node_config_optimized(node: Dict[str, Any],
                                all_nodes: List[Dict[str, Any]],
                                peer_map: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Build configuration for a single node using optimized peer map.
    
    Args:
        node: Node configuration
        all_nodes: All node configurations
        peer_map: Pre-built bidirectional peer map
        
    Returns:
        Node configuration with peer information
    """
    node_name = node['name']
    
    # Create node lookup
    node_lookup = {n['name']: n for n in all_nodes}
    
    # Get peers from map
    node_peers = []
    peer_connections = peer_map.get(node_name, [])
    
    for peer_conn in peer_connections:
        peer_node = node_lookup[peer_conn['node']]
        
        # Determine endpoint
        endpoint = None
        if peer_conn['direction'] == 'outgoing' and peer_node.get('endpoints'):
            # For outgoing connections, use the first endpoint from the target node
            endpoint = peer_node['endpoints'][0] if peer_node['endpoints'] else None
        else:
            # For incoming connections or if no endpoint specified on peer
            endpoint = peer_conn.get('endpoint')
        
        peer_config = {
            'name': peer_node['name'],
            'public_key': peer_node['public_key'],
            'endpoint': endpoint,
            'allowed_ips': peer_conn.get('allowed_ips', []),
            'persistent_keepalive': peer_conn.get('persistent_keepalive')
        }
        node_peers.append(peer_config)
    
    # Extract listen_port from endpoints if not explicitly set
    listen_port = node.get('listen_port')
    if not listen_port and node.get('endpoints'):
        # Try to extract port from first endpoint
        first_endpoint = node['endpoints'][0]
        if ':' in first_endpoint:
            try:
                listen_port = int(first_endpoint.split(':')[-1])
            except ValueError:
                pass
    
    # Build final configuration
    config = {
        'interface': {
            'private_key': node['private_key'],
            'address': node.get('wireguard_ip'),
            'listen_port': listen_port,
            'dns': node.get('dns'),
            'mtu': node.get('mtu'),
            'post_up': node.get('post_up'),
            'post_down': node.get('post_down')
        },
        'peers': node_peers
    }
    
    return config
